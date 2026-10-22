"""What actually happened in the frozen history, and the anchors the scenario launcher needs.

The history is simulated by the engine, not written out batch by batch: this module supplies the unplanned breakdowns and
the deterministic rules (which share of batches assays low, which fail spec, how long QC takes). Each scenario anchor is
CHOSEN FROM THE GENERATED DATA, so a card can never point at something that is not there — the generator asserts every
anchor resolves before it writes the file.
"""
from . import config as CFG
from .common import R, at, iso, pick, rint, between

UNIT_IDS = [u["id"] for u in CFG.UNITS]


def build_events():
    months = (CFG.HISTORY_DAYS + CFG.FORWARD_DAYS) / 30.0
    n = int(round(CFG.EXEC["breakdownsPerMonth"] * months))
    bd = []
    for i in range(n):
        u = pick(UNIT_IDS)
        d = rint(-CFG.HISTORY_DAYS + 1, CFG.FORWARD_DAYS - 2)
        bd.append(dict(id="BD-%04d" % (120 + i * 3), unitId=u, start=iso(at(d, rint(0, 23), rint(0, 59))),
                       durMin=int(between(*CFG.EXEC["breakdownHours"]) * 60),
                       reason=pick(["Agitator seal failure", "Jacket leak", "Vacuum pump trip", "Instrument air loss",
                                    "Motor overload", "Valve actuator failure", "Utility interruption"]),
                       category=pick(["Mechanical", "Instrumentation", "Utility", "Electrical"])))
    bd.sort(key=lambda x: (x["start"], x["id"]))
    return dict(breakdowns=bd,
                yieldRule=dict(shortShare=CFG.EXEC["yieldShortShare"], offSpecShare=CFG.EXEC["offSpecShare"]),
                qcRule=dict(minDays=CFG.EXEC["qcDays"][0], maxDays=CFG.EXEC["qcDays"][1]),
                utilityRule=dict(tripShare=CFG.EXEC["utilityTripShare"]),
                delayReasons=CFG.EXEC["delayReasons"])


