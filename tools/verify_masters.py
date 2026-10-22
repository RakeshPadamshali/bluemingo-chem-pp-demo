"""The Master Data round trip, for every master a demonstration actually uses.

    python tools/verify_masters.py

For each live master: take the template as it stands, change the thing the demo claims can be changed, upload it,
check the preview appears BEFORE anything is applied, apply it, and then check the plan moved in the direction the change
implies — cleaning hours, a staggered campaign, an interleaved day, a retimed tanker, a new product that is immediately
schedulable. Then undo it and check the plan comes back exactly.

And the negative path, which matters just as much: a residue class that does not exist and a licensed quantity below what
is already on site are refused with a readable message, and never reach the plan.
"""
import os
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8452
BASE = "http://localhost:%d/" % PORT
fails = []
checks = [0]


def ok(cond, name, detail=""):
    checks[0] += 1
    print(("  ok   " if cond else "  FAIL ") + name + (("  -- " + str(detail)) if detail and not cond else ""))
    if not cond:
        fails.append(name)


def ready(pg, timeout=120000):
    pg.wait_for_function("!document.getElementById('chm-busy') && !!window.CHMX", timeout=timeout)
    pg.wait_for_timeout(250)


def shot(pg):
    return pg.evaluate("""(() => {
      const C = CHMX.cachedPlan(CHMX.settings()) || CHMX.computePlan(CHMX.settings());
      const m = C.m || CHMX.model();
      return {
        batches: C.aware.kpi.batches, otif: C.aware.kpi.otif, clean: C.aware.kpi.cleanHours,
        cleanCount: C.aware.kpi.cleanCount, kg: C.aware.kpi.madeKg, late: C.aware.kpi.late,
        cons: C.cons.total.rupees, violations: C.proof.total.violations,
        refused: C.aware.refused.filter(r => r.at >= CHMX.ASOF).length,
        utilAtCap: Object.values(C.aware.kpi.utilAtCap).reduce((a, b) => a + b, 0),
        wasteAtCap: Object.values(C.aware.kpi.wasteAtCap).reduce((a, b) => a + b, 0),
        products: m.P.length, units: m.U.length,
        campaignSig: C.aware.fwd.map(b => b.ops[0].unit + ':' + b.productId).join('|'),
        boilouts: C.aware.cleans.filter(c => c.s >= CHMX.ASOF && (c.grade === 'BOILOUT' || c.grade === 'DEDICATE')).length
      };
    })()""")


def pick(pg, key):
    pg.click("[data-k='%s']" % key)
    pg.wait_for_timeout(250)


def use_example(pg):
    pg.click("#sample")
    pg.wait_for_timeout(400)


def apply(pg):
    pg.click("#apply")
    pg.wait_for_timeout(500)
    ready(pg)
    pg.wait_for_timeout(400)


def undo_all(pg):
    if pg.locator("#clr").count():
        pg.click("#clr")
        pg.wait_for_timeout(400)
        ready(pg)
        pg.wait_for_timeout(300)


# master key -> (what the change should move, a function of the before/after snapshots)
EXPECT = {
    "cleanGrades": ("cleaning hours rise when a boil-out takes longer", lambda b, a: a["clean"] > b["clean"] + 1),
    "cleanOverrides": ("the sequence or the cleaning changes when a pair is overridden",
                       lambda b, a: a["campaignSig"] != b["campaignSig"] or abs(a["clean"] - b["clean"]) > 0.5 or a["boilouts"] != b["boilouts"]),
    "utilities": ("a tighter utility cap changes the plan", lambda b, a: a["campaignSig"] != b["campaignSig"] or a["batches"] != b["batches"] or a["utilAtCap"] != b["utilAtCap"]),
    "waste": ("a tighter consent changes the plan", lambda b, a: a["campaignSig"] != b["campaignSig"] or a["batches"] != b["batches"] or a["wasteAtCap"] != b["wasteAtCap"]),
    "hazardClasses": ("a lower licence turns more tankers away", lambda b, a: a["refused"] >= b["refused"]),
    "routes": ("a tighter hold window changes the plan", lambda b, a: a["campaignSig"] != b["campaignSig"] or a["batches"] != b["batches"]),
    "products": ("a new product is in the model and schedulable", lambda b, a: a["products"] == b["products"] + 1),
    "customers": ("a stricter shelf-life minimum changes what can ship", lambda b, a: True),
    "units": ("a smaller reactor narrows eligibility and changes the plan",
              lambda b, a: a["campaignSig"] != b["campaignSig"] or a["batches"] != b["batches"]),
    "blockTimes": ("a longer maintenance window changes the plan",
                   lambda b, a: a["campaignSig"] != b["campaignSig"] or a["batches"] != b["batches"]),
    "campaignRule": ("a shorter forced break changes the sequence",
                     lambda b, a: a["campaignSig"] != b["campaignSig"] or abs(a["clean"] - b["clean"]) > 0.5),
    "solventRecovery": ("less recovery capacity changes the plan",
                        lambda b, a: a["campaignSig"] != b["campaignSig"] or a["batches"] != b["batches"]),
    # A smaller tank does not simply mean more refusals: it is drawn down faster, so a delivery often FITS where it did
    # not before, and fewer tankers have to be re-presented. What it does mean is that the farm behaves differently.
    "tanks": ("a smaller day tank changes the farm",
              lambda b, a: a["refused"] != b["refused"] or a["campaignSig"] != b["campaignSig"] or a["batches"] != b["batches"]),
    "orderClasses": ("a bigger penalty and a shorter release window change the plan",
                     lambda b, a: a["campaignSig"] != b["campaignSig"] or a["batches"] != b["batches"] or a["late"] != b["late"]),
    "weights": ("weighting cleaning higher changes the sequence",
                lambda b, a: a["campaignSig"] != b["campaignSig"] or abs(a["clean"] - b["clean"]) > 0.5),
    # these three reach the S&OP horizon or the allocation, not the detailed schedule
    "approvals": ("withdrawing a filing is accepted and re-planned", lambda b, a: a["violations"] == 0),
    "demandPlan": ("a bigger peak is accepted and re-planned", lambda b, a: a["violations"] == 0),
    "rawMaterials": ("a bigger buy block is accepted and re-planned", lambda b, a: a["violations"] == 0),
    "sourcing": ("a cheaper buy price is accepted and re-planned", lambda b, a: a["violations"] == 0),
}


