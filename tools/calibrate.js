/* Calibrate the plant's shared constraints against its own demand:  node tools/calibrate.js [percentile]

   The utility, effluent and recovery caps have to BIND — a demo where nothing binds has nothing to show — without
   halving the plant. So they are not guessed: this runs the plan with every shared constraint switched off, measures the
   hourly and daily load each resource would actually see, and prints the cap that leaves the chosen percentile of hours
   inside it. Those numbers go into tools/gen/config.py, and tools/verify_tension.py holds the band afterwards.
*/
const path = require('path');
const root = path.join(__dirname, '..');
global.window = global;
require(path.join(root, 'data', 'chm-data.js'));
require(path.join(root, 'assets', 'chm-engine.js'));
require(path.join(root, 'assets', 'chm-results.js'));
const E = global.CHMEngine, D = global.CHM;
const PCTL = +(process.argv[2] || 88) / 100;

const m = E.prepare(D, {});
// switch every shared constraint off so the measurement is of DEMAND, not of a cap feeding back on itself
m.utils.forEach(u => { for (let h = 0; h < m.H; h++) m.utilCap[u.ix * m.H + h] = 1e9; });
m.wastes.forEach(w => { w.cap = 1e9; });
m.recovery.cap = 1e9;
m.hazs.forEach(h => { h.licensedKL = 1e9; });

const hist = E.history(m);
const plan = E.plan(m, hist, { preset: 'balanced', rules: 'aware' });
console.log(`unconstrained plan: ${plan.kpi.batches} batches, ${plan.kpi.madeKg.toLocaleString('en-IN')} kg, OTIF ${(plan.kpi.otif * 100).toFixed(1)}%, utilisation ${(plan.kpi.util * 100).toFixed(1)}%\n`);

const h0 = Math.floor(m.asOf / 60), h1 = Math.ceil(m.end / 60);
const d0 = Math.floor(m.asOf / 1440), d1 = Math.ceil(m.end / 1440);
const q = (arr, p) => { const a = arr.slice().sort((x, y) => x - y); return a.length ? a[Math.min(a.length - 1, Math.floor(p * a.length))] : 0; };

console.log('UTILITIES — hourly load over the forward window (idle hours excluded from the percentile)');
console.log('id      unit     current    p50     p75     p88     p95     max   suggested');
m.utils.forEach(u => {
  const all = [];
  for (let h = h0; h < h1; h++) all.push(plan.state.util[u.ix * m.H + h]);
  const on = all.filter(x => x > 0);
  const sug = Math.max(1, Math.round(q(on, PCTL) / (u.unit === 't/h' ? 0.1 : 10)) * (u.unit === 't/h' ? 0.1 : 10));
  console.log(`${u.id.padEnd(7)} ${u.unit.padEnd(8)} ${String(u.cap).padStart(7)} ${q(on, .5).toFixed(1).padStart(7)} ${q(on, .75).toFixed(1).padStart(7)} ${q(on, .88).toFixed(1).padStart(7)} ${q(on, .95).toFixed(1).padStart(7)} ${Math.max(...all).toFixed(1).padStart(7)}   ${sug}`);
});

console.log('\nWASTE — daily load over the forward window');
console.log('id      unit         current    p50     p75     p88     p95     max   suggested');
m.wastes.forEach(w => {
  const all = [];
  for (let d = d0; d < d1; d++) all.push(plan.state.waste[w.ix * m.Dn + d]);
  const on = all.filter(x => x > 0);
  const sug = Math.round(q(on, PCTL) / 2) * 2;
  console.log(`${w.id.padEnd(7)} ${w.unit.padEnd(12)} ${String(w.cap === 1e9 ? '-' : w.cap).padStart(7)} ${q(on, .5).toFixed(1).padStart(7)} ${q(on, .75).toFixed(1).padStart(7)} ${q(on, .88).toFixed(1).padStart(7)} ${q(on, .95).toFixed(1).padStart(7)} ${Math.max(...all).toFixed(1).padStart(7)}   ${sug}`);
});

const rec = [];
for (let d = d0; d < d1; d++) rec.push(plan.state.recov[d]);
const recOn = rec.filter(x => x > 0);
console.log(`\nSOLVENT RECOVERY  kL/day  p50 ${q(recOn, .5).toFixed(1)}  p75 ${q(recOn, .75).toFixed(1)}  p88 ${q(recOn, .88).toFixed(1)}  p95 ${q(recOn, .95).toFixed(1)}  max ${Math.max(...rec).toFixed(1)}  suggested ${Math.round(q(recOn, PCTL))}`);

console.log('\nHAZARD LICENCE — kL held per class over the forward window');
m.hazs.forEach(hz => {
  const all = [];
  for (let d = d0; d < d1; d++) all.push(E.hazPos(m, plan.state, hz.ix, d));
  console.log(`  ${hz.id.padEnd(6)} p50 ${q(all, .5).toFixed(1).padStart(7)}  p88 ${q(all, .88).toFixed(1).padStart(7)}  max ${Math.max(...all).toFixed(1).padStart(7)}  suggested licence ${Math.round(Math.max(...all) / 5) * 5}`);
});

const cls = {};
plan.fwd.forEach(b => b.ops.forEach(o => { cls[o.cls] = (cls[o.cls] || 0) + (o.e - o.s) / 60; }));
const avail = {};
m.U.forEach(u => { avail[u.cls] = (avail[u.cls] || 0) + (m.end - m.asOf) / 60 * u.uptime; });
console.log('\nEQUIPMENT LOAD (unconstrained plan, processing only):');
Object.keys(cls).sort().forEach(c => console.log(`  ${c.padEnd(10)} ${Math.round(cls[c]).toLocaleString('en-IN').padStart(7)} h of ${Math.round(avail[c]).toLocaleString('en-IN').padStart(7)} h  = ${(cls[c] / avail[c] * 100).toFixed(1)}%`));
console.log('  cleaning  ', Math.round(plan.kpi.cleanHours).toLocaleString('en-IN'), 'h across all units');
