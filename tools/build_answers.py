"""Build the review-answers PDF: the twelve questions from the demo review, answered.

    python tools/build_answers.py [--out DIR]

Same discipline as tools/build_handover.py. Every number in the document is read out of the engine at build time by
facts() below, and every screen is captured from the live demo, so the answers cannot drift from the thing they describe.

Written OUTSIDE the repository by default, beside the hand-over walkthrough.
"""
import base64
import io
import json
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
PORT = 8457
BASE = "http://localhost:%d/" % PORT
TMP = os.path.join(os.environ.get("TEMP", "/tmp"), "chm-answers")
os.makedirs(TMP, exist_ok=True)

# key, page (with an optional #hash), css selector, what to do first, caption
SHOTS = [
    ("q1-two", "studio", "#twoplans", None,
     "Plan Studio now says what the two plans are before it scores them: one scheduler, one order book, one set of weights, seven rules switched."),
    ("q1-boards", "studio", ".boards", None,
     "Both scoreboards carry a difference column, so a row that is nearly identical can be told from one that is identical."),
    ("q2-time", "schedule", "#timeuse", None,
     "Utilisation is reported per equipment class, and every hour of every unit is accounted for rather than averaged."),
    ("q3-gantt", "schedule", ".gantt", None,
     "The block schedule from the as-of moment: the batch number is now on the bar, and work starts straight away."),
    ("q4-ladder", "cleaning", "#ladder", None,
     "The campaign ladder, rebuilt on a real time axis with a weekly date scale. Solid blocks are operations shaded by colour load; hatched blocks are clean-downs."),
    ("q5-clock", "stages", ".grid-2-1 > .card", None,
     "The hold clock, with one link worked end to end in clock times before the two hundred bars beneath it."),
    ("q6-util", "utilities", "#inten", None,
     "What a tonne of each product costs in utilities, computed from the duty profile and the charge volume."),
    ("q7-waste", "effluent", ".card:has(#inten)", None,
     "Effluent and solvent per batch and per tonne, by stream, with what the recovery train returns."),
    ("q8-farm", "tanks", "#whatfor", None,
     "What the tank farm is for, and what it is not for."),
    ("q9-draw", "tanks", "#draw", None,
     "Every tank, what the plan draws from it, what recovery returns, and the net make-up a tanker has to bring."),
    ("q10-gloss", "report", "#gloss", None,
     "The product glossary on the new Production Plan Report: what each code is, and the route behind it."),
    ("q11-reg", "report", ".card:has(#reg)", None,
     "The batch register: one row per batch, with its window, its output, its effluent, its solvent and its material cost."),
    ("q11-cons", "report", "#cons", "first-batch",
     "And for any batch: the charge sheet, the solvent loop, the utilities consumed and the effluent generated."),
    ("q12-chain", "lots", "#chain3", None,
     "Batch, lot and customer lot are three different objects, constrained by three different things."),
]


