/* Invariants over the engine:  node tools/verify_engine.js [--quiet]

   The rule this file lives by: it REBUILDS every series from the plan's OUTPUT — the batches, their operations, the
   cleans, the lots, the allocations — and never reads the scheduler's own typed arrays. If it checked the engine's
   internal buckets, the scheduler would be certifying itself, and a bucketing bug would pass twice.

   It checks, for every preset:
     the aware plan     every constraint the demo claims it honours, with ZERO violations
     the generic plan   that the replay finds EXACTLY the seven claimed violation classes, each with a named batch
     the fairness gate  that the generic plan WINS the naive scoreboard — if it ever loses on paper too, the comparison
                        is a straw man and this build must not ship
     the physics        that both rule sets face identical seeded yields, assays and QC times
     determinism        same input, same plan, twice; and the frozen history unchanged by any preset
*/
const path = require('path');
const root = path.join(__dirname, '..');
global.window = global;
require(path.join(root, 'data', 'chm-data.js'));
require(path.join(root, 'assets', 'chm-engine.js'));
require(path.join(root, 'assets', 'chm-results.js'));
const E = global.CHMEngine, D = global.CHM;
const QUIET = process.argv.includes('--quiet');

let checks = 0, fails = [];
const n = (x, d = 0) => (x == null || isNaN(x) ? '—' : Number(x).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d }));
function ok(cond, name, detail) {
  checks++;
  if (!cond) { fails.push(name + (detail ? '  — ' + detail : '')); if (fails.length <= 40) console.log('  FAIL ' + name + (detail ? '  — ' + detail : '')); }
}
function section(t) { if (!QUIET) console.log('\n' + t); }

const m = E.prepare(D, {});
const hist = E.history(m);
const PRESETS = Object.keys(m.presets);

// ---------------------------------------------------------------------------------------------------- rebuilt series
/* Everything below is recomputed from the plan's committed batches, as an independent observer would. */
function rebuild(plan) {
  const H = m.H, Dn = m.Dn;
  const util = new Float64Array(m.utils.length * H);
  const waste = new Float64Array(m.wastes.length * Dn);
  const recov = new Float64Array(Dn);
  const tank = new Float64Array(m.tanks.length * Dn);
  const byUnit = {}, lotKg = {};
  plan.batches.forEach(b => {
    const p = m.P[b.pix];
    b.ops.forEach(o => {
      const op = p.ops[o.seq - 1];
      // utility duty, bucketed per hour as the MAX of the segments touching that hour (one vessel, one state at a time)
      const dur = o.e - o.s; let t = o.s; const peak = {};
      op.duty.forEach((seg, g) => {
        const segEnd = g === op.duty.length - 1 ? o.e : t + dur * seg.frac;
        for (const k in seg.draw) {
          const ui = m.utix[k]; if (ui == null) continue;
          const row = peak[ui] || (peak[ui] = {});
          for (let h = Math.floor(t / 60); h < Math.ceil(segEnd / 60); h++) if (h >= 0 && h < H && !(row[h] >= seg.draw[k])) row[h] = seg.draw[k];
        }
        t = segEnd;
      });
      for (const ui in peak) for (const h in peak[ui]) util[ui * H + (+h)] += peak[ui][h];
      if (o.wix != null && o.efflM3) waste[o.wix * Dn + Math.floor(o.s / 1440)] += o.efflM3;
      if (o.solvKL) {
        // only the DRAW is derivable from a batch; how much came back depends on what the tank and the licence could
        // take, so it is read from the plan's own record rather than recomputed here
        recov[Math.floor(o.s / 1440)] += o.solvKL;
        if (p.tix != null) tank[p.tix * Dn + Math.floor(o.s / 1440)] -= o.solvKL;
      }
      (byUnit[o.unit] = byUnit[o.unit] || []).push({ b, o, op });
    });
    lotKg[b.productId] = (lotKg[b.productId] || 0) + b.kg;
  });
  Object.keys(byUnit).forEach(u => byUnit[u].sort((x, y) => x.o.s - y.o.s));
  return { util, waste, recov, tank, byUnit, lotKg };
}

