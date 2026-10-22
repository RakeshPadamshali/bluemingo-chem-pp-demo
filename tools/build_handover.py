"""Build the self-guided hand-over PDF.

    python tools/build_handover.py [--out DIR]

The reader is whoever wrote the Specialty Chemicals deck. They should be able to open the PDF and the URL, follow the
demo on their own, answer the questions a prospect will ask, and know exactly which claims are theirs to validate with the
product team. So the document is the demo's argument in order — not a feature list — with the screens it refers to.

It is written OUTSIDE the repository by default, because it quotes the deck.
"""
import base64
import io
import os
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(os.path.dirname(ROOT), "..", "Projects", "POC", "Bluemingo_Chemical_Spreciality")
for i, a in enumerate(sys.argv):
    if a == "--out" and i + 1 < len(sys.argv):
        OUT = sys.argv[i + 1]
OUT = os.path.abspath(OUT)
PORT = 8456
BASE = "http://localhost:%d/" % PORT
TMP = os.path.join(os.environ.get("TEMP", "/tmp"), "chm-handover")
os.makedirs(TMP, exist_ok=True)

SHOTS = [
    ("home", 0, "The PP Dashboard: the headline, the proof, and the deck map of all sixteen nuances"),
    ("home", 1, "The deck map, priced — click a nuance and it opens the page that carries it"),
    ("studio", 0, "Plan Studio: the two scoreboards, and the assumption ratchet beneath them"),
    ("studio", 1, "The consequence ledger, and what the chemical-aware plan did instead"),
    ("cleaning", 0, "The cleaning matrix as a view of the rule, with the campaign ladder below it"),
    ("stages", 0, "Hold times: the route as links with a minimum and a maximum lag, and the hold clock"),
    ("utilities", 0, "Duty against cap, hour by hour, and the hour the plan had least room in"),
    ("tanks", 0, "The licensed quantity held day by day, the farm by bund, and what was turned away"),
    ("lots", 0, "The blend arithmetic against the order's spec, and every refusal named"),
    ("capacity", 0, "One tonnage number struck through, and the ranking that reverses"),
    ("masters", 0, "Master Data: provenance, the Configure and Extend routes, and the upload that re-plans"),
]


def facts():
    """every number the document quotes, read from the engine so the PDF cannot drift from the demo"""
    js = r"""
    const path = require('path'); const root = process.argv[2];
    global.window = global;
    require(path.join(root,'data','chm-data.js'));
    require(path.join(root,'assets','chm-engine.js'));
    require(path.join(root,'assets','chm-results.js'));
    const E = global.CHMEngine, D = global.CHM;
    const m = E.prepare(D, {}); const hist = E.history(m);
    const C = E.compare(m, hist, { preset: 'balanced' });
    const out = {
      asOf: D.meta.asOf, forwardDays: D.meta.forwardDays, historyDays: D.meta.historyDays,
      products: m.P.length, units: m.U.length, customers: Object.keys(m.customers).length,
      orders: D.orders.length, lines: D.lines.length, bookKg: D.meta.stats.kg,
      awareBatches: C.aware.kpi.batches, genBatches: C.generic.kpi.batches,
      awareOtif: C.aware.kpi.otif, genOtif: C.generic.kpi.otif,
      awareClean: C.aware.kpi.cleanHours, genClean: C.generic.kpi.cleanHours,
      awareKg: C.aware.kpi.madeKg, nominalKg: C.aware.kpi.nominalKg, genNominalKg: C.generic.kpi.nominalKg,
      campaigns: C.aware.kpi.campaigns, perCampaign: C.aware.kpi.batchesPerCampaign,
      genCampaigns: C.generic.kpi.campaigns, genPerCampaign: C.generic.kpi.batchesPerCampaign,
      pulled: C.aware.kpi.pulledForCampaign,
      utilClass: C.aware.kpi.utilClass, utilBusiest: C.aware.kpi.utilBusiest,
      utilRun: C.aware.kpi.utilByClass[C.aware.kpi.utilClass].run,
      utilClean: C.aware.kpi.utilByClass[C.aware.kpi.utilClass].clean,
      cleanShareOfRun: C.aware.kpi.cleanHours * 60 / Math.max(1, C.aware.kpi.busyMin),
      failBy: E.stats && E.stats.failBy ? E.stats.failBy : {},
      awareShort: C.aware.kpi.shortLines, genShort: C.generic.kpi.shortLines,
      awareLate: C.aware.kpi.late, genLate: C.generic.kpi.late,
      consTotal: C.cons.total.rupees, consRows: C.cons.total.n, consKg: C.cons.total.kg, consHours: C.cons.total.hours,
      statusChanging: C.cons.statusChanging, unmodelled: C.cons.unmodelled,
      proofChecks: C.proof.total.checks, proofViolations: C.proof.total.violations,
      genViolations: C.proofGeneric.total.violations,
      awareContribution: C.aware.kpi.contribution, genContribution: C.generic.kpi.contribution,
      awareDelay: C.aware.kpi.delayCost, genDelay: C.generic.kpi.delayCost,
      blended: C.aware.kpi.blended, allocs: C.aware.kpi.allocs, rejects: C.aware.rejects.length,
      sacrifices: C.aware.sacrifices.length, sacrificeH: Math.round(C.aware.kpi.sacrificeMin / 60),
      refused: C.aware.refused.filter(r => r.at >= m.asOf).length,
      nameplateT: C.sop.nameplateTonnesMonth, realisedT: C.sop.realisedTonnesMonth, bottleneck: C.sop.bottleneck,
      byNuance: {}, ms: C.ms
    };
    ['P1','P2','P3','P4','P5','P6','P7'].forEach(k => {
      const r = C.cons.byNuance[k] || {};
      out.byNuance[k] = { n: r.n || 0, rupees: r.rupees || 0, kg: Math.round(r.kg || 0), hours: Math.round(r.hours || 0) };
    });
    console.log(JSON.stringify(out));
    """
    f = os.path.join(TMP, "facts.js")
    io.open(f, "w", encoding="utf-8").write(js)
    r = subprocess.run(["node", f, ROOT], capture_output=True, text=True, timeout=600)
    if r.returncode:
        print(r.stderr[-2000:])
        raise SystemExit("could not read the facts from the engine")
    import json
    return json.loads(r.stdout.strip().splitlines()[-1])


