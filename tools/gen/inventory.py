"""Opening stock: finished lots, the tank farm, tanker deliveries and the key raw materials.

Three of the deck's nuances live on this data. Lots carry an assay, an impurity and a PSD, so allocation is a spec
decision (P7) and a shelf-life decision (S6); tanks carry a hazard class, so a delivery can breach a LICENCE rather than
a tank (P6); raw materials come in minimum tanker blocks with a contract price that resets on a lag (S5).
"""
import math

from . import config as CFG
from .common import R, ASOF, BASE, DAY0, at, iso, pick, rint, between, rnd

SOLV = {s["id"]: s for s in CFG.SOLVENTS}


def build_opening_lots(products):
    """Finished lots on hand at the start of history — the pool the first allocations draw from.

    Deliberately uncomfortable: a few lots sit just inside spec, a few are close to their retest date, and one is
    already past the minimum remaining life every regulated customer asks for.
    """
    out, n = [], 0
    for p in products:
        if not p.get("sell", True):
            continue
        k = 2 if p["priceKg"] > 50000 else 3
        for j in range(k):
            n += 1
            # assay around the product mean; one lot per product is deliberately marginal
            marginal = j == 1
            assay = round(p["assayMean"] - (between(0.55, 0.95) if marginal else between(-0.20, 0.35)), 2)
            imp = round(p["impMax"] * (between(0.85, 1.02) if marginal else between(0.25, 0.75)), 3)
            psd = int(round(p["psdMean"] * between(0.88, 1.18)))
            made_off = -CFG.HISTORY_DAYS - rint(10, 240)
            made = at(made_off, rint(2, 20))
            retest_off = made_off + int(round(p["retestM"] * 30.4))
            age_m = (DAY0 - made).days / 30.4
            out.append(dict(id="L%05d" % (24000 + n * 7), productId=p["id"],
                            kg=int(round(p["batchKg"] * between(0.35, 1.0) / 5) * 5),
                            assay=assay, imp=imp, psd=psd,
                            madeAt=iso(made), retestAt=iso(at(retest_off, 0)),
                            lifeLeftM=round(max(0.0, p["retestM"] - age_m), 1),
                            released=True, opening=True, siteId="UNIT-2",
                            note="Opening stock at the start of history"))
    # make exactly one lot per family old enough to fail a regulated customer's minimum remaining life
    fam_of = {p["id"]: p["family"] for p in products}
    for fam in ("F1", "F2", "F3"):
        cand = [x for x in out if fam_of.get(x["productId"]) == fam]
        if cand:
            x = cand[0]
            x["lifeLeftM"] = round(between(4.0, 9.0), 1)
            x["retestAt"] = iso(at(int(round(x["lifeLeftM"] * 30.4)), 0))
            x["note"] = "Opening stock — short remaining life"
    return out


def build_tanks():
    """The tank farm. The ceiling that binds is the LICENCE per hazard class, not the steel."""
    out = []
    for s in CFG.SOLVENTS:
        out.append(dict(id=s["tank"], name="%s — %s" % (s["tank"], s["name"]), solventId=s["id"], bundId=s["bund"],
                        haz=s["haz"], capKL=s["capKL"], openKL=round(s["capKL"] * CFG.TANK_OPENING_SHARE, 1),
                        # a day tank is never sized to exactly one tanker: a full load has to fit into a tank that is not empty,
                        # or the delivery is refused for space every single time and the tank starves
                        tankerKL=min(s["tanker"], round(s["capKL"] * CFG.TANKER_MAX_SHARE, 1)),
                        priceKL=s["priceKL"], solvClass=s["cls"],
                        note="Day tank, %s service" % s["haz"].lower()))
    return out


