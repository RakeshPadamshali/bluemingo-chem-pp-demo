/* Bluemingo PP — the chemical-plant scheduler. DOM-free: runs in the browser (window.CHMEngine) and in Node for tests.

   ONE SCHEDULER, TWO RULE SETS. E.RULES.aware and E.RULES.generic are capability flags, not two code paths: every rule
   site reads the flag and does one thing or the other. The generic set is the deck's named assumptions — a flat
   changeover per product pair, nameplate yield, no hold-time check, no utility check, no effluent check, tank space
   instead of a hazard licence, allocation on quantity and date — and it keeps everything a real APS keeps: equipment
   non-overlap, eligibility, block times, due-date order, campaign grouping, batch sizes. Forking the builder would be a
   straw man, and would deserve to be called one.

   Four passes, in this order:
     history(m)                 30 frozen days, planned the generic way, with what actually happened
     plan(m, hist, settings)    the live plan from the as-of moment, under either rule set
     consequence(m, plan)       REPLAYS the generic plan and prices what its assumptions cost — it never re-schedules
     repair(m, plan, events)    one firefighting sweep that places the replacement batches, under generic rules again

   Determinism: every physical draw (yield, assay, impurity, PSD, QC time, breakdown) is keyed on (product, nth batch of
   that product), never on plan order — so BOTH rule sets face identical physics and only their reaction differs. That
   single detail is what makes the comparison valid; tools/verify_engine.js asserts the draws match.

   Times are integer minutes from the start of history (meta.base). Mass is kg, volume kL, duty per hour. */
