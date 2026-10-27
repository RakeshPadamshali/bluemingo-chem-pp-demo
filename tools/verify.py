"""Every page, headless: no JavaScript error, no failed request, NO REQUEST THAT LEAVES THE SITE, content actually
rendered, and the nuance registry fully owned.

    python tools/verify.py [--shots]

The off-site check is the one that matters most for a demo that has to run in a room with no network: fonts, icons and
every library are vendored under assets/vendor, and this fails the build if anything reaches for a CDN.
"""
import os
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):      # a Windows console defaults to cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8450
BASE = "http://localhost:%d/" % PORT
SHOTS = "--shots" in sys.argv
SHOT_DIR = os.path.join(ROOT, "tools", "shots")

PAGES = [
    ("index", "the tab host", "#chm-sidebar a"),
    ("home", "PP Dashboard", "#deck .nu"),
    ("studio", "Plan Studio", "#led tbody tr"),
    ("orders", "Order Book & Promise", "#ls tbody tr"),
    ("schedule", "Block Schedule", ".g-row .g-bar"),
    ("cleaning", "Cleaning & Campaigns", ".cm td[data-k]"),
    ("stages", "Multi-stage & Hold Times", ".clock .wb"),
    ("utilities", "Utilities & Thermal Duty", ".duty .col"),
    ("effluent", "Effluent & Solvent Recovery", ".days .d"),
    ("tanks", "Tank Farm & Hazard Licence", ".tank .tf"),
    ("batches", "Batch Record & Yield", "#reg tbody tr"),
    ("lots", "Lots, Blending & Allocation", "#al tbody tr"),
    ("report", "Production Plan Report", "#reg tbody tr"),
    ("capacity", "Capacity, Mix & Margin", ".mrow .mf"),
    ("sourcing", "Sourcing & Supply", ".ap td"),
    ("stock", "Stock, Shelf Life & Pack", ".ladder2 .lf"),
    ("masters", "Master Data", ".mitem[data-k]"),
]

fails = []
checks = [0]


def ok(cond, name, detail=""):
    checks[0] += 1
    print(("  ok   " if cond else "  FAIL ") + name + (("  -- " + str(detail)) if detail and not cond else ""))
    if not cond:
        fails.append(name)


