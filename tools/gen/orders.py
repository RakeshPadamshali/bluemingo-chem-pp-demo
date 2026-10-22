"""Demand: the order book for the detailed horizon, and the twelve-month demand plan for S&OP.

The order book is CALIBRATED: total demand is scaled so the plant's binding equipment class is loaded to
config.DEMAND_LOAD once an allowance for cleaning is included. A demo where nothing binds has nothing to show, and a demo
where everything is late is not believed — tools/verify_tension.py holds the band.
"""
import math

from . import config as CFG
from .common import R, ASOF, BASE, END, DAY0, at, iso, pick, rint, between, months_ahead
from .catalogue import UNIT
from .customers import customers_for

CLASS_BY_ID = {c["id"]: c for c in CFG.ORDER_CLASSES}
# priority order for trimming the book: the lower the rank, the more committed the class
CLASS_RANK = {c["id"]: i for i, c in enumerate(CFG.ORDER_CLASSES)}
# An allowance per OPERATION for the cleaning that unit will also have to absorb (hours). These are not guesses: they are
# measured from the chemical-aware plan with tools/calibrate.js, because cleaning is the single biggest claim on this
# plant's time -- a quarter of it. Under-booking it is how an order book ends up 40% larger than the plant can serve.
CLEAN_ALLOW_H = {"REACTOR": 5.3, "ISOLATION": 5.0, "DRYER": 5.2, "MILL": 0.5, "PACK": 1.0}


def class_hours(products):
    """Hours one batch of each product occupies, per equipment class, including a cleaning allowance."""
    out = {}
    for p in products:
        per = {}
        for o in p["ops"]:
            per[o["cls"]] = per.get(o["cls"], 0) + o["hours"] + CLEAN_ALLOW_H.get(o["cls"], 0)
        out[p["id"]] = per
    return out


def available_hours(days, friction=True):
    """Hours a window can REALISE, per equipment class: nameplate, less block time, less scheduling friction."""
    f = CFG.SCHEDULE_FRICTION if friction else 1.0
    out = {}
    for u in CFG.UNITS:
        out[u["cls"]] = out.get(u["cls"], 0) + days * 24.0 * CFG.UNIT_UPTIME * f
    return out


def build_orders(customers, products):
    prod = {p["id"]: p for p in products}
    sellable = [p for p in products if p.get("sell", True)]
    ch = class_hours(products)

    # ---- raw order book: ids and dates are fixed, quantities are scaled afterwards ----
    span_from, span_to = -CFG.HISTORY_DAYS - 4, CFG.FORWARD_DAYS + 16
    orders, lines, ln = [], [], 0
    for i in range(CFG.ORDERS_TARGET):
        cls = _class_pick()
        cust = _customer_for_class(customers, cls)
        if not cust:
            continue
        oid = "SO-%05d" % (41200 + i * 3)
        due_off = rint(span_from + 6, span_to)
        lead = rint(18, 70) if cls.startswith("EXPORT") else rint(10, 42)
        od = at(due_off - lead, rint(8, 17))
        o = dict(id=oid, customerId=cust["id"], cls=cls, orderDate=iso(od),
                 po="PO/%s/%04d" % (cust["id"][1:], 1000 + i), siteId="UNIT-2")
        orders.append(o)
        for _ in range(rint(*CFG.LINES_PER_ORDER)):
            pid = pick([p for p in cust["buys"]] or [p["id"] for p in sellable])
            p = prod[pid]
            ln += 1
            qty = round(between(*CFG.LINE_QTY_KG) / 10.0) * 10
            if p["priceKg"] > 50000:            # high-potency and filed APIs are ordered in far smaller quantities
                qty = max(20, round(qty / 40.0 / 5) * 5)
            elif p["priceKg"] > 5000:
                qty = max(60, round(qty / 6.0 / 10) * 10)
            tight = cust["regulated"] and R.random() < 0.5
            lines.append(dict(id="%s/%02d" % (oid, ln % 100), orderId=oid, productId=pid, qty=qty,
                              due=iso(at(due_off, rint(6, 20))), cls=cls, customerId=cust["id"],
                              priceKg=p["priceKg"], marginKg=p["marginKg"], siteId="UNIT-2",
                              minLifeM=cust["minLifeMonths"],
                              assayMin=round(p["assayMean"] - (0.15 if tight else 0.55), 2),
                              # a tight limit has to be one a BLEND can meet — tighter than most single lots, but reachable by mixing a clean
                              # lot with a marginal one, which is the whole purpose of blending
                              impMax=round(p["impMax"] * (0.86 if tight else 1.0), 3),
                              psdMax=int(round(p["psdMean"] * (1.12 if tight else 1.35))),
                              tightSpec=tight, coa=cust["coaRequired"]))

    # ---- calibrate: scale every quantity so the binding class is loaded to DEMAND_LOAD ----
    # Quantities are rounded to a sensible step and floored at one tenth of a batch, so a single multiplier does not land
    # on the target. Bisect the multiplier instead: cheap, exact, and the result is reproducible.
    days = CFG.HISTORY_DAYS + CFG.FORWARD_DAYS + 16 + 4
    avail = available_hours(days)
    q0 = {l["id"]: l["qty"] for l in lines}

    def apply(k):
        for l in lines:
            p = prod[l["productId"]]
            step = 5 if p["priceKg"] > 50000 else 10
            # A line consumes a WHOLE batch however small it is, so a floor of a tenth of a batch let the calibration hit
            # its target on batch count while the tonnage shrank away — a 17 t order book that cost 280 batches, against
            # a plant making 65 t. Nobody orders a tenth of a batch of an API.
            floor = max(step, int(round(p["batchKg"] * CFG.MIN_LINE_BATCHES / step) * step))
            l["qty"] = max(floor, int(round(q0[l["id"]] * k / step) * step))
        need = _class_need(lines, prod, ch)
        return max(need.get(c, 0) / avail[c] for c in avail if avail[c]), need

    lo, hi = 0.02, 6.0
    for _ in range(44):
        mid = (lo + hi) / 2
        r, _n = apply(mid)
        if r > CFG.DEMAND_LOAD:
            hi = mid
        else:
            lo = mid
    scale, (ratio, need) = lo, apply(lo)

    # Scaling alone cannot go below the floor: every line costs a whole batch, so a book of N lines costs at least N
    # batches whatever the quantities. Past that point the book itself is too big, and the honest fix is to carry fewer
    # lines — the open domestic ones first, then the furthest out, which is the order a planner would drop them in.
    dropped = 0
    if ratio > CFG.DEMAND_LOAD + 0.01:
        order = sorted(lines, key=lambda l: (-CLASS_RANK.get(l["cls"], 9), l["due"]), reverse=True)
        for l in order:
            if ratio <= CFG.DEMAND_LOAD:
                break
            lines.remove(l)
            dropped += 1
            ratio, need = apply(lo)
        # with fewer lines there is room to grow the rest back towards the target
        lo2, hi2 = lo, 6.0
        for _ in range(30):
            mid = (lo2 + hi2) / 2
            r, _n = apply(mid)
            if r > CFG.DEMAND_LOAD:
                hi2 = mid
            else:
                lo2 = mid
        scale, (ratio, need) = lo2, apply(lo2)

    load = {k: round(need.get(k, 0) / avail[k], 3) for k in avail if avail[k]}
    binding = max(load, key=lambda k: load[k])

    # drop orders whose every line vanished in the scaling
    keep = {l["orderId"] for l in lines}
    orders = [o for o in orders if o["id"] in keep]

    stats = dict(orders=len(orders), lines=len(lines), linesDropped=dropped, kg=int(sum(l["qty"] for l in lines)),
                 load=load, binding=binding, bindingLoad=load[binding], scale=round(scale, 4),
                 byClass={c["id"]: sum(1 for l in lines if l["cls"] == c["id"]) for c in CFG.ORDER_CLASSES},
                 value=int(sum(l["qty"] * l["priceKg"] for l in lines)),
                 batches=int(sum(math.ceil(l["qty"] / prod[l["productId"]]["batchKg"]) for l in lines)))
    return orders, lines, stats