def capture():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT)], cwd=ROOT,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    imgs = {}
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome", headless=True)
            pg = b.new_page(viewport={"width": 1680, "height": 1000}, device_scale_factor=2)
            for i in range(30):
                try:
                    pg.goto(BASE + "home.html", wait_until="load", timeout=30000)
                    break
                except Exception:
                    time.sleep(0.4)
            pg.evaluate("localStorage.removeItem('chm-demo-state')")
            for pid, frame, cap in SHOTS:
                pg.goto(BASE + pid + ".html", wait_until="load")
                pg.wait_for_function("!document.getElementById('chm-busy') && !!window.CHMX", timeout=120000)
                pg.wait_for_timeout(700)
                pg.evaluate("document.querySelector('.bm-content').scrollTop = %d" % (frame * 880))
                pg.wait_for_timeout(350)
                path = os.path.join(TMP, "%s-%d.png" % (pid, frame))
                pg.screenshot(path=path)
                with open(path, "rb") as fh:
                    imgs["%s-%d" % (pid, frame)] = base64.b64encode(fh.read()).decode()
                print("  captured %s frame %d" % (pid, frame))
            b.close()
    finally:
        srv.kill()
    return imgs

def main():
    print("reading the facts out of the engine ...")
    f = facts()
    print("  %d products, %d lines, aware %.1f%% OTIF, generic costs Rs %.2f Cr"
          % (f["products"], f["lines"], f["awareOtif"] * 100, f["consTotal"] / 1e7))
    print("capturing the screens ...")
    imgs = capture()

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import handover_doc
    url = "https://rakeshpadamshali.github.io/bluemingo-chem-pp-demo/"
    html = handover_doc.build(f, imgs, url)
    src = os.path.join(TMP, "handover.html")
    io.open(src, "w", encoding="utf-8").write(html)
    print("  document is %.1f MB of HTML" % (len(html) / 1e6))

    os.makedirs(OUT, exist_ok=True)
    pdf = os.path.join(OUT, "Bluemingo_Chem_PP_Demo_Walkthrough.pdf")
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        pg = b.new_page()
        pg.goto("file:///" + src.replace("\\", "/"), wait_until="load")
        pg.wait_for_timeout(1200)
        pg.pdf(path=pdf, format="A4", print_background=True,
               margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
               display_header_footer=True, header_template="<div></div>",
               footer_template="<div style='width:100%;font:8pt Roboto,sans-serif;color:#999;"
                               "padding:0 14mm;display:flex;justify-content:space-between'>"
                               "<span>Bluemingo PP &middot; Specialty Chemicals &amp; APIs &mdash; demo hand-over</span>"
                               "<span class='pageNumber'></span></div>")
        b.close()
    print("\nwrote %s  (%.2f MB)" % (pdf, os.path.getsize(pdf) / 1e6))


if __name__ == "__main__":
    main()