def facts():
    """Every number the document quotes, read out of the engine."""
    js = r"""
    const path = require('path'); const root = process.argv[2];
    global.window = global;
    require(path.join(root,'data','chm-data.js'));
    require(path.join(root,'assets','chm-engine.js'));
    require(path.join(root,'assets','chm-results.js'));
    const E = global.CHMEngine, D = global.CHM;
    const m = E.prepare(D, {});
    const hist = E.history(m);
    /* Instrument the AWARE plan on its own. E.stats is cumulative, and compare() runs several plans, so reading the
       counters after a compare attributes the generic plan's chain attempts to the aware one. */
    E.resetStats();
    const solo = E.plan(m, hist, { preset: 'balanced', rules: 'aware' });
    const st1 = JSON.parse(JSON.stringify(E.stats));
    let openAtEnd = 0;
    Object.keys(solo.state.lines).forEach(k => { const L = solo.state.lines[k]; if (L.rem > 0) openAtEnd += L.rem; });
    const ctx = E.context(m);
    let startUnits = 0; m.U.forEach(u => { if (ctx.starts[u.ix]) startUnits++; });

    const C = E.compare(m, hist, { preset: 'balanced' });
    const A = C.aware, G = C.generic, kpi = A.kpi, now = m.asOf, end = m.end, span = end - now;
    const out = {
      asOf: D.meta.asOf, forwardDays: D.meta.forwardDays, historyDays: D.meta.historyDays,
      products: m.P.length, units: m.U.length, orders: D.orders.length, lines: D.lines.length,
      bookKg: D.meta.stats.kg, demandLoad: D.meta.stats.bindingLoad, binding: D.meta.stats.binding, ms: C.ms,
      failBy: st1.failBy, idles: st1.idles, chains: st1.chains, chainFails: st1.fails, decisions: st1.iter,
      openAtEnd: Math.round(openAtEnd), startUnits: startUnits
    };

    // ---- Q1: the two rule sets ------------------------------------------------------------------------------------
    out.assumptions = (D.m.genericAssumptions || []).map(a => ({ id: a.id, nuance: a.nuance, generic: a.label, aware: a.real }));
    out.naive = [
      ['Cleaning hours booked', G.kpi.cleanHours, kpi.cleanHours, 'h'],
      ['On time, in full', G.kpi.otif, kpi.otif, 'pct'],
      ['Late lines', G.kpi.late, kpi.late, ''],
      ['Output booked', G.kpi.nominalKg, kpi.nominalKg, 'kg'],
      ['Batches', G.kpi.batches, kpi.batches, '']
    ];
    const lostKg = C.cons.events.reduce((s, r) => s + (r.statusChanging ? (r.cost.kg || 0) : 0), 0);
    out.real = [
      ['Output actually delivered', G.kpi.madeKg - lostKg, kpi.madeKg, 'kg'],
      ['Constraints broken', C.proofGeneric.total.violations, C.proof.total.violations, ''],
      ['Product written off or re-worked', C.cons.total.kg, 0, 'kg'],
      ['Plant hours lost to the consequences', C.cons.total.hours, 0, 'h'],
      ['Contribution', G.kpi.contribution, kpi.contribution, 'rs'],
      ['Cost of the assumptions', -C.cons.total.rupees, 0, 'rs']
    ];
    out.consTotal = C.cons.total.rupees; out.consRows = C.cons.total.n;
    out.proofChecks = C.proof.total.checks; out.proofViolations = C.proof.total.violations;
    out.genViolations = C.proofGeneric.total.violations;

    // ---- Q2 and Q3: where the time goes ---------------------------------------------------------------------------
    out.utilClass = kpi.utilClass;
    out.byClass = Object.keys(kpi.utilByClass).map(c => ({
      cls: c, units: m.U.filter(u => u.cls === c).length,
      run: kpi.utilByClass[c].run, clean: kpi.utilByClass[c].clean, busy: kpi.utilByClass[c].busy,
      ops: A.fwd.reduce((a, b) => a + b.ops.filter(o => m.U[o.uix].cls === c).length, 0)
    })).sort((a, b) => b.busy - a.busy);
    out.plantMean = kpi.util;
    // time accounting per class, the same arithmetic the page does
    const acc = {};
    m.U.forEach(u => {
      const g = acc[u.cls] || (acc[u.cls] = { n: 0, run: 0, clean: 0, block: 0, held: 0, avail: 0 });
      g.n++; g.avail += span;
      (m.blocks[u.ix] || []).forEach(b => { g.block += Math.max(0, Math.min(b[1], end) - Math.max(b[0], now)); });
    });
    A.fwd.forEach(b => b.ops.forEach(o => { acc[m.U[o.uix].cls].run += Math.max(0, Math.min(o.e, end) - Math.max(o.s, now)); }));
    A.cleans.filter(c => c.s >= now).forEach(c => { const u = m.U[c.uix]; if (u) acc[u.cls].clean += Math.max(0, Math.min(c.e, end) - Math.max(c.s, now)); });
    A.sacrifices.forEach(s => { const u = m.U[s.uix]; if (u) acc[u.cls].held += s.min; });
    out.timeUse = Object.keys(acc).map(c => Object.assign({ cls: c }, acc[c],
      { idle: Math.max(0, acc[c].avail - acc[c].run - acc[c].clean - acc[c].block - acc[c].held) }))
      .sort((a, b) => (b.run + b.clean) / b.avail - (a.run + a.clean) / a.avail);
    out.startsByWeek = [];
    for (let w = 0; w * 7 * 1440 < span; w++) {
      out.startsByWeek.push(A.fwd.filter(b => b.s >= now + w * 7 * 1440 && b.s < now + (w + 1) * 7 * 1440).length);
    }
    out.sacrifices = A.sacrifices.length;
    out.sacrificeH = Math.round(kpi.sacrificeMin / 60);
    out.blockH = Math.round(out.timeUse.reduce((a, g) => a + g.block, 0) / 60);
    const lags = [];
    A.fwd.forEach(b => { for (let i = 1; i < b.ops.length; i++) lags.push((b.ops[i].s - b.ops[i - 1].e) / 60); });
    out.links = lags.length;
    out.meanLagH = lags.length ? lags.reduce((a, x) => a + x, 0) / lags.length : 0;

    // ---- Q4: the campaign ladder ----------------------------------------------------------------------------------
    const byUnit = {};
    A.fwd.forEach(b => b.ops.forEach(o => { (byUnit[o.unit] = byUnit[o.unit] || []).push({ b: b, o: o }); }));
    let up = 0, down = 0, upH = 0, downH = 0;
    Object.keys(byUnit).forEach(u => {
      const seq = byUnit[u].sort((a, b) => a.o.s - b.o.s);
      for (let i = 1; i < seq.length; i++) {
        const pa = m.P[seq[i - 1].b.pix], pb = m.P[seq[i].b.pix];
        if (pa.ix === pb.ix) continue;
        const h = (seq[i].o.clean || 0) / 60;
        if (pb.colour >= pa.colour) { up++; upH += h; } else { down++; downH += h; }
      }
    });
    out.ladder = { up: up, down: down, upH: upH / Math.max(1, up), downH: downH / Math.max(1, down) };
    out.campaign = m.campaign;
    out.campaigns = kpi.campaigns; out.perCampaign = kpi.batchesPerCampaign;
    out.cleanHours = kpi.cleanHours; out.cleanCount = kpi.cleanCount;
    out.cleanByGrade = kpi.cleanByGrade;
    out.grades = (D.m.cleanGrades || []).map(g => ({ id: g.id, name: g.name, hours: g.hours }));

    // ---- Q5: the hold clock -------------------------------------------------------------------------------------
    const L = [];
    A.fwd.forEach(b => {
      const p = m.P[b.pix];
      for (let i = 1; i < b.ops.length; i++) {
        const lag = b.ops[i].s - b.ops[i - 1].e, win = p.ops[i].maxLag;
        L.push({ batch: b.id, from: p.ops[i - 1].label, to: p.ops[i].label, fromUnit: b.ops[i - 1].unit,
                 toUnit: b.ops[i].unit, lagH: lag / 60, minH: p.ops[i].minLagH, winH: p.ops[i].maxLagH,
                 use: win ? lag / win : 0, endPrev: b.ops[i - 1].e });
      }
    });
    L.sort((a, b) => b.use - a.use);
    out.tightestLink = L[0] || null;
    out.linksTight = L.filter(x => x.use > 0.85).length;
    let minWin = 1e9, minWinP = '', minWinOp = '';
    m.P.forEach(p => p.ops.forEach((o, i) => { if (i && o.maxLagH < minWin) { minWin = o.maxLagH; minWinP = p.id; minWinOp = o.label; } }));
    out.minWindow = { h: minWin, productId: minWinP, op: minWinOp };
    out.holdChecks = (C.proof.byNuance.P3 || {}).checks || 0;

    // ---- Q6 and Q7: consumption per volume ------------------------------------------------------------------------
    out.utilities = m.utils.map(u => ({ id: u.id, name: u.name, rateUnit: u.unit, qtyUnit: E.UTIL_QTY_UNIT[u.unit] || u.unit, cap: u.cap }));
    out.archetypes = Object.keys(D.cfg.archetypes).sort().map(k => ({
      id: k, label: D.cfg.archetypes[k].label,
      segs: D.cfg.archetypes[k].segs.map(s => ({ frac: s[0], draw: s[1] }))
    }));
    out.intensity = m.P.map(p => {
      const u = E.utilPerBatch(m, p), w = E.wastePerBatch(m, p), t = p.batchKg / 1000;
      const inp = E.inputs(m, p);
      const per = {}; Object.keys(u).forEach(k => { per[k] = u[k] / t; });
      return { id: p.id, name: p.name, family: p.family, chargeKL: p.chargeKL, batchKg: p.batchKg, cycleH: p.cycleH,
               util: u, utilPerT: per, efflM3: w.efflM3, efflPerT: w.efflM3 / t, byCat: w.byCat,
               solvKL: w.solvKL, recoveredKL: w.recoveredKL, makeupKL: w.makeupKL, solvPerT: w.solvKL / t,
               rmCost: inp.reduce((a, x) => a + x.rupees, 0), costKg: p.costKg,
               inputs: inp.map(x => ({ role: x.roleName, rm: x.rmId, rmName: x.rmName, perKL: x.perKL, qty: x.net, unit: x.unit, rupees: x.rupees })) };
    }).sort((a, b) => b.efflPerT - a.efflPerT);
    out.recovery = { min: m.recovery.min, max: m.recovery.max, turnH: m.recovery.turnMin / 60, cap: m.recovery.cap };
    out.wastes = m.wastes.map(w => ({ id: w.id, name: w.name, unit: w.unit, cap: w.cap }));
    let planEffl = 0, planMakeup = 0, planSteam = 0, planRm = 0;
    A.fwd.forEach(b => {
      const p = m.P[b.pix], u = E.utilPerBatch(m, p), w = E.wastePerBatch(m, p);
      planEffl += w.efflM3; planMakeup += w.makeupKL; planSteam += (u.STEAM || 0);
      planRm += E.inputs(m, p).reduce((a, x) => a + x.rupees, 0);
    });
    out.planEffl = planEffl; out.planMakeup = planMakeup; out.planSteam = planSteam; out.planRm = planRm;
    out.madeKg = kpi.madeKg;

    // ---- Q8 and Q9: the tank farm ---------------------------------------------------------------------------------
    out.hazards = m.hazs.map(h => ({ id: h.id, name: h.name, licensedKL: h.licensedKL,
                                     peak: kpi.licencePeak[h.id], headroom: kpi.licenceMin[h.id] }));
    out.bunds = m.bunds.map(b => ({ id: b.id, name: b.name, classes: b.classes }));
    const tankDraw = {};
    A.fwd.forEach(b => {
      const p = m.P[b.pix]; if (p.tix == null) return;
      const w = E.wastePerBatch(m, p);
      const g = tankDraw[p.tix] || (tankDraw[p.tix] = { draw: 0, back: 0, n: 0, prods: {} });
      g.draw += w.solvKL; g.back += w.recoveredKL; g.n++; g.prods[p.id] = 1;
    });
    out.tanks = m.tanks.map(t => {
      const g = tankDraw[t.ix] || { draw: 0, back: 0, n: 0, prods: {} };
      return { id: t.id, solvent: t.solventId, haz: t.haz, bund: t.bundId, capKL: t.capKL, openKL: t.openKL,
               tankerKL: t.tankerKL, batches: g.n, draw: g.draw, back: g.back, net: g.draw - g.back,
               prods: Object.keys(g.prods).sort() };
    }).sort((a, b) => b.draw - a.draw);
    /* A refused tanker comes back in two days and may present up to five times, so the refusal COUNT is events, not
       tankers. Report both, or "47 refused against 13 accepted" reads as a farm that turns away three loads in four. */
    const refAll = A.refused.filter(r => r.at >= now);
    const accAll = A.state.accepted.filter(d => d.at >= now);
    const accIds = new Set(accAll.map(d => d.id)), refIds = new Set(refAll.map(r => r.id));
    out.deliveries = { accepted: accIds.size, refusalEvents: refAll.length,
                       refusedTankers: refIds.size,
                       neverAdmitted: [...refIds].filter(i => !accIds.has(i)).length,
                       scheduled: m.deliveries.filter(d => d.at >= now).length,
                       refused: refAll.length,
                       byLicence: refAll.filter(r => r.overLicence).length,
                       emergency: (A.state.emergency || []).filter(e => e.at >= now).length,
                       emergencyRs: (A.state.emergency || []).filter(e => e.at >= now).reduce((a, e) => a + e.rupees, 0),
                       heldInRecovery: (A.state.heldInRecovery || []).filter(r => r.at >= now).length };

    // ---- Q10 and Q11: the register --------------------------------------------------------------------------------
    out.families = (D.m.families || []).map(f => ({ id: f.id, name: f.name, kind: f.kind, note: f.note }));
    out.catalogue = m.P.map(p => ({ id: p.id, name: p.name, family: p.family, chargeKL: p.chargeKL, batchKg: p.batchKg,
                                    ops: p.ops.length, cycleH: p.cycleH, solv: p.solv, regulated: p.regulated,
                                    intermediate: p.intermediate, potency: p.potency,
                                    route: p.ops.map(o => o.label).join(' → '),
                                    made: A.fwd.filter(b => b.pix === p.ix).length }));
    // one real batch, worked through, for the document to show
    const multi = A.fwd.filter(b => b.ops.length >= 5).sort((a, b) => a.s - b.s)[0] || A.fwd[0];
    if (multi) {
      const p = m.P[multi.pix], u = {}, ef = {};
      let solv = 0;
      multi.ops.forEach(o => {
        const op = p.ops[o.seq - 1]; if (!op) return;
        const hrs = (o.e - o.s) / 60;
        op.duty.forEach(sg => Object.keys(sg.draw).forEach(k => { u[k] = (u[k] || 0) + sg.draw[k] * hrs * sg.frac; }));
        if (o.efflM3) ef[op.wasteCat] = (ef[op.wasteCat] || 0) + o.efflM3;
        solv += o.solvKL || 0;
      });
      const rec = (m.recovery.min + m.recovery.max) / 2;
      out.worked = {
        id: multi.id, productId: p.id, productName: p.name, kg: multi.kg, nominalKg: multi.nominalKg,
        assay: multi.assay, imp: multi.imp, psd: multi.psd, s: multi.s, e: multi.e, readyAt: multi.readyAt,
        base: D.meta.base,
        ops: multi.ops.map((o, i) => ({ seq: o.seq, label: o.label, unit: o.unit, s: o.s, e: o.e,
                                        hours: (o.e - o.s) / 60, cleanH: (o.clean || 0) / 60,
                                        lagH: i ? (o.s - multi.ops[i - 1].e) / 60 : null,
                                        winH: i ? p.ops[i].maxLagH : null })),
        inputs: E.inputs(m, p).map(x => ({ seq: x.seq, op: x.opLabel, role: x.roleName, rm: x.rmId, rmName: x.rmName,
                                           perKL: x.perKL, qty: x.net, unit: x.unit, rupees: x.rupees })),
        util: u, effl: ef, solvKL: solv, recoveredKL: solv * rec, makeupKL: solv * (1 - rec),
        lines: (multi.lineIds || []).slice()
      };
    }

    // ---- Q12: lots ------------------------------------------------------------------------------------------------
    // one batch makes one lot, so count the lots of THIS plan's batches: a few history batches are still in flight at
    // the as-of moment, and filtering on the made-at date alone reports more lots than there are batches
    const fwdIds = {}; A.fwd.forEach(b => { fwdIds[b.id] = 1; });
    const planLots = A.lots.filter(l => !l.opening && fwdIds[l.batchId]);
    out.lots = { made: planLots.length, opening: A.lots.filter(l => l.opening).length,
                 allocs: kpi.allocs, blended: kpi.blended, rejects: A.rejects.length };
    const why = {}; A.rejects.forEach(r => { why[r.why] = (why[r.why] || 0) + 1; });
    out.lots.rejectWhy = why;
    out.lots.qcDays = planLots.reduce((a, l) => a + (l.readyAt - l.madeAt), 0) / Math.max(1, planLots.length) / 1440;

    console.log(JSON.stringify(out));
    """
    f = os.path.join(TMP, "answers_facts.js")
    io.open(f, "w", encoding="utf-8").write(js)
    # node writes UTF-8; without saying so, Windows decodes it as cp1252 and every en dash arrives as mojibake
    r = subprocess.run(["node", f, ROOT], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=600)
    if r.returncode:
        raise SystemExit("facts failed:\n" + (r.stderr or "")[-4000:])
    out = json.loads(r.stdout.strip().splitlines()[-1])
    # two calibration knobs are the generator's own and never reach the dataset; read them from the file it used
    try:
        sys.path.insert(0, ROOT)
        from tools.gen import config as gcfg
        out["friction"] = gcfg.SCHEDULE_FRICTION
        out["ordersTarget"] = gcfg.ORDERS_TARGET
        out["inputProfile"] = {k: v for k, v in gcfg.INPUT_PROFILE.items()}
        out["familyInputs"] = gcfg.FAMILY_INPUTS
        out["roleNames"] = gcfg.ROLE_NAMES
        out["rawMaterials"] = gcfg.RAW_MATERIALS
    except Exception as e:
        print("  (generator knobs unavailable: %s)" % e)
        out["friction"] = out["ordersTarget"] = None
        out["inputProfile"] = out["familyInputs"] = out["roleNames"] = {}
        out["rawMaterials"] = []
    return out