def build_deliveries(tanks, products, lines):
    """Tanker deliveries, sized from the plant's own consumption rather than a guessed calendar.

    A tanker brings MAKE-UP: most solvent returns from the recovery train, so net draw is a fraction of the charge. Size
    the calendar to that net draw per tank and the farm balances by construction — too generous and every tank fills to
    the licensed ceiling and refuses the next tanker (which starves whichever tank actually needed it); too thin and the
    plan waits on solvent that was never ordered.

    One week is then deliberately crowded: four flammable tankers land together ahead of a campaign build-up, which is
    what takes the licence to within a few per cent of its ceiling — the point of nuance 6.
    """
    span = CFG.HISTORY_DAYS + CFG.FORWARD_DAYS + 20
    recov = (CFG.SOLVENT_RECOVERY["recoveryMin"] + CFG.SOLVENT_RECOVERY["recoveryMax"]) / 2.0
    makeup_share = 1.0 - recov
    prod = {p["id"]: p for p in products}

    # net kL a day each solvent actually loses, from the order book
    draw = {}
    for l in lines:
        p = prod[l["productId"]]
        nb = max(1.0, l["qty"] / float(p["batchKg"]))
        draw[p["solv"]] = draw.get(p["solv"], 0.0) + nb * p["solvKL"] * makeup_share
    for k in draw:
        draw[k] /= float(span)

    out, n = [], 0
    for t in tanks:
        per_day = draw.get(t["solventId"], 0.0)
        if per_day <= 1e-6:
            period = 45                                     # not consumed by anything: a top-up now and then
        else:
            period = t["tankerKL"] / (per_day * CFG.TANKER_COVER)   # a tanker every this many days
        period = int(max(6, min(45, round(period))))
        d = -CFG.HISTORY_DAYS + rint(1, period)
        while d < CFG.FORWARD_DAYS + 10:
            n += 1
            out.append(dict(id="TK-%05d" % (7100 + n * 3), tankId=t["id"], solventId=t["solventId"],
                            kl=t["tankerKL"], eta=iso(at(d, rint(6, 18))), haz=t["haz"], everyDays=period,
                            supplier=pick(["Arcadia Solvents", "Deccan Chem Logistics", "Harbourline Supply",
                                           "Satpura Chemicals", "Vindhya Petrochem"]),
                            priceKL=int(t["priceKL"] * between(0.94, 1.08))))
            d += period
    # the crowded week: pull the next flammable delivery of four different tanks onto the same two days
    wk = CFG.LICENCE_SQUEEZE_DAY
    flam = [t for t in tanks if t["haz"] == "FLAM"][:4]
    for i, t in enumerate(flam):
        cand = [d for d in out if d["tankId"] == t["id"] and d["eta"] > iso(at(wk - 25))]
        if cand:
            cand[0]["eta"] = iso(at(wk + (i % 2), 7 + i * 3))
            cand[0]["squeeze"] = True
    out.sort(key=lambda x: (x["eta"], x["id"]))
    return out


def build_raw_materials(products):
    """Key raw materials, in minimum tanker / drum blocks, with a contract price that resets on a lag."""
    names = [("RM-01", "Aniline", "kL", 24.0), ("RM-02", "Toluene feedstock", "kL", 25.0), ("RM-03", "Sodium nitrite", "t", 10.0),
             ("RM-04", "Catalyst (Pd/C 5%)", "kg", 25.0), ("RM-05", "Protected amine", "t", 2.0), ("RM-06", "Chiral auxiliary", "kg", 15.0),
             ("RM-07", "Caustic lye", "kL", 20.0), ("RM-08", "Acetic anhydride", "kL", 20.0)]
    out = []
    for i, (rid, nm, unit, block) in enumerate(names):
        price = int(between(28000, 420000))
        out.append(dict(id=rid, name=nm, unit=unit, minBlock=block, priceUnit=price,
                        leadDays=rint(18, 52), priceLagDays=CFG.RM_BLOCKS["priceLagDays"],
                        priceMove=round(between(-0.06, 0.19), 3),
                        onHand=round(block * between(0.6, 2.4), 1),
                        usedBy=sorted({p["id"] for p in R.sample(products, min(len(products), rint(2, 5)))}),
                        note="Minimum buy block %g %s; contract price resets %d days after the index moves"
                             % (block, unit, CFG.RM_BLOCKS["priceLagDays"])))
    return out


def build_sourcing_options(products):
    """Make, buy or toll for each intermediate — the recurring call of S&OP nuance 3."""
    out = []
    for p in products:
        if not (p.get("intermediate") or p["family"] in ("F1", "F2")):
            continue
        make = p["costKg"]
        out.append(dict(id=p["id"], productId=p["id"],
                        makeCostKg=make,
                        buyCostKg=int(round(make * (1 + CFG.SOURCING["buyPremium"]) / 5) * 5),
                        tollCostKg=int(round(make * (1 + CFG.SOURCING["tollPremium"]) / 5) * 5),
                        buyLeadDays=CFG.SOURCING["buyLeadDays"], tollLeadDays=CFG.SOURCING["tollLeadDays"],
                        tollSite="TOLL-A", buySupplier=pick(["Kalyani Fine Chem", "Mahanadi Organics", "Shivalik Intermediates"]),
                        note="Buying frees every hour this product takes on site; tolling frees the reaction hours only"))
    return out
