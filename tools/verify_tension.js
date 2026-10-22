/* The tension gate:  node tools/verify_tension.js

   A demo where nothing binds has nothing to show. Every claim this demo makes needs something in the data to bite on —
   a utility that runs out, a consent that is reached, a licence with no headroom left, a pair that cannot be sequenced,
   a lot that cannot be shipped. It is easy to regenerate the dataset, or retune a cap, and quietly lose all of that: the
   pages still render, the verifiers still pass, and the demo says nothing.

   So the bands below are part of the build. They are deliberately two-sided — a constraint that binds on every hour is
   as useless as one that never binds, because a plant that cannot move is not a planning problem.
*/
const path = require('path');
const root = path.join(__dirname, '..');
global.window = global;
require(path.join(root, 'data', 'chm-data.js'));
require(path.join(root, 'assets', 'chm-engine.js'));
require(path.join(root, 'assets', 'chm-results.js'));
const E = global.CHMEngine, D = global.CHM;

const n = (x, d = 0) => (x == null || isNaN(x) ? '—' : Number(x).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d }));
const pct = (x, d = 1) => (x * 100).toFixed(d) + '%';
let fails = [], checks = 0;
function band(name, v, lo, hi, fmt) {
  checks++;
  const f = fmt || (x => n(x));
  const ok = v >= lo && v <= hi;
  console.log((ok ? '  ok   ' : '  FAIL ') + name.padEnd(62) + f(v).padStart(10) + '   band ' + f(lo) + ' – ' + f(hi));
  if (!ok) fails.push(name + ' = ' + f(v) + ', outside ' + f(lo) + '–' + f(hi));
}
function atLeast(name, v, lo, fmt) { band(name, v, lo, Infinity, fmt || (x => n(x))); }

const m = E.prepare(D, {});
const hist = E.history(m);
const C = E.compare(m, hist, { preset: 'balanced' });
const A = C.aware, G = C.generic;

console.log('TENSION — does this dataset give every claim something to bite on?\n');
console.log('the plant');
band('demand as a share of the capacity a plan can realise', D.meta.stats.bindingLoad, D.cfg.demandLoad - 0.03, D.cfg.demandLoad + 0.03, x => x.toFixed(3));
band('short lines, as a share of the book (uncomfortable, not broken)',
     A.kpi.shortLines / A.lines.length, 0.0, 0.09, x => pct(x, 1));
// A plant at this load with these windows runs some orders late; a plan that runs none is not a plan anyone believes.
// The band is wide on purpose — it is here to catch a BROKEN plan, not a pressured one.
band('late lines in the chemical-aware plan', A.kpi.late / A.lines.length, 0.02, 0.32, x => pct(x, 1));
// Measured on the busiest class, not across every unit: a mill that runs an hour a batch and a packing line that runs a
// shift a week drag a plant-wide share towards zero and say nothing about whether cleaning binds on the train that matters.
band("cleaning as a share of the busiest class's hours", A.kpi.utilByClass[A.kpi.utilClass].clean, 0.08, 0.50, x => pct(x, 1));
band("cleaning as a share of the plan's run time", A.kpi.cleanHours * 60 / Math.max(1, A.kpi.busyMin), 0.15, 0.70, x => pct(x, 1));
atLeast("batches per campaign at the route's first operation", A.kpi.batches / Math.max(1, A.kpi.campaigns || 1), 1.8, x => n(x, 2));

console.log('\nthe seven plant nuances each cost the generic plan something');
['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7'].forEach(nu => {
  const r = C.cons.byNuance[nu] || { n: 0, rupees: 0 };
  checks++;
  const ok = r.n > 0 && r.rupees > 0;
  console.log((ok ? '  ok   ' : '  FAIL ') + (nu + ' ' + (global.window.CHM_NU ? '' : '')).padEnd(62) +
              (String(r.n) + ' events').padStart(10) + '   ' + (r.rupees / 1e5).toFixed(1) + ' L');
  if (!ok) fails.push(nu + ' costs the generic plan nothing — the demo claims this nuance and would show an empty page');
});

console.log('\nshared resources bind — in the aware plan, the generic one, or both');
let utilBind = 0;
m.utils.forEach(u => {
  const at = A.kpi.utilAtCap[u.id] || 0;
  const genOver = (G.kpi.utilPeak[u.id] || 0) > u.cap + 1e-6;
  if (at > 0 || genOver) utilBind++;
  console.log(`         ${u.id.padEnd(8)} aware peak ${n(A.kpi.utilPeak[u.id], 1).padStart(8)} / cap ${n(u.cap, 1).padStart(7)}` +
              `  ${String(at).padStart(4)} h at cap   generic peak ${n(G.kpi.utilPeak[u.id], 1).padStart(8)}${genOver ? '  OVER' : ''}`);
});
atLeast('utilities that bind somewhere', utilBind, 2);
let wasteBind = 0;
m.wastes.forEach(w => {
  const at = A.kpi.wasteAtCap[w.id] || 0;
  const genOver = C.cons.events.some(e => e.waste === w.id);
  if (at > 0 || genOver) wasteBind++;
});
atLeast('waste streams that bind somewhere', wasteBind, 1);
const tightHaz = m.hazs.filter(h => (A.kpi.licenceMin[h.id] != null ? A.kpi.licenceMin[h.id] : 1) < 0.05).length;
atLeast('hazard classes with under 5% licence headroom', tightHaz, 1);
atLeast('tankers the licence or a full tank turned away', A.refused.filter(r => r.at >= m.asOf).length, 1);