def build_scenarios(products, orders, lines, customers, matrix, tanks, deliveries, lots, demand_plan, binding):
    """Thirteen cards plus three follow-ons. Every id here is looked up in the generated data."""
    P = {p["id"]: p for p in products}
    cust = {c["id"]: c for c in customers}
    fwd = [l for l in lines if l["due"] > iso(at(0))]

    def line_for(pid, cls=None, tight=None):
        pool = [l for l in fwd if l["productId"] == pid and (cls is None or l["cls"] == cls) and (tight is None or l["tightSpec"] == tight)]
        pool = pool or [l for l in fwd if l["productId"] == pid]
        pool = pool or [l for l in lines if l["productId"] == pid]
        pool.sort(key=lambda l: (l["due"], l["id"]))
        return pool[0] if pool else None

    # ---- C1 cleaning matrix: the biggest colour drop that still has a cell (a boil-out the plan must pay for) ----
    boil = [r for r in matrix if r["grade"] == "BOILOUT" and r["train"] == "A"]
    boil.sort(key=lambda r: (-(P[r["frm"]]["colour"] - P[r["to"]]["colour"]), r["frm"], r["to"]))
    c1 = boil[0]
    # a forbidden pair to show beside it
    forb = [r for r in matrix if r["grade"] == "FORBIDDEN" and r["train"] == "A"]
    forb.sort(key=lambda r: (r["frm"], r["to"]))

    # ---- C2 yield: the product with the widest yield spread that carries committed work ----
    cand = sorted([p for p in products if line_for(p["id"])], key=lambda p: (-p["yieldSd"], p["id"]))
    c2p = cand[0]

    # ---- C3 hold window: the tightest maximum lag in the plant ----
    tight_hold = None
    for p in products:
        for o in p["ops"][:-1]:
            if tight_hold is None or o["maxLagH"] < tight_hold[1]["maxLagH"]:
                tight_hold = (p, o)
    c3p, c3op = tight_hold

    # ---- C4 utilities: the three products that draw the most brine at their peak ----
    def peak(p, util):
        return max((s["draw"].get(util, 0) for o in p["ops"] for s in o["duty"]), default=0)
    brine = sorted(products, key=lambda p: (-peak(p, "BRINE"), p["id"]))[:3]

    # ---- C5 effluent: the two heaviest effluent producers ----
    effl = sorted(products, key=lambda p: (-p["efflM3"], p["id"]))[:2]

    # ---- C6 licence: the flammable delivery that lands when the licence has least headroom ----
    flam = [d for d in deliveries if d["haz"] == "FLAM" and d["eta"] > iso(at(2))]
    c6 = flam[len(flam) // 6] if flam else deliveries[0]

    # ---- C7 blending: a tight-spec regulated line big enough to need more than one batch ----
    tights = [l for l in fwd if l["tightSpec"] and l["qty"] > P[l["productId"]]["batchKg"] * 1.2]
    tights.sort(key=lambda l: (l["due"], l["id"]))
    c7 = tights[0] if tights else line_for(c2p["id"])

    # ---- C8 / C9 mix and margin ----
    # The deck's claim only bites if the ranking actually REVERSES, and it reverses on hours of the BOTTLENECK, not on
    # total cycle time — a product can be slow overall and still barely touch the constraint. Search for a real pair.
    def bh(p):
        return sum(o["hours"] for o in p["ops"] if o["cls"] == binding)

    def per_t(p):
        return p["marginKg"] * 1000.0

    def per_bh(p):
        return p["marginKg"] * p["batchKg"] / bh(p) if bh(p) else None

    users = [p for p in products if bh(p) > 0]
    offbn = [p for p in products if bh(p) == 0]       # never touches the constraint at all — the sharpest form of the point
    by_t = sorted(users, key=lambda p: (-per_t(p), p["id"]))
    by_h = sorted(users, key=lambda p: (-per_bh(p), p["id"]))
    # A flip of 1% is a rounding error, not an argument. Take the pair whose reversal is largest on BOTH measures —
    # rank by the weaker of the two ratios, so neither gap can be marginal.
    best, flip = 0.0, None
    for a in users:
        for b in users:
            if a["id"] == b["id"] or per_t(a) <= per_t(b) or per_bh(b) <= per_bh(a):
                continue
            strength = min(per_t(a) / per_t(b), per_bh(b) / per_bh(a))
            if strength > best or (abs(strength - best) < 1e-9 and flip and (a["id"], b["id"]) < (flip[0]["id"], flip[1]["id"])):
                best, flip = strength, (a, b)
    flip = flip or (by_t[0], by_h[0])

    # ---- C10 co-product ----
    cop = [p for p in products if p.get("coprod")]
    c10p = cop[0] if cop else products[0]

    # ---- C11 shelf life: the shortest-life lot, and a regulated customer who cannot take it ----
    short = sorted([x for x in lots if x["lifeLeftM"] > 0], key=lambda x: (x["lifeLeftM"], x["id"]))[0]
    picky = sorted([c for c in customers if c["regulated"] and short["productId"] in c["buys"]],
                   key=lambda c: (-c["minLifeMonths"], c["id"]))
    c11c = picky[0] if picky else sorted([c for c in customers if c["regulated"]], key=lambda c: -c["minLifeMonths"])[0]

    # ---- C12 approved sites: a regulated customer qualified at this plant only ----
    only = [c for c in customers if c["regulated"] and c["sites"] == ["UNIT-2"] and c["buys"]]
    c12c = only[0] if only else [c for c in customers if c["regulated"]][0]
    c12l = line_for(c12c["buys"][0], "EXPORT_REG") or line_for(c12c["buys"][0])

    # pack postponement only means something for a product that HAS a pack operation
    packable = [p for p in products if any(o["cls"] == "PACK" for o in p["ops"])]

    # ---- C13 season and shutdown ----
    sd = demand_plan["shutdownMonth"]

    S = {
        "C1": dict(nuance="P1", title="Deep colour, then a pale product", frm=c1["frm"], to=c1["to"],
                   grade=c1["grade"], hours=c1["hours"], why=c1["why"],
                   forbidden=[dict(frm=r["frm"], to=r["to"], why=r["why"]) for r in forb[:3]],
                   lineId=(line_for(c1["to"]) or {}).get("id")),
        "C2": dict(nuance="P2", title="The campaign that ends short", productId=c2p["id"],
                   yieldMean=c2p["yieldMean"], yieldSd=c2p["yieldSd"], shortTo=round(c2p["yieldMean"] - 2.1 * c2p["yieldSd"], 3),
                   lineId=(line_for(c2p["id"]) or {}).get("id")),
        "C2b": dict(nuance="S3", title="Cover the shortfall: make, buy or toll", productId=c2p["id"]),
        "C3": dict(nuance="P3", title="The intermediate that spoils", productId=c3p["id"], op=c3op["op"],
                   maxLagH=c3op["maxLagH"], tightenTo=max(3, int(c3op["maxLagH"] * 0.55)),
                   lineId=(line_for(c3p["id"]) or {}).get("id")),
        "C4": dict(nuance="P4", title="Three exotherms in one hour", utility="BRINE",
                   productIds=[p["id"] for p in brine], derateTo=CFG.UTILITIES[1]["derate"]["cap"]),
        "C5": dict(nuance="P5", title="Two heavy-effluent campaigns back to back",
                   productIds=[p["id"] for p in effl], waste="ETP", cutTo=round(CFG.WASTE[0]["cap"] * 0.78)),
        "C6": dict(nuance="P6", title="A delivery that breaches the licence", deliveryId=c6["id"],
                   tankId=c6["tankId"], haz=c6["haz"], kl=c6["kl"],
                   licenceCutTo=round(CFG.HAZARD_CLASSES[0]["licensedKL"] * 0.82)),
        "C7": dict(nuance="P7", title="Three batches blended into one lot", lineId=c7["id"],
                   productId=c7["productId"], assayMin=c7["assayMin"], impMax=c7["impMax"]),
        "C8": dict(nuance="S1", title="Same plant, a different mix",
                   fromProduct=effl[0]["id"], toProduct=by_h[0]["id"], shift=0.35, binding=binding),
        "C9": dict(nuance="S2", title="Margin per tonne against margin per bottleneck hour",
                   perTonneWinner=flip[0]["id"], perHourWinner=flip[1]["id"], binding=binding,
                   perTonne={p["id"]: round(per_t(p)) for p in users}, perBhHours={p["id"]: bh(p) for p in users},
                   flipStrength=round(best, 3),
                   offBottleneck=[p["id"] for p in offbn]),
        "C10": dict(nuance="S4", title="A co-product that fills the tank", productId=c10p["id"],
                    coprodId=c10p["coprod"]["id"], ratio=c10p["coprod"]["ratio"],
                    capCutTo=round(CFG.HAZARD_CLASSES[3]["licensedKL"] * 0.55)),
        "C11": dict(nuance="S6", title="A lot too old for this customer", lotId=short["id"],
                    productId=short["productId"], lifeLeftM=short["lifeLeftM"],
                    customerId=c11c["id"], minLifeM=c11c["minLifeMonths"]),
        "C12": dict(nuance="S7", title="A site the customer has not approved", customerId=c12c["id"],
                    lineId=(c12l or {}).get("id"), productId=c12c["buys"][0],
                    sites=c12c["sites"], qualWeeks=c12c["qualWeeks"]),
        "C13": dict(nuance="S8", title="A pre-build before the shutdown", shutdownMonth=sd,
                    shutdownDays=CFG.SEASON["shutdownDays"]),
        "C13b": dict(nuance="S5", title="Book the raw-material block", rmId="RM-03"),
        "C13c": dict(nuance="S9", title="Hold it as bulk, pack it late", productId=packable[0]["id"] if packable else by_h[0]["id"]),
    }
    return S