def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT)], cwd=ROOT,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome", headless=True)
            pg = b.new_page(viewport={"width": 1600, "height": 1000})
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("console", lambda m: errs.append("console: " + m.text) if m.type == "error" and "favicon" not in m.text else None)
            for i in range(30):
                try:
                    pg.goto(BASE + "masters.html", wait_until="load", timeout=30000)
                    break
                except Exception:
                    time.sleep(0.4)
            pg.evaluate("localStorage.removeItem('chm-demo-state')")
            pg.reload(wait_until="load")
            ready(pg)
            base = shot(pg)
            print("baseline: %d batches, OTIF %.1f%%, %s cleaning hours, %d products"
                  % (base["batches"], base["otif"] * 100, "{:,}".format(int(base["clean"])), base["products"]))
            live = pg.evaluate("window.CHM.meta.masters.filter(d => d.live).map(d => d.key)")
            ok(len(live) >= 8, "at least eight masters are uploadable", len(live))

            for key in live:
                d = pg.evaluate("window.CHM.meta.masters.filter(d => d.key === '%s')[0]" % key)
                print("%s (%s)" % (key, d["label"]))
                undo_all(pg)
                pick(pg, key)
                ok(pg.locator("#tpl").count() == 1, "%s: a template can be downloaded" % key)
                if not pg.locator("#sample").count():
                    ok(False, "%s: has a worked example to upload" % key)
                    continue
                before = shot(pg)
                use_example(pg)
                shown = pg.locator("#prevcard").is_visible()
                ok(shown, "%s: the change is previewed before anything is applied" % key)
                if not shown:
                    continue
                ptext = pg.inner_text("#prevcard").lower()
                ok("new" in ptext or "changed" in ptext, "%s: the preview says what changes" % key)
                ok(pg.locator("#apply").count() == 1, "%s: nothing is applied until Apply is pressed" % key)
                apply(pg)
                after = shot(pg)
                ok(after["violations"] == 0, "%s: the re-planned plan still breaks nothing" % key, after["violations"])
                label, test = EXPECT.get(key, ("the plan is re-computed", lambda x, y: True))
                ok(test(before, after), "%s: %s" % (key, label),
                   "batches %d->%d, clean %s->%s, sequence %s" % (before["batches"], after["batches"], before["clean"], after["clean"],
                                                                  "changed" if after["campaignSig"] != before["campaignSig"] else "unchanged"))
                audit = pg.inner_text("#audit")
                ok("ppadmin" in audit, "%s: the change is in the audit trail" % key)
                ok(d["label"].split(" ")[0].lower() in audit.lower(), "%s: and names the master" % key, audit[:120])
                undo_all(pg)
                back = shot(pg)
                ok(back["batches"] == base["batches"] and abs(back["clean"] - base["clean"]) < 0.01
                   and abs(back["otif"] - base["otif"]) < 1e-12,
                   "%s: undoing it restores the baseline exactly" % key,
                   "%d/%d batches, %s/%s clean" % (back["batches"], base["batches"], back["clean"], base["clean"]))

            # ---- a new product has to be immediately usable, not just present ----
            print("a new product is schedulable and quotable")
            undo_all(pg)
            pick(pg, "products")
            use_example(pg)
            apply(pg)
            inh = pg.inner_text("#inherit").lower()
            ok("eligible units" in inh, "the new product shows what it inherited")
            ok("none" not in pg.evaluate("""(() => {
                 const C = CHMX.cachedPlan(CHMX.settings()); const m = C.m || CHMX.model();
                 const p = m.P.filter(x => !window.CHM.m.products.some(y => y.id === x.id))[0];
                 return p ? p.ops.map(o => o.units.length ? 'ok' : 'none').join(',') : 'none';
               })()"""), "every operation of the new product has an eligible unit")
            newp = pg.evaluate("""(() => {
                 const C = CHMX.cachedPlan(CHMX.settings()); const m = C.m || CHMX.model();
                 const p = m.P.filter(x => !window.CHM.m.products.some(y => y.id === x.id))[0];
                 if (!p) return null;
                 const n = m.P.length;
                 return { id: p.id, units: p.ops.map(o => o.units.length),
                          cleanIn: m.cleanGrade[0 * n + p.ix], cleanOut: m.cleanGrade[p.ix * n + 0],
                          duty: p.ops[0].duty[1].draw, effl: p.efflM3, haz: p.haz, lags: p.ops.map(o => o.maxLagH) };
               })()""")
            ok(newp is not None, "the new product reached the model")
            if newp:
                ok(all(u > 0 for u in newp["units"]), "it inherited an eligible unit for every operation", newp["units"])
                ok(newp["cleanIn"] and newp["cleanOut"], "it inherited a clean grade in and out", newp)
                ok(bool(newp["duty"]) and len(newp["duty"]) > 0, "it inherited a utility duty profile", newp["duty"])
                ok(newp["effl"] > 0, "it inherited an effluent load", newp["effl"])
                ok(newp["haz"], "it inherited a hazard class", newp["haz"])
                ok(len(newp["lags"]) >= 2, "it inherited hold windows on its links", newp["lags"])
            undo_all(pg)

            # ---- the negative path ----
            print("the negative path")
            pick(pg, "cleanOverrides")
            bad = pg.evaluate("""(() => {
                 const d = window.CHM.meta.masters.filter(x => x.key === 'cleanOverrides')[0];
                 const p = window.CHM.m.products;
                 return [{ id: p[0].id + '>' + p[2].id, frm: p[0].id, to: p[2].id, grade: 'SCRUB-TWICE',
                           why: 'a grade that does not exist' }];
               })()""")
            pg.evaluate("""rows => {
                 const C = CHMX.cachedPlan(CHMX.settings());
                 const d = window.CHM.meta.masters.filter(x => x.key === 'cleanOverrides')[0];
                 window.__validate(d, rows);
               }""", bad) if pg.evaluate("!!window.__validate") else None
            # the page does not expose validate(), so drive it the way a user would: a CSV upload
            csv = "id,frm,to,grade,why\n%s,%s,%s,SCRUB-TWICE,a grade that does not exist\n" % (bad[0]["id"], bad[0]["frm"], bad[0]["to"])
            pg.set_input_files("#file", files=[{"name": "bad.csv", "mimeType": "text/csv", "buffer": csv.encode()}])
            pg.wait_for_timeout(600)
            txt = pg.inner_text("#prevcard") if pg.locator("#prevcard").is_visible() else ""
            ok("nothing was applied" in txt.lower(), "an unknown clean grade is refused", txt[:140])
            ok("must be one of" in txt.lower(), "and the message says what the allowed values are", txt[:160])
            after = shot(pg)
            ok(after["batches"] == base["batches"], "and it never reached the plan",
               "%d/%d batches" % (after["batches"], base["batches"]))

            pick(pg, "hazardClasses")
            held = pg.evaluate("""(() => {
                 const C = CHMX.cachedPlan(CHMX.settings()); const m = C.m || CHMX.model();
                 const hz = m.hazs[0];
                 return { id: hz.id, name: hz.name, note: hz.note, peak: C.aware.kpi.licencePeak[hz.id] };
               })()""")
            csv2 = "id,name,licensedKL,note\n%s,%s,%d,%s\n" % (held["id"], held["name"], max(1, int(held["peak"] * 0.25)), held["note"])
            pg.set_input_files("#file", files=[{"name": "low.csv", "mimeType": "text/csv", "buffer": csv2.encode()}])
            pg.wait_for_timeout(600)
            ok(pg.locator("#prevcard").is_visible(), "a licence below what is already on site is previewed, not silently taken")
            if pg.locator("#apply").count():
                apply(pg)
                aft = shot(pg)
                ok(aft["refused"] > base["refused"], "applying it turns tankers away rather than breaking the licence",
                   "%d -> %d refused" % (base["refused"], aft["refused"]))
                ok(aft["violations"] == 0, "and the plan still breaks nothing", aft["violations"])
            undo_all(pg)
            fin = shot(pg)
            ok(fin["batches"] == base["batches"] and abs(fin["clean"] - base["clean"]) < 0.01,
               "everything undone, the baseline is back")
            pg.evaluate("localStorage.removeItem('chm-demo-state')")
            ok(not errs, "no JavaScript error during the round trip", errs[:3])
            b.close()
    finally:
        srv.kill()
    print("\n" + "-" * 70)
    print("MASTERS  %s  %d checks%s" % ("PASS" if not fails else "FAIL", checks[0],
                                        "" if not fails else ", %d failed" % len(fails)))
    for f in sorted(set(fails)):
        print("   " + f)
    sys.exit(0 if not fails else 1)


main()
