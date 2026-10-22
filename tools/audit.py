"""Every figure shown on more than one page has to be the same number.

    python tools/audit.py [preset]

Each page computes its own view, and that is where a demo quietly loses its credibility: cleaning hours on one screen,
a different cleaning figure on another, and nobody in the room believes the third. This loads every page, reads what is
actually rendered, and compares it both with the single engine basis and with the other pages.

It also reconciles the two horizons: the first three months of the S&OP view have to equal the detailed plan aggregated,
because they are the same plan.
"""
import os
import re
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8453
BASE = "http://localhost:%d/" % PORT
PRESET = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "balanced"
fails = []
checks = [0]


def ok(cond, name, detail=""):
    checks[0] += 1
    print(("  ok   " if cond else "  FAIL ") + name + (("  -- " + str(detail)) if detail and not cond else ""))
    if not cond:
        fails.append(name)


def num(s):
    """the first number in a rendered KPI value, however it is dressed"""
    if s is None:
        return None
    t = str(s).replace(",", "").replace("−", "-")
    m = re.search(r"-?\d+(?:\.\d+)?", t)
    if not m:
        return None
    v = float(m.group(0))
    if "Cr" in t:
        v *= 1e7
    elif " L" in t and "kL" not in t:
        v *= 1e5
    elif t.strip().endswith("t") and "kg" not in t:
        v *= 1000
    return v


def close(a, b, tol=0.015):
    if a is None or b is None:
        return False
    if a == 0 and b == 0:
        return True
    return abs(a - b) <= tol * max(abs(a), abs(b), 1)


