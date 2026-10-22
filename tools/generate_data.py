#!/usr/bin/env python3
"""Deterministic demo dataset for the Bluemingo specialty-chemicals PP demo.

Writes  data/chm-data.js   (window.CHM — read by every page and by the engine)
        data/chm-meta.js   (header stamp for the tab host)
        data/README.md     (the data dictionary)
        data/planner-input.sample.json  (the same plant in the Production Planner's own input contract)

Everything is FICTIONAL. Every generated parameter lives in tools/gen/config.py and is marked "generated" on the Master
Data page. The only things taken from outside are the rule SHAPES argued in the Bluemingo Specialty Chemicals deck and the
vocabulary of the Production Planner design docs.

Run:  python tools/generate_data.py                  (as-of = today 09:30)
      python tools/generate_data.py --asof 2026-10-22
"""
import json
import math
import os
import sys
from collections import Counter
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen import config as CFG
from gen.common import ASOF, BASE, END, ASOF_MINUTE, END_MINUTE, iso, at
from gen.catalogue import build_products, build_clean_matrix, forbidden_pairs, bottleneck_class, UNIT, op_volume
from gen.customers import build_customers, approval_rows
from gen.orders import build_orders, build_demand_plan, class_hours, available_hours
from gen.inventory import build_opening_lots, build_tanks, build_deliveries, build_raw_materials, build_sourcing_options
from gen.events import build_events, build_scenarios
from gen.masters import build_masters, masters_desc
from gen import planner_input

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = lambda f: os.path.join(ROOT, "data", f)

# ---------------------------------------------------------------- build
products = build_products()
matrix = build_clean_matrix(products)
customers = build_customers(products)
approvals = approval_rows(customers)
orders, lines, stats = build_orders(customers, products)
demand_plan = build_demand_plan(products, lines)
lots = build_opening_lots(products)
tanks = build_tanks()
deliveries = build_deliveries(tanks, products, lines)
raws = build_raw_materials(products)
sourcing = build_sourcing_options(products)
events = build_events()
scenarios = build_scenarios(products, orders, lines, customers, matrix, tanks, deliveries, lots, demand_plan, stats["binding"])
m = build_masters(products, matrix, customers, approvals, tanks, deliveries, raws, sourcing, lots, demand_plan)
desc = masters_desc(m)

# ---------------------------------------------------------------- integrity asserts
def uniq(name, rows, key="id"):
    dup = [k for k, n in Counter(r[key] for r in rows).items() if n > 1]
    assert not dup, "duplicate ids in %s: %s" % (name, dup[:5])


for name, rows in (("products", products), ("customers", customers), ("orders", orders), ("lines", lines),
                   ("tanks", tanks), ("deliveries", deliveries), ("lots", lots), ("rawMaterials", raws),
                   ("cleanMatrix", matrix), ("approvals", approvals), ("demandPlan", demand_plan["rows"])):
    uniq(name, rows)

P = {p["id"]: p for p in products}
C = {c["id"]: c for c in customers}
O = {o["id"]: o for o in orders}
for p in products:
    assert p["ops"], "product with no route: " + p["id"]
    for o in p["ops"]:
        assert o["units"], "no eligible unit for %s (%s, %s, needs %.2f kL)" % (o["op"], o["cls"], p["id"], op_volume(p, o["cls"]))
        assert o["maxLagH"] > o["minLagH"], "hold window not a window: " + o["op"]
        assert o["duty"] and abs(sum(s["frac"] for s in o["duty"]) - 1.0) < 1e-6, "duty profile does not sum to the operation: " + o["op"]
    assert p["marginKg"] > 0, "product sold below cost: " + p["id"]
    assert 0.6 < p["yieldMean"] < 1.0 and 0 < p["yieldSd"] < 0.1, p["id"]
for l in lines:
    assert l["productId"] in P and l["customerId"] in C and l["orderId"] in O, l["id"]
    assert l["qty"] > 0 and l["due"] > iso(BASE), l["id"]
    assert l["productId"] in C[l["customerId"]]["buys"], "%s buys a product it does not buy: %s" % (l["customerId"], l["productId"])
    assert l["assayMin"] < P[l["productId"]]["assayMean"] and l["impMax"] <= P[l["productId"]]["impMax"], l["id"]
for r in matrix:
    assert r["frm"] in P and r["to"] in P and r["grade"] in {g["id"] for g in CFG.CLEAN_GRADES}, r["id"]
