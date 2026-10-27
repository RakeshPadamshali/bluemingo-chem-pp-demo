"""Products, routes, specs and the cleaning matrix.

The generator emits ATTRIBUTES and the override table only. Eligible units, clean grades and utility duty are DERIVED
from those attributes by the engine (assets/chm-engine.js), so a product uploaded from Excel inherits all of it with no
mapping table. The derivations repeated here exist for the generator's own asserts (coverage, capacity, tension) — the
engine is the single source of truth at run time, and tools/verify_engine.js checks the two agree.
"""
from . import config as CFG
from .common import R, between, rnd

UNIT = {u["id"]: u for u in CFG.UNITS}
PROD = {p["id"]: p for p in CFG.PRODUCTS}
FAM = {f["id"]: f for f in CFG.FAMILIES}
SOLV = {s["id"]: s for s in CFG.SOLVENTS}
ARCH = CFG.OP_ARCHETYPES


# ---------------------------------------------------------------------------------------------------- eligibility (rule)
def eligible_units(prod, arch_id):
    """Which units may run this operation of this product — read off attributes, never a lookup table.

    class            the archetype's equipment class
    containment      potency 3 is segregated: block B only; everything else stays in block A
    material         halogenated solvent service needs a glass-lined vessel
    cryo             a cryogenic reaction needs a unit with brine / cryo service
    charge fit       the charge must fit, and must not be lost in a grossly oversized vessel
    """
    a = ARCH[arch_id]
    need = op_volume(prod, a["cls"])
    out = []
    for u in CFG.UNITS:
        if u["cls"] != a["cls"]:
            continue
        if prod["potency"] >= 3 and u["block"] != "B":
            continue
        if prod["potency"] < 3 and u["block"] == "B":
            continue
        if a["cls"] == "REACTOR":
            if SOLV.get(prod["solv"], {}).get("cls") == "HAL" and u["mat"] != "GL":
                continue
            if arch_id == "RXN_CRYO" and not u["cryo"]:
                continue
        if u["vol"] + 1e-9 < need:
            continue
        if a["cls"] in CFG.OVERSIZE_CLASSES and u["vol"] > need * CFG.OVERSIZE_FACTOR:
            continue
        out.append(u["id"])
    return out


def op_volume(prod, cls):
    """Vessel volume this operation needs: the reaction charge scaled by the class's share (a dryer holds the wet cake,
    not the reaction mass)."""
    return round(prod["chargeKL"] * CFG.OP_VOL_SHARE.get(cls, 1.0), 2)


def why_not(prod, arch_id, unit_id):
    """Plain-language reasons a unit cannot run an operation (the Eligibility panel)."""
    a, u, out = ARCH[arch_id], UNIT[unit_id], []
    if u["cls"] != a["cls"]:
        out.append("%s is a %s, this operation needs a %s" % (unit_id, u["cls"].lower(), a["cls"].lower()))
        return out
    need = op_volume(prod, a["cls"])
    if prod["potency"] >= 3 and u["block"] != "B":
        out.append("high-potency work is segregated to Block B")
    if prod["potency"] < 3 and u["block"] == "B":
        out.append("Block B is reserved for high-potency work")
    if a["cls"] == "REACTOR" and SOLV.get(prod["solv"], {}).get("cls") == "HAL" and u["mat"] != "GL":
        out.append("halogenated solvent service needs a glass-lined vessel")
    if arch_id == "RXN_CRYO" and not u["cryo"]:
        out.append("a cryogenic step needs brine / cryo service")
    if u["vol"] + 1e-9 < need:
        out.append("a %.2f kL load does not fit a %.1f kL vessel" % (need, u["vol"]))
    elif a["cls"] in CFG.OVERSIZE_CLASSES and u["vol"] > need * CFG.OVERSIZE_FACTOR:
        out.append("a %.2f kL load is lost in a %.1f kL vessel (agitation limit)" % (need, u["vol"]))
    return out


# ---------------------------------------------------------------------------------------------------- cleaning (rule)
def clean_grade(a, b):
    """The clean grade needed to follow product a with product b on the same unit, derived from attributes.

    Returns (grade, why). The matrix on screen is a VIEW of this; the override table wins where the plant has validated
    something different.
    """
    if a["id"] == b["id"]:
        return "NONE", "same product, the campaign continues"
    if (a["potency"] >= 3) != (b["potency"] >= 3):
        # cannot arise: high-potency work never shares a unit with the rest of the plant. Stated, not scheduled.
        return "FORBIDDEN", "high-potency residue is not cleaned down to a normal-product limit (segregated suite)"
    if a["genotox"] and FAM[b["family"]]["id"] == "F3":
        return "DEDICATE", "a genotoxic residue before a filed API route needs a full validated clean-down and a swab to the dedicated limit"
    if a["potency"] >= 2 and b["potency"] < 2:
        return "BOILOUT", "a potent residue before a normal product needs a boil-out and a swab test"
    if a["colour"] > b["colour"] + 1:
        return "BOILOUT", "colour load falls from %d to %d: pale product needs a boil-out first" % (a["colour"], b["colour"])
    same_fam = a["family"] == b["family"]
    same_solv = SOLV.get(a["solv"], {}).get("cls") == SOLV.get(b["solv"], {}).get("cls")
    if same_fam and same_solv and b["colour"] >= a["colour"]:
        return "RINSE", "same family and solvent class, colour load not falling"
    if same_solv and b["colour"] >= a["colour"]:
        return "WASH", "solvent class is shared but the family changes"
    return "WASH", "family or solvent class changes"