// ---------------------------------------------------------------------------------------------------- the aware plan
const results = {};
PRESETS.forEach(preset => {
  const C = E.compare(m, hist, { preset });
  results[preset] = C;
  section(`preset ${preset} — aware ${C.aware.kpi.batches} batches / generic ${C.generic.kpi.batches}; compare ${C.ms} ms`);

  const A = C.aware, R = rebuild(A), nP = m.P.length;
  const now = m.asOf;

  // equipment: no overlap, eligible unit, outside every block time, cleaning at least what the matrix requires
  const aheadBy = {};
  A.cleans.forEach(c => { if (c.ahead) (aheadBy[c.unit] = aheadBy[c.unit] || []).push(c); });
  Object.keys(R.byUnit).forEach(uid => {
    const seq = R.byUnit[uid], ah = aheadBy[uid] || [];
    seq.forEach((x, i) => {
      ok(x.op.units.indexOf(m.uix[uid]) >= 0, 'aware/' + preset + ': operation on an eligible unit', x.b.id + ' ' + x.o.label + ' on ' + uid);
      const hit = (m.blocks[m.uix[uid]] || []).find(bl => x.o.s < bl[1] && x.o.e > bl[0]);
      ok(!hit, 'aware/' + preset + ': no operation inside a block time', hit ? x.b.id + ' through ' + hit[2] : '');
      if (i === 0) return;
      const prev = seq[i - 1];
      ok(x.o.s + 1e-6 >= prev.o.e, 'aware/' + preset + ': equipment never double-booked', uid + ': ' + prev.b.id + ' / ' + x.b.id);
      if (x.b.phase !== 'P') return;            // the frozen history was planned the generic way; it is not on trial here
      if (prev.b.pix === x.b.pix) return;
      const grade = m.cleanGrade[prev.b.pix * nP + x.b.pix];
      ok(grade !== 'FORBIDDEN', 'aware/' + preset + ': no forbidden pair ever adjacent', uid + ': ' + prev.b.productId + ' then ' + x.b.productId);
      let done = x.o.clean;
      ah.forEach(c => { if (c.s >= prev.o.e - 1e-6 && c.e <= x.o.s + 1e-6) done += c.min; });
      ok(done + 1e-6 >= m.cleanMin[prev.b.pix * nP + x.b.pix], 'aware/' + preset + ': cleaning at least the matrix grade',
         uid + ': ' + prev.b.productId + '→' + x.b.productId + ' needs ' + Math.round(m.cleanMin[prev.b.pix * nP + x.b.pix] / 60) + ' h, performed ' + Math.round(done / 60) + ' h');
    });
  });
  // links: every minimum and maximum lag honoured
  A.fwd.forEach(b => {
    const p = m.P[b.pix];
    for (let i = 1; i < b.ops.length; i++) {
      const lag = b.ops[i].s - b.ops[i - 1].e;
      ok(lag + 1e-6 >= p.ops[i].minLag, 'aware/' + preset + ': minimum lag on every link', b.id + ' ' + Math.round(lag / 60) + ' h < ' + p.ops[i].minLagH + ' h');
      ok(lag <= p.ops[i].maxLag + 1e-6, 'aware/' + preset + ': hold window on every link', b.id + ' ' + Math.round(lag / 60) + ' h > ' + p.ops[i].maxLagH + ' h');
    }
    ok(b.ops.length === p.ops.length, 'aware/' + preset + ': every batch runs its whole route', b.id);
    ok(b.kg > 0 && b.assay > 0, 'aware/' + preset + ': every batch has a mass and an assay', b.id);
  });
  // utilities, hour by hour, against the derated cap — the frozen history is allowed to be over, the plan may not add to it
  const inh = rebuild({ batches: hist.batches }).util;
  m.utils.forEach(u => {
    for (let h = Math.floor(now / 60); h < Math.min(m.H, Math.ceil(m.end / 60)); h++) {
      const cap = m.utilCap[u.ix * m.H + h], v = R.util[u.ix * m.H + h];
      ok(!cap || v <= cap + 1e-6 || v <= inh[u.ix * m.H + h] + 1e-6, 'aware/' + preset + ': utility duty inside the cap',
         u.id + ' hour ' + h + ': ' + v.toFixed(1) + ' vs ' + cap);
    }
  });
  // waste and recovery, day by day
  const inhW = rebuild({ batches: hist.batches }).waste;
  m.wastes.forEach(w => {
    for (let d = Math.floor(now / 1440); d < Math.min(m.Dn, Math.ceil(m.end / 1440)); d++) {
      ok(R.waste[w.ix * m.Dn + d] <= w.cap + 1e-6 || R.waste[w.ix * m.Dn + d] <= inhW[w.ix * m.Dn + d] + 1e-6,
         'aware/' + preset + ': waste load inside the daily consent', w.id + ' day ' + d + ': ' + R.waste[w.ix * m.Dn + d].toFixed(1) + ' vs ' + w.cap);
    }
  });
  // the tank farm and the licence, rebuilt from the batches plus the deliveries the plan accepted
  // rebuilt from the plan's OWN record of which tankers it took in, plus the solvent its batches drew and returned
  const tankSeries = new Float64Array(m.tanks.length * m.Dn);
  m.tanks.forEach(t => { tankSeries[t.ix * m.Dn] += t.openKL; });
  (A.state.accepted || []).forEach(dl => { tankSeries[dl.tix * m.Dn + Math.min(m.Dn - 1, Math.floor(dl.at / 1440))] += dl.kl; });
  (A.state.emergency || []).forEach(x => { const ti = m.tix[x.tank]; if (ti != null) tankSeries[ti * m.Dn + Math.min(m.Dn - 1, Math.floor(x.at / 1440))] += x.kl; });
  (A.state.returns || []).forEach(x => { tankSeries[x.tix * m.Dn + Math.min(m.Dn - 1, Math.floor(x.at / 1440))] += x.kl; });
  ok((A.state.returns || []).every(x => x.kl > 0), 'aware/' + preset + ': every recorded solvent return is positive');
  for (let i = 0; i < m.tanks.length * m.Dn; i++) tankSeries[i] += R.tank[i];
  m.tanks.forEach(t => {
    let lvl = 0;
    for (let d = 0; d < Math.min(m.Dn, Math.ceil(m.end / 1440)); d++) {
      lvl += tankSeries[t.ix * m.Dn + d];
      ok(lvl >= -1e-3, 'aware/' + preset + ': no tank ever holds a negative volume', t.id + ' day ' + d + ': ' + lvl.toFixed(1) + ' kL');
      ok(lvl <= t.capKL + 1e-3, 'aware/' + preset + ': no tank ever overflows', t.id + ' day ' + d + ': ' + lvl.toFixed(1) + ' vs ' + t.capKL);
    }
  });
  m.hazs.forEach(hz => {
    let run = 0;
    for (let d = 0; d < Math.min(m.Dn, Math.ceil(m.end / 1440)); d++) {
      m.tanks.forEach(t => { if (t.hix === hz.ix) run += tankSeries[t.ix * m.Dn + d]; });
      if (d >= Math.floor(now / 1440)) {
        ok(run <= hz.licensedKL + 1e-3, 'aware/' + preset + ': licensed quantity never exceeded',
           hz.id + ' day ' + d + ': ' + run.toFixed(1) + ' vs ' + hz.licensedKL);
      }
    }
  });
  m.bunds.forEach(b => m.segregation.forEach(sg =>
    ok(!(b.classes.indexOf(sg[0]) >= 0 && b.classes.indexOf(sg[1]) >= 0), 'aware/' + preset + ': segregated classes never share a bund', b.id)));
  // allocation: spec, approved route, remaining life, one COA per lot, at most a three-lot blend
  A.allocs.forEach(a => {
    const L = A.byId[a.lineId];
    ok(!!L, 'aware/' + preset + ': every allocation belongs to a line', a.lineId);
    if (!L) return;
    ok(a.assay >= L.assayMin - 1e-9, 'aware/' + preset + ': allocation meets the assay minimum', a.lineId + ': ' + a.assay + ' < ' + L.assayMin);
    ok(a.imp <= L.impMax + 1e-9, 'aware/' + preset + ': allocation inside the impurity limit', a.lineId + ': ' + a.imp + ' > ' + L.impMax);
    ok(a.psd <= L.psdMax + 1e-9, 'aware/' + preset + ': allocation inside the particle-size limit', a.lineId);
    ok(a.lots.length <= 3, 'aware/' + preset + ': a customer lot is at most a three-lot blend', a.lineId + ' blends ' + a.lots.length);
    ok(!L.minLifeM || (a.retestAt - m.asOf) / (30.4 * 1440) >= L.minLifeM - 1e-6,
       'aware/' + preset + ': allocation meets the customer minimum remaining life', a.lineId);
    ok(a.kg > 0 && a.kg <= L.qty + 1e-6, 'aware/' + preset + ': allocation never exceeds the ordered quantity', a.lineId);
  });
  // mass balance per product, rebuilt from the batches and the lots
  m.P.forEach(p => {
    const lots = A.lots.filter(x => x.pix === p.ix && !x.opening).reduce((s, x) => s + x.kg, 0);
    ok(Math.abs((R.lotKg[p.id] || 0) - lots) < 1, 'aware/' + preset + ': mass balance per product',
       p.id + ': ' + n(R.lotKg[p.id] || 0) + ' kg made vs ' + n(lots) + ' kg in lots');
    const shipped = A.lines.filter(l => l.productId === p.id).reduce((s, l) => s + l.shipped, 0);
    const opening = A.lots.filter(x => x.pix === p.ix && x.opening).reduce((s, x) => s + x.kg, 0);
    ok(shipped <= opening + (R.lotKg[p.id] || 0) + 1e-6, 'aware/' + preset + ': nothing ships that was never made',
       p.id + ': shipped ' + n(shipped) + ' vs ' + n(opening + (R.lotKg[p.id] || 0)) + ' available');
  });
  // the engine's own proof must agree with this independent rebuild
  ok(C.proof.total.violations === 0, 'aware/' + preset + ': the engine proof also reports zero violations',
     C.proof.total.violations + ' violations in ' + n(C.proof.total.checks) + ' checks');

  // ------------------------------------------------------------------------------------ the generic plan and its cost
  const CODES = ['CLEAN_SHORT', 'CLEAN_FORBIDDEN', 'YIELD', 'HOLD', 'UTIL', 'WASTE', 'LICENCE', 'ALLOC'];
  const NUANCES = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7'];
  NUANCES.forEach(nu => {
    const row = C.cons.byNuance[nu];
    ok(row && row.n > 0, 'generic/' + preset + ': nuance ' + nu + ' actually costs something in the ledger',
       row ? row.n + ' events' : 'no events at all — the demo claims this nuance and shows nothing');
    if (row) ok(row.rupees > 0 || row.kg > 0 || row.hours > 0, 'generic/' + preset + ': nuance ' + nu + ' is priced', nu);
  });
  C.cons.events.forEach(ev => {
    ok(CODES.indexOf(ev.code) >= 0, 'generic/' + preset + ': every ledger row has a known code', ev.code);
    ok(NUANCES.indexOf(ev.nuance) >= 0, 'generic/' + preset + ': every ledger row names its nuance', ev.code);
    ok(!!ev.cause && !!ev.outcome, 'generic/' + preset + ': every ledger row says what happened and what followed', ev.code);
    ok(ev.code === 'LICENCE' || ev.code === 'ALLOC' || !!ev.batch, 'generic/' + preset + ': every batch-level row names its batch', ev.code);
  });
  const sum = Object.values(C.cons.byCode).reduce((a, c) => a + c.rupees, 0);
  ok(Math.abs(sum - C.cons.total.rupees) < 1, 'generic/' + preset + ': the ledger sums to its total', n(sum) + ' vs ' + n(C.cons.total.rupees));
  ok(C.repair.unplaced === 0 || C.repair.placed > 0, 'generic/' + preset + ': the repair sweep places what it can', C.repair.placed + '/' + (C.repair.placed + C.repair.unplaced));
  ok(C.proofGeneric.total.violations > 0, 'generic/' + preset + ': the generic plan really does break constraints',
     C.proofGeneric.total.violations + ' violations');

  // the fairness gate
  ok(C.naive.generic.otif >= C.naive.aware.otif - 1e-9 || C.naive.generic.cleanHours <= C.naive.aware.cleanHours,
     'FAIRNESS/' + preset + ': the generic plan wins the naive scoreboard',
     'generic OTIF ' + (C.naive.generic.otif * 100).toFixed(1) + '% vs aware ' + (C.naive.aware.otif * 100).toFixed(1) + '%');
  ok(C.fair, 'FAIRNESS/' + preset + ': engine agrees the comparison is not a straw man');

  // identical physics under both rule sets
  const gY = {}, aY = {};
  C.generic.fwd.forEach(b => { gY[b.productId + '|' + b.nth] = b; });
  C.aware.fwd.forEach(b => { aY[b.productId + '|' + b.nth] = b; });
  let compared = 0;
  Object.keys(aY).forEach(k => {
    if (!gY[k]) return;
    compared++;
    ok(Math.abs(aY[k].actualKg - gY[k].actualKg) < 1e-6, 'PHYSICS/' + preset + ': the same batch yields the same mass under both rule sets', k);
    ok(Math.abs(aY[k].assay - gY[k].assay) < 1e-9, 'PHYSICS/' + preset + ': the same batch assays the same under both rule sets', k);
    ok(aY[k].qcMin === gY[k].qcMin, 'PHYSICS/' + preset + ': QC release takes the same time under both rule sets', k);
  });
  ok(compared > 20, 'PHYSICS/' + preset + ': enough batches in common to compare', compared + ' compared');
  if (!QUIET) console.log(`  ${n(checks)} checks so far · ledger ₹${(C.cons.total.rupees / 1e7).toFixed(2)} Cr over ${C.cons.total.n} rows · physics pairs ${compared}`);
});