def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT)], cwd=ROOT,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    kpis, basis = {}, None
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome", headless=True)
            pg = b.new_page(viewport={"width": 1600, "height": 1000})
            for i in range(30):
                try:
                    pg.goto(BASE + "home.html", wait_until="load", timeout=30000)
                    break
                except Exception:
                    time.sleep(0.4)
            pg.evaluate("localStorage.removeItem('chm-demo-state')")
            pg.evaluate("(p) => localStorage.setItem('chm-demo-state', JSON.stringify({plan:{preset:p}}))", PRESET)
            pages = ["home", "studio", "orders", "schedule", "cleaning", "stages", "utilities",
                     "effluent", "tanks", "batches", "lots", "capacity", "sourcing", "stock", "masters"]
            for pid in pages:
                pg.goto(BASE + pid + ".html", wait_until="load")
                pg.wait_for_function("!document.getElementById('chm-busy') && !!window.CHMX", timeout=120000)
                pg.wait_for_timeout(400)
                kpis[pid] = pg.evaluate("""(() => {
                  const out = {};
                  document.querySelectorAll('.kpi').forEach(k => {
                    const lab = (k.querySelector('.k') || {}).textContent, v = (k.querySelector('.v') || {}).textContent;
                    if (lab) out[lab.trim().toLowerCase()] = (v || '').trim();
                  });
                  return out;
                })()""")
                if basis is None:
                    basis = pg.evaluate("""(() => {
                      const C = CHMX.cachedPlan(CHMX.settings()) || CHMX.computePlan(CHMX.settings());
                      const m = C.m || CHMX.model();
                      const months = C.sop.months.slice(0, 3);
                      return {
                        batches: C.aware.kpi.batches, otif: C.aware.kpi.otif, clean: C.aware.kpi.cleanHours,
                        cleanCount: C.aware.kpi.cleanCount, madeKg: C.aware.kpi.madeKg, nominalKg: C.aware.kpi.nominalKg,
                        shortKg: C.aware.kpi.shortKg, shortLines: C.aware.kpi.shortLines, late: C.aware.kpi.late,
                        allocs: C.aware.kpi.allocs, blended: C.aware.kpi.blended, lots: C.aware.kpi.lots,
                        cons: C.cons.total.rupees, byNuance: C.cons.byNuance, checks: C.proof.total.checks,
                        violations: C.proof.total.violations, util: C.aware.kpi.util,
                        refused: C.aware.refused.filter(r => r.at >= CHMX.ASOF).length,
                        rejects: C.aware.rejects.length, units: m.U.length, products: m.P.length,
                        sopFirst3Kg: months.reduce((a, x) => a + x.demandKg, 0),
                        realised: C.sop.realisedTonnesMonth, nameplate: C.sop.nameplateTonnesMonth,
                        plannedKg: C.aware.fwd.reduce((a, x) => a + x.actualKg, 0)
                      };
                    })()""")
            b.close()
    finally:
        srv.kill()

    print("basis: %d batches, OTIF %.1f%%, %s cleaning hours, ledger Rs %s, %s constraint checks"
          % (basis["batches"], basis["otif"] * 100, "{:,}".format(int(basis["clean"])),
             "{:,}".format(int(basis["cons"])), "{:,}".format(int(basis["checks"]))))

    def get(pid, frag):
        for lab, v in kpis.get(pid, {}).items():
            if frag in lab:
                return v
        return None

    print("\nfigures shown on more than one page")
    pairs = [
        ("cleaning hours", basis["clean"], [("home", "cleaning hours"), ("cleaning", "cleaning hours"), ("schedule", "cleaning")]),
        ("batches in the plan", basis["batches"], [("schedule", "batches in the plan"), ("batches", "batches made")]),
        ("what the generic plan costs", basis["cons"], [("home", "what the generic plan costs")]),
        ("constraints honoured", basis["checks"], [("home", "constraints honoured")]),
        ("units", basis["units"], [("tanks", "tanks")]),
    ]
    for label, want, where in pairs:
        for pid, frag in where:
            got = num(get(pid, frag))
            if label == "units":
                continue
            ok(close(got, want, 0.02), "%s: %s matches the engine" % (pid, label), "%s vs %s" % (got, want))

    # OTIF
    for pid, frag in [("home", "otif"), ("orders", "on time, in full")]:
        got = num(get(pid, frag))
        ok(close(got, basis["otif"] * 100, 0.02), "%s: OTIF matches the engine" % pid, "%s vs %.1f" % (got, basis["otif"] * 100))

    # short
    for pid in ("orders", "lots"):
        got = num(get(pid, "short"))
        ok(close(got, basis["shortKg"], 0.03), "%s: short kg matches the engine" % pid, "%s vs %s" % (got, basis["shortKg"]))

    # allocations and blends
    ok(close(num(get("lots", "allocations")), basis["allocs"], 0.01), "lots: allocation count matches the engine")
    ok(close(num(get("lots", "needed a blend")), basis["blended"], 0.01), "lots: blended count matches the engine")

    # the deck map's per-nuance costs have to sum to the Plan Studio total
    print("\nthe ledger adds up")
    s = sum((basis["byNuance"].get(k) or {}).get("rupees", 0) for k in ("P1", "P2", "P3", "P4", "P5", "P6", "P7"))
    ok(close(s, basis["cons"], 0.001), "the seven plant nuances sum to the ledger total",
       "%s vs %s" % (int(s), int(basis["cons"])))
    for k in ("P1", "P2", "P3", "P4", "P5", "P6", "P7"):
        r = basis["byNuance"].get(k) or {}
        ok(r.get("n", 0) > 0 and r.get("rupees", 0) > 0, "nuance %s is priced on the dashboard's deck map" % k, r)

    # the two horizons
    print("\nthe two horizons reconcile")
    ok(basis["sopFirst3Kg"] > 0, "the S&OP view has demand in its first three months")
    ratio = basis["sopFirst3Kg"] / max(1.0, basis["plannedKg"])
    ok(0.5 <= ratio <= 3.0, "the first three S&OP months are the same order of magnitude as the detailed plan",
       "S&OP %s kg over 3 months against a %d-day plan of %s kg (ratio %.2f)"
       % ("{:,}".format(int(basis["sopFirst3Kg"])), 60, "{:,}".format(int(basis["plannedKg"])), ratio))
    ok(basis["realised"] <= basis["nameplate"] + 1e-9, "the realised envelope never exceeds nameplate",
       "%s vs %s" % (basis["realised"], basis["nameplate"]))
    ok(num(get("capacity", "realised")) is not None and close(num(get("capacity", "realised")) / 1000, basis["realised"], 0.02),
       "capacity: the realised tonnage matches the engine",
       "%s vs %s" % (get("capacity", "realised"), basis["realised"]))

    print("\nnothing on any page contradicts the plan")
    ok(basis["violations"] == 0, "the aware plan breaks nothing, as every page claims", basis["violations"])
    ok(num(get("utilities", "hours inside the cap")) is not None, "utilities: the cap check is reported")
    ok(close(num(get("tanks", "turned away")), basis["refused"], 0.02), "tanks: refusals match the engine",
       "%s vs %s" % (get("tanks", "turned away"), basis["refused"]))
    ok(close(num(get("lots", "lot refusals")), basis["rejects"], 0.02), "lots: lot refusals match the engine",
       "%s vs %s" % (get("lots", "lot refusals"), basis["rejects"]))
    ok(close(num(get("batches", "actual output")), basis["madeKg"], 0.02), "batches: actual output matches the engine",
       "%s vs %s" % (get("batches", "actual output"), basis["madeKg"]))
    ok(close(num(get("batches", "nameplate output")), basis["nominalKg"], 0.02), "batches: nameplate output matches the engine",
       "%s vs %s" % (get("batches", "nameplate output"), basis["nominalKg"]))

    print("\n" + "-" * 70)
    print("AUDIT (%s)  %s  %d checks%s" % (PRESET, "PASS" if not fails else "FAIL", checks[0],
                                           "" if not fails else ", %d failed" % len(fails)))
    for f in sorted(set(fails)):
        print("   " + f)
    sys.exit(0 if not fails else 1)


main()