console.log('\nthe cleaning matrix has something to sequence around');
const mx = D.m.cleanMatrix;
atLeast('pairs that need a clean-down or cannot run at all', mx.filter(r => (r.grade === 'DEDICATE' || r.grade === 'FORBIDDEN') && r.frm !== r.to).length, 6);
atLeast('pairs that need a boil-out', mx.filter(r => r.grade === 'BOILOUT').length, 10);
atLeast('cleans in the plan that are a boil-out or longer',
        A.cleans.filter(c => c.s >= m.asOf && (c.grade === 'BOILOUT' || c.grade === 'DEDICATE')).length, 10);

console.log('\nhold windows are actually tight');
let links = 0, tight = 0;
A.fwd.forEach(b => {
  const p = m.P[b.pix];
  for (let i = 1; i < b.ops.length; i++) {
    links++;
    if ((b.ops[i].s - b.ops[i - 1].e) > p.ops[i].maxLag * 0.8) tight++;
  }
});
atLeast('links in the plan', links, 80);
// how much of a window a link uses is an OUTPUT; what the data has to carry is windows that are genuinely tight
let tightWin = 0, allWin = 0;
m.P.forEach(p => { for (let i = 1; i < p.ops.length; i++) { allWin++; if (p.ops[i].maxLagH <= 24) tightWin++; } });
band('links whose window is 24 h or less', tightWin / Math.max(1, allWin), 0.30, 1.0, x => pct(x, 0));
band('links that used over 80% of their window', tight / Math.max(1, links), 0.005, 0.75, x => pct(x, 1));
atLeast('starts held back on purpose to protect a window', A.sacrifices.length, 1);
atLeast('hours a unit was held idle to protect a window', A.kpi.sacrificeMin / 60, 20, x => n(x, 0));

console.log('\nallocation is a real decision');
// Most blends are there because an order is several batches, which says nothing about matching on spec. The blend that
// matters is the one the SPEC forced: a lot held the quantity and still could not be used.
// Lines whose served lots were NOT simply the oldest available: the spec, the approval or the remaining life turned
// at least one lot away, so what this line shipped was decided by more than quantity and date.
const SPECWHY = ['assay', 'impurity', 'psd', 'life', 'site'];
const rejByLine = {};
A.rejects.forEach(r => { if (SPECWHY.indexOf(r.why) >= 0) (rejByLine[r.lineId] = rejByLine[r.lineId] || new Set()).add(r.lotId); });
let specBlend = 0;
A.allocs.forEach(a => { if ((rejByLine[a.lineId] || new Set()).size > 0) specBlend++; });
band('allocations that needed more than one lot', A.kpi.blended / Math.max(1, A.kpi.allocs), 0.10, 0.92, x => pct(x, 1));
atLeast('allocations the spec, the route or the remaining life redirected', specBlend, 10);
atLeast('lots turned down on spec, route, approval or remaining life', A.rejects.length, 20);
const whys = {};
A.rejects.forEach(r => { whys[r.why] = (whys[r.why] || 0) + 1; });
atLeast('distinct reasons a lot was turned down', Object.keys(whys).length, 3);
console.log('         ' + Object.keys(whys).sort().map(k => k + ' ' + whys[k]).join(' · '));
atLeast('lines a customer minimum shelf life applies to', A.lines.filter(l => l.minLifeM > 0).length, 20);

console.log('\nthe comparison is fair and the aware plan is clean');
checks++;
const fair = C.naive.generic.otif >= C.naive.aware.otif - 1e-9 || C.naive.generic.cleanHours <= C.naive.aware.cleanHours;
console.log((fair ? '  ok   ' : '  FAIL ') + 'the generic plan wins the naive scoreboard'.padEnd(62) +
            (pct(C.naive.generic.otif) + ' / ' + pct(C.naive.aware.otif)).padStart(16));
if (!fair) fails.push('the generic plan loses the naive scoreboard too — the comparison is a straw man');
checks++;
console.log((C.proof.total.violations === 0 ? '  ok   ' : '  FAIL ') + 'the aware plan breaks nothing'.padEnd(62) +
            (C.proof.total.violations + ' of ' + n(C.proof.total.checks)).padStart(16));
if (C.proof.total.violations) fails.push('the aware plan breaks ' + C.proof.total.violations + ' constraints');
atLeast('constraints the generic plan breaks', C.proofGeneric.total.violations, 50);
atLeast('what the generic plan\'s assumptions cost, in crore', C.cons.total.rupees / 1e7, 3, x => x.toFixed(2));

console.log('\n' + '-'.repeat(92));
if (fails.length) {
  console.log(`TENSION  FAIL  ${fails.length} of ${checks} checks`);
  fails.forEach(f => console.log('   ' + f));
  console.log('\n   Re-measure with  node tools/calibrate.js 92  and set the caps in tools/gen/config.py from it.');
  process.exit(1);
}
console.log(`TENSION  PASS  ${checks} checks — every claim has something in the data to bite on`);
process.exit(0);