// ---------------------------------------------------------------------------------------------------- determinism
section('determinism and the frozen history');
const a1 = E.plan(m, hist, { preset: 'balanced', rules: 'aware' });
const a2 = E.plan(m, hist, { preset: 'balanced', rules: 'aware' });
ok(a1.kpi.batches === a2.kpi.batches && Math.abs(a1.kpi.otif - a2.kpi.otif) < 1e-12 && a1.kpi.madeKg === a2.kpi.madeKg,
   'the same settings give the same plan twice', a1.kpi.batches + ' vs ' + a2.kpi.batches);
ok(JSON.stringify(a1.batches.map(b => [b.id, b.s, b.e])) === JSON.stringify(a2.batches.map(b => [b.id, b.s, b.e])),
   'every batch lands at the same minute on a re-run');
const h2 = E.history(m);
ok(JSON.stringify(hist.batches.map(b => [b.id, b.s, b.e])) === JSON.stringify(h2.batches.map(b => [b.id, b.s, b.e])),
   'the frozen history is reproducible');
PRESETS.forEach(p => ok(results[p].aware.nHist === hist.batches.length, 'the frozen history is unchanged by preset ' + p));
const m2 = E.prepare(D, {});
const hist2 = E.history(m2);
ok(hist2.batches.length === hist.batches.length, 'a fresh model gives the same history', hist2.batches.length + ' vs ' + hist.batches.length);