for t in tanks:
    assert t["haz"] in {h["id"] for h in CFG.HAZARD_CLASSES} and t["bundId"] in {b["id"] for b in CFG.BUNDS}, t["id"]
    assert t["openKL"] <= t["capKL"], t["id"]
    assert t["tankerKL"] + t["openKL"] <= t["capKL"] + 1e-9, (
        "a tanker for %s cannot fit on top of its own opening stock: %.1f + %.1f > %.1f"
        % (t["id"], t["tankerKL"], t["openKL"], t["capKL"]))
for b in CFG.BUNDS:                       # a bund may not hold two classes the segregation rules keep apart
    for a1, a2 in CFG.SEGREGATION:
        assert not (a1 in b["classes"] and a2 in b["classes"]), "bund %s holds segregated classes" % b["id"]
for d in deliveries:
    assert d["tankId"] in {t["id"] for t in tanks}, d["id"]
for x in lots:
    assert x["productId"] in P and x["kg"] > 0, x["id"]
for u in CFG.UNITS:
    assert any(bt["unit"] == u["id"] for bt in CFG.BLOCK_TIMES), "unit with no block time: " + u["id"]
for row in m["routes"]:
    assert row["wasteCat"] in {w["id"] for w in CFG.WASTE}, row["id"]
# opening licence position must itself be legal
for h in CFG.HAZARD_CLASSES:
    held = sum(t["openKL"] for t in tanks if t["haz"] == h["id"])
    assert held <= h["licensedKL"], "opening stock already over the %s licence: %.1f > %.1f" % (h["id"], held, h["licensedKL"])

# every nuance has a scenario card, and every card resolves against the generated data
NUANCES = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9"]
covered = {s["nuance"] for s in scenarios.values()}
assert covered == set(NUANCES), "nuances without a scenario: %s" % sorted(set(NUANCES) - covered)
line_ids, prod_ids = {l["id"] for l in lines}, set(P)
for k, s in scenarios.items():
    if s.get("lineId"):
        assert s["lineId"] in line_ids, "%s points at a missing line %s" % (k, s["lineId"])
    for key in ("productId", "frm", "to", "fromProduct", "toProduct", "perTonneWinner", "perHourWinner"):
        if s.get(key):
            assert s[key] in prod_ids, "%s.%s points at a missing product %s" % (k, key, s[key])
    for pid in s.get("productIds", []):
        assert pid in prod_ids, "%s points at a missing product %s" % (k, pid)
assert scenarios["C6"]["deliveryId"] in {d["id"] for d in deliveries}
assert scenarios["C11"]["lotId"] in {x["id"] for x in lots}
assert scenarios["C12"]["customerId"] in C and scenarios["C13"]["shutdownMonth"]
assert scenarios["C13b"]["rmId"] in {r["id"] for r in raws}
assert scenarios["C1"]["grade"] == "BOILOUT" and scenarios["C1"]["forbidden"], "C1 needs a boil-out pair and a forbidden pair"
assert scenarios["C9"]["perTonneWinner"] != scenarios["C9"]["perHourWinner"], "C9 needs the ranking to actually flip"
assert scenarios["C9"]["flipStrength"] >= 1.2, "C9 flip is only %.2fx — too small to argue from" % scenarios["C9"]["flipStrength"]

# ---- the tension gate's static half (the engine half is tools/verify_tension.py) ----
fb = forbidden_pairs(matrix)
costly = [r for r in matrix if r["grade"] in ("DEDICATE", "FORBIDDEN") and r["frm"] != r["to"]]
assert len(costly) >= 6, "only %d pairs a generic sequence would pay dearly for: the cleaning story has nothing to bite on" % len(costly)
tight_holds = sum(1 for p in products for o in p["ops"][:-1] if o["maxLagH"] <= 14)
assert tight_holds >= 8, "only %d tight hold windows" % tight_holds
assert abs(stats["bindingLoad"] - CFG.DEMAND_LOAD) <= 0.03, "demand is %.3f of realisable capacity on %s, not the %.2f asked for" % (stats["bindingLoad"], stats["binding"], CFG.DEMAND_LOAD)
assert sum(1 for r in matrix if r["grade"] == "BOILOUT") >= 10, "too few boil-out pairs to sequence around"
assert sum(1 for c in customers if c["regulated"] and c["sites"] == ["UNIT-2"]) >= 3, "nobody is locked to this site"
assert sum(1 for x in lots if x["lifeLeftM"] < 12) >= 3, "no short-life stock: the shelf-life story has nothing to show"
assert sum(1 for l in lines if l["tightSpec"]) >= max(10, 0.08 * len(lines)), "too few tight-spec lines to need blending"

bneck, bratio = bottleneck_class(products)