def capture():
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT)], cwd=ROOT,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    imgs = {}
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome", headless=True)
            pg = b.new_page(viewport={"width": 1560, "height": 1050}, device_scale_factor=2)
            for i in range(30):
                try:
                    pg.goto(BASE + "home.html", wait_until="load", timeout=30000)
                    break
                except Exception:
                    time.sleep(0.4)
            pg.evaluate("localStorage.removeItem('chm-demo-state')")
            for key, page, sel, act, cap in SHOTS:
                pg.goto(BASE + page + ".html", wait_until="load")
                pg.wait_for_function("!document.getElementById('chm-busy') && !!window.CHMX", timeout=120000)
                pg.wait_for_timeout(800)
                if act == "first-batch":
                    # pick a real batch rather than naming one that may not exist after a regenerate
                    pg.evaluate("document.querySelector('#reg tbody tr[data-id]').click()")
                    pg.wait_for_timeout(500)
                el = pg.locator(sel).first
                el.scroll_into_view_if_needed(timeout=10000)
                pg.wait_for_timeout(250)
                path = os.path.join(TMP, key + ".png")
                el.screenshot(path=path)
                with open(path, "rb") as fh:
                    imgs[key] = base64.b64encode(fh.read()).decode()
                print("  captured %s" % key)
            b.close()
    finally:
        srv.kill()
    return imgs


