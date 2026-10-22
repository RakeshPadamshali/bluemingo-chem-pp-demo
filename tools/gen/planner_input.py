"""The same plant, written in the Bluemingo Production Planner's own input contract.

Why this exists: the demo's masters should not be a parallel invention. Writing them out in the planner's documented
contract (docs/design/2026-10-13-Planner-Input-and-Output-Format.md) proves they map onto it — and gives the product team a
real specialty-chemicals test case next to the steel one.

Where the contract has no home for something, it goes under `_extensions` with the nuance it serves, clearly outside the
contract. That list IS the Extend column of slide 39, stated in the product's own terms.
"""
import math
from datetime import timedelta

from . import config as CFG
from .common import ASOF, DAY0, at, iso

TZ = "+05:30"
PRIORITY = {"EXPORT_REG": 1, "EXPORT": 2, "DOM_COMMITTED": 3, "DOM_OPEN": 4}


def _iso(d):
    return d.strftime("%Y-%m-%dT%H:%M:%S") + TZ


def build(products, m, orders, lines, matrix):
    P = {p["id"]: p for p in products}
    classes = []
    for u in CFG.UNITS:
        if u["cls"] not in classes:
            classes.append(u["cls"])

    out = {}
    out["plan"] = dict(plan_id="CHM-UNIT2-%s" % DAY0.strftime("%Y%m%d"),
                       name="API Site Unit 2 — %d-day detailed plan" % CFG.FORWARD_DAYS,
                       plan_start=_iso(ASOF))
    out["plan_parameters"] = dict(
        version="chem-demo-1",
        rule_chains=[dict(rules=[dict(rule="bucket"), dict(rule="est"), dict(rule="priority"),
                                 dict(rule="earliest_due_date"), dict(rule="campaign"), dict(rule="changeover")])],
        count_early_delay=True, optimisation_window_days=CFG.FORWARD_DAYS, time_budget_seconds=120, seed=CFG.SEED)

    out["factories"] = [dict(factory_id="F-BLOCK-A", name="Block A — general plant"),
                        dict(factory_id="F-BLOCK-B", name="Block B — segregated high-potency suite")]
    out["transfer_times"] = [dict(from_factory_id="F-BLOCK-A", to_factory_id="F-BLOCK-B", minutes=90),
                             dict(from_factory_id="F-BLOCK-B", to_factory_id="F-BLOCK-A", minutes=90)]

    out["skus"] = [dict(sku_id=p["id"], name=p["name"], unit="kg",
                        attributes=dict(family=p["family"], solvent=p["solv"], solvent_class=p["solvClass"],
                                        hazard_class=p["haz"], colour_load=p["colour"], potency=p["potency"],
                                        genotoxic=p["genotox"], regulated=p["regulated"],
                                        charge_kl=p["chargeKL"], batch_kg=p["batchKg"]))
                   for p in products]

    out["operations"] = [dict(operation_id=c, code="OP_" + c, name=c.title(), operation_type="batch", bucket_days=1)
                         for c in classes]
    out["machines"] = [dict(machine_id=u["id"], code=u["id"].replace("-", ""), name=u["name"],
                            factory_id="F-BLOCK-" + u["block"], operation_id=u["cls"]) for u in CFG.UNITS]
    # rate_per_hour is kg of product per hour on that unit; min/max batch are the charges the unit may take
    caps = []
    for u in CFG.UNITS:
        fits = [p for p in products if u["id"] in {x for o in p["ops"] if o["cls"] == u["cls"] for x in o["units"]}]
        if not fits:
            caps.append(dict(machine_id=u["id"], rate_per_hour=0, min_batch=0, max_batch=0))
            continue
        rates = []
        for p in fits:
            for o in p["ops"]:
                if o["cls"] == u["cls"] and u["id"] in o["units"]:
                    rates.append(p["batchKg"] / float(o["hours"]))
        caps.append(dict(machine_id=u["id"], rate_per_hour=round(sum(rates) / len(rates), 2),
                         min_batch=min(p["batchKg"] for p in fits), max_batch=max(p["batchKg"] for p in fits)))
    out["machine_capabilities"] = caps

    out["routings"] = [dict(routing_id="R-" + p["id"],
                            positions=[dict(position_no=(i + 1) * 10, operation_id=o["cls"],
                                            **({"sku_id": p["id"]} if i == 0 else {}),
                                            minimum_lag_minutes=o["minLagH"] * 60,
                                            maximum_lag_minutes=o["maxLagH"] * 60,
                                            processing_minutes=o["hours"] * 60)
                                       for i, o in enumerate(p["ops"])])
                       for p in products]

    # block times: the weekly rules expanded into dated rows across the plan window
    bts = []
    for b in CFG.BLOCK_TIMES:
        for d in range(0, CFG.FORWARD_DAYS + 1):
            day = at(d)
            if day.weekday() != b["dow"]:
                continue
            if b["every"] == 14 and (d // 7) % 2:
                continue
            bts.append(dict(machine_id=b["unit"], date=day.strftime("%Y-%m-%d"),
                            start="%02d:00" % b["start"], end="%02d:00" % min(24, b["start"] + b["hours"]),
                            reason=b["reason"]))
    out["block_times"] = bts

    O = {o["id"]: o for o in orders}
    out["order_lines"] = [dict(order_line_id=l["id"], customer_order_id=l["orderId"],
                               production_order_id="PR-" + l["id"].replace("/", "-"),
                               sku_id=l["productId"], quantity=l["qty"],
                               delivery_date=_iso(_dt(l["due"])), priority=PRIORITY.get(l["cls"], 5),
                               attributes=dict(order_class=l["cls"], customer=l["customerId"],
                                               assay_min=l["assayMin"], impurity_max=l["impMax"],
                                               psd_max=l["psdMax"], min_life_months=l["minLifeM"],
                                               coa_required=l["coa"]),
                               routing_id="R-" + l["productId"])
                          for l in lines]

    rel = {c["id"]: c["relWinDays"] for c in CFG.ORDER_CLASSES}
    out["material_availability"] = [dict(order_line_id=l["id"], position_no=10,
                                         available_from=_iso(max(_dt(O[l["orderId"]]["orderDate"]),
                                                                 _dt(l["due"]) - timedelta(days=rel.get(l["cls"], 14)))))
                                    for l in lines]

    # a candidate product mix: due-date order, first eligible machine, the bucket that holds the latest start
    mix = []
    for l in sorted(lines, key=lambda x: (x["due"], x["id"])):
        p = P[l["productId"]]
        nb = max(1, math.ceil(l["qty"] / p["batchKg"]))
        tail = 0.0
        for i, o in enumerate(reversed(p["ops"])):
            tail += o["hours"]
            start = _dt(l["due"]) - timedelta(hours=tail)
            pos = (len(p["ops"]) - i) * 10
            mix.append(dict(order_line_id=l["id"], position_no=pos, machine_id=o["units"][0], sku_id=p["id"],
                            bucket_id=start.strftime("%Y-%m-%d"),
                            bucket_start=_iso(start.replace(hour=6, minute=0, second=0)),
                            bucket_end=_iso((start + timedelta(days=1)).replace(hour=6, minute=0, second=0)),
                            quantity=l["qty"] if pos == len(p["ops"]) * 10 else nb * p["batchKg"]))
    out["product_mix"] = mix

    # changeovers: the cleaning matrix, as a changeover matrix keyed on the SKU, plus the attribute-level fallbacks.
    # FORBIDDEN pairs have no home in the contract — they are listed under _extensions, which is the finding.
    ch = []
    for cls in classes:
        if not any(a["cls"] == cls and a["clean"] for a in CFG.OP_ARCHETYPES.values()):
            continue
        for r in matrix:
            if r["grade"] == "FORBIDDEN" or r["frm"] == r["to"]:
                continue
            if cls not in {o["cls"] for o in P[r["frm"]]["ops"]} or cls not in {o["cls"] for o in P[r["to"]]["ops"]}:
                continue
            ch.append(dict(operation_id=cls, key="sku", from_value=r["frm"], to_value=r["to"],
                           minutes=int(round((r["hours"] or 0) * 60))))
        ch.append(dict(operation_id=cls, key="family", from_value="any", to_value="any",
                       minutes=int(CFG.CLEAN_GRADES[2]["hours"] * 60)))
    out["changeovers"] = ch

    out["_extensions"] = dict(
        why="Everything below is a rule this plant schedules against that the current input contract has no field for. "
            "It is the Extend column of the deck's slide 39, stated in the planner's own terms.",
        forbidden_pairs=dict(nuance="P1",
                             need="A changeover matrix cell that means 'never', not 'expensive'. Today a forbidden pair "
                                  "can only be approximated with a very large changeover time, which an optimiser may still buy.",
                             rows=[dict(operation_id="REACTOR", key="sku", from_value=r["frm"], to_value=r["to"], why=r["why"])
                                   for r in matrix if r["grade"] == "FORBIDDEN"]),
        yield_distribution=dict(nuance="P2",
                                need="A yield mean and spread per SKU, and a plan that re-costs the campaign as each batch assays.",
                                rows=[dict(sku_id=p["id"], yield_mean=p["yieldMean"], yield_sd=p["yieldSd"],
                                           assay_mean=p["assayMean"], assay_sd=p["assaySd"]) for p in products]),
        secondary_resource_duty=dict(nuance="P4",
                                     need="A per-hour capacity on a shared resource, and a duty PROFILE per operation so the peak "
                                          "of concurrent batches binds instead of an average.",
                                     resources=[dict(resource_id=u["id"], name=u["name"], unit=u["unit"], capacity_per_hour=u["cap"],
                                                     derate=u.get("derate")) for u in CFG.UTILITIES]),
        waste_limits=dict(nuance="P5",
                          need="A daily limit per waste category with carry-over, and a recovery credit that returns material later.",
                          rows=[dict(category=w["id"], per_day=w["cap"], unit=w["unit"]) for w in CFG.WASTE]),
        hazard_licence=dict(nuance="P6",
                            need="A licensed ceiling per hazard class over the whole site, checked across time, plus bund segregation.",
                            rows=[dict(hazard_class=h["id"], licensed_kl=h["licensedKL"]) for h in CFG.HAZARD_CLASSES]),
        spec_allocation=dict(nuance="P7",
                             need="Allocation that matches a lot's measured assay, impurity and PSD to the order's spec, the "
                                  "customer's approved site and route, and a minimum remaining shelf life — blending lots where one will not do."),
    )
    return out


def _dt(s):
    from datetime import datetime
    return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S")
