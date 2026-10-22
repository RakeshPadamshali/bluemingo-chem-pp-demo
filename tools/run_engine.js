/* Run the engine outside the browser: node tools/run_engine.js [preset]
   Prints the two plans side by side, the consequence ledger and the proof. */
const path = require('path');
const root = path.join(__dirname, '..');
global.window = global;
require(path.join(root, 'data', 'chm-data.js'));
require(path.join(root, 'assets', 'chm-engine.js'));
require(path.join(root, 'assets', 'chm-results.js'));

const E = global.CHMEngine, D = global.CHM;
const preset = process.argv[2] || 'balanced';
const n = (x, d = 0) => (x == null || isNaN(x) ? '—' : Number(x).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d }));
const pct = (x, d = 1) => (x == null || isNaN(x) ? '—' : (x * 100).toFixed(d) + '%');
const rs = (x) => { const a = Math.abs(x); return (x < 0 ? '−' : '') + '₹' + (a >= 1e7 ? (a / 1e7).toFixed(2) + ' Cr' : a >= 1e5 ? (a / 1e5).toFixed(1) + ' L' : n(a)); };

let t0 = Date.now();
const m = E.prepare(D, {});
const tPrep = Date.now() - t0;
t0 = Date.now();
const hist = E.history(m);
const tHist = Date.now() - t0;
console.log(`prepare ${tPrep} ms | history ${tHist} ms — ${hist.batches.length} batches, ${hist.cleans.length} cleans, ${hist.refused.length} refused deliveries`);

t0 = Date.now();
const C = E.compare(m, hist, { preset });
console.log(`compare ${Date.now() - t0} ms (engine reports ${C.ms} ms) | preset ${preset}`);

const rows = [
  ['batches', C.generic.kpi.batches, C.aware.kpi.batches],
  ['output kg (actual)', n(C.generic.kpi.madeKg), n(C.aware.kpi.madeKg)],
  ['output kg (nominal)', n(C.generic.kpi.nominalKg), n(C.aware.kpi.nominalKg)],
  ['yield realisation', pct(C.generic.kpi.yieldRealisation), pct(C.aware.kpi.yieldRealisation)],
  ['OTIF', pct(C.generic.kpi.otif), pct(C.aware.kpi.otif)],
  ['late lines', C.generic.kpi.late, C.aware.kpi.late],
  ['short lines / kg', C.generic.kpi.shortLines + ' / ' + n(C.generic.kpi.shortKg), C.aware.kpi.shortLines + ' / ' + n(C.aware.kpi.shortKg)],
  ['delay cost', rs(C.generic.kpi.delayCost), rs(C.aware.kpi.delayCost)],
  ['contribution', rs(C.generic.kpi.contribution), rs(C.aware.kpi.contribution)],
  ['cleans / hours', C.generic.kpi.cleanCount + ' / ' + C.generic.kpi.cleanHours, C.aware.kpi.cleanCount + ' / ' + C.aware.kpi.cleanHours],
  ['unit utilisation', pct(C.generic.kpi.util), pct(C.aware.kpi.util)],
  ['sacrifices (idle on purpose)', C.generic.kpi.sacrifices, C.aware.kpi.sacrifices + ' (' + Math.round(C.aware.kpi.sacrificeMin / 60) + ' h)'],
  ['deliveries refused', C.generic.kpi.refused, C.aware.kpi.refused],
  ['allocations / blended', C.generic.kpi.allocs + ' / ' + C.generic.kpi.blended, C.aware.kpi.allocs + ' / ' + C.aware.kpi.blended],
  ['proof violations', C.proofGeneric.total.violations + ' / ' + n(C.proofGeneric.total.checks), C.proof.total.violations + ' / ' + n(C.proof.total.checks)],
];
console.log('\n' + 'metric'.padEnd(30) + 'GENERIC'.padStart(18) + 'CHEMICAL-AWARE'.padStart(20));
console.log('-'.repeat(68));
rows.forEach(r => console.log(String(r[0]).padEnd(30) + String(r[1]).padStart(18) + String(r[2]).padStart(20)));