def _class_need(lines, prod, ch):
    need = {}
    for l in lines:
        p = prod[l["productId"]]
        nb = math.ceil(l["qty"] / p["batchKg"])
        for cls, h in ch[p["id"]].items():
            need[cls] = need.get(cls, 0) + nb * h
    return need


def _class_pick():
    return pick([c["id"] for c in CFG.ORDER_CLASSES for _ in range(int(c["share"] * 100))])


def _customer_for_class(customers, cls):
    want_reg = cls == "EXPORT_REG"
    pool = [c for c in customers if c["regulated"] == want_reg and c["buys"]]
    return pick(pool) if pool else None


# ---------------------------------------------------------------------------------------------------- S&OP demand plan
def build_demand_plan(products, lines):
    """Twelve monthly buckets per product, with a seasonal peak, a trough and the annual shutdown month.

    Months one to three are anchored on the order book that the detailed plan actually works from, so the two horizons
    reconcile (tools/audit.py asserts it); months four to twelve carry the season.
    """
    prod = {p["id"]: p for p in products}
    # base monthly rate from the order book, per product (kg per 30 days)
    span = CFG.HISTORY_DAYS + CFG.FORWARD_DAYS + 20
    base = {}
    for l in lines:
        base[l["productId"]] = base.get(l["productId"], 0) + l["qty"]
    for k in base:
        base[k] = base[k] / span * 30.0

    rows, sd_month = [], None
    for n in range(CFG.SOP_MONTHS):
        d = months_ahead(n)
        mkey = "%04d-%02d" % (d.year, d.month)
        lift = 1.0
        if d.month in CFG.SEASON["peakMonths"]:
            lift += CFG.SEASON["peakLift"]
        if d.month in CFG.SEASON["troughMonths"]:
            lift -= CFG.SEASON["troughDrop"]
        shut = n == CFG.SEASON["shutdownMonthOffset"]
        if shut:
            sd_month = mkey
        for pid, kg in sorted(base.items()):
            if kg <= 0:
                continue
            noise = 1.0 + between(-0.07, 0.07)
            rows.append(dict(id="%s|%s" % (mkey, pid), month=mkey, monthNo=n + 1, productId=pid,
                             kg=int(round(kg * lift * noise / 10.0) * 10),
                             peak=d.month in CFG.SEASON["peakMonths"], shutdown=shut,
                             priceKg=prod[pid]["priceKg"], marginKg=prod[pid]["marginKg"]))
    plan = dict(rows=rows, shutdownMonth=sd_month, shutdownDays=CFG.SEASON["shutdownDays"],
                months=[{"month": "%04d-%02d" % (months_ahead(n).year, months_ahead(n).month),
                         "label": months_ahead(n).strftime("%b %Y"), "no": n + 1,
                         "shutdown": n == CFG.SEASON["shutdownMonthOffset"]} for n in range(CFG.SOP_MONTHS)])
    return plan
