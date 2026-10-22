"""The masters, and the descriptor that drives the Master Data page.

Every row carries where its numbers come from, and every master carries the Configure / Extend route from slide 39 of the
deck — the one place in the demo where that distinction is shown, so it never interrupts the flow of the plan.

`live` masters are the ones a scenario or a what-if actually re-plans from: template -> upload -> validate -> preview ->
apply -> re-plan -> audit. The rest are reference views of the same data.
"""
from . import config as CFG


def build_masters(products, matrix, customers, approvals, tanks, deliveries, raws, sourcing, lots, demand_plan):
    m = {}
    m["products"] = [dict(id=p["id"], name=p["name"], family=p["family"], solv=p["solv"], solvClass=p["solvClass"],
                          haz=p["haz"], colour=p["colour"], potency=p["potency"], genotox=p["genotox"],
                          chargeKL=p["chargeKL"], batchKg=p["batchKg"], cycleH=p["cycleH"],
                          assayMean=p["assayMean"], assaySd=p["assaySd"], impMax=p["impMax"],
                          psdMean=p["psdMean"], psdSd=p["psdSd"], retestM=p["retestM"],
                          yieldMean=p["yieldMean"], yieldSd=p["yieldSd"],
                          priceKg=p["priceKg"], costKg=p["costKg"], marginKg=p["marginKg"],
                          regulated=p["regulated"], intermediate=p["intermediate"],
                          coprodId=(p["coprod"] or {}).get("id"), coprodRatio=(p["coprod"] or {}).get("ratio"))
                     for p in products]
    m["routes"] = [dict(id=o["op"], productId=p["id"], seq=o["seq"], arch=o["arch"], label=o["label"], cls=o["cls"],
                        hours=o["hours"], minLagH=o["minLagH"], maxLagH=o["maxLagH"],
                        efflM3=o["efflM3"], wasteCat=o["wasteCat"], solvKL=o["solvKL"])
                   for p in products for o in p["ops"]]
    m["units"] = [dict(id=u["id"], name=u["name"], cls=u["cls"], block=u["block"], vol=u["vol"], mat=u["mat"],
                       cryo=u["cryo"], uptime=CFG.UNIT_UPTIME, note=u["note"]) for u in CFG.UNITS]
    m["blockTimes"] = [dict(id="BT-%02d" % (i + 1), **b) for i, b in enumerate(CFG.BLOCK_TIMES)]
    m["utilities"] = [dict(id=u["id"], name=u["name"], unit=u["unit"], cap=u["cap"], kind=u["kind"],
                           derateMonths=",".join(str(x) for x in u.get("derate", {}).get("months", [])) or None,
                           derateCap=u.get("derate", {}).get("cap"), derateWhy=u.get("derate", {}).get("why"))
                      for u in CFG.UTILITIES]
    m["dutyProfiles"] = [dict(id=k, label=a["label"], cls=a["cls"], clean=a["clean"],
                              seg1=_seg(a["segs"][0]), seg2=_seg(a["segs"][1]), seg3=_seg(a["segs"][2]))
                         for k, a in sorted(CFG.OP_ARCHETYPES.items())]
    m["waste"] = [dict(**w) for w in CFG.WASTE]
    m["solventRecovery"] = [dict(id="RECOVERY", **CFG.SOLVENT_RECOVERY)]
    m["hazardClasses"] = [dict(**h) for h in CFG.HAZARD_CLASSES]
    m["bunds"] = [dict(id=b["id"], name=b["name"], classes=",".join(b["classes"])) for b in CFG.BUNDS]
    m["segregation"] = [dict(id="%s|%s" % (a, b), classA=a, classB=b, why="These classes may not share a bund")
                        for a, b in CFG.SEGREGATION]
    m["tanks"] = tanks
    m["deliveries"] = deliveries
    m["cleanGrades"] = [dict(**g) for g in CFG.CLEAN_GRADES]
    m["cleanMatrix"] = matrix
    m["cleanOverrides"] = [dict(id="%s>%s" % (o["frm"], o["to"]), **o) for o in CFG.CLEAN_OVERRIDES]
    m["campaignRule"] = [dict(id="CAMPAIGN", **CFG.CAMPAIGN)]
    m["families"] = [dict(**f) for f in CFG.FAMILIES]
    m["sites"] = [dict(**s) for s in CFG.SITES]
    m["customers"] = [dict(id=c["id"], name=c["name"], region=c["region"], regulated=c["regulated"],
                           sites=",".join(c["sites"]), buys=",".join(c["buys"]), minLifeMonths=c["minLifeMonths"],
                           qualWeeks=c["qualWeeks"], coaRequired=c["coaRequired"]) for c in customers]
    m["approvals"] = approvals
    m["orderClasses"] = [dict(**c) for c in CFG.ORDER_CLASSES]
    m["rawMaterials"] = [dict(id=r["id"], name=r["name"], unit=r["unit"], minBlock=r["minBlock"],
                              priceUnit=r["priceUnit"], leadDays=r["leadDays"], priceLagDays=r["priceLagDays"],
                              priceMove=r["priceMove"], onHand=r["onHand"], usedBy=",".join(r["usedBy"]), note=r["note"])
                         for r in raws]
    m["sourcing"] = sourcing
    m["openingLots"] = lots
    m["demandPlan"] = demand_plan["rows"]
    m["weights"] = [dict(**w) for w in CFG.WEIGHT_PRESETS]
    m["genericAssumptions"] = [dict(**a) for a in CFG.GENERIC_ASSUMPTIONS]
    return m