console.log('\nutility peaks (aware):', Object.entries(C.aware.kpi.utilPeak).map(([k, v]) => `${k} ${v} (${C.aware.kpi.utilAtCap[k]} h at cap)`).join(', '));
console.log('utility peaks (generic):', Object.entries(C.generic.kpi.utilPeak).map(([k, v]) => `${k} ${v} (${C.generic.kpi.utilAtCap[k]} h at cap)`).join(', '));
console.log('waste (aware):', Object.entries(C.aware.kpi.wasteTotal).map(([k, v]) => `${k} ${v} (${C.aware.kpi.wasteAtCap[k]} d at cap)`).join(', '));
console.log('licence headroom min (aware):', JSON.stringify(C.aware.kpi.licenceMin), '| generic:', JSON.stringify(C.generic.kpi.licenceMin));

console.log('\n--- CONSEQUENCE LEDGER (what the generic plan\'s assumptions cost) ---');
console.log('nuance  code              n   kg        hours     cost');
Object.values(C.cons.byCode).sort((a, b) => b.rupees - a.rupees).forEach(c =>
  console.log(`${c.nuance.padEnd(7)} ${c.code.padEnd(17)} ${String(c.n).padStart(3)}  ${n(c.kg).padStart(8)}  ${n(c.hours, 1).padStart(8)}  ${rs(c.rupees)}`));
console.log(`TOTAL   ${String(C.cons.total.n).padStart(21)}  ${n(C.cons.total.kg).padStart(8)}  ${n(C.cons.total.hours, 1).padStart(8)}  ${rs(C.cons.total.rupees)}`);
console.log(`status-changing ${C.cons.statusChanging} · priced but not propagated ${C.cons.unmodelled} · repairs placed ${C.repair.placed}, unplaced ${C.repair.unplaced}`);

console.log('\n--- PROOF (aware plan) ---');
Object.values(C.proof.byNuance).forEach(r => console.log(`  ${r.nuance.padEnd(5)} ${r.label.padEnd(48)} ${n(r.checks).padStart(8)} checks  ${r.violations} violations`));
if (C.proof.total.violations) {
  console.log('\n  FIRST VIOLATIONS:');
  Object.values(C.proof.byNuance).forEach(r => r.detail.slice(0, 4).forEach(d => console.log('   ! ' + r.nuance + ' ' + d)));
}
console.log('\n--- FAIRNESS GATE (generic must win the naive scoreboard) ---');
console.log('  naive OTIF    generic', pct(C.naive.generic.otif), ' aware', pct(C.naive.aware.otif));
console.log('  naive cleans  generic', C.naive.generic.cleanHours, 'h  aware', C.naive.aware.cleanHours, 'h');
console.log('  naive output  generic', n(C.naive.generic.outputKg), ' aware', n(C.naive.aware.outputKg));
console.log('  gate:', C.fair ? 'PASS' : 'FAIL — the generic plan loses on paper too, which makes it a straw man');

console.log('\n--- S&OP ---');
console.log(' ', C.sop.headline, '| bottleneck', C.sop.bottleneck, '| cleaning share', pct(C.sop.cleanShare));
console.log('  months over capacity:', C.sop.months.filter(x => !x.feasible).map(x => `${x.label} ${pct(x.loadPct)}`).join(', ') || 'none');
console.log('  top 3 by margin per bottleneck hour:', C.sop.rank.filter(r => !r.offBottleneck).slice(0, 3).map(r => `${r.productId} ${rs(r.perBhHour)}/h`).join(', '));
console.log('  off the bottleneck entirely:', C.sop.rank.filter(r => r.offBottleneck).map(r => r.productId).join(', ') || 'none');
console.log('\nengine stats:', JSON.stringify(E.stats));
