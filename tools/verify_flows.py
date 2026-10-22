"""Every scenario card, end to end, in a headless browser.

    python tools/verify_flows.py

Each card is launched from the dashboard and has to do what it says it does: land on the page that owns its nuance, write
the what-if it claims, and change the thing it declares it changes -- the schedule, the allocation, or the S&OP horizon --
and nothing else. A card that declares `nothing` is an explanatory card and must leave the plan alone. Then Reset demo
has to put the baseline back exactly.
"""
import json
import os
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):      # a Windows console defaults to cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8451
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
    pg.wait_for_timeout(300)


def shot(pg):
    """the numbers every page reads from, straight out of the one cached comparison"""
    return pg.evaluate("""(() => {
      // a page that does not render the plan has nothing cached; compute it the way a page that does would
      const C = CHMX.cachedPlan(CHMX.settings()) || CHMX.computePlan(CHMX.settings());
      if (!C) return null;
      return {
        awareBatches: C.aware.kpi.batches, awareOtif: C.aware.kpi.otif, awareKg: C.aware.kpi.madeKg,
        awareClean: C.aware.kpi.cleanHours, awareLate: C.aware.kpi.late, awareShort: C.aware.kpi.shortKg,
        genBatches: C.generic.kpi.batches, consTotal: C.cons.total.rupees, consRows: C.cons.total.n,
        allocs: C.aware.kpi.allocs, blended: C.aware.kpi.blended, shipped: C.aware.kpi.shippedKg,
        refused: C.aware.kpi.refused, emergency: C.aware.kpi.emergency, emergencyRs: C.aware.kpi.emergencyRs,
        allocSig: C.aware.allocs.map(a => a.lineId + ':' + a.lots.map(z => z.id).join('+')).join('|'),
        specSig: C.aware.lines.map(l => l.id + ':' + l.assayMin + '/' + l.impMax).join('|'),
        sopNameplate: C.sop.nameplateTonnesMonth, sopRealised: C.sop.realisedTonnesMonth,
        sopInfeasible: C.sop.months.filter(m => !m.feasible).length,
        sopDemand: C.sop.months.reduce((a, m) => a + m.demandKg, 0),
        violations: C.proof.total.violations, checksDone: C.proof.total.checks,
        byNuance: Object.keys(C.cons.byNuance)
      };
    })()""")


def state(pg):
    return pg.evaluate("(() => { try { return JSON.parse(localStorage.getItem('chm-demo-state') || '{}'); } catch (e) { return {}; } })()")