// presets must actually do something
const spread = new Set(PRESETS.map(p => results[p].aware.kpi.batches + '/' + results[p].aware.kpi.cleanHours));
ok(spread.size > 1, 'the objective weights change the plan', 'all presets produced the identical plan: the weights are not reaching the scheduler');

// ---------------------------------------------------------------------------------------------------- report
console.log('\n' + '-'.repeat(72));
if (fails.length) {
  console.log(`ENGINE  FAIL  ${n(fails.length)} of ${n(checks)} checks`);
  const by = {};
  fails.forEach(f => { const k = f.split('  — ')[0]; by[k] = (by[k] || 0) + 1; });
  Object.entries(by).sort((a, b) => b[1] - a[1]).slice(0, 18).forEach(([k, v]) => console.log(`   ${String(v).padStart(6)}  ${k}`));
  process.exit(1);
}
console.log(`ENGINE  PASS  ${n(checks)} checks, 0 violations`);
const C = results.balanced;
console.log(`  aware   ${C.aware.kpi.batches} batches · OTIF ${(C.aware.kpi.otif * 100).toFixed(1)}% · ${n(C.aware.kpi.cleanHours)} cleaning hours · ${n(C.proof.total.checks)} constraint checks, 0 violations`);
console.log(`  generic ${C.generic.kpi.batches} batches · OTIF ${(C.generic.kpi.otif * 100).toFixed(1)}% · ${n(C.generic.kpi.cleanHours)} cleaning hours · ${n(C.proofGeneric.total.violations)} violations`);
console.log(`  the generic plan's assumptions cost ₹${(C.cons.total.rupees / 1e7).toFixed(2)} Cr across ${C.cons.total.n} priced events on all seven plant nuances`);
process.exit(0);