OVR = {(o["frm"], o["to"]): o for o in CFG.CLEAN_OVERRIDES}


def clean_cell(a, b):
    """grade, hours, why, source — the override table wins over the derived rule."""
    o = OVR.get((a["id"], b["id"]))
    if o:
        return o["grade"], GRADE_HOURS[o["grade"]], o["why"], "override"
    g, why = clean_grade(a, b)
    return g, GRADE_HOURS[g], why, "derived"


GRADE_HOURS = {g["id"]: g["hours"] for g in CFG.CLEAN_GRADES}


# ---------------------------------------------------------------------------------------------------- routes and duty
def duty_of(prod, arch_id):
    """The three-segment utility duty of one operation, in absolute units: the archetype's per-kL draw times the charge."""
    a, out = ARCH[arch_id], []
    for frac, rates in a["segs"]:
        out.append(dict(frac=frac, draw={k: rnd(v * prod["chargeKL"], 2) for k, v in rates.items()}))
    return out


def charge_sheet(prod):
    """What one batch of this product CONSUMES in materials, operation by operation.

    Same shape as the duty profile and for the same reason: the rate is per kL of charge against the archetype, so the
    quantity follows the batch size and a new product inherits the whole bill of materials from its family and its route.
    The FEED role is charged at the first reaction only — every later reaction consumes the intermediate the stage before
    it made, and that link is already in the route.
    """
    fam = CFG.FAMILY_INPUTS.get(prod["family"], {})
    rm = {r["id"]: r for r in CFG.RAW_MATERIALS}
    out, seen_feed = [], False
    for o in prod["ops"]:
        for role, rate in CFG.INPUT_PROFILE.get(o["arch"], []):
            if role == "FEED":
                if seen_feed:
                    continue                       # stage two onwards is fed by stage one, not from the store
                seen_feed = True
            mat = rm.get(fam.get(role))
            if not mat:
                continue
            qty = rnd(rate * prod["chargeKL"], 2)
            net = rnd(qty * (1 - CFG.CATALYST_RECOVERY), 3) if role == "CATALYST" else qty
            out.append(dict(seq=o["seq"], op=o["op"], opLabel=o["label"], role=role,
                            roleName=CFG.ROLE_NAMES.get(role, role), rmId=mat["id"], rmName=mat["name"],
                            unit=mat["unit"], perKL=rate, qty=qty, net=net, priceUnit=mat["priceUnit"],
                            rupees=int(round(net * mat["priceUnit"])),
                            note="recovered and returned; only the %.0f%% loss is consumed"
                                 % ((1 - CFG.CATALYST_RECOVERY) * 100) if role == "CATALYST" else ""))
    return out


def utility_per_batch(prod):
    """Utility consumed by one batch, per utility: the duty profile integrated over each operation's hours.

    A rate times a time is a quantity: t of steam, TR-hours of refrigeration, Nm3 of nitrogen, m3 of vacuum. This is the
    arithmetic that ties consumption to volume — the duty is per kL of charge, so the quantity is too.
    """
    tot, by_op = {}, []
    for o in prod["ops"]:
        row = {}
        for seg in duty_of(prod, o["arch"]):
            hrs = o["hours"] * seg["frac"]
            for k, v in seg["draw"].items():
                row[k] = row.get(k, 0.0) + v * hrs
        by_op.append(dict(seq=o["seq"], op=o["op"], opLabel=o["label"], hours=o["hours"],
                          draw={k: rnd(v, 2) for k, v in sorted(row.items())}))
        for k, v in row.items():
            tot[k] = tot.get(k, 0.0) + v
    return {k: rnd(v, 2) for k, v in sorted(tot.items())}, by_op


def waste_per_batch(prod):
    """Effluent by category, spent solvent, what the recovery train gives back and what has to be bought in."""
    rec = (CFG.SOLVENT_RECOVERY["recoveryMin"] + CFG.SOLVENT_RECOVERY["recoveryMax"]) / 2.0
    by_cat, solv = {}, 0.0
    for o in prod["ops"]:
        by_cat[o["wasteCat"]] = rnd(by_cat.get(o["wasteCat"], 0.0) + o["efflM3"], 2)
        solv += o["solvKL"]
    return dict(byCat=by_cat, efflM3=rnd(sum(by_cat.values()), 2), solvKL=rnd(solv, 2),
                recoveredKL=rnd(solv * rec, 2), makeupKL=rnd(solv * (1 - rec), 2), recoveryRate=rnd(rec, 3))