def _seg(seg):
    frac, rates = seg
    return "%d%% · %s" % (round(frac * 100), ", ".join("%s %g/kL" % (k, v) for k, v in sorted(rates.items())) or "no utility draw")


# key, label, group, icon, key field, live (uploadable and re-plans), provenance, slide-39 route, nuances it carries
MASTERS = [
    ("products", "Products and attributes", "Product", "fa-vial", "id", True, "GENERATED",
     "Configure", ["P1", "P2", "P7"], "Every rule is read off these attributes. A product added here inherits its units, clean grades, duty and waste."),
    ("routes", "Routes, stages and hold windows", "Product", "fa-diagram-project", "id", True, "GENERATED",
     "Configure", ["P3"], "One row per operation. minLagH / maxLagH are the planner's minimum and maximum lag on the link to the next operation — the hold window."),
    ("cleanOverrides", "Cleaning matrix overrides", "Product", "fa-soap", "id", True, "GENERATED",
     "Configure", ["P1"], "The derived matrix is a rule over attributes; these rows are what the plant has validated differently."),
    ("cleanMatrix", "Cleaning matrix (derived)", "Product", "fa-table-cells", "id", False, "RULE",
     "Configure", ["P1"], "A view, not an input: the grade for each pair, from the attributes plus the overrides above."),
    ("cleanGrades", "Clean grades", "Product", "fa-droplet", "id", True, "GENERATED",
     "Configure", ["P1"], "What each grade costs in hours. Change a grade here and every sequence that uses it re-plans."),
    ("campaignRule", "Campaign rule", "Product", "fa-layer-group", "id", True, "GENERATED",
     "Configure", ["P1"], "Minimum and maximum campaign size, how far demand may be pulled forward to reach the minimum, the attribute the campaign sorts on, and the forced break."),
    ("families", "Product families", "Product", "fa-sitemap", "id", False, "GENERATED", "Configure", [], "Grouping only; the rules read attributes, not the family name."),
    ("units", "Equipment", "Plant", "fa-industry", "id", True, "GENERATED",
     "Configure", [], "Class, block, working volume, material and service. Eligibility is derived from these against the product's attributes."),
    ("blockTimes", "Block times", "Plant", "fa-calendar-xmark", "id", True, "GENERATED",
     "Configure", [], "Planned maintenance and service windows. A plan cannot run a batch through a block time."),
    ("utilities", "Utilities (secondary resources)", "Plant", "fa-bolt", "id", True, "GENERATED",
     "Extend", ["P4"], "Hourly capacity per utility, with the seasonal derate. The cap binds on the PEAK of concurrent batches."),
    ("dutyProfiles", "Duty profiles", "Plant", "fa-chart-area", "id", False, "GENERATED",
     "Extend", ["P4"], "Three segments per operation archetype, drawn per kL of charge — so a bigger batch draws more without a second table."),
    ("waste", "Effluent and waste limits", "Plant", "fa-recycle", "id", True, "GENERATED",
     "Extend", ["P5"], "A daily limit per waste category. Load over the limit is not a warning; it stops the batch."),
    ("solventRecovery", "Solvent recovery", "Plant", "fa-arrows-rotate", "id", True, "GENERATED",
     "Extend", ["P5"], "Daily distillation capacity and recovery band; recovered solvent returns to the tank farm after QC."),
    ("hazardClasses", "Hazard licence ceilings", "Plant", "fa-triangle-exclamation", "id", True, "GENERATED",
     "Extend", ["P6"], "The licensed quantity per hazard class. This is the ceiling that refuses a delivery, not the tank."),
    ("bunds", "Bunds", "Plant", "fa-border-all", "id", False, "GENERATED", "Extend", ["P6"], "Which hazard classes each bund may hold."),
    ("segregation", "Segregation rules", "Plant", "fa-arrows-left-right-to-line", "id", False, "GENERATED", "Extend", ["P6"], "Hazard classes that may not share a bund."),
    ("tanks", "Tank farm", "Plant", "fa-oil-well", "id", True, "GENERATED", "Extend", ["P6"], "Day tanks: capacity, opening level, hazard class and bund."),
    ("deliveries", "Tanker deliveries", "Plant", "fa-truck-droplet", "id", False, "GENERATED", "Extend", ["P6"], "The delivery calendar the licence check runs against."),
    ("customers", "Customers", "Demand", "fa-users", "id", True, "GENERATED",
     "Extend", ["P7", "S6", "S7"], "Approved sites, the filed route, COA requirement and the minimum remaining shelf life on receipt."),
    ("approvals", "Site approval matrix", "Demand", "fa-building-shield", "id", True, "GENERATED",
     "Extend", ["S7"], "Customer by site, with the qualification lead time where a site is not yet filed."),
    ("orderClasses", "Order classes", "Demand", "fa-tags", "id", True, "GENERATED",
     "Configure", [], "Priority, delay penalty per day and the release window — how early a class may be started."),
    ("demandPlan", "Demand plan (12 months)", "Demand", "fa-chart-column", "id", True, "GENERATED",
     "Configure", ["S1", "S8"], "Monthly volume per product, with the seasonal peak and the shutdown month."),
    ("openingLots", "Opening lots", "Inventory", "fa-boxes-stacked", "id", False, "GENERATED",
     "Extend", ["P7", "S6"], "Stock at the start of history, each lot with its assay, impurity, PSD and retest date."),
    ("rawMaterials", "Raw materials", "Inventory", "fa-flask-vial", "id", True, "GENERATED",
     "Configure", ["S5"], "Minimum buy block, lead time and the price lag."),
    ("sourcing", "Make, buy or toll", "Inventory", "fa-handshake", "id", True, "GENERATED",
     "Configure", ["S3"], "The three sourcing options per intermediate, each with its cost and lead time."),
    ("sites", "Sites", "Inventory", "fa-location-dot", "id", False, "GENERATED", "Extend", ["S7"], "The network. This demo schedules Unit 2 in detail; the others are S&OP-level."),
    ("weights", "Objective weights", "Planning", "fa-sliders", "id", True, "GENERATED",
     "Configure", [], "The five levers. BOTH rule sets use the same weights, so the comparison is about rules, not priorities."),
    ("genericAssumptions", "Generic planning assumptions", "Planning", "fa-list-check", "id", False, "DECK",
     "—", [], "The seven assumptions the deck names. The assumption ratchet in Plan Studio turns them on one at a time."),
]


def masters_desc(m):
    out = []
    for key, label, group, icon, kf, live, source, route, nus, note in MASTERS:
        rows = m.get(key) or []
        cols = []
        for r in rows[:40]:
            for k in r:
                if k not in cols:
                    cols.append(k)
        out.append(dict(key=key, label=label, group=group, icon=icon, kf=kf, live=live, source=source,
                        route=route, nuances=nus, note=note, n=len(rows), cols=cols))
    return out