(function (root) {
  'use strict';
  var E = {};

  // =====================================================================================================================
  // RULE SETS — the only difference between the two plans
  // =====================================================================================================================
  E.RULES = {
    // NOTE the r-prefix. These are merged into the weight object, and `clean`, `util` and `waste` are also the names of
    // three objective weights — an unprefixed flag silently overwrote the number and made every score NaN.
    aware: { id: 'aware', rClean: 'matrix', rYield: 'assay', rHold: 'window', rUtil: 'duty', rWaste: 'cap', rLicence: 'ceiling', rAlloc: 'spec' },
    generic: { id: 'generic', rClean: 'flat', rYield: 'nameplate', rHold: 'none', rUtil: 'none', rWaste: 'none', rLicence: 'space', rAlloc: 'qty' }
  };
  // which flag each of the deck's seven assumptions turns on (the Plan Studio's assumption ratchet)
  E.ASSUMPTION_FLAG = { clean: 'rClean', yield: 'rYield', hold: 'rHold', util: 'rUtil', waste: 'rWaste', licence: 'rLicence', alloc: 'rAlloc' };
  E.rulesFor = function (id, on) {
    var base = id === 'aware' ? E.RULES.aware : E.RULES.generic;
    if (!on || !on.length) return base;
    var out = {}, k;
    for (k in base) out[k] = base[k];
    out.id = id + '+' + on.slice().sort().join(',');
    on.forEach(function (a) { var f = E.ASSUMPTION_FLAG[a]; if (f) out[f] = E.RULES.aware[f]; });
    return out;
  };

  var CLS_RANK = { EXPORT_REG: 0, EXPORT: 1, DOM_COMMITTED: 2, DOM_OPEN: 3 };
  function hash01(s) { var h = 2166136261; s = String(s); for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return ((h >>> 0) % 1000003) / 1000003; }
  function gauss(seed) { var a = hash01(seed + '|a'), b = hash01(seed + '|b'); return Math.sqrt(-2 * Math.log(a + 1e-9)) * Math.cos(2 * Math.PI * b); }
  function minOf(iso, base) { return Math.round((new Date(iso) - base) / 60000); }
  function clamp(x, a, b) { return x < a ? a : x > b ? b : x; }
  function cmpId(a, b) { return a < b ? -1 : a > b ? 1 : 0; }

  // =====================================================================================================================
  // MODEL — masters (plus Master Data uploads) turned into indexed structures. Every rule is DERIVED from attributes
  // here, so a product, unit or customer added from Excel inherits its eligibility, clean grades and duty with no
  // mapping table anywhere.
  // =====================================================================================================================
  E.prepare = function (DATA, overlay) {
    overlay = overlay || {};
    var M = DATA.m, cfg = DATA.cfg, m = {};
    function rows(key) {
      var base = (M[key] || []).map(function (r) { return Object.assign({}, r); });
      var o = overlay[key]; if (!o || !o.rows) return base;
      var kf = o.kf || 'id', idx = {}; base.forEach(function (r, i) { idx[r[kf]] = i; });
      o.rows.forEach(function (r) { if (r[kf] in idx) base[idx[r[kf]]] = Object.assign({}, base[idx[r[kf]]], r); else base.push(Object.assign({}, r)); });
      return base;
    }
    m.DATA = DATA; m.cfg = cfg; m.base = new Date(DATA.meta.base); m.asOf = DATA.meta.asOfMinute; m.end = DATA.meta.endMinute;
    m.H = Math.ceil(m.end / 60) + 72; m.Dn = Math.ceil(m.end / 1440) + 3;
    m.flatChgMin = Math.round((cfg.generic.flatChangeoverH || 3) * 60);
    m.confSd = cfg.aware.yieldConfidenceSd != null ? cfg.aware.yieldConfidenceSd : 1.0;

    // ---- equipment ------------------------------------------------------------------------------------------------
    m.U = rows('units').map(function (u, i) {
      return { ix: i, id: u.id, name: u.name, cls: u.cls, block: u.block, vol: +u.vol, mat: u.mat, cryo: !!u.cryo,
               uptime: u.uptime != null ? +u.uptime : (cfg.unitUptime || 0.92), note: u.note };
    });
    m.uix = {}; m.U.forEach(function (u) { m.uix[u.id] = u.ix; });
    m.unitsByCls = {}; m.U.forEach(function (u) { (m.unitsByCls[u.cls] = m.unitsByCls[u.cls] || []).push(u); });
    m.clsList = Object.keys(m.unitsByCls).sort();

    // block times: the weekly rules expanded into concrete intervals, plus unplanned breakdowns
    m.blocks = {}; m.U.forEach(function (u) { m.blocks[u.ix] = []; });
    var day0 = new Date(m.base); // minute 0's calendar day
    rows('blockTimes').forEach(function (b) {
      var ui = m.uix[b.unit]; if (ui == null) return;
      for (var d = 0; d * 1440 < m.end + 1440; d++) {
        var dt = new Date(m.base.getTime() + d * 86400000);
        if (dt.getDay() !== ((+b.dow + 1) % 7)) continue;                 // config dow 0 = Monday
        if (+b.every === 14 && Math.floor(d / 7) % 2) continue;
        var s = d * 1440 + (+b.start) * 60;
        m.blocks[ui].push([s, s + (+b.hours) * 60, b.reason, 'planned']);
      }
    });
    ((DATA.events || {}).breakdowns || []).forEach(function (b) {
      var ui = m.uix[b.unitId]; if (ui == null) return;
      var s = minOf(b.start, m.base);
      m.blocks[ui].push([s, s + (+b.durMin), b.reason, 'breakdown', b.id]);
    });
    Object.keys(m.blocks).forEach(function (k) { m.blocks[k].sort(function (a, b) { return a[0] - b[0]; }); });

    // ---- secondary resources, waste, licence ----------------------------------------------------------------------
    m.utils = rows('utilities').map(function (u, i) {
      var der = null;
      if (u.derateMonths) der = { months: String(u.derateMonths).split(',').map(Number), cap: +u.derateCap, why: u.derateWhy };
      return { ix: i, id: u.id, name: u.name, unit: u.unit, cap: +u.cap, kind: u.kind, derate: der };
    });
    m.utix = {}; m.utils.forEach(function (u) { m.utix[u.id] = u.ix; });
    // cap per hour, with the seasonal derate resolved once into a flat array (hot loops never look at a date)
    m.utilCap = new Float64Array(m.utils.length * m.H);
    m.utils.forEach(function (u) {
      for (var h = 0; h < m.H; h++) {
        var mo = new Date(m.base.getTime() + h * 3600000).getMonth() + 1;
        m.utilCap[u.ix * m.H + h] = (u.derate && u.derate.months.indexOf(mo) >= 0) ? u.derate.cap : u.cap;
      }
    });
    m.wastes = rows('waste').map(function (w, i) { return { ix: i, id: w.id, name: w.name, unit: w.unit, cap: +w.cap, note: w.note }; });
    m.wix = {}; m.wastes.forEach(function (w) { m.wix[w.id] = w.ix; });
    var rec = rows('solventRecovery')[0] || {};
    m.recovery = { cap: +rec.cap || 18, min: +rec.recoveryMin || 0.7, max: +rec.recoveryMax || 0.92, turnMin: (+rec.turnaroundHours || 36) * 60 };
    m.hazs = rows('hazardClasses').map(function (h, i) { return { ix: i, id: h.id, name: h.name, licensedKL: +h.licensedKL, note: h.note }; });
    m.hix = {}; m.hazs.forEach(function (h) { m.hix[h.id] = h.ix; });
    m.bunds = rows('bunds').map(function (b) { return { id: b.id, name: b.name, classes: String(b.classes || '').split(',').filter(Boolean) }; });
    m.segregation = rows('segregation').map(function (s) { return [s.classA, s.classB]; });
    m.tanks = rows('tanks').map(function (t, i) {
      return { ix: i, id: t.id, name: t.name, solventId: t.solventId, bundId: t.bundId, haz: t.haz, hix: m.hix[t.haz],
               capKL: +t.capKL, openKL: +t.openKL, tankerKL: +t.tankerKL, priceKL: +t.priceKL, solvClass: t.solvClass };
    });
    m.tix = {}; m.solvTank = {}; m.tanks.forEach(function (t) { m.tix[t.id] = t.ix; m.solvTank[t.solventId] = t.ix; });
    m.deliveries = rows('deliveries').map(function (d) {
      return { id: d.id, tix: m.tix[d.tankId], solventId: d.solventId, kl: +d.kl, at: minOf(d.eta, m.base), haz: d.haz,
               hix: m.hix[d.haz], supplier: d.supplier, priceKL: +d.priceKL };
    }).filter(function (d) { return d.tix != null; }).sort(function (a, b) { return a.at - b.at || cmpId(a.id, b.id); });

    // ---- cleaning: grades, overrides, and the derived rule ---------------------------------------------------------
    m.grades = {}; rows('cleanGrades').forEach(function (g) { m.grades[g.id] = g.hours == null ? null : +g.hours; });
    m.gradeRows = rows('cleanGrades');
    m.ovr = {}; rows('cleanOverrides').forEach(function (o) { m.ovr[o.frm + '>' + o.to] = o; });
    m.campaign = rows('campaignRule')[0] || cfg.campaign || { minBatches: 2, maxBatches: 9, forcedBreakAfter: 9, pullAheadDays: 21 };

    // ---- products -------------------------------------------------------------------------------------------------
    var routeRows = rows('routes'), byProd = {};
    routeRows.forEach(function (r) { (byProd[r.productId] = byProd[r.productId] || []).push(r); });
    m.P = []; m.pix = {};
    rows('products').forEach(function (p) {
      var o = { ix: m.P.length, id: p.id, name: p.name, family: p.family, solv: p.solv, solvClass: p.solvClass, haz: p.haz,
                colour: +p.colour, potency: +p.potency, genotox: !!p.genotox, chargeKL: +p.chargeKL, batchKg: +p.batchKg,
                assayMean: +p.assayMean, assaySd: +p.assaySd, impMax: +p.impMax, psdMean: +p.psdMean, psdSd: +p.psdSd,
                retestM: +p.retestM, yieldMean: +p.yieldMean, yieldSd: +p.yieldSd, priceKg: +p.priceKg, costKg: +p.costKg,
                marginKg: +p.marginKg, regulated: !!p.regulated, intermediate: !!p.intermediate,
                coprodId: p.coprodId || null, coprodRatio: +p.coprodRatio || 0 };
      var rs = (byProd[p.id] || []).slice().sort(function (a, b) { return (+a.seq) - (+b.seq); });
      o.ops = rs.map(function (r, i) {
        var arch = (cfg.archetypes || {})[r.arch] || { segs: [], cls: r.cls, clean: true, label: r.label };
        return { seq: +r.seq || i + 1, id: r.id, arch: r.arch, label: r.label || arch.label, cls: r.cls,
                 min: Math.round((+r.hours) * 60), hours: +r.hours,
                 minLag: Math.round((+r.minLagH) * 60), maxLag: Math.round((+r.maxLagH) * 60),
                 maxLagH: +r.maxLagH, minLagH: +r.minLagH,
                 efflM3: +r.efflM3, wix: m.wix[r.wasteCat], wasteCat: r.wasteCat, solvKL: +r.solvKL,
                 clean: arch.clean !== false, duty: E.duty(o, arch), units: [] };
      });
      o.nameplateKg = Math.round(o.batchKg / o.yieldMean);   // output of this charge at theoretical yield
      o.cycleH = o.ops.reduce(function (a, x) { return a + x.hours; }, 0);
      o.efflM3 = o.ops.reduce(function (a, x) { return a + x.efflM3; }, 0);
      o.solvKL = o.ops.reduce(function (a, x) { return a + x.solvKL; }, 0);
      o.tix = m.solvTank[o.solv];
      m.pix[o.id] = o.ix; m.P.push(o);
    });
    /* A product with no routing cannot be planned — and somebody WILL add one to the Products master and press Apply.
       Hold it back with a reason rather than letting the scheduler dereference an operation that is not there. */
    m.unroutable = m.P.filter(function (p) { return !p.ops.length; }).map(function (p) {
      return { id: p.id, name: p.name, why: 'no routing: add its operations to the Routes master before it can be planned' };
    });
    if (m.unroutable.length) {
      m.P = m.P.filter(function (p) { return p.ops.length; });
      m.pix = {};
      m.P.forEach(function (p, i) { p.ix = i; m.pix[p.id] = i; });
    }
    // eligibility, derived (so an uploaded product or unit needs no mapping table)
    m.P.forEach(function (p) { p.ops.forEach(function (op) { op.units = E.eligible(m, p, op).map(function (u) { return u.ix; }); }); });
    // the clean matrix, derived once into a flat table of minutes (-1 = forbidden)
    var n = m.P.length;
    m.cleanMin = new Float64Array(n * n); m.cleanGrade = new Array(n * n); m.cleanWhy = new Array(n * n);
    m.P.forEach(function (a) {
      m.P.forEach(function (b) {
        var r = E.cleanCell(m, a, b), k = a.ix * n + b.ix;
        m.cleanGrade[k] = r.grade; m.cleanWhy[k] = r.why;
        m.cleanMin[k] = r.grade === 'FORBIDDEN' ? -1 : Math.round(r.hours * 60);
      });
    });

    // ---- demand ---------------------------------------------------------------------------------------------------
    m.oclass = {}; rows('orderClasses').forEach(function (c) { m.oclass[c.id] = { id: c.id, name: c.name, penalty: +c.penaltyPerDay, relWin: +c.relWinDays, note: c.note }; });
    m.customers = {}; rows('customers').forEach(function (c) {
      m.customers[c.id] = { id: c.id, name: c.name, region: c.region, regulated: !!c.regulated,
                            sites: String(c.sites || '').split(',').filter(Boolean), minLifeM: +c.minLifeMonths || 0,
                            qualWeeks: +c.qualWeeks || 0, coa: !!c.coaRequired };
    });
    m.orders = {}; (DATA.orders || []).forEach(function (o) { m.orders[o.id] = o; });
    m.lines = (DATA.lines || []).map(function (l) { return E.mkLine(m, l, m.orders[l.orderId]); }).filter(function (l) { return l.pix != null; });
    m.lotsOpen = rows('openingLots').map(function (x) {
      return { id: x.id, pix: m.pix[x.productId], productId: x.productId, kg: +x.kg, assay: +x.assay, imp: +x.imp, psd: +x.psd,
               madeAt: minOf(x.madeAt, m.base), retestAt: minOf(x.retestAt, m.base), opening: true, released: true, batchId: null };
    }).filter(function (x) { return x.pix != null; });
    m.sourcing = {}; rows('sourcing').forEach(function (s) { m.sourcing[s.productId] = s; });
    m.raws = rows('rawMaterials');
    m.approvals = {}; rows('approvals').forEach(function (a) { m.approvals[a.customerId + '|' + a.siteId] = a; });
    m.demandPlan = rows('demandPlan');
    m.presets = {}; rows('weights').forEach(function (w) { m.presets[w.id] = w; });
    m.assumptions = rows('genericAssumptions');
    m.ev = DATA.events || {};
    return m;
  };

  // ---- derived rules (the engine is the single source of truth; the generator repeats them only for its asserts) ----
  E.opVolume = function (m, p, cls) { return Math.round(p.chargeKL * ((m.cfg.opVolShare || {})[cls] != null ? m.cfg.opVolShare[cls] : 1) * 100) / 100; };
  E.eligible = function (m, p, op) {
    var need = E.opVolume(m, p, op.cls), over = m.cfg.oversize || 2.6;
    return (m.unitsByCls[op.cls] || []).filter(function (u) {
      if ((p.potency >= 3) !== (u.block === 'B')) return false;
      if (op.cls === 'REACTOR') {
        if (p.solvClass === 'HAL' && u.mat !== 'GL') return false;
        if (op.arch === 'RXN_CRYO' && !u.cryo) return false;
      }
      if (u.vol + 1e-9 < need) return false;
      if ((m.cfg.oversizeClasses || ['REACTOR']).indexOf(op.cls) >= 0 && u.vol > need * over) return false;
      return true;
    });
  };
  E.whyNot = function (m, p, op, u) {
    var out = [], need = E.opVolume(m, p, op.cls), over = m.cfg.oversize || 2.6;
    if (u.cls !== op.cls) { out.push(u.id + ' is a ' + u.cls.toLowerCase() + '; this operation needs a ' + op.cls.toLowerCase()); return out; }
    if (p.potency >= 3 && u.block !== 'B') out.push('high-potency work is segregated to Block B');
    if (p.potency < 3 && u.block === 'B') out.push('Block B is reserved for high-potency work');
    if (op.cls === 'REACTOR' && p.solvClass === 'HAL' && u.mat !== 'GL') out.push('halogenated solvent service needs a glass-lined vessel');
    if (op.arch === 'RXN_CRYO' && !u.cryo) out.push('a cryogenic step needs brine / cryo service');
    if (u.vol + 1e-9 < need) out.push('a ' + need.toFixed(2) + ' kL load does not fit a ' + u.vol + ' kL vessel');
    else if ((m.cfg.oversizeClasses || ['REACTOR']).indexOf(op.cls) >= 0 && u.vol > need * over) out.push('a ' + need.toFixed(2) + ' kL load is lost in a ' + u.vol + ' kL vessel (agitation limit)');
    return out;
  };
  /* What one batch CONSUMES and PRODUCES, derived the same way its duty is.

     These three answer the question "where is the master that ties this to the volume?" — there is no per-product table
     anywhere: the rate is per kL of charge against the operation archetype, the charge is the product's own, and the
     material that fills each role comes from the family. A product added from Excel gets all of it for free.

     They are computed here rather than read from the generated master so that an uploaded charge profile, a changed
     batch size or a new product is reflected immediately; tools/audit.py checks the two agree. */
  E.inputs = function (m, p) {
    var prof = m.cfg.inputProfile || {}, fam = (m.cfg.familyInputs || {})[p.family] || {};
    var names = m.cfg.roleNames || {}, rec = m.cfg.catalystRecovery != null ? m.cfg.catalystRecovery : 0;
    var rm = {}; (m.raws || []).forEach(function (r) { rm[r.id] = r; });
    var out = [], feed = false;
    p.ops.forEach(function (op) {
      (prof[op.arch] || []).forEach(function (pr) {
        var role = pr[0], rate = +pr[1];
        if (role === 'FEED') { if (feed) return; feed = true; }
        var mat = rm[fam[role]];
        if (!mat) return;
        var qty = Math.round(rate * p.chargeKL * 100) / 100;
        var net = role === 'CATALYST' ? Math.round(qty * (1 - rec) * 1000) / 1000 : qty;
        out.push({ seq: op.seq, op: op.id, opLabel: op.label, role: role, roleName: names[role] || role,
                   rmId: mat.id, rmName: mat.name, unit: mat.unit, perKL: rate, qty: qty, net: net,
                   priceUnit: +mat.priceUnit, rupees: Math.round(net * (+mat.priceUnit || 0)),
                   recovered: role === 'CATALYST' ? Math.round((qty - net) * 1000) / 1000 : 0 });
      });
    });
    return out;
  };
  // a rate times a time is a quantity: t of steam, TR-hours of refrigeration, Nm3 of nitrogen, m3 of vacuum
  E.utilPerBatch = function (m, p) {
    var tot = {};
    p.ops.forEach(function (op) {
      op.duty.forEach(function (seg) {
        var hrs = op.hours * seg.frac;
        Object.keys(seg.draw).forEach(function (k) { tot[k] = (tot[k] || 0) + seg.draw[k] * hrs; });
      });
    });
    Object.keys(tot).forEach(function (k) { tot[k] = Math.round(tot[k] * 100) / 100; });
    return tot;
  };
  E.UTIL_QTY_UNIT = { 't/h': 't', 'TR': 'TR-h', 'm3/h': 'm3', 'Nm3/h': 'Nm3' };
  E.wastePerBatch = function (m, p) {
    var byCat = {}, solv = 0, rate = (m.recovery.min + m.recovery.max) / 2;
    p.ops.forEach(function (op) {
      if (op.wasteCat) byCat[op.wasteCat] = Math.round(((byCat[op.wasteCat] || 0) + op.efflM3) * 100) / 100;
      solv += op.solvKL;
    });
    return { byCat: byCat, efflM3: Math.round(p.efflM3 * 100) / 100, solvKL: Math.round(solv * 100) / 100,
             recoveredKL: Math.round(solv * rate * 100) / 100, makeupKL: Math.round(solv * (1 - rate) * 100) / 100,
             recoveryRate: Math.round(rate * 1000) / 1000 };
  };

  E.duty = function (p, arch) {
    return (arch.segs || []).map(function (s) {
      var draw = {}; Object.keys(s[1] || {}).forEach(function (k) { draw[k] = Math.round(s[1][k] * p.chargeKL * 100) / 100; });
      return { frac: s[0], draw: draw };
    });
  };
  // the clean grade needed to follow product a with product b on one unit — read off attributes, overrides win
  E.cleanGradeOf = function (a, b) {
    if (a.id === b.id) return ['NONE', 'same product, the campaign continues'];
    if ((a.potency >= 3) !== (b.potency >= 3)) return ['FORBIDDEN', 'high-potency residue is not cleaned down to a normal-product limit (segregated suite)'];
    if (a.genotox && b.family === 'F3') return ['DEDICATE', 'a genotoxic residue before a filed API route needs a full validated clean-down and a swab to the dedicated limit'];
    if (a.potency >= 2 && b.potency < 2) return ['BOILOUT', 'a potent residue before a normal product needs a boil-out and a swab test'];
    if (a.colour > b.colour + 1) return ['BOILOUT', 'colour load falls from ' + a.colour + ' to ' + b.colour + ': pale product needs a boil-out first'];
    var sameFam = a.family === b.family, sameSolv = a.solvClass === b.solvClass;
    if (sameFam && sameSolv && b.colour >= a.colour) return ['RINSE', 'same family and solvent class, colour load not falling'];
    if (sameSolv && b.colour >= a.colour) return ['WASH', 'solvent class is shared but the family changes'];
    return ['WASH', 'family or solvent class changes'];
  };
  E.cleanCell = function (m, a, b) {
    var o = m.ovr[a.id + '>' + b.id];
    if (o) return { grade: o.grade, hours: m.grades[o.grade] || 0, why: o.why, source: 'override' };
    var g = E.cleanGradeOf(a, b);
    return { grade: g[0], hours: m.grades[g[0]] || 0, why: g[1], source: 'derived' };
  };

  E.mkLine = function (m, l, o) {
    o = o || {};
    var oc = m.oclass[l.cls] || { relWin: 14, penalty: 0 };
    var ord = Math.max(0, minOf(o.orderDate || l.orderDate, m.base)), due = minOf(l.due, m.base);
    var c = m.customers[l.customerId] || {};
    return { id: l.id, orderId: l.orderId, pix: m.pix[l.productId], productId: l.productId, qty: +l.qty, cls: l.cls,
             cust: l.customerId, custName: c.name || l.customerId, regulated: !!c.regulated, siteId: l.siteId || 'UNIT-2',
             priceKg: +l.priceKg, marginKg: +l.marginKg, minLifeM: +l.minLifeM || 0, assayMin: +l.assayMin,
             impMax: +l.impMax, psdMax: +l.psdMax, tightSpec: !!l.tightSpec, coa: !!l.coa,
             ord: ord, due: due, rel: Math.max(ord, due - oc.relWin * 1440), penalty: oc.penalty, rush: !!l.rush };
  };

  // =====================================================================================================================
  // STATE
  // =====================================================================================================================
  function newState(m) {
    var nU = m.U.length, nP = m.P.length;
    var st = {
      free: new Float64Array(nU),            // when each unit is next free
      last: new Int32Array(nU),              // product index last run on it (-1 = clean / never used)
      lastEnd: new Float64Array(nU),
      util: new Float64Array(m.utils.length * m.H),
      waste: new Float64Array(m.wastes.length * m.Dn),
      recov: new Float64Array(m.Dn),
      tankD: new Float64Array(m.tanks.length * m.Dn),   // net change per day
      runs: new Int32Array(nP),              // batches of each product produced so far (the seed for its physics)
      camp: new Int32Array(nU),              // batches of `last` run consecutively on this unit
      cleanFor: new Int32Array(nU),          // the product this unit has been cleaned down FOR, or -1
      lines: {}, lineOrder: [], pend: [], relIdx: 0,
      lots: [], batches: [], jobs: [], cleans: [], sacrifices: [], pulls: [], refused: [], emergency: [], accepted: [],
      delIdx: 0, nextBatch: 1, delQ: m.deliveries.map(function (d) { return d; })
    };
    for (var i = 0; i < nU; i++) { st.last[i] = -1; st.cleanFor[i] = -1; }
    m.lines.forEach(function (l) { addLine(m, st, l); });
    sortPend(st);
    m.lotsOpen.forEach(function (x) { st.lots.push(Object.assign({}, x, { left: x.kg })); });
    return st;
  }
  function addLine(m, st, l) {
    st.lines[l.id] = { l: l, rem: 0, released: false, made: 0, nominal: 0, booked: 0, cancelled: 0, batches: [], firstStart: null, lastEnd: null, shipped: 0, waitFor: null };
    st.lineOrder.push(l.id);
    st.pend.push([l.rel, l.id]);
  }
  function sortPend(st) {
    var done = st.pend.slice(0, st.relIdx), rest = st.pend.slice(st.relIdx).sort(function (a, b) { return a[0] - b[0] || cmpId(a[1], b[1]); });
    st.pend = done.concat(rest);
  }
  // Typed arrays do not survive JSON cloning, so the state is copied field by field.
  function cloneState(m, st) {
    var o = {};
    ['free', 'last', 'lastEnd', 'util', 'waste', 'recov', 'tankD', 'runs', 'camp', 'cleanFor'].forEach(function (k) { o[k] = st[k].slice(); });
    o.lines = {}; st.lineOrder.forEach(function (id) {
      var L = st.lines[id];
      o.lines[id] = { l: L.l, rem: L.rem, released: L.released, made: L.made, nominal: L.nominal, booked: L.booked || 0, cancelled: L.cancelled,
                      batches: L.batches.slice(), firstStart: L.firstStart, lastEnd: L.lastEnd, shipped: L.shipped, waitFor: L.waitFor };
    });
    o.lineOrder = st.lineOrder.slice(); o.pend = st.pend.map(function (x) { return [x[0], x[1]]; }); o.relIdx = st.relIdx;
    o.lots = st.lots.map(function (x) { return Object.assign({}, x); });
    o.batches = st.batches.map(function (b) { return Object.assign({}, b, { ops: b.ops.map(function (x) { return Object.assign({}, x); }) }); });
    o.jobs = st.jobs.slice(); o.cleans = st.cleans.slice(); o.sacrifices = st.sacrifices.slice(); o.refused = st.refused.slice();
    o.pulls = (st.pulls || []).slice();
    o.emergency = st.emergency.slice(); o.accepted = st.accepted.slice(); o.heldInRecovery = (st.heldInRecovery || []).slice(); o.returns = (st.returns || []).slice();
    o.delIdx = st.delIdx; o.nextBatch = st.nextBatch; o.delQ = st.delQ.slice(); o.tankOpenInDelta = !!st.tankOpenInDelta;
    return o;
  }

  // ---------------------------------------------------------------------------------------------------- bucket helpers
  /* An operation's utility draw, as hour -> rate.

     Two things this has to get right, and both were wrong before:
     - A segment boundary lands mid-hour, so one hour can be touched by two segments of the SAME operation. A vessel is
       not simultaneously in reaction and in quench, so that hour's draw is the MAXIMUM of the segments touching it, not
       their sum. Summing overstated the peak, and made the admission test and the commit disagree.
     - The admission test has to see the rest of the train. Checking each operation against the state alone let two
       operations of one batch each pass and then together break the cap. `pend` carries the train's own load. */
  function dutyHours(m, op, s, e) {
    var dur = e - s, t = s, out = {};
    for (var g = 0; g < op.duty.length; g++) {
      var seg = op.duty[g], segEnd = g === op.duty.length - 1 ? e : t + dur * seg.frac;
      for (var k in seg.draw) {
        var ui = m.utix[k];
        if (ui == null) continue;
        var o = out[ui] || (out[ui] = {});
        for (var h = Math.floor(t / 60); h < Math.ceil(segEnd / 60); h++) {
          if (h < 0 || h >= m.H) continue;
          if (!(o[h] >= seg.draw[k])) o[h] = seg.draw[k];
        }
      }
      t = segEnd;
    }
    return out;
  }
  function newPend() { return { util: {}, waste: {}, recov: {} }; }
  function pendAdd(m, pend, op, s, e) {
    var dh = dutyHours(m, op, s, e), ui, h;
    for (ui in dh) {
      var o = pend.util[ui] || (pend.util[ui] = {});
      for (h in dh[ui]) o[h] = (o[h] || 0) + dh[ui][h];
    }
    if (op.wix != null && op.efflM3) {
      var d = Math.floor(s / 1440), w = pend.waste[op.wix] || (pend.waste[op.wix] = {});
      w[d] = (w[d] || 0) + op.efflM3;
    }
    if (op.solvKL) { var d2 = Math.floor(s / 1440); pend.recov[d2] = (pend.recov[d2] || 0) + op.solvKL; }
  }
  function pv(map, a, b) { var o = map && map[a]; return (o && o[b]) || 0; }

  // peak-respecting admission test: does adding this duty keep every hour inside its cap?
  function utilFits(m, st, op, s, e, pend) {
    var dh = dutyHours(m, op, s, e), push = null;
    for (var ui in dh) {
      for (var h in dh[ui]) {
        var hh = +h, cap = m.utilCap[ui * m.H + hh];
        if (!cap) continue;
        if (st.util[ui * m.H + hh] + pv(pend && pend.util, ui, hh) + dh[ui][h] > cap + 1e-9) {
          var next = (hh + 1) * 60;
          if (push == null || next > push) push = next;
        }
      }
    }
    return push;
  }
  function utilAdd(m, st, op, s, e, sign) {
    var dh = dutyHours(m, op, s, e);
    for (var ui in dh) for (var h in dh[ui]) st.util[ui * m.H + (+h)] += sign * dh[ui][h];
  }
  function wasteFits(m, st, op, t, pend) {
    if (op.wix == null || !op.efflM3) return null;
    var d = Math.floor(t / 1440), w = m.wastes[op.wix];
    if (st.waste[op.wix * m.Dn + d] + pv(pend && pend.waste, op.wix, d) + op.efflM3 <= w.cap + 1e-9) return null;
    return (d + 1) * 1440;
  }
  function recovFits(m, st, op, t, pend) {
    if (!op.solvKL) return null;
    var d = Math.floor(t / 1440);
    return st.recov[d] + ((pend && pend.recov[d]) || 0) + op.solvKL <= m.recovery.cap + 1e-9 ? null : (d + 1) * 1440;
  }
  // every cap this rule set respects, in one place: the earliest time the operation could be admitted, or null if now
  function admit(m, st, p, op, s, e, W, pend) {
    var push = null;
    if (W.rUtil === 'duty') push = utilFits(m, st, op, s, e, pend);
    if (push == null && W.rWaste === 'cap') push = wasteFits(m, st, op, s, pend);
    if (push == null && W.rWaste === 'cap') push = recovFits(m, st, op, s, pend);
    if (push == null && W.rLicence === 'ceiling' && op.solvKL) push = solventWait(m, st, p, op, s);
    return push;
  }
  function tankPos(m, st, tix, day) {
    var v = st.tankOpenInDelta ? 0 : m.tanks[tix].openKL;
    for (var d = 0; d <= day && d < m.Dn; d++) v += st.tankD[tix * m.Dn + d];
    return v;
  }
  function hazPos(m, st, hix, day) {
    var v = 0;
    for (var i = 0; i < m.tanks.length; i++) if (m.tanks[i].hix === hix) v += tankPos(m, st, i, day);
    return v;
  }
  // block time and breakdown: earliest start >= t where [start, start+dur) is clear
  function blocked(m, ui, t, dur) {
    var bl = m.blocks[ui];
    for (var guard = 0; guard < 40; guard++) {
      var moved = false;
      for (var i = 0; i < bl.length; i++) { if (t < bl[i][1] && t + dur > bl[i][0]) { t = bl[i][1]; moved = true; } }
      if (!moved) return t;
    }
    return t;
  }

  // =====================================================================================================================
  // PHYSICS — keyed on (product, nth batch of that product). Both rule sets face the SAME draws.
  // =====================================================================================================================
  E.physics = function (m, p, nth) {
    var k = p.id + '|' + nth;
    // yieldShift is the live-demo what-if "this campaign assays low": the mean moves, the spread and the seed do not,
    // so both rule sets still face exactly the same draw and only their reaction differs.
    var mean = p.yieldShift != null ? p.yieldShift : p.yieldMean;
    var y = clamp(mean + gauss('y|' + k) * p.yieldSd, 0.35, 1.0);
    var assay = clamp(p.assayMean + gauss('a|' + k) * p.assaySd, 90, 100);
    // batch-to-batch impurity in a controlled process varies by tens of per cent, not by half: the old spread had a
    // coefficient of variation of 56%, which put a quarter of the order book out of specification by arithmetic alone
    var imp = Math.max(0, p.impMax * clamp(0.70 + 0.18 * gauss('i|' + k), 0.08, 1.3));
    var psd = Math.max(5, Math.round(p.psdMean + gauss('d|' + k) * p.psdSd));
    var qc = m.ev.qcRule || { minDays: 1.5, maxDays: 3 };
    return { y: y, kg: Math.round(p.batchKg * y / p.yieldMean), assay: Math.round(assay * 100) / 100,
             imp: Math.round(imp * 1000) / 1000, psd: psd,
             qcMin: Math.round((qc.minDays + hash01('q|' + k) * (qc.maxDays - qc.minDays)) * 1440),
             offSpec: hash01('o|' + k) < ((m.ev.yieldRule || {}).offSpecShare || 0) };
  };

  // =====================================================================================================================
  // CHAIN PLACEMENT — the unit of commit is a TRAIN: one batch through every operation of its route.
  // Forward-greedy with the hold window checked at each link. When an operation cannot be placed inside its window the
  // chain fails and returns tStar: the earliest moment it COULD work. The caller then leaves the unit idle rather than
  // start something that would strand an intermediate, and records that choice as a sacrifice.
  // =====================================================================================================================
  function planChain(m, st, p, t0, W, firstUnit) {
    var ops = p.ops, place = [], t = t0, tStar = Infinity, fail = null, pend = newPend();
    for (var i = 0; i < ops.length; i++) {
      var op = ops[i], best = null, lastCause = 'none';
      var lo = i === 0 ? t0 : place[i - 1].e + op.minLag;
      var hi = i === 0 ? Infinity : place[i - 1].e + op.maxLag;
      if (W.rHold === 'none') hi = Infinity;
      for (var j = 0; j < op.units.length; j++) {
        var ui = op.units[j];
        if (i === 0 && firstUnit != null && ui !== firstUnit) continue;
        var cm = cleanMinFor(m, st, ui, p, W);
        if (cm < 0) { lastCause = 'forbidden'; continue; }        // forbidden pair on this unit
        // The clean starts as soon as the unit is free, NOT after the upstream stage ends — a filter is cleaned while
        // the reactor it feeds from is still running. Adding the clean on top of the earliest start instead would make
        // every link whose hold window is shorter than its boil-out impossible to satisfy, which is not how a plant works.
        var s = Math.max(lo, st.free[ui] + cm), guard = 0, clear = false, over = null, pushed = false;
        while (guard++ < 60) {
          var s2 = blocked(m, ui, s - cm, op.min + cm) + cm;
          if (s2 !== s) { s = s2; continue; }
          var push = admit(m, st, p, op, s, s + op.min, W, pend);
          if (push == null) { clear = true; break; }
          if (push > hi + op.min) { over = push; break; }     // the cap only clears after the hold window closes
          pushed = true; s = Math.max(s + 15, push + cm);
        }
        var end = s + op.min;
        // Never commit an operation that did not pass the admission test. Giving up here and committing anyway is how a
        // scheduler ends up "honouring" a cap it has actually broken.
        if (!clear || s > hi) {
          lastCause = !clear ? 'cap' : (pushed ? 'cap-then-window' : 'window');
          // How much later would the WHOLE train have to start for this operation to land inside its window? The
          // window travels with the stage before it, so the shift is the deficit at this link, not the minimum lag.
          // the earliest start this unit could ever offer: where the search stopped, or where the cap finally clears
          var target = clear ? s : (over != null ? over + cm : s);
          var shift = i === 0 ? target - t0 : (target - op.maxLag) - place[i - 1].e;
          if (shift > 0) tStar = Math.min(tStar, t0 + shift);
          continue;
        }
        if (!best || end < best.e || (end === best.e && ui < best.ui)) best = { ui: ui, s: s, e: end, clean: cm, op: op, ix: i };
      }
      if (!best) {
        fail = { op: op, ix: i, prev: i > 0 ? place[i - 1] : null, cause: lastCause,
                 why: i === 0 ? 'no eligible unit is free' : 'no eligible unit for ' + op.label + ' inside the ' + op.maxLagH + ' h hold window' };
        var fk = i + '|' + op.cls + '|' + lastCause;
        E.stats.failBy[fk] = (E.stats.failBy[fk] || 0) + 1;
        return { ok: false, tStar: isFinite(tStar) ? Math.max(tStar, t0 + 15) : t0 + 60, fail: fail, place: place };
      }
      place.push(best);
      pendAdd(m, pend, op, best.s, best.e);
    }
    return { ok: true, place: place, s: place[0].s, e: place[place.length - 1].e };
  }
  /* What this unit owes before it can run p.

     A clean-down is validated FOR a product: having cleaned the train for A does not make it clean for B, so the clean
     still has to be done from whatever last ran. And a forbidden pair is forbidden at any clean grade — it is a
     cross-contamination risk the plant does not accept, not an expensive changeover — so it survives every clean. */
  function cleanMinFor(m, st, ui, p, W) {
    var lastIx = st.last[ui];
    if (lastIx < 0 || lastIx === p.ix) return 0;
    if (W.rClean !== 'matrix') return m.flatChgMin;               // generic: one changeover time per pair, forbidden ignored
    var need = m.cleanMin[lastIx * m.P.length + p.ix];
    if (need < 0) return -1;                                      // forbidden, and no clean changes that
    return st.cleanFor[ui] === p.ix ? 0 : need;                   // already cleaned down for exactly this product
  }
  // the aware plan will not start an operation whose solvent is not in the tank (because a delivery was refused by the licence)
  function solventWait(m, st, p, op, t) {
    var tix = p.tix; if (tix == null) return null;
    var d = Math.floor(t / 1440);
    if (tankPos(m, st, tix, d) >= op.solvKL - 1e-9) return null;
    // wait only for a tanker that is close. Beyond that the plant buys the charge in rather than stand still, so the
    // operation is admitted and commitChain records the premium.
    for (var k = st.delIdx; k < st.delQ.length; k++) {
      var dl = st.delQ[k];
      if (dl.tix !== tix || dl.at <= t) continue;
      return dl.at - t <= 2880 ? dl.at + 60 : null;
    }
    return null;
  }

  function commitChain(m, st, p, r, W, phase, ctx) {
    var nth = st.runs[p.ix]++, ph = E.physics(m, p, nth);
    var bid = p.id + '-B' + String(1000 + nth).slice(1);
    var b = { id: bid, pix: p.ix, productId: p.id, nth: nth, phase: phase, s: r.s, e: r.e, ops: [], rules: W.id,
              kg: ph.kg, actualKg: ph.kg, nominalKg: p.nameplateKg,
              booked: W.rYield === 'nameplate' ? p.nameplateKg : ph.kg,   // the planning basis; the physical output is ph.kg either way
              assay: ph.assay, imp: ph.imp, psd: ph.psd, y: ph.y, offSpec: ph.offSpec, qcMin: ph.qcMin, lineIds: [] };
    r.place.forEach(function (pl) {
      var op = pl.op, ui = pl.ui;
      if (pl.clean > 0) {
        var lastIx = st.last[ui], g = W.rClean === 'matrix' ? m.cleanGrade[lastIx * m.P.length + p.ix] : 'FLAT';
        st.cleans.push({ unit: m.U[ui].id, uix: ui, s: pl.s - pl.clean, e: pl.s, min: pl.clean, grade: g,
                         frm: lastIx >= 0 ? m.P[lastIx].id : null, to: p.id, batch: bid, phase: phase,
                         why: lastIx >= 0 && W.rClean === 'matrix' ? m.cleanWhy[lastIx * m.P.length + p.ix] : 'flat changeover per product pair' });
      }
      b.ops.push({ seq: op.seq, opId: op.id, label: op.label, cls: op.cls, uix: ui, unit: m.U[ui].id,
                   s: pl.s, e: pl.e, clean: pl.clean, efflM3: op.efflM3, wix: op.wix, solvKL: op.solvKL });
      st.free[ui] = pl.e;
      st.camp[ui] = st.last[ui] === p.ix ? st.camp[ui] + 1 : 1;
      st.last[ui] = p.ix; st.cleanFor[ui] = p.ix; st.lastEnd[ui] = pl.e;
      utilAdd(m, st, op, pl.s, pl.e, +1);
      if (op.wix != null && op.efflM3) st.waste[op.wix * m.Dn + Math.floor(pl.s / 1440)] += op.efflM3;
      if (op.solvKL) {
        st.recov[Math.floor(pl.s / 1440)] += op.solvKL;
        if (p.tix != null) {
          var dd = Math.floor(pl.s / 1440), have = tankPos(m, st, p.tix, dd);
          if (have < op.solvKL - 1e-9) {          // the tank cannot cover the charge: buy it in, at a premium
            var buy = Math.ceil((op.solvKL - Math.max(0, have)) * 10) / 10;
            st.tankD[p.tix * m.Dn + dd] += buy;
            st.emergency.push({ at: pl.s, tank: m.tanks[p.tix].id, solventId: p.solv, kl: buy, batch: b.id,
                                productId: p.id, rupees: Math.round(buy * m.tanks[p.tix].priceKL * 1.35),
                                why: 'the tank could not cover the charge, so ' + buy + ' kL was bought in at a premium' });
          }
          st.tankD[p.tix * m.Dn + dd] -= op.solvKL;
        }
        // recovered solvent comes back after the distillation turnaround
        var back = Math.floor((pl.s + m.recovery.turnMin) / 1440);
        var rate = m.recovery.min + hash01('r|' + bid + '|' + op.seq) * (m.recovery.max - m.recovery.min);
        if (p.tix != null && back < m.Dn) st.tankD[p.tix * m.Dn + back] += op.solvKL * rate;
      }
    });
    b.readyAt = b.e + b.qcMin;
    st.batches.push(b);
    if (p.coprodId && p.coprodRatio) b.coprodKg = Math.round(b.kg * p.coprodRatio);
    return b;
  }

  /* Minimum campaign size — the other half of the Production Planner's campaign rule. The rule already breaks a campaign
     that has run too long; without a MINIMUM it never starts one, because only demand inside its release window can be
     seen, and at any instant that is about one line per product. The plan then pays a clean-down for every single batch,
     which is not how any campaigned plant runs.

     So when a unit is mid-campaign and still short of the minimum, the next batch of the same product may be pulled
     forward from inside the pull-ahead window: make it now, because we will not be clean for it again for weeks. The
     window is what bounds it — nothing is built arbitrarily early, and shelf life is what sets the window.

     BOTH rule sets get this. It is a planning policy, not a chemical rule, and giving it only to the aware plan would be
     exactly the straw man this demo is built to avoid. What differs is what each believes breaking a campaign COSTS:
     the matrix prices it per pair, the generic rule books a flat changeover and therefore breaks campaigns cheaply. */
  function gather(m, st, ui, t, W) {
    var out = [];
    for (var k = 0; k < st.lineOrder.length; k++) {
      var L = st.lines[st.lineOrder[k]];
      if (!L.released || L.rem <= 0) continue;
      var p = m.P[L.l.pix];
      if (p.ops[0].units.indexOf(ui) < 0) continue;
      // a line pulled forward to finish a campaign belongs to the train that pulled it, for as long as that train holds
      // the product — otherwise the pull just starts a one-batch campaign somewhere else, which is what it is for
      if (L.pullUnit != null && L.pullUnit !== ui && st.last[L.pullUnit] === L.l.pix) continue;
      if (cleanMinFor(m, st, ui, p, W) < 0) continue;
      if (st.last[ui] === p.ix && st.camp[ui] >= (+m.campaign.forcedBreakAfter || 9)) continue;   // forced campaign break
      L._sc = score(m, st, L, t, W, ui);
      out.push(L);
    }
    return out;
  }

  function pullForCampaign(m, st, ui, t) {
    var minB = +m.campaign.minBatches || 1;
    if (!(st.camp[ui] > 0 && st.camp[ui] < minB)) return;
    var pix = st.last[ui];
    if (pix == null || pix < 0) return;
    var pull = (+m.campaign.pullAheadDays || 0) * 1440;
    if (pull <= 0) return;
    var p = m.P[pix];
    if (!p || p.ops[0].units.indexOf(ui) < 0) return;
    for (var i = st.relIdx; i < st.pend.length; i++) {
      var L = st.lines[st.pend[i][1]];
      if (!L || L.released || L.rem > 0 || L.l.pix !== pix) continue;
      if (L.l.rel - t > pull) continue;
      L.released = true; L.rem = L.l.qty - L.cancelled; L.pulledAt = t; L.pullUnit = ui;
      st.pulls.push({ lineId: L.l.id, productId: p.id, unit: m.U[ui].id, at: t, earlyMin: L.l.rel - t,
                      camp: st.camp[ui], why: 'campaign' });
      return;                                   // one line at a time: the campaign is re-tested on the next decision
    }
  }

  // =====================================================================================================================
  // THE LOOP
  // =====================================================================================================================
  function advance(m, st, t, W, ctx) {
    while (st.relIdx < st.pend.length && st.pend[st.relIdx][0] <= t) {
      var L = st.lines[st.pend[st.relIdx++][1]];
      if (L.released) continue;
      L.released = true; L.rem = L.l.qty - L.cancelled;
    }
    // tanker deliveries: the LICENCE refuses one, not the tank. Generic looks at tank space only.
    while (st.delIdx < st.delQ.length && st.delQ[st.delIdx].at <= t) {
      var d = st.delQ[st.delIdx++], day = Math.floor(d.at / 1440), tk = m.tanks[d.tix];
      var lvl = tankPos(m, st, d.tix, day), haz = hazPos(m, st, d.hix, day);
      var noSpace = lvl + d.kl > tk.capKL + 1e-9;
      var overLic = haz + d.kl > m.hazs[d.hix].licensedKL + 1e-9;
      var refuse = W.rLicence === 'ceiling' ? (noSpace || overLic) : noSpace;
      if (refuse) {
        var tries = (d.tries || 0) + 1;
        st.refused.push({ id: d.id, tank: tk.id, haz: d.haz, kl: d.kl, at: d.at, level: Math.round(lvl * 10) / 10,
                          hazPos: Math.round(haz * 10) / 10, licensed: m.hazs[d.hix].licensedKL, tries: tries,
                          reason: overLic && W.rLicence === 'ceiling' ? 'licence' : 'tank full', overLicence: overLic,
                          requeued: tries <= 4 });
        // it waits at the gate and comes back in two days; demurrage is priced in the ledger, not modelled as a loss
        if (tries <= 4) {
          var again = Object.assign({}, d, { at: d.at + 2880, tries: tries });
          var k2 = st.delIdx;
          while (k2 < st.delQ.length && st.delQ[k2].at <= again.at) k2++;
          st.delQ.splice(k2, 0, again);
        }
      } else {
        st.tankD[d.tix * m.Dn + day] += d.kl;
        st.accepted.push({ id: d.id, tix: d.tix, tank: tk.id, haz: d.haz, hix: d.hix, kl: d.kl, at: d.at,
                          supplier: d.supplier, priceKL: d.priceKL, tries: d.tries || 0 });
      }
    }
  }

  function score(m, st, L, t, W, ui) {
    var l = L.l, p = m.P[l.pix];
    var slack = (l.due - t) / 1440 - (p.cycleH / 24) - 1;
    var committed = l.cls === 'EXPORT_REG' || l.cls === 'EXPORT' || l.cls === 'DOM_COMMITTED';
    var U = committed ? 1.15 + clamp(1 - slack / 18, 0, 1) + (slack < 0 ? Math.min(1, -slack / 6) : 0) : 0.3 * clamp(1 - slack / 24, 0, 1);
    var near = committed ? clamp(1 - slack / 18, 0.2, 1) : 0.2;
    var P = clamp(l.marginKg * p.batchKg / 4.0e5, 0.25, 1.4) * near;
    // campaign continuity: what NOT cleaning is worth. The rule set decides what a clean would have cost.
    var cm = ui != null ? cleanMinFor(m, st, ui, p, W) : 0;
    var C = cm < 0 ? -99 : clamp(1 - cm / 960, 0, 1);
    var V = W.rUtil === 'duty' ? headroom(m, st, p, t) : 0.5;
    var S = W.rWaste === 'cap' ? 1 - clamp(p.efflM3 / 24, 0, 1) : 0.5;
    var D = slack < 0 ? W.delayScale * (l.penalty || 0) * (-slack) / 2.4e6 : 0;
    return (W.dates * (U + D) + W.profit * P + W.clean * C + W.util * V + W.waste * S) / 100 + (l.rush ? 6 : 0);
  }
  function headroom(m, st, p, t) {
    var h = Math.floor(t / 60), worst = 1;
    for (var i = 0; i < p.ops.length; i++) for (var g = 0; g < p.ops[i].duty.length; g++) {
      var dr = p.ops[i].duty[g].draw;
      for (var k in dr) { var ui = m.utix[k]; if (ui == null || h >= m.H) continue; var cap = m.utilCap[ui * m.H + h]; if (!cap) continue; worst = Math.min(worst, 1 - (st.util[ui * m.H + h] + dr[k]) / cap); }
    }
    return clamp(worst, 0, 1);
  }
  E.scoreParts = function (m, st, L, t, W, ui) {
    var l = L.l, p = m.P[l.pix];
    var slack = (l.due - t) / 1440 - (p.cycleH / 24) - 1;
    var committed = l.cls === 'EXPORT_REG' || l.cls === 'EXPORT' || l.cls === 'DOM_COMMITTED';
    var U = committed ? 1.15 + clamp(1 - slack / 18, 0, 1) + (slack < 0 ? Math.min(1, -slack / 6) : 0) : 0.3 * clamp(1 - slack / 24, 0, 1);
    var near = committed ? clamp(1 - slack / 18, 0.2, 1) : 0.2;
    var P = clamp(l.marginKg * p.batchKg / 4.0e5, 0.25, 1.4) * near;
    var cm = ui != null ? cleanMinFor(m, st, ui, p, W) : 0;
    var C = cm < 0 ? -99 : clamp(1 - cm / 960, 0, 1);
    var V = W.rUtil === 'duty' ? headroom(m, st, p, t) : 0.5;
    var S = W.rWaste === 'cap' ? 1 - clamp(p.efflM3 / 24, 0, 1) : 0.5;
    var D = slack < 0 ? W.delayScale * (l.penalty || 0) * (-slack) / 2.4e6 : 0;
    return { slackDays: slack, cleanMin: cm, parts: { dates: W.dates * U / 100, delay: W.dates * D / 100, profit: W.profit * P / 100,
             clean: W.clean * C / 100, util: W.util * V / 100, waste: W.waste * S / 100 },
             total: (W.dates * (U + D) + W.profit * P + W.clean * C + W.util * V + W.waste * S) / 100 + (l.rush ? 6 : 0), rush: !!l.rush };
  };

  E.stats = { chains: 0, fails: 0, idles: 0, iter: 0, waits: 0, waitMin: 0, failBy: {} };
  E.resetStats = function () { E.stats = { chains: 0, fails: 0, idles: 0, iter: 0, waits: 0, waitMin: 0, failBy: {} }; };
  function run(m, st, until, W, phase, ctx) {
    var nP = m.P.length;
    for (var guard = 0; guard < 300000; guard++) {
      E.stats.iter++;
      // the frontier: the earliest moment any unit that can START a route is free
      var ui = -1, tf = Infinity;
      for (var i = 0; i < m.U.length; i++) {
        if (!ctx.starts[i]) continue;
        if (st.free[i] < until && st.free[i] < tf) { tf = st.free[i]; ui = i; }
      }
      if (ui < 0) break;
      var t = Math.max(tf, 0);
      /* Every unit free at the frontier is a real option, and eligibility here is narrow enough that the one which
         happens to free first may not be able to make what is due. Score the best candidate on each and take the best
         pair — same rules, same weights, just not blind to the other units. */
      var opts = [];
      for (var q = 0; q < m.U.length; q++) {
        if (!ctx.starts[q] || st.free[q] > t + 120 || st.free[q] >= until) continue;
        var topSc = -1e9;
        for (var z = 0; z < st.lineOrder.length; z++) {
          var Lz = st.lines[st.lineOrder[z]];
          if (!Lz.released || Lz.rem <= 0) continue;
          var pz = m.P[Lz.l.pix];
          if (pz.ops[0].units.indexOf(q) < 0) continue;
          if (cleanMinFor(m, st, q, pz, W) < 0) continue;
          if (st.last[q] === pz.ix && st.camp[q] >= (+m.campaign.forcedBreakAfter || 9)) continue;
          var sc = score(m, st, Lz, t, W, q);
          if (sc > topSc) topSc = sc;
        }
        if (topSc > -1e8) opts.push({ ui: q, sc: topSc });
      }
      if (opts.length) {
        opts.sort(function (a, b) { return b.sc - a.sc || st.free[a.ui] - st.free[b.ui] || a.ui - b.ui; });
        ui = opts[0].ui;
        t = Math.max(st.free[ui], t);
      }
      advance(m, st, t, W, ctx);
      pullForCampaign(m, st, ui, t);
      if (W.rClean === 'matrix' && t > (st.ahT || -1)) { st.ahT = t; cleanAhead(m, st, t, W, ctx); }

      // candidates: released demand this unit can start, best score first
      var cands = gather(m, st, ui, t, W);
      if (!cands.length) { st.free[ui] = nextEvent(m, st, t); E.stats.idles++; continue; }
      cands.sort(function (a, b) { return b._sc - a._sc || a.l.due - b.l.due || cmpId(a.l.id, b.l.id); });

      var done = false, best = null, cand = [];
      for (var c = 0; c < cands.length && !done && c < PROBE; c++) {
        var Lc = cands[c], pc = m.P[Lc.l.pix];
        E.stats.chains++;
        var r = planChain(m, st, pc, t, W, ui);
        if (!r.ok) {
          E.stats.fails++;
          cand.push({ L: Lc, tStar: r.tStar, fail: r.fail, p: pc });
          continue;
        }
        var b = commitChain(m, st, pc, r, W, phase, ctx);
        allocateBatch(m, st, b, Lc, W);
        done = true;
      }
      /* Nothing can START at t — usually because a downstream unit is busy and the hold window will not stretch. Wait
         for the moment a train DOES fit and run it there. Which train to wait for matters: waiting for whichever fits
         SOONEST fills the unit but lets committed dates slip, so among the trains that fit soon enough to be worth
         waiting for, take the one the objective ranks highest. Only if none is close does the soonest win.
         The idle time is recorded as a sacrifice — it is the aware plan's visible cost of obeying chemistry. */
      if (!done && cand.length) {
        var soon = cand.filter(function (x) { return x.tStar <= t + 720; });
        if (soon.length) { soon.sort(function (a, b) { return b.L._sc - a.L._sc || a.tStar - b.tStar || cmpId(a.L.l.id, b.L.l.id); }); best = soon[0]; }
        else { cand.sort(function (a, b) { return a.tStar - b.tStar || b.L._sc - a.L._sc || cmpId(a.L.l.id, b.L.l.id); }); best = cand[0]; }
      }
      if (!done && best && best.tStar > t && best.tStar < until) {
        var ts = best.tStar;
        for (var k2 = 0; k2 < 8 && !done && ts < until; k2++) {
          E.stats.chains++;
          var r2 = planChain(m, st, best.p, ts, W, ui);
          if (r2.ok) {
            var idle = r2.s - (r2.place[0].clean || 0) - t;
            E.stats.waits++; E.stats.waitMin += Math.max(0, idle);
            if (idle > 60 && W.rHold === 'window') recordSacrifice(m, st, ui, t, r2.s, best, idle);
            var b2 = commitChain(m, st, best.p, r2, W, phase, ctx);
            allocateBatch(m, st, b2, best.L, W);
            done = true;
          } else {
            E.stats.fails++;
            if (!(r2.tStar > ts)) break;      // not converging: leave it for the next decision
            ts = r2.tStar;
          }
        }
      }
      if (!done) { st.free[ui] = Math.max(t + 30, Math.min(best ? best.tStar : Infinity, nextEvent(m, st, t), t + 360)); E.stats.idles++; }
    }
    advance(m, st, until, W, ctx);
  }
  /* Schedule a clean-down into the plan, ahead of the work that needs it.

     Why this is necessary rather than tidy: a filter needs a 16 h boil-out between a deep product and a pale one, but the
     pale product's slurry may only stand for 12 h. Attach that clean to the batch and the link can never be made — the
     clean eats the hold window. A plant does not work that way: it cleans the filter down while the reactor is still
     running, as a scheduled job. So does this.

     It cannot thrash, because of the rule it uses: a unit is only cleaned ahead when NOTHING waiting can use it as it
     stands. Once cleaned, the product it was cleaned for can use it, so the condition is false next time.  */
  function cleanAhead(m, st, t, W, ctx) {
    var nP = m.P.length;
    for (var ui = 0; ui < m.U.length; ui++) {
      if (ctx.starts[ui] || st.last[ui] < 0) continue;      // a route's first operation cleans inside its own chain
      var fr = st.free[ui];
      if (fr > t + 2880) continue;                          // too far out to be worth committing a clean to
      var cls = m.U[ui].cls, best = null, bestSc = -1e9, bestCm = 0, usable = false;
      for (var k = 0; k < st.lineOrder.length && !usable; k++) {
        var L = st.lines[st.lineOrder[k]];
        if (!L.released || L.rem <= 0) continue;
        var p = m.P[L.l.pix], uses = false;
        for (var i = 0; i < p.ops.length; i++) if (p.ops[i].cls === cls && p.ops[i].units.indexOf(ui) >= 0) { uses = true; break; }
        if (!uses) continue;
        var cm = cleanMinFor(m, st, ui, p, W);
        if (cm === 0) { usable = true; break; }              // something waiting can run here as it stands: leave it
        if (cm < 0) continue;
        if (cm < (m.grades.WASH || 6) * 60) continue;         // a rinse fits inside a hold window; no need to plan it
        var sc = score(m, st, L, Math.max(t, fr), W, null);
        if (sc > bestSc) { bestSc = sc; best = p; bestCm = cm; }
      }
      if (usable || !best) continue;
      var s0 = blocked(m, ui, Math.max(t, fr), bestCm);
      st.cleans.push({ unit: m.U[ui].id, uix: ui, s: s0, e: s0 + bestCm, min: bestCm, phase: 'P', ahead: true,
                       grade: m.cleanGrade[st.last[ui] * nP + best.ix], frm: m.P[st.last[ui]].id, to: best.id, batch: null,
                       why: 'cleaned down ahead of the ' + best.id + ' campaign: nothing waiting could use ' + m.U[ui].id + ' as it stood' });
      st.free[ui] = s0 + bestCm; st.cleanFor[ui] = best.ix;
    }
  }
  var PROBE = 60;                     // candidates probed per decision. The score has already ranked them, but a
                                      // chemical plant narrows eligibility so hard that a shallow probe starves units.
  function recordSacrifice(m, st, ui, t, startedAt, best, idle) {
    var f = best.fail || {}, op = f.op;
    st.sacrifices.push({ unit: m.U[ui].id, uix: ui, s: t, e: startedAt, min: idle, productId: best.p.id,
                         lineId: best.L.l.id, nuance: f.ix > 0 ? 'P3' : 'P4', why: f.why || 'nothing could start here',
                         text: m.U[ui].id + ' idled ' + Math.round(idle / 60) + ' h before starting ' + best.p.id +
                               (op && f.ix > 0 ? ': beginning it any earlier would have left ' + op.label.toLowerCase() +
                                ' more than ' + op.maxLagH + ' h after the stage before it, past the hold window'
                                       : ': no eligible unit could take it any sooner') });
  }
  function nextEvent(m, st, t) {
    var n = t + 240;
    if (st.relIdx < st.pend.length && st.pend[st.relIdx][0] > t) n = Math.min(n, st.pend[st.relIdx][0]);
    if (st.delIdx < st.delQ.length && st.delQ[st.delIdx].at > t) n = Math.min(n, st.delQ[st.delIdx].at);
    return Math.max(n, t + 30);
  }
  // a committed batch pays down the line that triggered it; the campaign keeps running while that line still wants kg
  function allocateBatch(m, st, b, L, W) {
    // the campaign runs while the line still WANTS kg; what it is credited with is the planning basis, and what it
    // actually gets is the physical output. Those two are the same number only under the aware rule set.
    L.rem = Math.max(0, L.rem - Math.min(L.rem, b.booked));
    L.made += b.kg; L.nominal += b.nominalKg; L.booked = (L.booked || 0) + b.booked;
    L.batches.push(b.id); b.lineIds.push(L.l.id);
    if (L.firstStart == null) L.firstStart = b.s;
    L.lastEnd = Math.max(L.lastEnd || 0, b.readyAt);
  }

  // =====================================================================================================================
  // PUBLIC — history, weights, plan
  // =====================================================================================================================
  function context(m) {
    var starts = new Int8Array(m.U.length);
    m.P.forEach(function (p) { p.ops[0].units.forEach(function (ui) { starts[ui] = 1; }); });
    return { starts: starts };
  }
  E.history = function (m) {
    var st = newState(m), ctx = context(m), W = E.weightsFor(m, { preset: 'balanced' });
    W = Object.assign({}, W, E.RULES.generic, { id: 'generic', key: 'hist' });
    run(m, st, m.asOf, W, 'H', ctx);
    E.settleTanks(m, st, W);
    return { state: cloneState(m, st), batches: st.batches.slice(), cleans: st.cleans.slice(), refused: st.refused.slice() };
  };
  E.weightsFor = function (m, s) {
    s = s || {};
    var pr = m.presets[s.preset || 'balanced'] || m.presets.balanced || {};
    var w = s.preset === 'custom' && s.weights ? s.weights : pr;
    var W = { preset: s.preset || 'balanced', dates: +w.dates || 0, profit: +w.profit || 0, clean: +w.clean || 0,
              util: +w.util || 0, waste: +w.waste || 0, delayScale: w.delayScale != null ? +w.delayScale : 1 };
    W.wkey = [W.dates, W.profit, W.clean, W.util, W.waste, W.delayScale].join('|');
    return W;
  };

  /* One plan. `settings` = { preset, weights, rules: 'aware'|'generic', assume: ['clean',...], whatifs: [...] }.
     The SAME weights are used for both rule sets — the comparison is about rules, never about priorities. */
  E.plan = function (m, hist, settings) {
    settings = settings || {};
    var t0 = Date.now(), st = cloneState(m, hist.state), ctx = context(m);
    var R = E.rulesFor(settings.rules === 'aware' ? 'aware' : 'generic', settings.assume);
    var W = Object.assign({}, E.weightsFor(m, settings), R);
    W.key = [W.wkey, R.id].join('#');
    m.lines.forEach(function (l) { if (!st.lines[l.id]) { addLine(m, st, l); } else { st.lines[l.id].l = l; } });
    var wi = applyWhatifs(m, st, settings.whatifs || [], W), res;
    sortPend(st);
    try {
      run(m, st, m.end, W, 'P', ctx);
      E.settleTanks(m, st, W);
      res = E.assemble(m, hist, st, W, settings);
    } finally {
      // the model is cached and shared: put back everything the what-ifs changed, or they outlive this plan
      for (var u = wi.undo.length - 1; u >= 0; u--) wi.undo[u]();
    }
    res.applied = wi.applied; res.rules = R; res.ms = Date.now() - t0;
    return res;
  };

  /* Apply the live-demo what-ifs.

     Several of these change the MODEL (a utility cap, a hold window, a licensed quantity), and the model is cached and
     shared between plans — so each one also records how to put it back, and E.plan restores them when the plan is done.
     Without that, a what-if would survive Reset demo and quietly poison every later plan. */
  function applyWhatifs(m, st, list, W) {
    var out = [], undo = [];
    function setCap(ui, from, cap) {
      var old = [];
      for (var h = from; h < m.H; h++) { old.push(m.utilCap[ui * m.H + h]); m.utilCap[ui * m.H + h] = Math.min(m.utilCap[ui * m.H + h], cap); }
      undo.push(function () { for (var h = from, i = 0; h < m.H; h++, i++) m.utilCap[ui * m.H + h] = old[i]; });
    }
    list.forEach(function (w) {
      if (w.type === 'rush' && w.line && m.pix[w.line.productId] != null) {
        var L = E.mkLine(m, w.line, w.line); L.rush = true; L.rel = Math.max(L.rel, m.asOf);
        if (!st.lines[L.id]) { addLine(m, st, L); out.push(w); }
      } else if (w.type === 'cancel') {
        st.lineOrder.forEach(function (id) { var L2 = st.lines[id]; if (L2.l.orderId === w.orderId) { L2.cancelled += Math.max(0, L2.released ? L2.rem : L2.l.qty); L2.rem = 0; L2.released = true; L2.whatifCancel = true; } });
        out.push(w);
      } else if (w.type === 'derate' && m.utix[w.utility] != null) {
        setCap(m.utix[w.utility], Math.floor(m.asOf / 60), +w.cap);
        out.push(w);
      } else if (w.type === 'wasteCut' && m.wix[w.waste] != null) {
        var ww = m.wastes[m.wix[w.waste]], oldCap = ww.cap;
        ww.cap = +w.cap; undo.push(function () { ww.cap = oldCap; });
        out.push(w);
      } else if (w.type === 'licenceCut' && m.hix[w.haz] != null) {
        var hz = m.hazs[m.hix[w.haz]], oldL = hz.licensedKL;
        hz.licensedKL = +w.kl; undo.push(function () { hz.licensedKL = oldL; });
        out.push(w);
      } else if (w.type === 'holdTighten' && m.pix[w.productId] != null) {
        var p = m.P[m.pix[w.productId]], op = p.ops.filter(function (o) { return o.id === w.op; })[0] || p.ops[0];
        var oM = op.maxLag, oH = op.maxLagH;
        op.maxLag = Math.round((+w.hours) * 60); op.maxLagH = +w.hours;
        undo.push(function () { op.maxLag = oM; op.maxLagH = oH; });
        out.push(w);
      } else if (w.type === 'blockUnit' && m.uix[w.unitId] != null) {
        var ui2 = m.uix[w.unitId], before = m.blocks[ui2].slice();
        m.blocks[ui2].push([m.asOf, m.asOf + (+w.hours || 24) * 60, w.reason || 'Taken out of service (what-if)', 'whatif']);
        m.blocks[ui2].sort(function (a, b) { return a[0] - b[0]; });
        undo.push(function () { m.blocks[ui2] = before; });
        out.push(w);
      } else if (w.type === 'yieldShort' && m.pix[w.productId] != null) {
        var p2 = m.P[m.pix[w.productId]], oY = p2.yieldShift;
        p2.yieldShift = +w.to; undo.push(function () { p2.yieldShift = oY; });
        out.push(w);
      } else if (w.type === 'tightSpec' && st.lines[w.lineId]) {
        var L3 = st.lines[w.lineId], pr = m.P[L3.l.pix];
        // tighten against the product's own assay distribution, so it is certain to exclude part of the lot pool
        // a null means "leave this one alone": C7 tightens impurity only, because assay cannot be blended upwards
        var amin = w.assayMin != null ? +w.assayMin : L3.l.assayMin;
        var imax = w.impMax != null ? +w.impMax : pr.impMax * 0.6;
        L3.l = Object.assign({}, L3.l, { assayMin: Math.round(amin * 100) / 100, impMax: Math.round(imax * 1000) / 1000, tightSpec: true });
        out.push(Object.assign({}, w, { assayMin: L3.l.assayMin, impMax: L3.l.impMax }));
      } else if (w.type === 'lotAge') {
        // age a lot: its retest date moves in, so a customer minimum remaining life can no longer be met from it
        var hit = false;
        st.lots.forEach(function (x) {
          if (x.id !== w.lotId) return;
          x.retestAt = m.asOf + Math.round((+w.monthsLeft || 3) * 30.4 * 1440);
          x.aged = true; hit = true;
        });
        if (hit) out.push(w);
      } else if (w.type === 'unapprove' && m.approvals[w.customerId + '|' + w.siteId]) {
        var ap = m.approvals[w.customerId + '|' + w.siteId], oA = ap.approved;
        ap.approved = false; undo.push(function () { ap.approved = oA; });
        out.push(w);
      } else if (w.type === 'mix' || w.type === 'prebuild' || w.type === 'coprodCap' || w.type === 'sourcing' || w.type === 'rmBlock' || w.type === 'pack') {
        out.push(w);     // S&OP-horizon only: read by sop(), the detailed schedule does not move
      }
    });
    return { applied: out, undo: undo };
  }


  /* Settle the tank farm in strict time order. Deliveries are accepted or refused against the level and the LICENCE as
     they actually arrive; a draw that the tank cannot cover is bought in at a premium. Authoritative: st.tankD,
     st.accepted, st.refused and st.emergency are all rebuilt here, so every later reader sees one consistent farm. */
  E.settleTanks = function (m, st, W) {
    var ev = [], i, k;
    // every delivery the calendar offers, including the two-day re-presentations a refusal creates
    var queue = m.deliveries.map(function (d) { return { t: d.at, kind: 'in', d: d, tries: 0 }; });
    // every draw and every return the committed batches make
    st.batches.forEach(function (b) {
      var p = m.P[b.pix];
      if (p.tix == null) return;
      b.ops.forEach(function (o) {
        if (!o.solvKL) return;
        ev.push({ t: o.s, kind: 'draw', tix: p.tix, kl: o.solvKL, batch: b.id, productId: p.id });
        var rate = m.recovery.min + hash01('r|' + b.id + '|' + o.seq) * (m.recovery.max - m.recovery.min);
        ev.push({ t: o.s + m.recovery.turnMin, kind: 'back', tix: p.tix, kl: o.solvKL * rate, batch: b.id });
      });
    });
    var lvl = new Float64Array(m.tanks.length);
    m.tanks.forEach(function (t) { lvl[t.ix] = t.openKL; });
    var accepted = [], refused = [], emergency = [], held = [], returns = [], delta = new Float64Array(m.tanks.length * m.Dn);
    m.tanks.forEach(function (t) { delta[t.ix * m.Dn] = t.openKL; });

    function hazNow(hix) { var v = 0; for (var q = 0; q < m.tanks.length; q++) if (m.tanks[q].hix === hix) v += lvl[q]; return v; }
    function note(e) { var d = Math.min(m.Dn - 1, Math.max(0, Math.floor(e.t / 1440))); return d; }

    // one merged, strictly time-ordered pass; a refusal re-presents itself, so the queue can grow as it is walked
    ev.sort(function (a, b) { return a.t - b.t || (a.kind < b.kind ? -1 : 1); });
    queue.sort(function (a, b) { return a.t - b.t; });
    var qi = 0, ei = 0;
    while (qi < queue.length || ei < ev.length) {
      var takeQ = qi < queue.length && (ei >= ev.length || queue[qi].t <= ev[ei].t);
      if (takeQ) {
        var q = queue[qi++], d = q.d, tk = m.tanks[d.tix];
        var noSpace = lvl[d.tix] + d.kl > tk.capKL + 1e-9;
        var overLic = hazNow(d.hix) + d.kl > m.hazs[d.hix].licensedKL + 1e-9;
        var refuse = W.rLicence === 'ceiling' ? (noSpace || overLic) : noSpace;
        if (!refuse) {
          lvl[d.tix] += d.kl; delta[d.tix * m.Dn + note(q)] += d.kl;
          accepted.push({ id: d.id, tix: d.tix, tank: tk.id, haz: d.haz, hix: d.hix, kl: d.kl, at: q.t,
                          supplier: d.supplier, priceKL: d.priceKL, tries: q.tries });
        } else {
          var tries = q.tries + 1;
          refused.push({ id: d.id, tank: tk.id, haz: d.haz, kl: d.kl, at: q.t, level: Math.round(lvl[d.tix] * 10) / 10,
                         hazPos: Math.round(hazNow(d.hix) * 10) / 10, licensed: m.hazs[d.hix].licensedKL, tries: tries,
                         reason: overLic && W.rLicence === 'ceiling' ? 'licence' : 'tank full', overLicence: overLic,
                         requeued: tries <= 4 });
          if (tries <= 4) {
            var again = { t: q.t + 2880, kind: 'in', d: d, tries: tries }, at = qi;
            while (at < queue.length && queue[at].t <= again.t) at++;
            queue.splice(at, 0, again);
          }
        }
        continue;
      }
      var e = ev[ei++];
      if (e.kind === 'back') {
        // Recovered solvent only returns as far as the tank and the licence allow. The surplus stays in the recovery
        // train as intermediate-grade stock -- it does not vanish, and it does not overflow a licensed store either.
        var room = m.tanks[e.tix].capKL - lvl[e.tix];
        if (W.rLicence === 'ceiling') room = Math.min(room, m.hazs[m.tanks[e.tix].hix].licensedKL - hazNow(m.tanks[e.tix].hix));
        var back = Math.max(0, Math.min(e.kl, room));
        if (back > 0) { lvl[e.tix] += back; delta[e.tix * m.Dn + note(e)] += back; returns.push({ at: e.t, tix: e.tix, kl: back, batch: e.batch }); }
        if (back < e.kl - 1e-9) held.push({ at: e.t, tank: m.tanks[e.tix].id, kl: Math.round((e.kl - back) * 100) / 100, batch: e.batch });
        continue;
      }
      if (lvl[e.tix] < e.kl - 1e-9) {                 // the tank cannot cover the charge: buy it in, at a premium
        var buy = Math.ceil((e.kl - Math.max(0, lvl[e.tix])) * 10) / 10;
        lvl[e.tix] += buy; delta[e.tix * m.Dn + note(e)] += buy;
        emergency.push({ at: e.t, tank: m.tanks[e.tix].id, solventId: m.tanks[e.tix].solventId, kl: buy, batch: e.batch,
                         productId: e.productId, rupees: Math.round(buy * m.tanks[e.tix].priceKL * 1.35),
                         why: 'the tank could not cover the charge, so ' + buy + ' kL was bought in at a premium' });
      }
      lvl[e.tix] -= e.kl; delta[e.tix * m.Dn + note(e)] -= e.kl;
    }
    st.tankD = delta;            // tankPos() now reads the settled farm, opening level included
    st.tankOpenInDelta = true;
    st.accepted = accepted; st.refused = refused; st.emergency = emergency; st.heldInRecovery = held; st.returns = returns;
    return { accepted: accepted, refused: refused, emergency: emergency, held: held, returns: returns };
  };

  E.hash01 = hash01;
  E.gauss = gauss;
  E.cloneState = cloneState;
  E.newState = newState;
  E.context = context;
  E.runLoop = run;
  E.planChain = planChain;
  E.cleanMinFor = cleanMinFor;
  E.tankPos = tankPos;
  E.hazPos = hazPos;
  E.blockedAt = blocked;

  // assemble, allocation, consequence, repair, proof and sop live in chm-results.js (loaded straight after this)
  root.CHMEngine = E;
})(typeof window !== 'undefined' ? window : globalThis);