def build_products():
    """The product master: attributes, spec, route operations, and (for the asserts) eligible units and duty."""
    out = []
    for p in CFG.PRODUCTS:
        ops = []
        for i, (arch, hours, mn, mx, effl, cat, solv) in enumerate(p["route"]):
            a = ARCH[arch]
            ops.append(dict(seq=i + 1, op="%s/%02d" % (p["id"], i + 1), arch=arch, label=a["label"], cls=a["cls"],
                            hours=hours, minLagH=mn, maxLagH=mx, efflM3=effl, wasteCat=cat, solvKL=solv,
                            clean=a["clean"], units=eligible_units(p, arch), duty=duty_of(p, arch)))
        assay_mean, assay_sd = p["assay"]
        psd_mean, psd_sd = p["psd"]
        row = dict(id=p["id"], name=p["name"], family=p["family"], solv=p["solv"],
                   solvClass=SOLV[p["solv"]]["cls"], haz=SOLV[p["solv"]]["haz"],
                   colour=p["colour"], potency=p["potency"], genotox=p["genotox"],
                   chargeKL=p["chargeKL"], batchKg=p["batchKg"],
                   assayMean=assay_mean, assaySd=assay_sd, impMax=p["impMax"], psdMean=psd_mean, psdSd=psd_sd,
                   retestM=p["retestM"], priceKg=p["priceKg"], costKg=p["costKg"],
                   marginKg=p["priceKg"] - p["costKg"], regulated=bool(p.get("regulated")),
                   intermediate=bool(p.get("intermediate")), ops=ops,
                   yieldMean=round(between(0.79, 0.93), 3), yieldSd=round(between(0.022, 0.055), 3),
                   coprod=p.get("coprod"))
        row["cycleH"] = sum(o["hours"] for o in ops)
        row["efflM3"] = round(sum(o["efflM3"] for o in ops), 2)
        row["solvKL"] = round(sum(o["solvKL"] for o in ops), 2)
        # what one batch consumes and produces as waste — the arithmetic that ties both to the batch volume
        row["charge"] = charge_sheet(row)
        row["utilBatch"], row["utilByOp"] = utility_per_batch(row)
        row["wasteBatch"] = waste_per_batch(row)
        row["rmCostBatch"] = sum(c["rupees"] for c in row["charge"])
        out.append(row)
    return out


def shares_unit(a, b):
    """Can these two products ever meet on the same unit? Only then does a matrix cell mean anything — which is why the
    board shows one grid per train (Block A and Block B), instead of a grid full of cells that cannot arise."""
    ua = {u for o in a["ops"] for u in o["units"]}
    return any(u in ua for o in b["ops"] for u in o["units"])


def build_clean_matrix(products):
    """The grid as rows — a view of the rule, with the overrides marked. Only pairs that can actually follow one another
    on a unit get a cell; the rest are segregated by equipment and never reach a sequencing decision."""
    rows = []
    for a in products:
        for b in products:
            if a["id"] != b["id"] and not shares_unit(a, b):
                continue
            g, h, why, src = clean_cell(a, b)
            rows.append(dict(id="%s>%s" % (a["id"], b["id"]), frm=a["id"], to=b["id"], grade=g,
                             hours=h, why=why, source=src,
                             train="B" if a["potency"] >= 3 else "A"))
    return rows


def forbidden_pairs(matrix):
    return [r for r in matrix if r["grade"] == "FORBIDDEN" and r["frm"] != r["to"]]


# ---------------------------------------------------------------------------------------------------- capacity estimate
def unit_hours_per_day():
    """Scheduled hours a day per equipment class, after block time."""
    out = {}
    for u in CFG.UNITS:
        out[u["cls"]] = out.get(u["cls"], 0) + 24.0 * CFG.UNIT_UPTIME
    return out


def bottleneck_class(products, mix=None):
    """Which equipment class the mix loads hardest — hours demanded against hours available."""
    cap = unit_hours_per_day()
    need = {}
    for p in products:
        w = (mix or {}).get(p["id"], 1.0)
        for o in p["ops"]:
            need[o["cls"]] = need.get(o["cls"], 0) + o["hours"] * w
    ratio = {k: need[k] / cap.get(k, 1e-9) for k in need}
    top = max(ratio, key=lambda k: ratio[k])
    return top, ratio


def batch_minutes(products):
    """Total occupied unit-minutes for one batch of each product (the capacity currency)."""
    return {p["id"]: sum(o["hours"] for o in p["ops"]) * 60 for p in products}