def main():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT)], cwd=ROOT,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if SHOTS:
        os.makedirs(SHOT_DIR, exist_ok=True)
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome", headless=True)
            for pid, label, sel in PAGES:
                pg = b.new_page(viewport={"width": 1600, "height": 1000})
                errs, bad, offsite = [], [], []
                pg.on("pageerror", lambda e: errs.append(str(e)))
                pg.on("console", lambda msg: errs.append("console: " + msg.text)
                      if msg.type == "error" and "favicon" not in msg.text else None)
                pg.on("response", lambda r: bad.append("%d %s" % (r.status, r.url))
                      if r.status >= 400 and "favicon" not in r.url else None)
                pg.on("request", lambda r: offsite.append(r.url)
                      if not r.url.startswith(BASE) and not r.url.startswith("data:") else None)
                for i in range(30):
                    try:
                        pg.goto(BASE + pid + ".html", wait_until="load", timeout=30000)
                        break
                    except Exception:
                        time.sleep(0.4)
                try:
                    pg.wait_for_function("!document.getElementById('chm-busy')", timeout=90000)
                except Exception:
                    pass
                pg.wait_for_timeout(500)
                print("%s (%s)" % (pid, label))
                ok(not errs, "%s: no JavaScript error" % pid, errs[:3])
                ok(not bad, "%s: every request served" % pid, bad[:3])
                ok(not offsite, "%s: nothing leaves the site" % pid, offsite[:3])
                try:
                    cnt = pg.locator(sel).count()
                except Exception:
                    cnt = 0
                ok(cnt > 0, "%s: content rendered (%s)" % (pid, sel), "0 matches")
                body = pg.inner_text("body")
                ok(len(body) > 400, "%s: the page says something" % pid, "%d characters" % len(body))
                ok("undefined" not in body and "NaN" not in body and "[object" not in body,
                   "%s: no undefined, NaN or raw object on screen" % pid,
                   [w for w in ("undefined", "NaN", "[object") if w in body])
                # Markup rendered AS TEXT. It happens whenever a helper that returns HTML is handed to something that
                # escapes it, and it reads as a broken page rather than as a missing value, so the check above misses it.
                tags = [w for w in ("<span", "<div", "<i ", "<b>", "&lt;span", "&lt;div") if w in body]
                ok(not tags, "%s: no markup rendered as text" % pid, tags)
                if pid in ("index", "home", "studio"):
                    ok("Bluemingo" in body, "%s: carries the Bluemingo name" % pid)
                if pid == "home":
                    n = pg.locator("#deck .nu").count()
                    ok(n == 16, "home: the deck map shows all sixteen nuances", "%d chips" % n)
                    owned = pg.evaluate("window.CHM_NUANCES.map(function(x){return x.page;})")
                    pages = pg.evaluate("Object.keys(window.CHM_PAGES)")
                    orphan = sorted(set(owned) - set(pages))
                    ok(not orphan, "home: every nuance is owned by a real page", orphan)
                    ids = pg.evaluate("window.CHM_NUANCES.map(function(x){return x.id;})")
                    ok(len(ids) == len(set(ids)) == 16, "home: sixteen distinct nuances, none twice", len(set(ids)))
                    ok(pg.locator(".kpi").count() >= 6, "home: the KPI row is complete")
                    kpis = pg.evaluate("[...document.querySelectorAll('.kpi .v')].map(e=>e.textContent)")
                    ok(all(k.strip() not in ("", "--") for k in kpis), "home: no KPI tile renders a dash", kpis)
                    ok(pg.locator(".scen .sc").count() >= 13, "home: thirteen scenario cards",
                       pg.locator(".scen .sc").count())
                if pid == "cleaning":
                    ok(pg.locator(".cm td[data-k]").count() > 60, "cleaning: the matrix is a grid, not a list",
                       pg.locator(".cm td[data-k]").count())
                    ok(pg.locator(".lrow").count() >= 10, "cleaning: a campaign ladder per unit", pg.locator(".lrow").count())
                    ok(pg.locator(".cm td.ovr").count() > 0, "cleaning: the overrides are marked")
                if pid == "stages":
                    ok(pg.locator(".route .op").count() >= 2, "stages: the route is drawn")
                    ok(pg.locator(".route .lk").count() >= 1, "stages: with the link lags on it")
                    ok(pg.locator(".clock").count() >= 20, "stages: the hold clock is populated", pg.locator(".clock").count())
                    over = pg.evaluate("document.querySelectorAll('.clock .wf2.over').length")
                    ok(over == 0, "stages: no link in the aware plan is past its window", over)
                if pid == "schedule":
                    ok(pg.locator(".g-row").count() >= 15, "schedule: every unit has a lane", pg.locator(".g-row").count())
                    ok(pg.locator(".g-bar").count() > 40, "schedule: the Gantt has bars", pg.locator(".g-bar").count())
                    ok(pg.locator(".g-bar.chg").count() > 0, "schedule: cleaning is drawn on the Gantt")
                    ok(pg.locator(".g-bar.down").count() > 0, "schedule: block time is drawn on the Gantt")
                    ok(pg.locator(".g-now").count() > 0, "schedule: the as-of moment is marked")
                if pid == "utilities":
                    ok(pg.locator(".duty .col").count() > 40, "utilities: the duty curve is drawn", pg.locator(".duty .col").count())
                    ok(pg.locator(".duty .capline").count() > 0, "utilities: the cap is drawn on it")
                    over = pg.evaluate("document.querySelectorAll('.duty .col.over').length")
                    ok(over == 0, "utilities: the aware plan never goes over the cap", over)
                    ok(pg.locator(".segbar div").count() >= 3, "utilities: the three-segment duty profile is shown")
                if pid == "effluent":
                    ok(pg.locator(".days .d").count() > 30, "effluent: a bar per day", pg.locator(".days .d").count())
                    ok(pg.locator(".days .capl").count() > 0, "effluent: the consent is drawn on it")
                    ok(pg.evaluate("document.querySelectorAll('.days .d.over').length") == 0,
                       "effluent: the aware plan never exceeds a consent")
                    ok(pg.locator(".flow .bx").count() >= 4, "effluent: the solvent loop is drawn")
                if pid == "tanks":
                    ok(pg.locator(".bund").count() >= 3, "tanks: the farm is grouped by bund", pg.locator(".bund").count())
                    ok(pg.locator(".tank").count() >= 8, "tanks: every tank has a gauge", pg.locator(".tank").count())
                    ok(pg.locator(".lic .col").count() > 30, "tanks: the licence position is drawn day by day")
                    ok(pg.evaluate("document.querySelectorAll('.lic .col.over').length") == 0,
                       "tanks: the aware plan never exceeds a licensed quantity")
                if pid == "orders":
                    ok(pg.locator("#ls tbody tr").count() > 30, "orders: the book is listed", pg.locator("#ls tbody tr").count())
                    pg.locator("#ls tbody tr.lrow").first.click(); pg.wait_for_timeout(300)
                    ok(pg.locator(".bind").count() >= 2, "orders: a line explains what sets its date", pg.locator(".bind").count())
                    # .sub-title is uppercased by CSS, so compare case-insensitively
                    ok("what sets this date" in pg.inner_text("body").lower(), "orders: that explanation is labelled")
                if pid == "batches":
                    ok(pg.locator("#reg tbody tr").count() > 30, "batches: the register is listed", pg.locator("#reg tbody tr").count())
                    ok(pg.locator(".yrow").count() >= 5, "batches: realisation per product", pg.locator(".yrow").count())
                    ok(pg.locator(".dots .pt").count() >= 3, "batches: every batch of one product is plotted")
                if pid == "lots":
                    ok(pg.locator("#al tbody tr").count() >= 5, "lots: allocations are listed", pg.locator("#al tbody tr").count())
                    ok(pg.locator(".spec .win").count() == 3, "lots: assay, impurity and particle size each get a window",
                       pg.locator(".spec .win").count())
                    ok(pg.locator(".spec .pt.blend").count() == 3, "lots: and the blend is placed in each")
                    ok(pg.locator(".gen .bx").count() >= 3, "lots: the genealogy is drawn")
                if pid == "capacity":
                    ok(pg.locator(".struck").count() == 1, "capacity: the single tonnage number is struck through")
                    ok(pg.locator(".mrow.flip").count() == 2, "capacity: the two products whose ranking reverses are marked",
                       pg.locator(".mrow.flip").count())
                    ok(pg.locator(".mo").count() >= 12, "capacity: twelve months against a finite plant", pg.locator(".mo").count())
                if pid == "sourcing":
                    ok(pg.locator(".opt").count() >= 4, "sourcing: make, buy and toll each costed", pg.locator(".opt").count())
                    ok(pg.locator(".ap td.no").count() > 0, "sourcing: the approval matrix has gaps in it")
                    ok(pg.locator(".ap td.yes").count() > 0, "sourcing: and approvals in it")
                    ok(pg.locator("#rm tbody tr").count() >= 5, "sourcing: the raw materials are listed")
                if pid == "stock":
                    ok(pg.locator(".ladder2").count() >= 10, "stock: the remaining-life ladder is drawn", pg.locator(".ladder2").count())
                    ok(pg.locator(".mo2").count() >= 12, "stock: twelve months of demand against the plant")
                    ok(pg.locator(".mo2.shut").count() == 1, "stock: the shutdown month is marked")
                if pid == "masters":
                    ok(pg.locator(".mitem[data-k]").count() >= 20, "masters: every master is listed", pg.locator(".mitem[data-k]").count())
                    ok(pg.locator(".route-Configure").count() > 0 and pg.locator(".route-Extend").count() > 0,
                       "masters: the Configure and Extend routes are both shown")
                    ok(pg.locator("#mtable tbody tr").count() > 5, "masters: the selected master shows its rows")
                    ok("generated" in pg.inner_text("body").lower(), "masters: the provenance is stated")
                    live = pg.evaluate("window.CHM.meta.masters.filter(d => d.live).length")
                    ok(live >= 8, "masters: at least eight masters can be uploaded", live)
                if pid == "studio":
                    ok(pg.locator("#ratchet .rr").count() == 7, "studio: seven assumptions in the ratchet",
                       pg.locator("#ratchet .rr").count())
                    ok(pg.locator("#naive table.score tbody tr").count() >= 5, "studio: the naive scoreboard is filled")
                    ok(pg.locator("#real table.score tbody tr").count() >= 7, "studio: the real scoreboard is filled")
                    ok(pg.locator("#led tbody tr").count() > 20, "studio: the ledger has rows",
                       pg.locator("#led tbody tr").count())
                    ok("Read the left-hand scoreboard first" in body, "studio: the fairness statement is on screen")
                if SHOTS:
                    pg.screenshot(path=os.path.join(SHOT_DIR, pid + ".png"), full_page=True)
                pg.close()
            b.close()
    finally:
        srv.kill()
    print("\n" + "-" * 68)
    print("PAGES  %s  %d checks%s" % ("PASS" if not fails else "FAIL", checks[0],
                                      "" if not fails else ", %d failed" % len(fails)))
    if fails:
        for f in sorted(set(fails)):
            print("   " + f)
    sys.exit(0 if not fails else 1)


main()