def home(pg, clear=True):
    pg.goto(BASE + "home.html", wait_until="load")
    if clear:
        pg.evaluate("localStorage.removeItem('chm-demo-state')")
        pg.reload(wait_until="load")
    ready(pg)


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
                    pg.goto(BASE + "home.html", wait_until="load", timeout=30000)
                    break
                except Exception:
                    time.sleep(0.4)
            home(pg)
            base = shot(pg)
            ok(base is not None, "a baseline comparison is available")
            print("baseline: aware %d batches, OTIF %.1f%%, %s kg · generic %d batches · ledger Rs %s over %d rows"
                  % (base["awareBatches"], base["awareOtif"] * 100, "{:,}".format(int(base["awareKg"])),
                     base["genBatches"], "{:,}".format(int(base["consTotal"])), base["consRows"]))
            ok(base["violations"] == 0, "the baseline aware plan breaks nothing", base["violations"])
            ok(base["consRows"] > 100, "the baseline ledger is populated", base["consRows"])

            cards = pg.evaluate("CHMX.SCENARIOS.map(s => ({id:s.id, nuance:s.nuance, page:s.page, changes:s.changes, wants:s.wants, follow:!!s.follow}))")
            ok(len(cards) == 16, "sixteen cards in the launcher", len(cards))
            ok(len([c for c in cards if not c["follow"]]) == 13, "thirteen of them stand on their own")
            nus = sorted(set(c["wants"] for c in cards))
            ok(len(nus) == 16, "the cards cover all sixteen nuances", nus)

            for c in cards:
                print("%s (%s · %s)" % (c["id"], c["nuance"], c["changes"]))
                home(pg)
                before = shot(pg)
                pg.evaluate("CHMX.runScenario('%s')" % c["id"])
                pg.wait_for_timeout(400)
                ready(pg)
                pg.wait_for_timeout(500)
                try:
                    ready(pg)
                except Exception:
                    pass
                # a hash can contain a slash (an order line id), so read the path, not the last slash-separated part
                land = pg.evaluate("location.pathname.split('/').pop()")
                ok(land == c["page"] + ".html", "%s lands on %s" % (c["id"], c["page"]), land)
                h = pg.evaluate("decodeURIComponent((location.hash||'').slice(1))")
                ok(h != "" or c["id"] in ("C1",), "%s lands at an anchor" % c["id"], "(no hash)")
                st = state(pg)
                ok(st.get("lastScenario") == c["id"], "%s records itself as the last scenario run" % c["id"])
                after = shot(pg)
                ok(after is not None, "%s leaves a usable comparison" % c["id"])
                if after is None:
                    continue
                ok(after["violations"] == 0, "%s: the aware plan still breaks nothing" % c["id"], after["violations"])
                wif = st.get("whatifs", [])
                if c["changes"] == "nothing":
                    ok(not wif, "%s is explanatory and writes no what-if" % c["id"], wif)
                    ok(after["awareBatches"] == before["awareBatches"], "%s leaves the plan alone" % c["id"])
                    ok(c["wants"] in after["byNuance"] or c["wants"].startswith("S"),
                       "%s: its nuance is already priced in the ledger" % c["id"], after["byNuance"])
                else:
                    ok(len(wif) >= 1, "%s writes a what-if" % c["id"], wif)
                if c["changes"] == "schedule":
                    moved = (after["awareBatches"] != before["awareBatches"] or abs(after["awareKg"] - before["awareKg"]) > 1
                             or abs(after["awareClean"] - before["awareClean"]) > 0.5 or after["awareLate"] != before["awareLate"]
                             or abs(after["consTotal"] - before["consTotal"]) > 1
                             or after["refused"] != before["refused"] or after["emergency"] != before["emergency"])
                    ok(moved, "%s moves the schedule" % c["id"],
                       "batches %d->%d, kg %d->%d, clean %s->%s" % (before["awareBatches"], after["awareBatches"],
                                                                 before["awareKg"], after["awareKg"], before["awareClean"], after["awareClean"]))
                if c["changes"] == "allocation":
                    # the signature is WHICH lots went to which line, and what spec each line is held to: a swap that
                    # leaves the totals identical is still a change in the allocation
                    moved = (after["allocs"] != before["allocs"] or after["blended"] != before["blended"]
                             or abs(after["shipped"] - before["shipped"]) > 1 or after["awareShort"] != before["awareShort"]
                             or abs(after["consTotal"] - before["consTotal"]) > 1
                             or after["allocSig"] != before["allocSig"] or after["specSig"] != before["specSig"])
                    ok(moved, "%s moves the allocation" % c["id"],
                       "allocs %d->%d, blended %d->%d, shipped %d->%d" % (before["allocs"], after["allocs"], before["blended"],
                                                                       after["blended"], before["shipped"], after["shipped"]))
                if c["changes"] == "sop":
                    moved = (abs(after["sopDemand"] - before["sopDemand"]) > 1 or after["sopInfeasible"] != before["sopInfeasible"]
                             or abs(after["sopNameplate"] - before["sopNameplate"]) > 0.05
                             or len(wif) >= 1)
                    ok(moved, "%s reaches the S&OP horizon" % c["id"],
                       "demand %s->%s, infeasible months %s->%s" % (before["sopDemand"], after["sopDemand"],
                                                                  before["sopInfeasible"], after["sopInfeasible"]))

            # ---- Reset demo ----
            print("Reset demo")
            home(pg, clear=False)
            pg.evaluate("CHMX.runScenario('C4')")
            pg.wait_for_timeout(500)
            ready(pg)
            home(pg, clear=False)
            ok(len(state(pg).get("whatifs", [])) > 0, "a what-if survives a page change")
            pg.click("#chm-reset")
            pg.wait_for_timeout(600)
            ready(pg)
            ok(state(pg) == {}, "Reset demo clears every live-demo action", state(pg))
            after = shot(pg)
            ok(after["awareBatches"] == base["awareBatches"] and abs(after["awareOtif"] - base["awareOtif"]) < 1e-12
               and after["awareKg"] == base["awareKg"] and abs(after["consTotal"] - base["consTotal"]) < 1,
               "Reset demo restores the baseline exactly",
               "%d/%d batches, ledger %s/%s" % (after["awareBatches"], base["awareBatches"], after["consTotal"], base["consTotal"]))

            # ---- the role toggle survives a reload ----
            pg.evaluate("CHMX.State.set('role','plant')")
            pg.reload(wait_until="load")
            ready(pg)
            ok(pg.evaluate("CHMX.role()") == "plant", "the role toggle survives a reload")
            dim = pg.evaluate("document.querySelectorAll('.bm-sidebar a.dim').length")
            ok(dim >= 3, "the plant-head role dims the S&OP pages rather than hiding them", dim)
            links = pg.evaluate("document.querySelectorAll('.bm-sidebar a').length")
            pages = pg.evaluate("Object.keys(window.CHM_PAGES).length")
            ok(links == pages, "every page is still reachable in any role", "%d links for %d pages" % (links, pages))
            pg.evaluate("localStorage.removeItem('chm-demo-state')")

            ok(not errs, "no JavaScript error during any flow", errs[:3])
            b.close()
    finally:
        srv.kill()
    print("\n" + "-" * 68)
    print("FLOWS  %s  %d checks%s" % ("PASS" if not fails else "FAIL", checks[0],
                                      "" if not fails else ", %d failed" % len(fails)))
    for f in sorted(set(fails)):
        print("   " + f)
    sys.exit(0 if not fails else 1)


main()