def main():
    print("reading the facts out of the engine ...")
    f = facts()
    print("  %d products, %d lines, %d batches, busiest class %s at %.1f%%"
          % (f["products"], f["lines"], f["naive"][4][2], f["utilClass"], f["byClass"][0]["busy"] * 100))
    print("capturing the screens ...")
    imgs = capture()

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import answers_doc
    url = "https://rakeshpadamshali.github.io/bluemingo-chem-pp-demo/"
    html = answers_doc.build(f, imgs, url)
    src = os.path.join(TMP, "answers.html")
    io.open(src, "w", encoding="utf-8").write(html)
    print("  document is %.1f MB of HTML" % (len(html) / 1e6))

    os.makedirs(OUT, exist_ok=True)
    pdf = os.path.join(OUT, "Bluemingo_Chem_PP_Demo_Review_Answers.pdf")
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        pg = b.new_page()
        pg.goto("file:///" + src.replace("\\", "/"), wait_until="load")
        pg.wait_for_timeout(1400)
        pg.pdf(path=pdf, format="A4", print_background=True,
               margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
               display_header_footer=True, header_template="<div></div>",
               footer_template="<div style='width:100%;font:8pt Roboto,sans-serif;color:#999;"
                               "padding:0 14mm;display:flex;justify-content:space-between'>"
                               "<span>Bluemingo PP &middot; Specialty Chemicals &amp; APIs &mdash; review questions answered</span>"
                               "<span class='pageNumber'></span></div>")
        b.close()
    print("\nwrote %s  (%.2f MB)" % (pdf, os.path.getsize(pdf) / 1e6))


if __name__ == "__main__":
    main()