# ---------------------------------------------------------------- write
meta = dict(company=CFG.PLANT["company"], site=CFG.PLANT["site"], title=CFG.PLANT["title"],
            product=CFG.PLANT["product"], subtitle=CFG.PLANT["subtitle"],
            asOf=iso(ASOF), base=iso(BASE), end=iso(END), asOfMinute=ASOF_MINUTE, endMinute=END_MINUTE,
            historyDays=CFG.HISTORY_DAYS, forwardDays=CFG.FORWARD_DAYS, sopMonths=CFG.SOP_MONTHS,
            generated=iso(datetime.now()), seed=CFG.SEED, fictional=True, stats=stats,
            bottleneck=bneck, classLoad={k: round(v, 3) for k, v in bratio.items()},
            masters=desc)
cfg = dict(unitUptime=CFG.UNIT_UPTIME, oversize=CFG.OVERSIZE_FACTOR, oversizeClasses=CFG.OVERSIZE_CLASSES, opVolShare=CFG.OP_VOL_SHARE,
           campaign=CFG.CAMPAIGN, season=CFG.SEASON, sourcing=CFG.SOURCING, rmBlocks=CFG.RM_BLOCKS,
           exec=CFG.EXEC, cleanGradeHours={g["id"]: g["hours"] for g in CFG.CLEAN_GRADES},
           demandLoad=CFG.DEMAND_LOAD, cleanAllowH=None, shutdownMonth=demand_plan["shutdownMonth"],
           shutdownDays=demand_plan["shutdownDays"], sopMonthList=demand_plan["months"],
           recovery=CFG.SOLVENT_RECOVERY, assumptions=[a["id"] for a in CFG.GENERIC_ASSUMPTIONS],
           generic=CFG.GENERIC, aware=CFG.AWARE, utilities=CFG.UTILITIES, waste=CFG.WASTE,
           hazardClasses=CFG.HAZARD_CLASSES, bunds=CFG.BUNDS, segregation=CFG.SEGREGATION,
           orderClasses=CFG.ORDER_CLASSES, archetypes=CFG.OP_ARCHETYPES, opClasses=sorted({u["cls"] for u in CFG.UNITS}))
data = dict(meta=meta, cfg=cfg, m=m, orders=orders, lines=lines, events=events, scenarios=scenarios)

os.makedirs(os.path.dirname(OUT("x")), exist_ok=True)
with open(OUT("chm-data.js"), "w", encoding="utf-8") as f:
    f.write("/* GENERATED by tools/generate_data.py — do not hand-edit. As-of %s. Fictional data; see data/README.md */\n" % iso(ASOF))
    f.write("window.CHM = ")
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    f.write(";\n")

lab = ASOF.strftime("%a %d %b %Y %H:%M").replace(" 0", " ")
with open(OUT("chm-meta.js"), "w", encoding="utf-8") as f:
    f.write("window.CHM_META = %s;\n" % json.dumps(dict(asOf=iso(ASOF), asOfLabel=lab, site=CFG.PLANT["site"],
                                                        presets={w["id"]: w["label"] for w in CFG.WEIGHT_PRESETS})))

