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
    ("schedule", 0, "The block schedule: one row per unit, every operation of a batch, and the cleans between them"),
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
    // ---- the plant as modelled: processes, operations, equipment, and the configuration behind them ----------------
    const A = C.aware, kpi = A.kpi, cfg = m.cfg, now = m.asOf, span = m.end - now;
    const DOW = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const bt = {};
    (D.m.blockTimes || []).forEach(function (b) {
      bt[b.unit] = (+b.every > 7 ? 'every ' + (+b.every / 7) + ' weeks' : 'weekly') + ', ' + DOW[+b.dow] + ' ' +
        ('0' + b.start).slice(-2) + ':00, ' + b.hours + ' h (' + b.reason + ')';
    });
    const eOps = {}, eProd = {}, busyU = {}, clnU = {}, archUse = {};
    m.P.forEach(function (p) {
      p.ops.forEach(function (op) {
        archUse[op.arch] = (archUse[op.arch] || 0) + 1;
        op.units.forEach(function (ui) { eOps[ui] = (eOps[ui] || 0) + 1; (eProd[ui] = eProd[ui] || {})[p.id] = 1; });
      });
    });
    A.fwd.forEach(function (b) {
      b.ops.forEach(function (o) { busyU[o.uix] = (busyU[o.uix] || 0) + Math.max(0, Math.min(o.e, m.end) - Math.max(o.s, now)); });
    });
    (A.cleans || []).filter(function (c) { return c.s >= now; })
      .forEach(function (c) { clnU[c.uix] = (clnU[c.uix] || 0) + c.min; });
    const nP = m.P.length, gradeN = {};
    for (let a = 0; a < nP; a++) {
      for (let b = 0; b < nP; b++) {
        if (a === b) continue;
        const g = m.cleanGrade[a * nP + b]; gradeN[g] = (gradeN[g] || 0) + 1;
      }
    }
    /* Eligibility is DERIVED from attributes, so prove it on the reaction step whose refusals are the most varied. */
    let ex = null;
    m.P.forEach(function (p) {
      p.ops.forEach(function (op) {
        if (op.cls !== 'REACTOR') return;
        const no = (m.unitsByCls[op.cls] || []).filter(function (u) { return op.units.indexOf(u.ix) < 0; })
          .map(function (u) { return { id: u.id, vol: u.vol, why: (E.whyNot(m, p, op, u) || [])[0] || '' }; });
        const kinds = {}; no.forEach(function (r) { kinds[r.why] = 1; });
        const score = Object.keys(kinds).length * 100 - op.units.length;
        if (!ex || score > ex.score) ex = { score: score, p: p, op: op, no: no };
      });
    });
    out.plant = {
      classes: m.clsList.map(function (c) {
        const k = kpi.utilByClass[c] || {};
        return { cls: c, units: m.unitsByCls[c].length, share: (cfg.opVolShare || {})[c],
                 oversize: (cfg.oversizeClasses || []).indexOf(c) >= 0,
                 ops: m.P.reduce(function (q, p) { return q + p.ops.filter(function (o) { return o.cls === c; }).length; }, 0),
                 products: m.P.filter(function (p) { return p.ops.some(function (o) { return o.cls === c; }); }).length,
                 busy: k.busy || 0, run: k.run || 0, clean: k.clean || 0 };
      }),
      units: m.U.map(function (u) {
        return { id: u.id, name: u.name, cls: u.cls, block: u.block, vol: u.vol, mat: u.mat, cryo: !!u.cryo,
                 note: u.note || '', uptime: u.uptime, blockTime: bt[u.id] || '',
                 eligOps: eOps[u.ix] || 0, eligProducts: Object.keys(eProd[u.ix] || {}).length,
                 runH: Math.round((busyU[u.ix] || 0) / 60), cleanH: Math.round((clnU[u.ix] || 0) / 60),
                 busy: ((busyU[u.ix] || 0) + (clnU[u.ix] || 0)) / Math.max(1, span * u.uptime) };
      }),
      archetypes: (D.m.dutyProfiles || []).map(function (a2) {
        return { id: a2.id, label: a2.label, cls: a2.cls, clean: a2.clean !== false,
                 seg1: a2.seg1, seg2: a2.seg2, seg3: a2.seg3, ops: archUse[a2.id] || 0 };
      }),
      routes: m.P.map(function (p) {
        const lags = p.ops.slice(1).map(function (o) { return o.maxLagH; });
        return { id: p.id, name: p.name, family: p.family, regulated: !!p.regulated, intermediate: !!p.intermediate,
                 solv: p.solv, solvClass: p.solvClass, colour: p.colour, potency: p.potency,
                 chargeKL: p.chargeKL, batchKg: p.batchKg, nameplateKg: p.nameplateKg, yieldMean: p.yieldMean,
                 cycleH: p.cycleH, stages: p.ops.filter(function (o) { return o.cls === 'REACTOR'; }).length,
                 tightest: lags.length ? Math.min.apply(null, lags) : null,
                 ops: p.ops.map(function (o) {
                   return { seq: o.seq, label: o.label, arch: o.arch, cls: o.cls, hours: o.hours,
                            minLagH: o.minLagH, maxLagH: o.maxLagH, needKL: E.opVolume(m, p, o.cls),
                            units: o.units.map(function (ui) { return m.U[ui].id; }),
                            efflM3: o.efflM3, wasteCat: o.wasteCat, solvKL: o.solvKL };
                 }) };
      }),
      elig: { product: ex.p.id, productName: ex.p.name, op: ex.op.label, seq: ex.op.seq, cls: ex.op.cls,
              arch: ex.op.arch, chargeKL: ex.p.chargeKL, needKL: E.opVolume(m, ex.p, ex.op.cls),
              solv: ex.p.solv, solvClass: ex.p.solvClass, potency: ex.p.potency,
              ok: ex.op.units.map(function (ui) { return m.U[ui].id + ' (' + m.U[ui].vol + ' kL)'; }), no: ex.no },
      limits: []
        .concat(m.utils.map(function (u) {
          return { group: 'Utility', id: u.id, name: u.name, basis: 'per hour', cap: u.cap, unit: u.unit,
                   derate: u.derate ? { cap: u.derate.cap, why: u.derate.why } : null, note: '',
                   peak: kpi.utilPeak[u.id], atCap: kpi.utilAtCap[u.id], of: Math.round(span / 60), ofUnit: 'hours' };
        }))
        .concat(m.wastes.map(function (w) {
          return { group: 'Waste', id: w.id, name: w.name, basis: 'per day', cap: w.cap, unit: w.unit, derate: null,
                   peak: kpi.wastePeak[w.id], atCap: kpi.wasteAtCap[w.id], of: Math.round(span / 1440), ofUnit: 'days',
                   note: w.note || '' };
        }))
        .concat([{ group: 'Recovery', id: 'SOLV', name: 'Solvent recovery (distillation train)', basis: 'per day',
                   cap: m.recovery.cap, unit: 'kL/day', derate: null, peak: null, atCap: null, of: null, ofUnit: '',
                   note: 'returns ' + Math.round(m.recovery.min * 100) + '-' + Math.round(m.recovery.max * 100) +
                         '% of the solvent after ' + Math.round(m.recovery.turnMin / 60) + ' h' }])
        .concat(m.hazs.map(function (h) {
          return { group: 'Licence', id: h.id, name: h.name, basis: 'licensed quantity', cap: h.licensedKL, unit: 'kL',
                   derate: null, peak: (kpi.licencePeak || {})[h.id], atCap: null, of: null, ofUnit: '',
                   headroom: kpi.licenceMin[h.id], note: h.note || '' };
        })),
      cleanGrades: (D.m.cleanGrades || []).map(function (g) {
        return { id: g.id, name: g.name, hours: g.hours, note: g.note, pairs: gradeN[g.id] || 0 };
      }),
      overrides: (D.m.cleanOverrides || []).map(function (o) {
        return { frm: o.frm, to: o.to, grade: o.grade, why: o.why };
      }),
      campaign: (D.m.campaignRule || [])[0] || {},
      families: (D.m.families || []), presets: (D.m.weights || []),
      generic: cfg.generic, aware: cfg.aware,
      uptime: cfg.unitUptime, oversize: cfg.oversize, oversizeClasses: cfg.oversizeClasses, opVolShare: cfg.opVolShare,
      demandLoad: cfg.demandLoad, blockRules: (D.m.blockTimes || []).length, sopMonths: D.meta.sopMonths,
      pairs: nP * (nP - 1), horizonH: Math.round(span / 60)
    };
    console.log(JSON.stringify(out));
    """
    f = os.path.join(TMP, "facts.js")
    io.open(f, "w", encoding="utf-8").write(js)
    # node writes UTF-8; without saying so, Windows decodes it as cp1252 and every en dash arrives as mojibake
    r = subprocess.run(["node", f, ROOT], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    if r.returncode:
        print(r.stderr[-2000:])
        raise SystemExit("could not read the facts from the engine")
    import json
    out = json.loads(r.stdout.strip().splitlines()[-1])
    # two calibration knobs are the generator's own and never reach the dataset; read them from the file it used
    try:
        sys.path.insert(0, ROOT)
        from tools.gen import config as gcfg
        out["plant"]["friction"] = gcfg.SCHEDULE_FRICTION
        out["plant"]["minLineBatches"] = gcfg.MIN_LINE_BATCHES
    except Exception:
        out["plant"]["friction"] = out["plant"]["minLineBatches"] = None
    return out


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
