/* Bluemingo PP — results: allocation, the one KPI basis, the consequence replay, the repair sweep, the proof and S&OP.
   Loads straight after chm-engine.js and extends the same CHMEngine object.

   The three things this file exists to keep honest:

   1. ONE BASIS. assemble() is the only place a KPI is computed. Every page reads kpi.* and lines[]; nothing recounts.
   2. consequence() REPLAYS, it never re-schedules. It walks the generic plan in time order, rebuilds every clock and
      level from scratch, and prices what each of the deck's seven assumptions cost on that plan's own timeline. Only ONE
      status-changing consequence per batch is modelled (highest priority first) and the rest are priced but not
      propagated — the unmodelled count is reported, not hidden.
   3. proof() re-checks every constraint over a committed plan and reports CHECKS and VIOLATIONS, so "honoured" is a
      number on screen and not a claim. */
(function (root) {
  'use strict';
  var E = root.CHMEngine;
  if (!E) { console.error('chm-engine.js must load before chm-results.js'); return; }

  function clamp(x, a, b) { return x < a ? a : x > b ? b : x; }
  function cmpId(a, b) { return a < b ? -1 : a > b ? 1 : 0; }
  var MONTH = 30.4 * 1440;

  // =====================================================================================================================
  // ALLOCATION — spec, route, approval and remaining life, with blending where one lot will not do
  // =====================================================================================================================
  /* Lines are served in a fixed priority (regulated export first: its approval set is the narrowest, so it has the least
     room to be served later). For each line: FEFO over the lots that pass on their own; then a two-lot blend, weighted
     on ACTIVE content; then one repair sweep that swaps the binding attribute's worst contributor. Cap three lots.
     A shortfall is reported with the reason that caused it, never as "infeasible". */
  var PRIO = { EXPORT_REG: 0, EXPORT: 1, DOM_COMMITTED: 2, DOM_OPEN: 3 };
  var CAP = 3;                 // at most three lots in one customer lot: more than that is not a blend, it is a bucket

  function lotOk(m, L, lot, now, W, horizon) {
    var l = L.l;
    if (lot.pix !== l.pix) return 'product';
    if (lot.left <= 0) return 'empty';
    // Released within the horizon at all, not released by today: a line already past its date is LATE, not short, and
    // reporting 6 t of released stock as "awaiting QC" because the line was overdue was simply wrong.
    if (lot.readyAt != null && lot.readyAt > horizon) return 'qc';
    if (W.rAlloc !== 'spec') return null;                        // generic: quantity and date only
    if (lot.assay < l.assayMin) return 'assay';
    if (lot.imp > l.impMax) return 'impurity';
    if (lot.psd > l.psdMax) return 'psd';
    if (l.minLifeM) {
      var leftM = (lot.retestAt - now) / MONTH;
      if (leftM < l.minLifeM) return 'life';
    }
    if (l.regulated) {
      var ap = m.approvals[l.cust + '|' + (lot.siteId || 'UNIT-2')];
      if (ap && ap.approved === false) return 'site';
    }
    return null;
  }
  function blendOf(parts) {
    var kg = 0, act = 0, imp = 0, psd = 0, life = Infinity;
    parts.forEach(function (x) { kg += x.kg; act += x.kg * x.lot.assay / 100; imp += x.kg * x.lot.imp; psd = Math.max(psd, x.lot.psd); life = Math.min(life, x.lot.retestAt); });
    return { kg: kg, assay: kg ? Math.round(act / kg * 10000) / 100 : 0, imp: kg ? Math.round(imp / kg * 1000) / 1000 : 0, psd: psd, retestAt: life };
  }
  function blendFits(m, L, b, now) {
    var l = L.l;
    if (b.assay < l.assayMin) return 'assay';
    if (b.imp > l.impMax) return 'impurity';
    if (b.psd > l.psdMax) return 'psd';
    if (l.minLifeM && (b.retestAt - now) / MONTH < l.minLifeM) return 'life';
    return null;
  }

  E.allocate = function (m, st, W, now) {
    var lines = st.lineOrder.map(function (id) { return st.lines[id]; })
      .filter(function (L) { return !L.whatifCancel && L.l.qty > L.cancelled; });
    /* Priority, then the lines that are actually FUSSY, then the date. The scarce in-spec material has to go where the
       spec requires it: served date-first, a loose line takes a lot that a tight line later cannot replace, and the
       tight line short-ships while in-spec stock sits against an order that would have taken anything. */
    lines.sort(function (a, b) {
      return (PRIO[a.l.cls] - PRIO[b.l.cls]) ||
             ((b.l.tightSpec ? 1 : 0) - (a.l.tightSpec ? 1 : 0)) ||
             ((b.l.minLifeM || 0) - (a.l.minLifeM || 0)) ||
             (a.l.due - b.l.due) || cmpId(a.l.id, b.l.id);
    });
    var lots = st.lots.slice().sort(function (a, b) { return a.retestAt - b.retestAt || cmpId(a.id, b.id); });  // FEFO
    var allocs = [], rejects = [];
    lines.forEach(function (L) {
      var want = Math.max(0, L.l.qty - L.cancelled - L.shipped), got = 0, used = [];
      if (want <= 0) return;
      /* A lot serves a line if it is released by the time the line has to SHIP, not by the time the planner happens to
         be looking. Testing every lot against the as-of moment made a lot that clears QC next week unusable for a line
         due next month — which is not a shortage, it is an arithmetic error. Remaining shelf life is measured at the
         same moment, because that is when the customer receives it. */
      var at = Math.max(now, L.l.due);
      // 1. single lots that pass on their own, FEFO, up to the blend cap (a customer lot is one COA, not a bucket)
      for (var i = 0; i < lots.length && got < want && used.length < CAP; i++) {
        var why = lotOk(m, L, lots[i], at, W, m.end);
        if (why) { if (why !== 'product' && why !== 'empty') rejects.push({ lineId: L.l.id, lotId: lots[i].id, why: why }); continue; }
        var take = Math.min(lots[i].left, want - got);
        used.push({ lot: lots[i], kg: take }); got += take;
      }
      /* 2. a blend, in the proportion the spec actually needs.
            Pair a lot that passes with one that does not, and work out how much of the marginal one the clean one can
            carry: for a limit that averages down (impurity) the share is (dirty - limit) / (dirty - clean); for a
            minimum that averages up (assay) it is the mirror. Mixing them one to one and hoping is not blending. */
      if (got < want && W.rAlloc === 'spec') {
        var pool = lots.filter(function (x) { return x.pix === L.l.pix && x.left > 0 && (x.readyAt == null || x.readyAt <= m.end) && !used.some(function (u) { return u.lot === x; }); });
        var clean = pool.filter(function (x) { return !lotOk(m, L, x, at, W, m.end); });
        var marg = pool.filter(function (x) { return lotOk(m, L, x, at, W, m.end) === 'impurity' || lotOk(m, L, x, at, W, m.end) === 'assay'; });
        for (var a = 0; a < clean.length && got < want && used.length + 2 <= CAP; a++) {
          for (var b2 = 0; b2 < marg.length && got < want && used.length + 2 <= CAP; b2++) {
            var cl = clean[a], mg = marg[b2];
            // the largest share of the marginal lot that still clears every averaging limit, with a little margin
            var share = 1;
            if (mg.imp > L.l.impMax && mg.imp > cl.imp) share = Math.min(share, (L.l.impMax - cl.imp) / (mg.imp - cl.imp));
            if (mg.assay < L.l.assayMin && cl.assay > mg.assay) share = Math.min(share, (cl.assay - L.l.assayMin) / (cl.assay - mg.assay));
            share = Math.max(0, Math.min(0.95, share * 0.96));
            if (share <= 0.02) continue;
            if (mg.psd > L.l.psdMax) continue;                  // particle size does not average, it is the worst of them
            var needKg = want - got;
            var kb2 = Math.min(mg.left, Math.floor(needKg * share));
            var ka2 = Math.min(cl.left, needKg - kb2);
            if (kb2 <= 0 || ka2 <= 0) continue;
            var parts = [{ lot: cl, kg: ka2 }, { lot: mg, kg: kb2 }];
            var bl = blendOf(parts), bad = blendFits(m, L, bl, at);
            if (bad) continue;
            used = used.concat(parts); got += bl.kg; blendmark(parts);
          }
        }
        /* and the plain case: two lots that each pass but neither of which holds enough on its own. Step 1 takes up to
           the blend cap of single lots; this picks up what is left when the cap was not the binding thing. */
        for (var c2 = 0; c2 < pool.length && got < want && used.length + 2 <= CAP; c2++) {
          for (var d2 = 0; d2 < pool.length && got < want && used.length + 2 <= CAP; d2++) {
            if (c2 === d2) continue;
            var pa = pool[c2], pb = pool[d2];
            if (used.some(function (u) { return u.lot === pa || u.lot === pb; })) continue;
            var ia = Math.min(pa.left, want - got), ib = Math.min(pb.left, want - got);
            if (ia <= 0 || ib <= 0) continue;
            var ps = [{ lot: pa, kg: ia }, { lot: pb, kg: ib }];
            var bl2 = blendOf(ps);
            if (blendFits(m, L, bl2, at)) continue;
            var take = Math.min(bl2.kg, want - got), sc2 = take / bl2.kg;
            ps.forEach(function (x) { x.kg = Math.round(x.kg * sc2); });
            used = used.concat(ps); got += take; blendmark(ps);
          }
        }
      }
      used.forEach(function (u) { u.lot.left -= u.kg; });
      if (used.length) {
        var bl2 = blendOf(used);
        var readyAll = used.reduce(function (q, u) { return Math.max(q, u.lot.readyAt == null ? 0 : u.lot.readyAt); }, 0);
        if (readyAll) L.lastEnd = Math.max(L.lastEnd || 0, readyAll);
        allocs.push({ lineId: L.l.id, orderId: L.l.orderId, productId: L.l.productId, cust: L.l.cust, cls: L.l.cls,
                      readyAt: readyAll || null,
                      kg: Math.min(got, want), lots: used.map(function (u) { return { id: u.lot.id, kg: u.kg, assay: u.lot.assay, imp: u.lot.imp, psd: u.lot.psd }; }),
                      blended: used.length > 1, assay: bl2.assay, imp: bl2.imp, psd: bl2.psd, retestAt: bl2.retestAt,
                      spec: { assayMin: L.l.assayMin, impMax: L.l.impMax, psdMax: L.l.psdMax, minLifeM: L.l.minLifeM },
                      coa: L.l.coa });
        L.shipped += Math.min(got, want);
      }
      L.short = Math.max(0, want - got);
      if (L.short > 0) {
        var rs = rejects.filter(function (r) { return r.lineId === L.l.id; });
        var counts = {}; rs.forEach(function (r) { counts[r.why] = (counts[r.why] || 0) + 1; });
        var top = Object.keys(counts).sort(function (x, y) { return counts[y] - counts[x] || cmpId(x, y); })[0];
        L.shortWhy = L.made + L.shipped <= 0 && !rs.length ? 'nothing made yet' : (top ? REASON[top] : 'not enough made in the horizon');
      }
    });
    return { allocs: allocs, rejects: rejects };
  };
  function blendmark(parts) { parts.forEach(function (p) { p.lot.blended = true; }); }
  var REASON = { assay: 'every available lot assays below the order spec', impurity: 'impurity above the order limit',
                 psd: 'particle size outside the order spec', life: 'remaining shelf life below the customer minimum',
                 site: 'no approved site for this customer', qc: 'lots still awaiting QC release', empty: 'stock exhausted' };

  // =====================================================================================================================
  // ASSEMBLE — the one basis
  // =====================================================================================================================
  E.assemble = function (m, hist, st, W, settings) {
    var now = m.asOf, nH = hist.batches.length;
    var batches = st.batches, fwd = batches.filter(function (b) { return b.phase === 'P'; });
    // lots: every released batch becomes a lot (history and plan alike)
    batches.forEach(function (b) {
      if (b._lot) return;
      b._lot = true;
      var p = m.P[b.pix];
      st.lots.push({ id: 'L' + b.id, pix: b.pix, productId: b.productId, kg: b.kg, left: b.kg, assay: b.assay, imp: b.imp,
                     psd: b.psd, madeAt: b.e, readyAt: b.readyAt, retestAt: b.e + Math.round(p.retestM * MONTH),
                     batchId: b.id, siteId: 'UNIT-2', opening: false, released: true, offSpec: b.offSpec });
    });
    /* A lot made by this plan does not exist yet when the what-ifs are applied — it is created here — so the "age a lot"
       what-if is honoured at the point the lot comes into being. */
    (settings.whatifs || []).forEach(function (w) {
      if (w.type !== 'lotAge') return;
      st.lots.forEach(function (x) {
        if (x.id !== w.lotId) return;
        x.retestAt = now + Math.round((+w.monthsLeft || 3) * MONTH);
        x.aged = true;
      });
    });
    var al = E.allocate(m, st, W, now);

    var lines = [];
    st.lineOrder.forEach(function (id) {
      var L = st.lines[id], l = L.l, p = m.P[l.pix];
      var ready = L.lastEnd, status, lateDays = 0;
      var qty = Math.max(0, l.qty - L.cancelled);
      if (L.whatifCancel || (L.cancelled >= l.qty && l.qty > 0)) status = 'Cancelled';
      else if (L.shipped >= qty - 0.5) status = (ready != null && ready <= now) ? 'Shipped' : (ready != null && ready <= l.due ? 'On track' : 'Late');
      else if (L.rem > 0) status = l.due <= m.end ? 'Not in horizon' : 'Beyond horizon';
      else status = 'Short';
      if (status !== 'Cancelled' && status !== 'Beyond horizon') {
        var rd = (L.rem > 0 || L.short > 0) ? m.end : (ready || now);
        if (rd > l.due) lateDays = Math.ceil((rd - l.due) / 1440);
      }
      lines.push({ id: l.id, orderId: l.orderId, productId: l.productId, product: p.name, family: p.family, cls: l.cls,
                   cust: l.cust, custName: l.custName, regulated: l.regulated, qty: l.qty, due: l.due, rel: l.rel, ord: l.ord,
                   priceKg: l.priceKg, marginKg: l.marginKg, tightSpec: l.tightSpec, coa: l.coa, minLifeM: l.minLifeM,
                   assayMin: l.assayMin, impMax: l.impMax, psdMax: l.psdMax, rush: !!l.rush,
                   made: Math.round(L.made), nominal: Math.round(L.nominal), shipped: Math.round(L.shipped),
                   short: Math.round(L.short || 0), shortWhy: L.shortWhy || null, cancelled: L.cancelled,
                   rem: Math.max(0, Math.round(L.rem)), btp: Math.max(0, Math.round(l.qty - L.cancelled - L.shipped)),
                   batches: L.batches.slice(), firstStart: L.firstStart, ready: ready, status: status,
                   lateDays: lateDays, delayCost: lateDays * (l.penalty || 0), penalty: l.penalty });
    });
    var byId = {}; lines.forEach(function (x) { byId[x.id] = x; });

    // ---- KPIs -----------------------------------------------------------------------------------------------------
    var committed = function (x) { return x.cls === 'EXPORT_REG' || x.cls === 'EXPORT' || x.cls === 'DOM_COMMITTED'; };
    var dueIn = lines.filter(function (x) { return committed(x) && x.due >= now && x.due <= m.end && x.status !== 'Cancelled'; });
    var onTime = dueIn.filter(function (x) { return x.status === 'On track' || x.status === 'Shipped'; });
    var kpi = {
      otif: dueIn.length ? onTime.length / dueIn.length : 1, dueIn: dueIn.length, onTime: onTime.length,
      late: lines.filter(function (x) { return x.lateDays > 0 && x.status !== 'Shipped'; }).length,
      // short means a line the plan HAD to serve and could not: due inside the horizon and still uncovered. A line due
      // after the horizon is not short, it is simply not due yet, and counting it makes every figure look worse than it is.
      shortLines: lines.filter(function (x) { return x.short > 0 && x.due <= m.end; }).length,
      shortKg: Math.round(lines.reduce(function (a, x) { return a + (x.due <= m.end ? x.short : 0); }, 0)),
      notDueYetKg: Math.round(lines.reduce(function (a, x) { return a + (x.due > m.end ? x.short : 0); }, 0)),
      delayCost: lines.reduce(function (a, x) { return a + (x.status === 'Shipped' ? 0 : x.delayCost); }, 0),
      shippedKg: Math.round(lines.reduce(function (a, x) { return a + x.shipped; }, 0)),
      contribution: Math.round(lines.reduce(function (a, x) { return a + x.shipped * x.marginKg; }, 0)),
      batches: fwd.length, histBatches: nH,
      madeKg: Math.round(fwd.reduce(function (a, b) { return a + b.actualKg; }, 0)),
      nominalKg: Math.round(fwd.reduce(function (a, b) { return a + b.nominalKg; }, 0)),
      offSpec: fwd.filter(function (b) { return b.offSpec; }).length
    };
    kpi.yieldRealisation = kpi.nominalKg ? kpi.madeKg / kpi.nominalKg : 1;

    // cleaning
    var cl = st.cleans.filter(function (c) { return c.s >= now; });
    kpi.cleanCount = cl.length;
    kpi.cleanHours = Math.round(cl.reduce(function (a, c) { return a + c.min; }, 0) / 60 * 10) / 10;
    kpi.cleanByGrade = {}; cl.forEach(function (c) { kpi.cleanByGrade[c.grade] = (kpi.cleanByGrade[c.grade] || 0) + 1; });

    // unit utilisation (processing time only; cleaning is reported beside it, never inside it)
    var busy = 0, avail = 0;
    m.U.forEach(function (u) { avail += (m.end - now) * u.uptime; });
    fwd.forEach(function (b) { b.ops.forEach(function (o) { busy += Math.max(0, Math.min(o.e, m.end) - Math.max(o.s, now)); }); });
    kpi.util = avail ? busy / avail : 0;
    kpi.busyMin = busy; kpi.availMin = avail;
    /* A plant mean is the wrong number to report and the easiest one to compute. A mill runs an hour a batch and a packing
       line a shift a week; averaging them with the reactors says a plant is idle when the train that matters is full. So
       utilisation is carried per CLASS, with cleaning beside processing rather than inside it, and the busiest class is
       what the headline reports. */
    var cBusy = {}, cClean = {}, cAvail = {};
    m.U.forEach(function (u) { cAvail[u.cls] = (cAvail[u.cls] || 0) + (m.end - now) * u.uptime; });
    fwd.forEach(function (b) {
      b.ops.forEach(function (o) {
        cBusy[o.cls] = (cBusy[o.cls] || 0) + Math.max(0, Math.min(o.e, m.end) - Math.max(o.s, now));
      });
    });
    cl.forEach(function (c) {
      var u = m.U[c.uix]; if (!u) return;
      cClean[u.cls] = (cClean[u.cls] || 0) + Math.max(0, Math.min(c.e, m.end) - Math.max(c.s, now));
    });
    kpi.utilByClass = {}; kpi.utilClass = null;
    Object.keys(cAvail).forEach(function (c) {
      var av = cAvail[c] || 1, r = (cBusy[c] || 0) / av, k = (cClean[c] || 0) / av;
      kpi.utilByClass[c] = { run: r, clean: k, busy: r + k, hours: Math.round((cBusy[c] || 0) / 60) };
      if (!kpi.utilClass || r + k > kpi.utilByClass[kpi.utilClass].busy) kpi.utilClass = c;
    });
    kpi.utilBusiest = kpi.utilClass ? kpi.utilByClass[kpi.utilClass].busy : 0;
    /* A campaign is consecutive BATCHES of one product on the unit that starts the route. Counting every operation instead
       makes a three-stage batch look like three campaigns and drives the average below one. */
    var cmp = 0, cByU = {};
    fwd.forEach(function (b) { var o = b.ops[0]; (cByU[o.unit] = cByU[o.unit] || []).push({ s: o.s, pix: b.pix }); });
    Object.keys(cByU).forEach(function (u) {
      var seq = cByU[u].sort(function (x, y) { return x.s - y.s; }), lastP = -1;
      seq.forEach(function (x) { if (x.pix !== lastP) cmp++; lastP = x.pix; });
    });
    kpi.campaigns = cmp;
    kpi.batchesPerCampaign = Math.round(kpi.batches / Math.max(1, cmp) * 100) / 100;
    kpi.pulledForCampaign = (st.pulls || []).filter(function (x) { return x.at >= now; }).length;

    /* Utilities and waste: peak, and the hours or days at the cap.

       The frozen history was planned the generic way and some of its work is still running at the as-of moment. Those
       hours can be over the cap before this plan places anything, and no plan can undo them — the constraint on a plan is
       that it may not ADD to an hour the history has already overrun. The proof applies exactly that rule, so the figures
       reported here must apply it too: a peak that quietly includes an inherited overrun reads as a plan breaking its own
       cap. What is inherited is reported separately, in its own words, rather than averaged into the plan's number. */
    var inhU = new Float64Array(m.utils.length * m.H), inhW = new Float64Array(m.wastes.length * m.Dn);
    (hist && hist.batches ? hist.batches : []).forEach(function (b) {
      b.ops.forEach(function (o) {
        addDuty(m, inhU, m.P[b.pix].ops[o.seq - 1], o.s, o.e);
        if (o.wix != null && o.efflM3) inhW[o.wix * m.Dn + Math.floor(o.s / 1440)] += o.efflM3;
      });
    });
    kpi.utilPeak = {}; kpi.utilAtCap = {}; kpi.utilInherited = {}; kpi.utilInhHours = {};
    var h0 = Math.floor(now / 60), h1 = Math.min(m.H, Math.ceil(m.end / 60));
    m.utils.forEach(function (u) {
      var pk = 0, at = 0, ipk = 0, ih = 0;
      for (var h = h0; h < h1; h++) {
        var v = st.util[u.ix * m.H + h], cap = m.utilCap[u.ix * m.H + h], iv = inhU[u.ix * m.H + h];
        if (cap && iv > cap + 1e-6) { ih++; if (v > ipk) ipk = v; continue; }   // already overrun before this plan existed
        if (v > pk) pk = v;
        if (cap && v >= cap - 1e-6) at++;   // binary floating point: a sum that is exactly the cap in decimal can land a hair below it
      }
      kpi.utilPeak[u.id] = Math.round(pk * 10) / 10; kpi.utilAtCap[u.id] = at;
      kpi.utilInherited[u.id] = Math.round(ipk * 10) / 10; kpi.utilInhHours[u.id] = ih;
    });
    kpi.wasteAtCap = {}; kpi.wasteTotal = {}; kpi.wastePeak = {}; kpi.wasteInherited = {}; kpi.wasteInhDays = {};
    var d0 = Math.floor(now / 1440), d1 = Math.min(m.Dn, Math.ceil(m.end / 1440));
    m.wastes.forEach(function (w) {
      var tot = 0, at = 0, pk = 0, ipk = 0, id = 0;
      for (var d = d0; d < d1; d++) {
        var v = st.waste[w.ix * m.Dn + d];
        tot += v;
        if (inhW[w.ix * m.Dn + d] > w.cap + 1e-6) { id++; if (v > ipk) ipk = v; continue; }
        if (v > pk) pk = v;
        if (v >= w.cap - 1e-6) at++;
      }
      kpi.wasteTotal[w.id] = Math.round(tot * 10) / 10; kpi.wasteAtCap[w.id] = at; kpi.wastePeak[w.id] = Math.round(pk * 10) / 10;
      kpi.wasteInherited[w.id] = Math.round(ipk * 10) / 10; kpi.wasteInhDays[w.id] = id;
    });
    // licence: the least headroom any class has over the horizon
    kpi.licenceMin = {}; kpi.refused = st.refused.filter(function (r) { return r.at >= now; }).length;
    kpi.licencePeak = {};
    m.hazs.forEach(function (hz) {
      var worst = 1, pk = 0;
      for (var d = d0; d < d1; d++) { var v = E.hazPos(m, st, hz.ix, d); if (v > pk) pk = v; worst = Math.min(worst, 1 - v / hz.licensedKL); }
      kpi.licenceMin[hz.id] = Math.round(worst * 1000) / 1000; kpi.licencePeak[hz.id] = Math.round(pk * 10) / 10;
    });
    // allocation
    kpi.allocs = al.allocs.length;
    kpi.blended = al.allocs.filter(function (a) { return a.blended; }).length;
    kpi.lots = st.lots.filter(function (x) { return !x.opening; }).length;
    kpi.sacrificeMin = st.sacrifices.reduce(function (a, s) { return a + s.min; }, 0);
    kpi.sacrifices = st.sacrifices.length;
    // what an hour of the binding resource is worth, from this mix (used to price every consequence)
    kpi.hourValue = hourValue(m);
    kpi.net = kpi.contribution - kpi.delayCost;

    return { m: m, W: W, settings: settings, rulesId: W.id, lines: lines, byId: byId, batches: batches, fwd: fwd,
             nHist: nH, cleans: st.cleans, sacrifices: st.sacrifices, refused: st.refused, lots: st.lots,
             allocs: al.allocs, rejects: al.rejects, kpi: kpi, state: st, hist: hist };
  };

  function hourValue(m) {
    var bn = m.DATA.meta.bottleneck, vals = [];
    m.P.forEach(function (p) {
      var h = p.ops.reduce(function (a, o) { return a + (o.cls === bn ? o.hours : 0); }, 0);
      if (h > 0) vals.push(p.marginKg * p.batchKg / h);
    });
    vals.sort(function (a, b) { return a - b; });
    return vals.length ? Math.round(vals[Math.floor(vals.length / 2)]) : 20000;
  }

  // =====================================================================================================================
  // CONSEQUENCE — replay the generic plan and price what its assumptions cost. It NEVER re-schedules.
  // =====================================================================================================================
  var PRIORITY = ['CLEAN_FORBIDDEN', 'HOLD', 'UTIL', 'WASTE', 'YIELD', 'LICENCE', 'ALLOC', 'CLEAN_SHORT'];
  var NUANCE = { CLEAN_FORBIDDEN: 'P1', CLEAN_SHORT: 'P1', YIELD: 'P2', HOLD: 'P3', UTIL: 'P4', WASTE: 'P5', LICENCE: 'P6', ALLOC: 'P7' };

  E.consequence = function (m, plan, aware) {
    var st = plan.state, now = m.asOf, hv = plan.kpi.hourValue, ev = [], nP = m.P.length;
    var fwd = plan.fwd.slice().sort(function (a, b) { return a.s - b.s || cmpId(a.id, b.id); });
    var byBatch = {};
    function add(code, b, o, cause, outcome, cost, extra) {
      var row = { code: code, nuance: NUANCE[code], batch: b ? b.id : null, productId: b ? b.productId : null,
                  unit: o ? o.unit : null, at: o ? o.s : (b ? b.s : now), cause: cause, outcome: outcome,
                  cost: cost, lines: b ? b.lineIds.slice() : [], statusChanging: false };
      if (extra) Object.assign(row, extra);
      ev.push(row);
      if (b) (byBatch[b.id] = byBatch[b.id] || []).push(row);
      return row;
    }

    // ---- P1 cleaning: what the matrix required against the flat changeover the plan booked --------------------------
    var byUnit = {};
    fwd.forEach(function (b) { b.ops.forEach(function (o) { (byUnit[o.unit] = byUnit[o.unit] || []).push({ b: b, o: o }); }); });
    Object.keys(byUnit).sort().forEach(function (uid) {
      var seq = byUnit[uid].sort(function (x, y) { return x.o.s - y.o.s; });
      for (var i = 1; i < seq.length; i++) {
        var prev = seq[i - 1], cur = seq[i];
        if (prev.b.pix === cur.b.pix) continue;
        var k = prev.b.pix * nP + cur.b.pix, need = m.cleanMin[k], grade = m.cleanGrade[k], got = cur.o.clean;
        if (grade === 'FORBIDDEN') {
          add('CLEAN_FORBIDDEN', cur.b, cur.o, m.P[prev.b.pix].id + ' ran on ' + uid + ' immediately before ' + cur.b.productId +
              ' — ' + m.cleanWhy[k], 'the batch is rejected at QC and the train is taken down for a full boil-out and swab test',
              cost(m, cur.b, { kg: cur.b.actualKg, hours: batchHours(cur.b) + 16, rupees: cur.b.actualKg * m.P[cur.b.pix].costKg + 16 * hv }),
              { frm: m.P[prev.b.pix].id, to: cur.b.productId, grade: grade, needMin: 0, gotMin: got, why: m.cleanWhy[k] });
        } else if (need > got + 1e-9) {
          add('CLEAN_SHORT', cur.b, cur.o, 'the matrix needs a ' + grade.toLowerCase() + ' (' + Math.round(need / 60) +
              ' h) between ' + m.P[prev.b.pix].id + ' and ' + cur.b.productId + '; the plan booked ' + Math.round(got / 60) + ' h',
              'carry-over risk: the batch needs a re-test, and ' + Math.round((need - got) / 60) + ' h of cleaning is still owed',
              cost(m, cur.b, { hours: (need - got) / 60, rupees: (need - got) / 60 * hv }),
              { frm: m.P[prev.b.pix].id, to: cur.b.productId, grade: grade, needMin: need, gotMin: got, why: m.cleanWhy[k] });
        }
      }
    });

    // ---- P3 hold windows: the lag on every link of every batch ----------------------------------------------------
    fwd.forEach(function (b) {
      var p = m.P[b.pix];
      for (var i = 1; i < b.ops.length; i++) {
        var lag = b.ops[i].s - b.ops[i - 1].e, mx = p.ops[i].maxLag;
        if (lag <= mx) continue;
        // How far past the window decides the outcome. A modest overrun degrades the intermediate and costs yield and a
        // re-test; a gross one means the stage is re-worked. Pricing every overrun as a write-off would not be credible.
        var over = lag / mx, gross = over > 2;
        var lossKg = Math.round(b.actualKg * Math.min(0.55, 0.11 * over));
        add('HOLD', b, b.ops[i], p.ops[i - 1].label + ' finished ' + hrs(lag) + ' before ' + p.ops[i].label.toLowerCase() +
            ' started; the hold window on that link is ' + p.ops[i].maxLagH + ' h (' + over.toFixed(1) + '× over)',
            gross ? 'the intermediate is past rescue: the stage is re-worked from ' + p.ops[i - 1].label.toLowerCase()
                  : 'the intermediate degrades: ' + lossKg + ' kg of yield is lost and the batch needs a re-test before release',
            cost(m, b, { kg: gross ? b.actualKg : lossKg,
                         hours: gross ? batchHours(b) * 0.6 : 3,
                         rupees: gross ? b.actualKg * p.costKg * 0.6 + batchHours(b) * 0.6 * hv : lossKg * p.costKg + 3 * hv }),
            { lagH: Math.round(lag / 60), maxLagH: p.ops[i].maxLagH, over: Math.round(over * 10) / 10, gross: gross,
              link: p.ops[i - 1].label + ' → ' + p.ops[i].label });
      }
    });

    // ---- P4 utilities: rebuild the duty curve from this plan and find the hours over the cap -----------------------
    var U2 = new Float64Array(m.utils.length * m.H);
    fwd.forEach(function (b) { b.ops.forEach(function (o) { addDuty(m, U2, m.P[b.pix].ops[o.seq - 1], o.s, o.e); }); });
    var h0 = Math.floor(now / 60), h1 = Math.min(m.H, Math.ceil(m.end / 60));
    m.utils.forEach(function (u) {
      var runs = [];
      for (var h = h0; h < h1; h++) {
        var v = U2[u.ix * m.H + h], cap = m.utilCap[u.ix * m.H + h];
        if (cap && v > cap + 1e-9) runs.push([h, v, cap]);
      }
      // group consecutive hours into one event, charged to the batch admitted last into that window
      var i = 0;
      while (i < runs.length) {
        var j = i; while (j + 1 < runs.length && runs[j + 1][0] === runs[j][0] + 1) j++;
        var hA = runs[i][0], hB = runs[j][0] + 1, peak = 0, cap2 = runs[i][2];
        for (var q = i; q <= j; q++) peak = Math.max(peak, runs[q][1]);
        var victim = lastAdmitted(m, fwd, u, hA * 60, hB * 60);
        if (victim) {
          add('UTIL', victim.b, victim.o, Math.round(peak * 10) / 10 + ' ' + u.unit + ' of ' + u.name.toLowerCase() +
              ' demanded against ' + cap2 + ' available, for ' + (hB - hA) + ' h from hour ' + hA,
              'the last batch admitted loses temperature control and is quenched; ' + u.name + ' trips',
              cost(m, victim.b, { kg: victim.b.actualKg, hours: (hB - hA), rupees: victim.b.actualKg * m.P[victim.b.pix].costKg * 0.5 + (hB - hA) * hv }),
              { utility: u.id, peak: Math.round(peak * 10) / 10, cap: cap2, hours: hB - hA });
        }
        i = j + 1;
      }
    });

    // ---- P5 effluent: rebuild the daily load and find the days over the consent --------------------------------
    var W2 = new Float64Array(m.wastes.length * m.Dn), R2 = new Float64Array(m.Dn);
    fwd.forEach(function (b) { b.ops.forEach(function (o) { if (o.wix != null && o.efflM3) W2[o.wix * m.Dn + Math.floor(o.s / 1440)] += o.efflM3; if (o.solvKL) R2[Math.floor(o.s / 1440)] += o.solvKL; }); });
    var d0 = Math.floor(now / 1440), d1 = Math.min(m.Dn, Math.ceil(m.end / 1440));
    m.wastes.forEach(function (w) {
      for (var d = d0; d < d1; d++) {
        var v = W2[w.ix * m.Dn + d];
        if (v <= w.cap + 1e-9) continue;
        var victim = lastAdmitted(m, fwd, null, d * 1440, (d + 1) * 1440, w.ix);
        if (!victim) continue;
        add('WASTE', victim.b, victim.o, Math.round(v * 10) / 10 + ' ' + w.unit.replace('/day', '') + ' of ' + w.name.toLowerCase() +
            ' load against a consented ' + w.cap + ' on day ' + (d - d0 + 1),
            'the treatment plant cannot absorb it: the batch is held in the reactor until the next day',
            cost(m, victim.b, { hours: 24, rupees: 24 * hv * 0.5 + (victim.b.lineIds.length ? penaltyOf(m, plan, victim.b) : 0) }),
            { waste: w.id, load: Math.round(v * 10) / 10, cap: w.cap, day: d });
      }
    });
    for (var d = d0; d < d1; d++) {
      if (R2[d] <= m.recovery.cap + 1e-9) continue;
      var v2 = R2[d], victim2 = lastAdmitted(m, fwd, null, d * 1440, (d + 1) * 1440, null, true);
      if (!victim2) continue;
      add('WASTE', victim2.b, victim2.o, Math.round(v2 * 10) / 10 + ' kL of spent solvent against ' + m.recovery.cap + ' kL/day of recovery',
          'the surplus goes to incineration instead of back to the tank farm, and fresh solvent is bought in',
          cost(m, victim2.b, { rupees: (v2 - m.recovery.cap) * 120000 }),
          { waste: 'RECOVERY', load: Math.round(v2 * 10) / 10, cap: m.recovery.cap, day: d });
    }

    // ---- P2 yield: the plan booked nameplate; the batches assayed otherwise -----------------------------------
    var byLine = {};
    fwd.forEach(function (b) { b.lineIds.forEach(function (id) { (byLine[id] = byLine[id] || []).push(b); }); });
    /* The generic plan books the THEORETICAL output of every charge; the plant gives it mean yield. Per order line that
       mostly hides — one batch booked at nameplate still covers a line that wanted less than a batch — but per product,
       over a campaign, the books say more than the warehouse holds, and covering the difference takes whole extra
       batches that each pay a clean in and a clean out. */
    var byProd = {};
    fwd.forEach(function (b) {
      var g = byProd[b.productId] = byProd[b.productId] || { booked: 0, act: 0, n: 0, last: null, lines: {} };
      g.booked += b.booked; g.act += b.actualKg; g.n++; g.last = b;
      b.lineIds.forEach(function (id) { g.lines[id] = (g.lines[id] || 0) + b.actualKg; });
    });
    Object.keys(byProd).sort().forEach(function (pid) {
      var g = byProd[pid], p = m.P[m.pix[pid]], gap = g.booked - g.act;
      if (gap < p.batchKg * 0.5) return;                 // under half a batch: inside the noise of a single campaign
      var extra = Math.ceil(gap / p.batchKg);
      var reclean = awayClean(m, plan, g.last, p);
      // the line carrying most of this product's output, so the row points somewhere a planner can look
      var top = Object.keys(g.lines).sort(function (a, b) { return g.lines[b] - g.lines[a]; })[0];
      var L = top ? plan.byId[top] : null;
      add('YIELD', g.last, g.last.ops[0],
          g.n + ' batch' + (g.n > 1 ? 'es' : '') + ' of ' + pid + ' were booked at nameplate as ' + Math.round(g.booked) +
          ' kg; they assayed out at ' + Math.round(g.act) + ' kg (' + pctOf(g.act / g.booked) + ' of nominal)',
          extra + ' further batch' + (extra > 1 ? 'es' : '') + ' is needed to cover the difference, and by then the campaign has been ' +
          'broken down — so each one pays a clean in and a clean out',
          cost(m, g.last, { kg: gap, hours: extra * p.cycleH + extra * reclean,
                            rupees: (extra * p.cycleH + extra * reclean) * hv + (L ? (L.penalty || 0) * 3 : 0) }),
          { productId: pid, lineId: top || null, bookedKg: Math.round(g.booked), actualKg: Math.round(g.act),
            batches: g.n, extraBatches: extra, shortKg: Math.round(gap), recleanH: reclean });
    });

    // ---- P6 licence: replay the tank farm under this plan's refusal rule ---------------------------------------
    m.hazs.forEach(function (hz) {
      for (var d = d0; d < d1; d++) {
        var pos = E.hazPos(m, st, hz.ix, d);
        if (pos <= hz.licensedKL + 1e-9) continue;
        add('LICENCE', null, null, Math.round(pos * 10) / 10 + ' kL of ' + hz.name.toLowerCase() + ' held against a licensed ' +
            hz.licensedKL + ' kL on day ' + (d - d0 + 1),
            'the site is outside its licence: the next tanker is refused at the gate and the campaign that needed it waits',
            { kg: 0, hours: 24, rupees: 24 * hv * 0.35, lines: 0 },
            { haz: hz.id, pos: Math.round(pos * 10) / 10, licensed: hz.licensedKL, day: d });
        break;         // one event per class: the first day it goes over is the one that matters
      }
    });

    // ---- P7 allocation: re-run allocation under the aware rules over the SAME lots ------------------------------
    var st2 = E.cloneState(m, st);
    st2.lots.forEach(function (x) { x.left = x.kg; });
    st2.lineOrder.forEach(function (id) { st2.lines[id].shipped = 0; st2.lines[id].short = 0; });
    var al2 = E.allocate(m, st2, Object.assign({}, plan.W, { rAlloc: 'spec' }), now);
    var spec = {}; al2.allocs.forEach(function (a) { spec[a.lineId] = a; });
    plan.allocs.forEach(function (a) {
      var L = plan.byId[a.lineId]; if (!L) return;
      var bad = [];
      a.lots.forEach(function (lt) {
        if (L.assayMin && lt.assay < L.assayMin) bad.push(lt.id + ' assays ' + lt.assay + '% against a ' + L.assayMin + '% minimum');
        else if (L.impMax && lt.imp > L.impMax) bad.push(lt.id + ' carries ' + lt.imp + '% impurity against a ' + L.impMax + '% limit');
        else if (L.psdMax && lt.psd > L.psdMax) bad.push(lt.id + ' has a d90 of ' + lt.psd + ' um against a ' + L.psdMax + ' um limit');
      });
      if (!bad.length) return;
      add('ALLOC', null, null, 'lot' + (bad.length > 1 ? 's' : '') + ' allocated to ' + a.lineId + ' on quantity and date alone: ' + bad.join('; '),
          'the customer rejects the consignment on the certificate of analysis and the line ships short',
          { kg: a.kg, hours: 0, rupees: a.kg * L.marginKg + (L.penalty || 0) * 7, lines: 1 },
          { lineId: a.lineId, lots: a.lots.map(function (x) { return x.id; }), cust: L.custName });
    });

    // ---- first order only: one status-changing consequence per batch, the rest priced but not propagated --------
    var changing = 0, unmodelled = 0;
    Object.keys(byBatch).forEach(function (bid) {
      var rows = byBatch[bid].slice().sort(function (a, b) { return PRIORITY.indexOf(a.code) - PRIORITY.indexOf(b.code); });
      rows.forEach(function (r, i) {
        var isStatus = PRIORITY.indexOf(r.code) <= PRIORITY.indexOf('LICENCE') && !(r.code === 'HOLD' && !r.gross);
        if (i === 0 && isStatus) { r.statusChanging = true; changing++; }
        else if (isStatus) { r.costOnly = true; unmodelled++; }
      });
    });
    // what the aware plan did instead, joined on (nuance, unit, product)
    if (aware) {
      var fix = {};
      (aware.sacrifices || []).forEach(function (s) { fix[s.nuance + '|' + s.unit + '|' + s.productId] = s.text; fix[s.nuance + '|*|' + s.productId] = s.text; });
      ev.forEach(function (r) { r.fix = fix[r.nuance + '|' + r.unit + '|' + r.productId] || fix[r.nuance + '|*|' + r.productId] || awareFix(m, aware, r); });
    }
    ev.sort(function (a, b) { return PRIORITY.indexOf(a.code) - PRIORITY.indexOf(b.code) || a.at - b.at; });

    var byCode = {};
    ev.forEach(function (r) {
      var c = byCode[r.code] = byCode[r.code] || { code: r.code, nuance: r.nuance, n: 0, kg: 0, hours: 0, rupees: 0, lines: 0 };
      c.n++; c.kg += r.cost.kg || 0; c.hours += r.cost.hours || 0; c.rupees += r.cost.rupees || 0; c.lines += r.cost.lines || 0;
    });
    var byNuance = {};
    Object.keys(byCode).forEach(function (k) {
      var c = byCode[k], n = byNuance[c.nuance] = byNuance[c.nuance] || { nuance: c.nuance, n: 0, kg: 0, hours: 0, rupees: 0, lines: 0 };
      n.n += c.n; n.kg += c.kg; n.hours += c.hours; n.rupees += c.rupees; n.lines += c.lines;
    });
    var total = { n: ev.length, kg: 0, hours: 0, rupees: 0, lines: 0 };
    ev.forEach(function (r) { total.kg += r.cost.kg || 0; total.hours += r.cost.hours || 0; total.rupees += r.cost.rupees || 0; total.lines += r.cost.lines || 0; });
    return { events: ev, byCode: byCode, byNuance: byNuance, total: total, statusChanging: changing, unmodelled: unmodelled };
  };

  function awareFix(m, aware, r) {
    if (r.code === 'YIELD') return 'the aware plan sized this campaign one standard deviation below mean yield and topped it up inside the campaign, with no second clean';
    if (r.code === 'CLEAN_SHORT' || r.code === 'CLEAN_FORBIDDEN') return 'the aware plan read the matrix and sequenced the pair differently, or paid the clean up front';
    if (r.code === 'UTIL') return 'the aware plan staggered the exotherms so the peak stayed inside the cap';
    if (r.code === 'WASTE') return 'the aware plan interleaved a light-effluent batch so the day stayed inside the consent';
    if (r.code === 'LICENCE') return 'the aware plan retimed the delivery so the licensed quantity was never exceeded';
    if (r.code === 'HOLD') return 'the aware plan left the unit idle rather than start a stage whose next step could not follow in time';
    if (r.code === 'ALLOC') return 'the aware plan matched the lot on assay, impurity, particle size, approved route and remaining life, blending where one lot would not do';
    return null;
  }
  // what a top-up batch pays in cleaning: whatever ran on that unit after the campaign closed has to be cleaned away,
  // and then cleaned off again. Read off the matrix, not assumed.
  function awayClean(m, plan, b, p) {
    var u = b.ops[0].uix, after = null;
    plan.fwd.forEach(function (x) { x.ops.forEach(function (o) { if (o.uix === u && o.s > b.ops[0].e && x.pix !== p.ix && (!after || o.s < after.s)) after = { s: o.s, pix: x.pix }; }); });
    if (!after) return 0;
    var inH = Math.max(0, m.cleanMin[after.pix * m.P.length + p.ix]) / 60;
    var outH = Math.max(0, m.cleanMin[p.ix * m.P.length + after.pix]) / 60;
    return Math.round((inH + outH) * 10) / 10;
  }
  function cost(m, b, c) { return { kg: Math.round(c.kg || 0), hours: Math.round((c.hours || 0) * 10) / 10, rupees: Math.round(c.rupees || 0), lines: c.lines != null ? c.lines : (b && b.lineIds.length ? 1 : 0) }; }
  function batchHours(b) { return b.ops.reduce(function (a, o) { return a + (o.e - o.s) / 60; }, 0); }
  function penaltyOf(m, plan, b) { var L = plan.byId[b.lineIds[0]]; return L ? (L.penalty || 0) : 0; }
  function hrs(min) { return Math.round(min / 60) + ' h'; }
  function pctOf(x) { return (x * 100).toFixed(1) + '%'; }
  // the same per-hour bucketing the scheduler admits against: the MAX across segments of one operation, never the sum
  function addDuty(m, arr, op, s, e) {
    if (!op) return;
    var dur = e - s, t = s, out = {};
    for (var g = 0; g < op.duty.length; g++) {
      var seg = op.duty[g], segEnd = g === op.duty.length - 1 ? e : t + dur * seg.frac;
      for (var k in seg.draw) {
        var ui = m.utix[k]; if (ui == null) continue;
        var o = out[ui] || (out[ui] = {});
        for (var h = Math.floor(t / 60); h < Math.ceil(segEnd / 60); h++) {
          if (h < 0 || h >= m.H) continue;
          if (!(o[h] >= seg.draw[k])) o[h] = seg.draw[k];
        }
      }
      t = segEnd;
    }
    for (var u2 in out) for (var h2 in out[u2]) arr[u2 * m.H + (+h2)] += out[u2][h2];
  }
  // the batch admitted LAST into a window — the one a real plant would have to quench or hold
  function lastAdmitted(m, fwd, u, s, e, wix, solvent) {
    var best = null;
    fwd.forEach(function (b) {
      b.ops.forEach(function (o) {
        if (o.e <= s || o.s >= e) return;
        if (wix != null && o.wix !== wix) return;
        if (solvent && !o.solvKL) return;
        if (u) {
          var op = m.P[b.pix].ops[o.seq - 1], draws = false;
          op.duty.forEach(function (sg) { if (sg.draw[u.id]) draws = true; });
          if (!draws) return;
        }
        if (!best || o.s > best.o.s || (o.s === best.o.s && b.id > best.b.id)) best = { b: b, o: o };
      });
    });
    return best;
  }

  // =====================================================================================================================
  // REPAIR — one firefighting sweep. Replacement batches are placed under the GENERIC rules again: firefighting does not
  // learn. Nothing is re-optimised; the rest of the plan stays exactly where it was.
  // =====================================================================================================================
  E.repair = function (m, plan, cons) {
    var st = E.cloneState(m, plan.state), W = plan.W, ctx = E.context(m), out = [];
    var need = cons.events.filter(function (r) { return r.statusChanging && r.batch; });
    need.sort(function (a, b) { return a.at - b.at || cmpId(a.batch, b.batch); });
    need.forEach(function (r) {
      var p = m.P[m.pix[r.productId]]; if (!p) return;
      var from = Math.max(r.at, m.asOf), ui = null, res = null;
      for (var g = 0; g < 48 && !res; g++) {
        var t = from + g * 240;
        if (t > m.end) break;
        for (var j = 0; j < p.ops[0].units.length && !res; j++) {
          var cand = p.ops[0].units[j], start = Math.max(t, st.free[cand]);
          var rr = E.planChain(m, st, p, start, W, cand);
          if (rr.ok) { res = rr; ui = cand; }
        }
      }
      if (!res) { out.push({ event: r.code, productId: p.id, placed: false, why: 'no slot left inside the horizon' }); return; }
      var nth = st.runs[p.ix];
      var b = commitRepair(m, st, p, res, W, r);
      out.push({ event: r.code, nuance: r.nuance, productId: p.id, placed: true, batch: b.id, unit: m.U[ui].id,
                 s: b.s, e: b.e, origBatch: r.batch, lateBy: Math.round((b.e - r.at) / 1440 * 10) / 10,
                 why: 'replacement for ' + r.batch + ', placed at the next free slot under the same generic rules' });
    });
    return { state: st, repairs: out, placed: out.filter(function (x) { return x.placed; }).length,
             unplaced: out.filter(function (x) { return !x.placed; }).length };
  };
  function commitRepair(m, st, p, r, W, cause) {
    var nth = st.runs[p.ix]++, ph = E.physics(m, p, nth);
    var b = { id: p.id + '-R' + String(1000 + nth).slice(1), pix: p.ix, productId: p.id, nth: nth, phase: 'R', s: r.s, e: r.e,
              ops: [], kg: ph.kg, actualKg: ph.kg, nominalKg: p.batchKg, assay: ph.assay, imp: ph.imp, psd: ph.psd,
              y: ph.y, offSpec: ph.offSpec, qcMin: ph.qcMin, lineIds: [], repair: true, cause: cause.code };
    r.place.forEach(function (pl) {
      b.ops.push({ seq: pl.op.seq, opId: pl.op.id, label: pl.op.label, cls: pl.op.cls, uix: pl.ui, unit: m.U[pl.ui].id,
                   s: pl.s, e: pl.e, clean: pl.clean, efflM3: pl.op.efflM3, wix: pl.op.wix, solvKL: pl.op.solvKL });
      st.free[pl.ui] = pl.e; st.last[pl.ui] = p.ix; st.lastEnd[pl.ui] = pl.e;
    });
    b.readyAt = b.e + b.qcMin;
    st.batches.push(b);
    return b;
  }

  // =====================================================================================================================
  // PROOF — re-check every constraint over a committed plan. Reports CHECKS and VIOLATIONS, per nuance.
  // =====================================================================================================================
  E.proof = function (m, plan) {
    var st = plan.state, fwd = plan.fwd, nP = m.P.length, out = {}, now = m.asOf;
    // what the frozen history left behind, still running at the as-of moment
    var inhU = new Float64Array(m.utils.length * m.H), inhW = new Float64Array(m.wastes.length * m.Dn);
    plan.hist.batches.forEach(function (b) {
      b.ops.forEach(function (o) {
        addDuty(m, inhU, m.P[b.pix].ops[o.seq - 1], o.s, o.e);
        if (o.wix != null && o.efflM3) inhW[o.wix * m.Dn + Math.floor(o.s / 1440)] += o.efflM3;
      });
    });
    function R(nu, label) { return out[nu] = out[nu] || { nuance: nu, label: label, checks: 0, violations: 0, detail: [] }; }
    var inherited = [];
    function chkInherit(u, h, inh, cap) { if (inherited.length < 40) inherited.push({ utility: u.id, hour: h, inherited: Math.round(inh * 10) / 10, cap: cap }); }
    function chk(nu, label, ok, text) { var r = R(nu, label); r.checks++; if (!ok) { r.violations++; if (r.detail.length < 12) r.detail.push(text); } }

    // P1 cleaning: every adjacent pair on every unit
    var byUnit = {};
    fwd.forEach(function (b) { b.ops.forEach(function (o) { (byUnit[o.unit] = byUnit[o.unit] || []).push({ b: b, o: o }); }); });
    // cleaning performed in a gap counts whether it was attached to the batch or scheduled ahead of it as its own job
    var aheadBy = {};
    plan.cleans.forEach(function (c) { if (c.ahead) (aheadBy[c.unit] = aheadBy[c.unit] || []).push(c); });
    Object.keys(byUnit).sort().forEach(function (uid) {
      var seq = byUnit[uid].sort(function (x, y) { return x.o.s - y.o.s; }), ah = aheadBy[uid] || [];
      for (var i = 1; i < seq.length; i++) {
        var a = seq[i - 1], c = seq[i];
        chk('P1', 'cleaning between consecutive products', a.b.pix === c.b.pix || m.cleanGrade[a.b.pix * nP + c.b.pix] !== 'FORBIDDEN',
            uid + ': ' + a.b.productId + ' → ' + c.b.productId + ' is a forbidden pair');
        if (a.b.pix !== c.b.pix) {
          var done = c.o.clean;
          for (var z = 0; z < ah.length; z++) if (ah[z].s >= a.o.e - 1e-6 && ah[z].e <= c.o.s + 1e-6) done += ah[z].min;
          chk('P1', 'cleaning between consecutive products', done + 1e-6 >= m.cleanMin[a.b.pix * nP + c.b.pix],
              uid + ': ' + a.b.productId + ' → ' + c.b.productId + ' needs ' + Math.round(m.cleanMin[a.b.pix * nP + c.b.pix] / 60) + ' h, performed ' + Math.round(done / 60) + ' h');
        }
        chk('P1', 'equipment never double-booked', c.o.s + 1e-6 >= a.o.e, uid + ': ' + a.b.id + ' and ' + c.b.id + ' overlap');
      }
    });
    // P3 hold windows + min lag, and eligibility and block times while we are walking the batches
    fwd.forEach(function (b) {
      var p = m.P[b.pix];
      b.ops.forEach(function (o, i) {
        chk('base', 'operation on an eligible unit', p.ops[i].units.indexOf(o.uix) >= 0, b.id + ' ' + o.label + ' on ' + o.unit);
        var bl = m.blocks[o.uix] || [], hit = bl.filter(function (x) { return o.s < x[1] && o.e > x[0]; })[0];
        chk('base', 'no operation runs through a block time', !hit, b.id + ' ' + o.label + ' runs through ' + (hit ? hit[2] : ''));
        if (i === 0) return;
        var lag = o.s - b.ops[i - 1].e;
        chk('P3', 'hold window on every link', lag <= p.ops[i].maxLag + 1e-6,
            b.id + ': ' + hrs(lag) + ' between ' + p.ops[i - 1].label + ' and ' + p.ops[i].label + ' (window ' + p.ops[i].maxLagH + ' h)');
        chk('P3', 'minimum lag on every link', lag + 1e-6 >= p.ops[i].minLag, b.id + ': ' + hrs(lag) + ' is under the ' + p.ops[i].minLagH + ' h minimum lag');
      });
    });
    // P4 utilities, every hour
    var h0 = Math.floor(now / 60), h1 = Math.min(m.H, Math.ceil(m.end / 60));
    m.utils.forEach(function (u) {
      for (var h = h0; h < h1; h++) {
        var cap = m.utilCap[u.ix * m.H + h], v = st.util[u.ix * m.H + h], inh = inhU[u.ix * m.H + h];
        var ok = !cap || v <= cap + 1e-6 || v <= inh + 1e-6;
        if (!ok) chkInherit(u, h, inh, cap);
        chk('P4', 'utility duty inside the cap, every hour', ok,
            u.id + ' hour ' + h + ': ' + Math.round(v * 10) / 10 + ' against ' + cap +
            (inh > cap ? ' (' + Math.round(inh * 10) / 10 + ' inherited from the frozen history)' : ''));
      }
    });
    // P5 waste, every day
    var d0 = Math.floor(now / 1440), d1 = Math.min(m.Dn, Math.ceil(m.end / 1440));
    m.wastes.forEach(function (w) {
      for (var d = d0; d < d1; d++) {
        var v = st.waste[w.ix * m.Dn + d], inh = inhW[w.ix * m.Dn + d];
        chk('P5', 'waste load inside the daily consent', v <= w.cap + 1e-6 || v <= inh + 1e-6,
            w.id + ' day ' + d + ': ' + Math.round(v * 10) / 10 + ' against ' + w.cap +
            (inh > w.cap ? ' (' + Math.round(inh * 10) / 10 + ' inherited from the frozen history)' : ''));
      }
    });
    // P6 licence and segregation
    m.hazs.forEach(function (hz) {
      for (var d = d0; d < d1; d++) chk('P6', 'licensed quantity never exceeded', E.hazPos(m, st, hz.ix, d) <= hz.licensedKL + 1e-6,
          hz.id + ' day ' + d + ': ' + Math.round(E.hazPos(m, st, hz.ix, d) * 10) / 10 + ' kL against ' + hz.licensedKL);
    });
    m.bunds.forEach(function (b) {
      m.segregation.forEach(function (sg) {
        chk('P6', 'segregated classes never share a bund', !(b.classes.indexOf(sg[0]) >= 0 && b.classes.indexOf(sg[1]) >= 0),
            b.id + ' holds both ' + sg[0] + ' and ' + sg[1]);
      });
    });
    // P7 allocation
    plan.allocs.forEach(function (a) {
      var L = plan.byId[a.lineId];
      chk('P7', 'allocation inside spec, route and remaining life', !L || (a.assay >= L.assayMin && a.imp <= L.impMax && a.psd <= L.psdMax),
          a.lineId + ': blend assays ' + a.assay + '%, impurity ' + a.imp + '%, d90 ' + a.psd);
      chk('P7', 'allocation inside spec, route and remaining life', !L || !L.minLifeM || (a.retestAt - now) / MONTH >= L.minLifeM,
          a.lineId + ': ' + Math.round((a.retestAt - now) / MONTH * 10) / 10 + ' months left against a ' + L.minLifeM + ' month minimum');
      chk('P7', 'allocation inside spec, route and remaining life', a.lots.length <= 3, a.lineId + ' blends ' + a.lots.length + ' lots');
    });
    // P2 mass balance per product: what came out of the batches equals what the lots hold plus what shipped
    m.P.forEach(function (p) {
      var made = 0, lots = 0;
      plan.batches.forEach(function (b) { if (b.pix === p.ix) made += b.kg; });
      plan.lots.forEach(function (x) { if (x.pix === p.ix && !x.opening) lots += x.kg; });
      chk('P2', 'mass balance per product', Math.abs(made - lots) < 1, p.id + ': ' + made + ' kg made against ' + lots + ' kg in lots');
    });
    var tot = { checks: 0, violations: 0 };
    Object.keys(out).forEach(function (k) { tot.checks += out[k].checks; tot.violations += out[k].violations; });
    return { byNuance: out, total: tot, inherited: inherited };
  };

  // =====================================================================================================================
  // S&OP — coarse arithmetic over the SAME masters, calibrated from the detailed plan so the two horizons reconcile
  // =====================================================================================================================
  E.sop = function (m, plan, settings) {
    settings = settings || {};
    var wi = settings.whatifs || [], mixShift = wi.filter(function (w) { return w.type === 'mix'; })[0];
    var bn = m.DATA.meta.bottleneck, months = m.cfg.sopMonthList || [];
    var rows = m.demandPlan.slice();
    if (mixShift) {
      rows = rows.map(function (r) {
        if (r.productId === mixShift.fromProduct) return Object.assign({}, r, { kg: Math.round(r.kg * (1 - mixShift.shift)) });
        if (r.productId === mixShift.toProduct) return Object.assign({}, r, { kg: Math.round(r.kg * (1 + mixShift.shift)) });
        return r;
      });
    }
    // hours available per class per month, and the realised rate the detailed plan actually achieved
    var hrsPerDay = {}; m.U.forEach(function (u) { hrsPerDay[u.cls] = (hrsPerDay[u.cls] || 0) + 24 * u.uptime; });
    var realised = plan.kpi.busyMin / Math.max(1, plan.kpi.availMin);
    var cleanShare = plan.kpi.busyMin ? (plan.kpi.cleanHours * 60) / plan.kpi.busyMin : 0;

    function bhOf(p) { return p.ops.reduce(function (a, o) { return a + (o.cls === bn ? o.hours : 0); }, 0); }
    var byMonth = months.map(function (mo) {
      var dem = rows.filter(function (r) { return r.month === mo.month; });
      var days = 30.4 - (mo.shutdown ? m.cfg.shutdownDays : 0);
      var need = {}, kg = 0, contrib = 0;
      dem.forEach(function (r) {
        var p = m.P[m.pix[r.productId]]; if (!p) return;
        var nb = r.kg / p.batchKg;
        p.ops.forEach(function (o) { need[o.cls] = (need[o.cls] || 0) + nb * o.hours; });
        kg += r.kg; contrib += r.kg * p.marginKg;
      });
      var load = {}, worst = 0, worstCls = bn;
      Object.keys(hrsPerDay).forEach(function (c) {
        var av = hrsPerDay[c] * days, nd = (need[c] || 0) * (1 + cleanShare);
        load[c] = av ? nd / av : 0;
        if (load[c] > worst) { worst = load[c]; worstCls = c; }
      });
      return { month: mo.month, label: mo.label, no: mo.no, shutdown: !!mo.shutdown, days: Math.round(days * 10) / 10,
               demandKg: Math.round(kg), contribution: Math.round(contrib), load: load, bottleneck: worstCls,
               loadPct: Math.round(worst * 1000) / 1000, feasible: worst <= 1.0,
               gapKg: worst > 1 ? Math.round(kg * (1 - 1 / worst)) : 0 };
    });
    // the capacity envelope of THIS mix, nameplate against the rate the plan actually realises
    var mixKg = {}, totKg = 0;
    rows.filter(function (r) { return r.monthNo <= 3; }).forEach(function (r) { mixKg[r.productId] = (mixKg[r.productId] || 0) + r.kg; totKg += r.kg; });
    var bhPerKg = 0;
    Object.keys(mixKg).forEach(function (pid) {
      var p = m.P[m.pix[pid]]; if (!p) return;
      bhPerKg += (mixKg[pid] / totKg) * bhOf(p) / p.batchKg;
    });
    var bnHoursMonth = hrsPerDay[bn] * 30.4;
    var nameplateT = bhPerKg ? bnHoursMonth / bhPerKg / 1000 : 0;
    var realisedT = nameplateT * (1 - cleanShare) * clamp(realised / Math.max(0.01, realised), 1, 1);
    realisedT = bhPerKg ? (bnHoursMonth * (1 - cleanShare)) / bhPerKg / 1000 : 0;

    var rank = m.P.map(function (p) {
      var bh = bhOf(p);
      return { productId: p.id, name: p.name, family: p.family, marginKg: p.marginKg, perTonne: p.marginKg * 1000,
               bhHours: bh, batchKg: p.batchKg, perBhHour: bh ? Math.round(p.marginKg * p.batchKg / bh) : null,
               offBottleneck: bh === 0 };
    });
    rank.sort(function (a, b) { return (b.perBhHour || 1e12) - (a.perBhHour || 1e12); });

    // co-product ceilings
    var copro = m.P.filter(function (p) { return p.coprodId; }).map(function (p) {
      var kgM = (mixKg[p.id] || 0) / 3;
      return { productId: p.id, coprodId: p.coprodId, ratio: p.coprodRatio, mainKgMonth: Math.round(kgM),
               coprodKgMonth: Math.round(kgM * p.coprodRatio) };
    });
    // pre-build for the shutdown, bounded by shelf life
    var sdIx = byMonth.filter(function (x) { return x.shutdown; })[0];
    var prebuild = [];
    if (sdIx) {
      rows.filter(function (r) { return r.month === sdIx.month; }).forEach(function (r) {
        var p = m.P[m.pix[r.productId]]; if (!p) return;
        var lost = Math.round(r.kg * m.cfg.shutdownDays / 30.4);
        prebuild.push({ productId: p.id, shutdownKg: lost, retestM: p.retestM,
                        monthsEarly: Math.min(3, Math.max(1, Math.floor(p.retestM / 6))),
                        feasible: p.retestM >= 12 });
      });
      prebuild.sort(function (a, b) { return b.shutdownKg - a.shutdownKg; });
    }
    return { months: byMonth, rank: rank, coproducts: copro, prebuild: prebuild, bottleneck: bn,
             nameplateTonnesMonth: Math.round(nameplateT * 10) / 10, realisedTonnesMonth: Math.round(realisedT * 10) / 10,
             cleanShare: Math.round(cleanShare * 1000) / 1000, shutdownMonth: m.cfg.shutdownMonth,
             shutdownDays: m.cfg.shutdownDays, mixKg: mixKg,
             headline: 'Nameplate capacity of this mix ' + (Math.round(nameplateT * 10) / 10) + ' t a month; at the rate the plan realises, ' +
                       (Math.round(realisedT * 10) / 10) + ' t' };
  };

  // =====================================================================================================================
  // COMPARE — the one call every page makes. Same data, same weights, two rule sets, then the consequences.
  // =====================================================================================================================
  E.compare = function (m, hist, settings) {
    settings = settings || {};
    var t0 = Date.now();
    var aware = E.plan(m, hist, Object.assign({}, settings, { rules: 'aware', assume: null }));
    var generic = E.plan(m, hist, Object.assign({}, settings, { rules: 'generic', assume: settings.assume || null }));
    var cons = E.consequence(m, generic, aware);
    var rep = E.repair(m, generic, cons);
    var pr = E.proof(m, aware), prG = E.proof(m, generic);
    var sop = E.sop(m, aware, settings);
    // the two scoreboards. On the NAIVE one the generic plan wins — it is scored on what it claims about itself.
    var naive = {
      generic: { otif: generic.kpi.otif, cleanHours: generic.kpi.cleanHours, outputKg: generic.kpi.nominalKg,
                 batches: generic.kpi.batches, util: generic.kpi.util, late: generic.kpi.late },
      aware: { otif: aware.kpi.otif, cleanHours: aware.kpi.cleanHours, outputKg: aware.kpi.nominalKg,
               batches: aware.kpi.batches, util: aware.kpi.util, late: aware.kpi.late }
    };
    var lostKg = cons.events.reduce(function (a, r) { return a + (r.statusChanging ? (r.cost.kg || 0) : 0); }, 0);
    var lostHours = cons.events.reduce(function (a, r) { return a + (r.cost.hours || 0); }, 0);
    var real = {
      generic: { outputKg: Math.round(generic.kpi.madeKg - lostKg), cost: cons.total.rupees,
                 cleanHours: Math.round((generic.kpi.cleanHours + cons.byNuance.P1 ? (cons.byNuance.P1 || {}).hours || 0 : 0) * 10) / 10,
                 lostHours: Math.round(lostHours * 10) / 10, violations: prG.total.violations,
                 delayCost: generic.kpi.delayCost, repairs: rep.placed, unplaced: rep.unplaced },
      aware: { outputKg: aware.kpi.madeKg, cost: 0, cleanHours: aware.kpi.cleanHours, lostHours: 0,
               violations: pr.total.violations, delayCost: aware.kpi.delayCost, repairs: 0, unplaced: 0 }
    };
    return { aware: aware, generic: generic, cons: cons, repair: rep, proof: pr, proofGeneric: prG, sop: sop,
             naive: naive, real: real, ms: Date.now() - t0,
             fair: naive.generic.otif >= naive.aware.otif - 1e-9 || naive.generic.cleanHours <= naive.aware.cleanHours };
  };
})(typeof window !== 'undefined' ? window : globalThis);