pin = planner_input.build(products, m, orders, lines, matrix)
with open(OUT("planner-input.sample.json"), "w", encoding="utf-8") as f:
    json.dump(pin, f, ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- data dictionary
def fields(rows):
    ks = []
    for r in rows[:50]:
        for k in r:
            if k not in ks:
                ks.append(k)
    return ", ".join("`%s`" % k for k in ks)


md = ["# Bluemingo PP · Specialty Chemicals & APIs — dataset (data dictionary)", "",
      "Generated by `tools/generate_data.py` (deterministic, seed %d). As-of **%s**; history from %s, detailed plan to %s, "
      "then %d monthly buckets." % (CFG.SEED, iso(ASOF), iso(BASE), iso(END), CFG.SOP_MONTHS), "",
      "**Everything here is fictional.** The site, the products, the customers, the people and the volumes are generated "
      "for the demo. What is *not* invented is the shape of the rules: the cleaning matrix, yield and assay, hold-time "
      "windows, utility concurrency, effluent and recycle, hazard ceilings and spec-driven blending come from the "
      "Bluemingo Specialty Chemicals deck, and the vocabulary (changeover matrix by attribute, links with a minimum and a "
      "maximum lag, campaign rules, secondary resources, block times) from the Bluemingo Production Planner design.", "",
      "Every generated parameter is in `tools/gen/config.py` and is marked **generated** on the Master Data page.", "",
      "## The plant", "", "| | |", "|---|---|",
      "| Equipment | %d units in %d classes (%s) |" % (len(CFG.UNITS), len({u["cls"] for u in CFG.UNITS}), ", ".join(sorted({u["cls"].title() for u in CFG.UNITS}))),
      "| Utilities | %s |" % ", ".join("%s %g %s" % (u["id"], u["cap"], u["unit"]) for u in CFG.UTILITIES),
      "| Waste | %s |" % ", ".join("%s %g %s" % (w["id"], w["cap"], w["unit"]) for w in CFG.WASTE),
      "| Tank farm | %d tanks in %d bunds; licensed %s |" % (len(tanks), len(CFG.BUNDS), ", ".join("%s %g kL" % (h["id"], h["licensedKL"]) for h in CFG.HAZARD_CLASSES)),
      "| Products | %d in %d families (%d regulated, %d intermediates also sold) |" % (len(products), len(CFG.FAMILIES), sum(1 for p in products if p["regulated"]), sum(1 for p in products if p["intermediate"])),
      "| Cleaning matrix | %d cells (%d not permitted, %d validated clean-down, %d boil-out, %d overrides) |" % (len(matrix), len(fb), sum(1 for r in matrix if r["grade"] == "DEDICATE"), sum(1 for r in matrix if r["grade"] == "BOILOUT"), len(CFG.CLEAN_OVERRIDES)),
      "| Customers | %d (%d regulated with an approved-site matrix) |" % (len(customers), sum(1 for c in customers if c["regulated"])),
      "| Order book | %d orders / %d lines / %s kg / Rs %s |" % (stats["orders"], stats["lines"], "{:,}".format(stats["kg"]), "{:,}".format(stats["value"])),
      "| Load | %s on %s (band 0.85-0.92) |" % (stats["bindingLoad"], stats["binding"]),
      "| Opening lots | %d |" % len(lots),
      "| Deliveries | %d tanker loads over the horizon |" % len(deliveries), "",
      "## Collections in `window.CHM`", ""]
for name, rows in (("orders", orders), ("lines", lines)):
    md += ["### `%s` — %d records" % (name, len(rows)), "", "Fields: " + fields(rows), ""]
md += ["### `m` — masters (one key per master on the Master Data page)", ""]
for d in desc:
    md.append("- `m.%s` (%d) **%s** — %s route, %s%s" % (d["key"], d["n"], d["label"], d["route"],
              ("nuances " + ", ".join(d["nuances"]) + "; ") if d["nuances"] else "", d["note"]))
md += ["", "### `events` — what happened in the frozen history", "",
       "%d unplanned breakdowns, plus the deterministic rules applied per batch: %.0f%% of batches assay low enough to "
       "matter, %.0f%% fail spec outright, QC release takes %.1f-%.1f days, and %.0f%% of batches meet a utility over its cap."
       % (len(events["breakdowns"]), CFG.EXEC["yieldShortShare"] * 100, CFG.EXEC["offSpecShare"] * 100,
          CFG.EXEC["qcDays"][0], CFG.EXEC["qcDays"][1], CFG.EXEC["utilityTripShare"] * 100), "",
       "### `scenarios` — the launcher's anchors, chosen from this data", ""]
for k in sorted(scenarios, key=lambda x: (len(x), x)):
    md.append("- **%s** (%s) %s" % (k, scenarios[k]["nuance"], scenarios[k]["title"]))
md += ["", "### `data/planner-input.sample.json`", "",
       "The same plant written in the Bluemingo Production Planner's own input contract (`plan`, `plan_parameters`, "
       "`factories`, `skus`, `operations`, `machines`, `machine_capabilities`, `routings`, `block_times`, `order_lines`, "
       "`material_availability`, `product_mix`, `changeovers`) — a real chemicals test case for the product team, and a "
       "check that these masters map onto the contract.", ""]
with open(OUT("README.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(md) + "\n")

print("as-of %s | products %d, customers %d, orders %d, lines %d, %s kg, batches ~%d"
      % (iso(ASOF), len(products), len(customers), stats["orders"], stats["lines"], "{:,}".format(stats["kg"]), stats["batches"]))
print("load %s | binding %s %.3f | bottleneck class %s" % (stats["load"], stats["binding"], stats["bindingLoad"], bneck))
print("matrix %d cells (%d not permitted, %d clean-down, %d boil-out) | tight hold windows %d | lots %d | deliveries %d"
      % (len(matrix), len(fb), sum(1 for r in matrix if r["grade"] == "DEDICATE"), sum(1 for r in matrix if r["grade"] == "BOILOUT"), tight_holds, len(lots), len(deliveries)))
print("wrote %s (%d KB), chm-meta.js, README.md, planner-input.sample.json"
      % (OUT("chm-data.js"), os.path.getsize(OUT("chm-data.js")) // 1024))
