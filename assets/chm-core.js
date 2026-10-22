/* Bluemingo PP — shared page runtime over window.CHM (data/chm-data.js), CHMEngine (chm-engine.js + chm-results.js) and
   CHM_NUANCES (chm-nuances.js).

   ONE BASIS: every page reads the same comparison. Inside the tab host (index.html) it is computed once by the host and
   every tab reads that result; a page opened on its own computes it itself. The live-demo state — objective weights, the
   assumption ratchet, what-ifs, the role toggle, Master Data uploads — lives in localStorage, so an action on one page is
   the plan on every page, and Reset demo clears it.

   Also here: formatting with the BASIS of every quantity attached, the validated data palette, the busy overlay, a
   minute-based Gantt with a window pager, Excel export, the nuance registry helpers, and the scenario launcher. */
(function () {
  var D = window.CHM, E = window.CHMEngine, NU = window.CHM_NUANCES;
  if (!D || !E || !NU) { console.error('CHM data / engine / nuances not loaded'); return; }
  var BASE = new Date(D.meta.base), ASOF = D.meta.asOfMinute, END = D.meta.endMinute;
  var WD = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'], MO = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  function pad(n) { return (n < 10 ? '0' : '') + n; }

  // ---------------------------------------------------------------- time (engine minutes from the start of history)
  function dateOf(min) { return new Date(BASE.getTime() + min * 60000); }
  function minOf(iso) { return Math.round((new Date(iso) - BASE) / 60000); }
  function fmt(min) { if (min == null) return '—'; var d = dateOf(min); return WD[d.getDay()] + ' ' + d.getDate() + ' ' + MO[d.getMonth()] + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes()); }
  function fmtD(min) { if (min == null) return '—'; var d = dateOf(min); return WD[d.getDay()] + ' ' + d.getDate() + ' ' + MO[d.getMonth()]; }
  function fmtDM(min) { if (min == null) return '—'; var d = dateOf(min); return d.getDate() + ' ' + MO[d.getMonth()]; }
  function fmtT(min) { if (min == null) return '—'; var d = dateOf(min); return pad(d.getHours()) + ':' + pad(d.getMinutes()); }
  function isoLocal(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + 'T' + pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds()); }
  function dur(mn) { mn = Math.round(mn); if (mn < 60) return mn + ' min'; var h = Math.floor(mn / 60), m = mn % 60; return h + ' h' + (m ? ' ' + m + ' m' : ''); }
  function hrs(mn) { return (mn / 60).toFixed(mn % 60 ? 1 : 0) + ' h'; }
  function days(mn) { return (mn / 1440).toFixed(1) + ' d'; }
  function shiftOf(min) { var h = dateOf(min).getHours(); return h >= 6 && h < 14 ? 'A' : h >= 14 && h < 22 ? 'B' : 'C'; }
  function monthOf(min) { var d = dateOf(min); return d.getFullYear() + '-' + pad(d.getMonth() + 1); }

  // ---------------------------------------------------------------- numbers and text
  // Every quantity carries its basis. kg of product is not kg on 100% assay, and an hour of a unit is not an hour of the
  // bottleneck; the formatters make that explicit so no page can quietly mix them.
  function n(x, d) { if (x == null || isNaN(x)) return '—'; return Number(x).toLocaleString('en-IN', { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 }); }
  function kg(x, d) { return n(x, d) + ' kg'; }
  function t(x, d) { return n(x / 1000, d == null ? 1 : d) + ' t'; }
  function kl(x, d) { return n(x, d == null ? 1 : d) + ' kL'; }
  function m3(x, d) { return n(x, d == null ? 1 : d) + ' m³'; }
  function assay(x) { return x == null ? '—' : Number(x).toFixed(2) + '%'; }
  function pct(x, d) { return x == null || isNaN(x) ? '—' : (x * 100).toFixed(d == null ? 1 : d) + '%'; }
  function rs(x) { if (x == null || isNaN(x)) return '—'; var a = Math.abs(x); return (x < 0 ? '−' : '') + '₹' + (a >= 1e7 ? (a / 1e7).toFixed(2) + ' Cr' : a >= 1e5 ? (a / 1e5).toFixed(1) + ' L' : n(a)); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  var CLS_LABEL = { EXPORT_REG: 'Regulated export', EXPORT: 'Export', DOM_COMMITTED: 'Committed domestic', DOM_OPEN: 'Open domestic' };
  function cls(c, rush) { return '<span class="cls cls-' + (rush ? 'RUSH' : c) + '">' + esc(rush ? 'Rush' : CLS_LABEL[c] || c) + '</span>'; }
  // Equipment classes read as shouting in a sentence or a KPI label, so they get written out. Anything not listed falls
  // back to its own id with the first letter capitalised rather than to nothing.
  var EQ_LABEL = { REACTOR: 'Reactor', ISOLATION: 'Isolation', DRYER: 'Drying', MILL: 'Milling', PACK: 'Packing' };
  function clsName(c) {
    if (!c) return '';
    return CLS_LABEL[c] || EQ_LABEL[c] || (String(c).charAt(0) + String(c).slice(1).toLowerCase());
  }
  var BADGE = { 'Shipped': 'b-green', 'On track': 'b-green', 'Late': 'b-red', 'Short': 'b-amber', 'Not in horizon': 'b-red',
                'Beyond horizon': 'b-grey', 'Cancelled': 'b-grey', 'Released': 'b-green', 'Awaiting QC': 'b-blue', 'Planned': 'b-grey' };
  function badge(s, label) { return '<span class="badge ' + (BADGE[s] || 'b-grey') + '">' + esc(label || s) + '</span>'; }
  function toast(msg, icon) { var x = document.createElement('div'); x.className = 'toast'; x.innerHTML = '<i class="fa-solid ' + (icon || 'fa-circle-check') + '"></i><span>' + msg + '</span>'; document.body.appendChild(x); setTimeout(function () { x.remove(); }, 4600); }
  function prov(label, where) { return '<span class="prov" title="' + esc(where) + '">' + esc(label) + '</span>'; }

  // ---------------------------------------------------------------- colour roles (validated: dataviz reference palette)
  // Categorical — product family (4 slots, all pairs separated). Clean grades — an ordinal ramp, light to dark, because
  // the grades ARE ordered. Status — the design system's reserved steps, always shown with a label.
  var COLOR = {
    fam: { F1: '#2a78d6', F2: '#eb6834', F3: '#1baf7a', F4: '#8e44ad' },
    grade: { NONE: '#e8f5e9', RINSE: '#a8d5ba', WASH: '#5598e7', BOILOUT: '#1c5cab', DEDICATE: '#4a148c', FORBIDDEN: '#b71c1c' },
    rules: { aware: '#25A9E0', generic: '#9e9e9e' },
    util: { STEAM: '#eb6834', BRINE: '#2a78d6', CHW: '#5598e7', VAC: '#8e44ad', N2: '#1baf7a' },
    status: { good: '#388e3c', warning: '#f57c00', serious: '#e65100', critical: '#d32f2f', neutral: '#9e9e9e', hist: '#bdbdbd' },
    accent: '#2a78d6', primary: '#25A9E0', ink: '#333333'
  };
  function textOn(hex) { var h = String(hex || '#999').replace('#', ''), r = parseInt(h.substr(0, 2), 16), g = parseInt(h.substr(2, 2), 16), b = parseInt(h.substr(4, 2), 16); return (0.2126 * r + 0.7152 * g + 0.0722 * b) > 130 ? '#333333' : '#ffffff'; }

  // ---------------------------------------------------------------- live-demo state (per browser)
  var KEY = 'chm-demo-state';
  var State = {
    all: function () { try { return JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { return {}; } },
    get: function (k, d) { var a = State.all(); return k in a ? a[k] : d; },
    set: function (k, v) { var a = State.all(); a[k] = v; try { localStorage.setItem(KEY, JSON.stringify(a)); } catch (e) {} return v; },
    reset: function () { try { localStorage.removeItem(KEY); } catch (e) {} }
  };
  window.CHMState = State;
  function settings() {
    var p = State.get('plan', { preset: 'balanced' });
    return { preset: p.preset || 'balanced', weights: p.weights || null, assume: State.get('assume', []), whatifs: State.get('whatifs', []) };
  }
  function role() { return State.get('role', 'both'); }
  function mastersOverlay() { return State.get('masters', {}); }

  // ---------------------------------------------------------------- ONE basis: host-shared engine results
  var isHost = !!window.CHM_IS_HOST;
  function hostX() { try { if (!isHost && window.parent !== window && window.parent.CHMX && window.parent.CHMX.isHost) return window.parent.CHMX; } catch (e) {} return null; }
  var C = { hist: null, models: {}, plans: {}, order: [] };
  function modelFor(ovKey, ov) { if (!C.models[ovKey]) C.models[ovKey] = E.prepare(D, ov); return C.models[ovKey]; }
  function histOf() { if (!C.hist) C.hist = E.history(modelFor('{}', {})); return C.hist; }
  function planKey(st, ovKey) { return JSON.stringify([st.preset, st.preset === 'custom' ? st.weights : null, st.assume, st.whatifs, ovKey]); }
  function computeLocal(st) {
    var ov = mastersOverlay(), ovKey = JSON.stringify(ov), k = planKey(st, ovKey);
    if (C.plans[k]) return C.plans[k];
    var m = modelFor(ovKey, ov);
    var r = E.compare(m, ovKey === '{}' ? histOf() : E.history(m), st);
    r.key = k; r.m = m; C.plans[k] = r; C.order.push(k);
    // Plan Studio holds two plans live, a scenario its before and after, and the ratchet one per assumption: keep 16.
    while (C.order.length > 16) delete C.plans[C.order.shift()];
    return r;
  }
  function cached(st) { var h = hostX(); if (h) return h._cached(st); var ov = mastersOverlay(); return C.plans[planKey(st, JSON.stringify(ov))] || null; }
  function compute(st) { var h = hostX(); return h ? h._compute(st) : computeLocal(st); }

  function busy(on, msg) {
    var o = document.getElementById('chm-busy');
    if (!on) { if (o) o.remove(); return; }
    if (!o) { o = document.createElement('div'); o.id = 'chm-busy'; o.style.cssText = 'position:fixed;inset:0;background:rgba(244,245,247,.72);z-index:9998;display:flex;align-items:center;justify-content:center'; document.body.appendChild(o); }
    o.innerHTML = '<div style="background:var(--color-surface);border:1px solid var(--color-border);border-radius:var(--radius-lg);padding:16px 22px;box-shadow:var(--shadow-lg);display:flex;gap:12px;align-items:center;font-size:13px">' +
      '<i class="fa-solid fa-gear fa-spin" style="color:var(--color-primary);font-size:18px"></i><div><b>' + esc(msg || 'Planning') + '</b>' +
      '<div class="hint" style="font-size:11px;margin-top:2px">' + D.m.units.length + ' units · ' + D.meta.forwardDays + ' days · both rule sets, then the consequences</div></div></div>';
  }
  // Get the comparison for the current settings and hand it to cb (at once if cached, else after the overlay has painted)
  function withPlan(cb, st, msg) {
    st = st || settings();
    var r = cached(st);
    if (r) { cb(r); return; }
    busy(true, msg || 'Planning the plant, both ways');
    setTimeout(function () { var t0 = Date.now(), res; try { res = compute(st); } finally { busy(false); } res.wallMs = Date.now() - t0; cb(res); }, 30);
  }
  function whenPlanChanges(fn) {
    window.addEventListener('chm:planchanged', function () { withPlan(fn); });
    window.addEventListener('storage', function (e) { if (e.key === KEY) withPlan(fn); });
  }
  function replan(mutate, msg, cb) {
    mutate();
    headerMode();
    withPlan(function (r) {
      try { if (window.parent !== window && window.parent.CHMHost) window.parent.CHMHost.planChanged(window); } catch (e) {}
      if (cb) cb(r);
    }, null, msg || 'Re-planning');
  }
  function go(id, hash) {
    try { if (window.parent !== window && window.parent.CHMHost) { window.parent.CHMHost.open(id, hash || ''); return; } } catch (e) {}
    location.href = id + '.html' + (hash ? '#' + hash : '');
  }
  function addWhatif(w) { var list = State.get('whatifs', []); w.id = w.id || (w.type + '-' + Date.now()); list.push(w); State.set('whatifs', list); return w; }
  function removeWhatif(id) { State.set('whatifs', State.get('whatifs', []).filter(function (w) { return w.id !== id; })); }
  function whatifLabel(w) {
    var u = byId.utils[w.utility], ws = byId.wastes[w.waste], hz = byId.hazs[w.haz];
    return w.type === 'rush' ? 'Rush order ' + w.line.id + ' for ' + custName(w.line.customerId)
      : w.type === 'cancel' ? 'Order ' + w.orderId + ' cancelled'
      : w.type === 'derate' ? (u ? u.name : w.utility) + ' derated to ' + w.cap + ' ' + (u ? u.unit : '')
      : w.type === 'wasteCut' ? (ws ? ws.name : w.waste) + ' cut to ' + w.cap + ' ' + (ws ? ws.unit : '')
      : w.type === 'licenceCut' ? (hz ? hz.name : w.haz) + ' licence cut to ' + w.kl + ' kL'
      : w.type === 'holdTighten' ? 'Hold window on ' + w.op + ' tightened to ' + w.hours + ' h'
      : w.type === 'blockUnit' ? w.unitId + ' out of service for ' + (w.hours || 24) + ' h'
      : w.type === 'yieldShort' ? w.productId + ' yield down to ' + pct(w.to)
      : w.type === 'tightSpec' ? 'Spec on ' + w.lineId + ' tightened to ' + assay(w.assayMin) + ' assay'
      : w.type === 'mix' ? 'Mix shifted ' + pct(w.shift, 0) + ' from ' + w.fromProduct + ' to ' + w.toProduct
      : w.type === 'unapprove' ? w.customerId + ' loses its approval for ' + w.siteId
      : w.type === 'lotAge' ? 'Lot ' + w.lotId + ' aged to ' + w.monthsLeft + ' months left'
      : w.type === 'prebuild' ? 'Pre-build ahead of the ' + w.month + ' shutdown'
      : w.type === 'sourcing' ? w.productId + ' sourced by ' + w.mode
      : w.type === 'rmBlock' ? 'Raw-material block booked for ' + w.rmId
      : w.type === 'pack' ? w.productId + ' held as bulk, packed to order'
      : w.type === 'coprodCap' ? 'Co-product ceiling cut to ' + w.kl + ' kL'
      : w.type;
  }

  // ---------------------------------------------------------------- lookups (base masters; uploads are seen via the model)
  var byId = {};
  function index(name, rows, key) { byId[name] = {}; (rows || []).forEach(function (r) { byId[name][r[key || 'id']] = r; }); }
  index('products', D.m.products); index('units', D.m.units); index('utils', D.m.utilities); index('wastes', D.m.waste);
  index('hazs', D.m.hazardClasses); index('bunds', D.m.bunds); index('tanks', D.m.tanks); index('customers', D.m.customers);
  index('grades', D.m.cleanGrades); index('families', D.m.families); index('orders', D.orders); index('lines', D.lines);
  index('sites', D.m.sites); index('raws', D.m.rawMaterials); index('oclass', D.m.orderClasses); index('lots', D.m.openingLots);
  function product(id) { return byId.products[id] || { id: id, name: id, family: 'F1' }; }
  function pname(id) { var p = byId.products[id]; return p ? p.id + ' · ' + p.name : id; }
  function unit(id) { return byId.units[id] || { id: id, name: id, cls: '' }; }
  function custName(id) { return (byId.customers[id] || {}).name || id || 'Stock'; }
  function famName(id) { return (byId.families[id] || {}).name || id; }
  function famColor(id) { return COLOR.fam[id] || COLOR.status.neutral; }
  function gradeName(id) { return (byId.grades[id] || {}).name || id; }
  function gradeHours(id) { var g = byId.grades[id]; return g && g.hours != null ? g.hours : null; }

  // ---------------------------------------------------------------- the nuance registry
  function nu(id) { return window.CHM_NU[id] || null; }
  function nuLabel(id) { return window.CHM_NU_LABEL(id); }
  function nuChip(id, extra) {
    var x = nu(id); if (!x) return '';
    return '<span class="nuchip ' + (x.grp === 'sop' ? 'sop' : '') + '" title="' + esc(x.claim) + '">' +
           '<i class="fa-solid ' + x.icon + '"></i>' + esc((x.grp === 'plant' ? 'Plant ' : 'S&OP ') + x.no) + ' · ' + esc(x.name) +
           (extra ? ' <b>' + esc(extra) + '</b>' : '') + '</span>';
  }
  function nuOf(page) { return NU.filter(function (x) { return x.page === page; }); }

  // ---------------------------------------------------------------- header chips
  function headerMode() {
    var st = settings(), el = document.getElementById('chm-mode'), a = document.getElementById('chm-asof');
    var pr = (D.m.weights || []).filter(function (w) { return w.id === st.preset; })[0];
    var label = st.preset === 'custom' ? 'Custom weights' : pr ? pr.label : st.preset;
    var extra = (st.whatifs.length ? ' · <b>' + st.whatifs.length + '</b> what-if' + (st.whatifs.length > 1 ? 's' : '') : '') +
                (st.assume.length ? ' · <b>' + st.assume.length + '</b> assumption' + (st.assume.length > 1 ? 's' : '') + ' on' : '');
    if (el) el.innerHTML = '<i class="fa-solid fa-sliders" style="margin-right:4px;color:var(--color-primary-light)"></i>Plan: <b>' + esc(label) + '</b>' + extra;
    if (a) a.innerHTML = '<i class="fa-regular fa-clock"></i> as of ' + fmt(ASOF) + ' · Shift ' + shiftOf(ASOF);
    paintRoles();
  }
  function paintRoles() {
    var host = document.getElementById('chm-roles');
    if (!host) return;
    var r = role();
    host.innerHTML = (window.CHM_ROLES || []).map(function (x) { return '<button data-role="' + x[0] + '" class="' + (x[0] === r ? 'on' : '') + '">' + x[1] + '</button>'; }).join('');
    if (!host._wired) {
      host._wired = true;
      host.addEventListener('click', function (e) {
        var b = e.target.closest('button[data-role]'); if (!b) return;
        State.set('role', b.getAttribute('data-role'));
        paintRoles();
        if (window.CHM_paintNav) window.CHM_paintNav(role());
        try { if (window.parent !== window && window.parent.CHMHost) window.parent.CHMHost.roleChanged(); } catch (err) {}
        window.dispatchEvent(new Event('chm:rolechanged'));
      });
    }
    if (window.CHM_paintNav) window.CHM_paintNav(r);
  }

  // ---------------------------------------------------------------- Gantt (minutes) + window pager
  function gantt(el, lanes, bars, opts) {
    opts = opts || {};
    var laneW = opts.laneW || 150, s0 = opts.startMin != null ? opts.startMin : ASOF, e0 = opts.endMin != null ? opts.endMin : END, span = Math.max(60, e0 - s0);
    var avail = Math.max(300, (el.clientWidth || 1200) - laneW - 4), px = avail / span, W = Math.round(span * px);
    function x(mn) { return Math.round((mn - s0) * px); }
    var step = span > 20 * 1440 ? 1440 : span > 4 * 1440 ? 720 : span > 1440 ? 360 : 120, grid = '', head = '';
    for (var tt = Math.ceil(s0 / step) * step; tt <= e0; tt += step) grid += '<div class="g-grid' + (tt % 1440 === 0 ? ' day' : '') + '" style="left:' + x(tt) + 'px"></div>';
    var nd = Math.ceil(span / 1440), every = Math.max(1, Math.ceil(nd / 16));
    for (var d = Math.floor(s0 / 1440), k = 0; d * 1440 < e0; d++, k++) {
      if (k % every) continue;
      var mid = Math.max(s0, d * 1440) + (Math.min(e0, (d + 1) * 1440) - Math.max(s0, d * 1440)) / 2;
      head += '<div class="g-day" style="left:' + x(mid) + 'px">' + WD[dateOf(d * 1440).getDay()] + '<span class="dm">' + fmtDM(d * 1440) + '</span></div>';
    }
    if (span <= 1440 * 1.01) for (var hh = Math.ceil(s0 / 240) * 240; hh < e0; hh += 240) head += '<div class="g-day" style="left:' + x(hh) + 'px;top:18px;font-weight:400;color:#9e9e9e">' + fmtT(hh) + '</div>';
    var now = ASOF >= s0 && ASOF <= e0 ? '<div class="g-now" style="left:' + x(ASOF) + 'px"></div>' : '';
    var html = '<div class="g-row head"' + (span <= 1440 * 1.01 ? ' style="min-height:40px"' : '') + '><div class="g-lane head-lane" style="width:' + laneW + 'px">' + esc(opts.laneTitle || 'Unit') + '</div><div class="g-track" style="min-width:' + W + 'px">' + grid + head + now + '</div></div>';
    var byLane = {}; bars.forEach(function (b) { (byLane[b.lane] = byLane[b.lane] || []).push(b); });
    lanes.forEach(function (ln) {
      var bs = (byLane[ln.id] || []).map(function (b) {
        if (b.e <= s0 || b.s >= e0) return '';
        var l = x(Math.max(b.s, s0)), w = Math.max(2, x(Math.min(b.e, e0)) - l);
        return '<div class="g-bar ' + (b.cls || '') + '" style="left:' + l + 'px;width:' + w + 'px;background:' + (b.color || COLOR.accent) + ';color:' + textOn(b.color || COLOR.accent) + '" title="' + esc(b.tip || '') + '"' + (b.id != null ? ' data-id="' + esc(b.id) + '"' : '') + '>' + (w > 40 && b.label ? esc(b.label) : '') + '</div>';
      }).join('');
      html += '<div class="g-row"><div class="g-lane" style="width:' + laneW + 'px" title="' + esc(ln.label) + '">' + esc(ln.label) + (ln.sub ? '&nbsp;<span class="sub">' + esc(ln.sub) + '</span>' : '') + '</div><div class="g-track" style="min-width:' + W + 'px">' + grid + now + bs + '</div></div>';
    });
    el.innerHTML = html;
    if (opts.onClick) el.onclick = function (e) { var b = e.target.closest('.g-bar[data-id]'); if (b) opts.onClick(b.getAttribute('data-id'), e); };
  }
  function pager(host, onChange, opts) {
    opts = opts || {};
    var fromMin = opts.from != null ? opts.from : ASOF, toMin = opts.to != null ? opts.to : END;
    var dflt = opts.days != null ? opts.days : 7, pg = 0;
    host.innerHTML = '<span class="fl">Window</span> <select class="pw">' +
      [[1, '1 day'], [3, '3 days'], [7, '7 days'], [14, '14 days'], [30, '30 days'], [0, 'Full plan']].map(function (o) { return '<option value="' + o[0] + '"' + (o[0] === dflt ? ' selected' : '') + '>' + o[1] + '</option>'; }).join('') + '</select> ' +
      '<span class="pager"><button data-a="first" title="First window">&laquo;</button><button data-a="prev" title="Previous window">&lsaquo;</button><span class="plab"></span><button data-a="next" title="Next window">&rsaquo;</button><button data-a="last" title="Last window">&raquo;</button><button class="now" data-a="now" title="Back to the window holding the as-of moment">Now</button></span>';
    var sel = host.querySelector('.pw'), pgr = host.querySelector('.pager'), lab = host.querySelector('.plab');
    function daysSel() { return +sel.value; }
    function startDay() { return Math.floor(fromMin / 1440); }
    function pages() { var d = daysSel(); return d ? Math.max(1, Math.ceil((Math.ceil(toMin / 1440) - startDay()) / d)) : 1; }
    function pageOfNow() { var d = daysSel(); return d ? Math.max(0, Math.min(pages() - 1, Math.floor((Math.floor(ASOF / 1440) - startDay()) / d))) : 0; }
    function win() { var d = daysSel(); if (!d) return { startMin: fromMin, endMin: toMin, days: 0 }; var s = (startDay() + pg * d) * 1440; return { startMin: s, endMin: s + d * 1440, days: d }; }
    function paint() {
      var d = daysSel(), np = pages(); pg = Math.max(0, Math.min(np - 1, pg)); pgr.style.display = d ? '' : 'none';
      var w = win(); lab.innerHTML = 'Page <b>' + (pg + 1) + '</b> of ' + np + ' · ' + fmtD(w.startMin) + (d > 1 ? ' – ' + fmtD(w.endMin - 1) : '');
      pgr.querySelector('[data-a=first]').disabled = pgr.querySelector('[data-a=prev]').disabled = pg === 0;
      pgr.querySelector('[data-a=last]').disabled = pgr.querySelector('[data-a=next]').disabled = pg >= np - 1;
      pgr.querySelector('[data-a=now]').disabled = pg === pageOfNow();
      onChange(w);
    }
    sel.addEventListener('change', function () { pg = pageOfNow(); paint(); });
    pgr.addEventListener('click', function (e) { var b = e.target.closest('button[data-a]'); if (!b) return; var a = b.getAttribute('data-a'); pg = a === 'first' ? 0 : a === 'prev' ? pg - 1 : a === 'next' ? pg + 1 : a === 'last' ? pages() - 1 : pageOfNow(); paint(); });
    pg = pageOfNow(); paint();
    return { win: win, repaint: paint };
  }

  // ---------------------------------------------------------------- Excel (SheetJS, vendored)
  function xlsx(sheets, filename) {
    if (!window.XLSX) { toast('Excel library not loaded on this page', 'fa-triangle-exclamation'); return; }
    var wb = XLSX.utils.book_new();
    sheets.forEach(function (s) {
      var ws = XLSX.utils.aoa_to_sheet([s.cols].concat(s.rows));
      ws['!cols'] = s.cols.map(function (c, i) { return { wch: (s.widths && s.widths[i]) || Math.max(10, String(c).length + 2) }; });
      XLSX.utils.book_append_sheet(wb, ws, s.name.slice(0, 31));
    });
    XLSX.writeFile(wb, filename);
  }

  // ---------------------------------------------------------------- scenario launcher
  var S = D.scenarios;
  function line(id) { return byId.lines[id]; }

  /* Four anchors cannot be fixed when the data is generated, because what they have to bite on is made by the plan
     itself. They are resolved here against the cached comparison, and fall back to the generated value before any plan
     has been computed. Chosen up front instead, three of these cards changed nothing at all. */
  function live() { return cached(settings()); }
  /* C4 derates the utility the plan is leaning on hardest, to just under the duty it is actually drawing. Picking the
     derate when the data was generated is how a card stops biting: the plan moves, and a cap chosen weeks ago sits in
     clear air. Read it off the plan instead. */
  function c4Derate() {
    var C = live(); if (!C) return S.C4.derateTo;
    return Math.max(1, Math.round(((C.aware.kpi.utilPeak || {})[S.C4.utility] || 0) * 0.86));
  }
  function c5Cap() {
    var C = live(); if (!C) return S.C5.cutTo;
    return Math.max(4, Math.round(((C.aware.kpi.wastePeak || {})[S.C5.waste] || 0) * 0.72));
  }
  function c6Licence() {
    var C = live(); if (!C) return S.C6.licenceCutTo;
    return Math.max(10, Math.round(((C.aware.kpi.licencePeak || {})[S.C6.haz] || 0) * 0.88));
  }
  /* C7 tightens the IMPURITY limit, not the assay.
     A blend's assay is the mass-weighted mean of its lots, so blending can never beat the best lot in the pool — an
     assay minimum is not something allocation can solve. Impurity averages DOWN, which is exactly what blending is for.
     The limit is set against the blend this plan actually made, so the current lots stop qualifying and the allocator
     has to find another combination or say plainly that it cannot. */
  function c3Op() {
    var C = live();
    if (!C) return { productId: S.C3.productId, op: S.C3.op, maxLagH: S.C3.maxLagH, tightenTo: S.C3.tightenTo };
    var m = C.m || C.aware.m, best = null;
    C.aware.fwd.forEach(function (b) {
      var p = m.P[b.pix];
      for (var i = 1; i < b.ops.length; i++) {
        var lag = (b.ops[i].s - b.ops[i - 1].e) / 60, win = p.ops[i].maxLagH;
        if (!win) continue;
        var use = lag / win;
        if (!best || use > best.use) best = { use: use, lagH: lag, productId: p.id, op: p.ops[i].id, maxLagH: win, label: p.ops[i].label };
      }
    });
    if (!best) return { productId: S.C3.productId, op: S.C3.op, maxLagH: S.C3.maxLagH, tightenTo: S.C3.tightenTo };
    // below the lag this link is taking AND at most half the window, so the next plan cannot simply keep it
    best.tightenTo = Math.max(2, Math.min(Math.floor(best.lagH) - 1, Math.floor(best.maxLagH * 0.5)));
    return best;
  }
  function c7Spec() {
    var C = live();
    if (!C) return { lineId: S.C7.lineId, impMax: S.C7.impMax };
    var cand = C.aware.allocs.filter(function (a) { return a.blended && a.kg > 0 && a.imp > 0; });
    cand.sort(function (a, b) { return b.kg - a.kg || (a.lineId < b.lineId ? -1 : 1); });
    var a0 = cand[0];
    if (!a0) return { lineId: S.C7.lineId, impMax: S.C7.impMax };
    return { lineId: a0.lineId, impMax: Math.round(a0.imp * 0.9 * 1000) / 1000, was: a0.imp, lots: a0.lots.length };
  }
  function c7Line() { return c7Spec().lineId; }
  function c11Lot() {
    var C = live();
    if (!C) return { lotId: S.C11.lotId, lineId: null, productId: S.C11.productId, lifeLeftM: S.C11.lifeLeftM };
    // only a lot serving a line with a minimum remaining life can demonstrate anything: age a lot nobody is picky
    // about and the plan is rightly unmoved
    var used = {};
    C.aware.allocs.forEach(function (a) {
      var L = C.aware.byId[a.lineId];
      if (!L || !L.minLifeM) return;
      a.lots.forEach(function (x) { used[x.id] = a; });
    });
    var pool = C.aware.lots.filter(function (x) { return used[x.id] && x.retestAt != null; });
    pool.sort(function (a, b) { return a.retestAt - b.retestAt || (a.id < b.id ? -1 : 1); });
    var x = pool[0];
    return x ? { lotId: x.id, lineId: used[x.id].lineId, productId: x.productId,
                 lifeLeftM: Math.max(0, Math.round((x.retestAt - ASOF) / (30.4 * 1440) * 10) / 10) }
             : { lotId: S.C11.lotId, lineId: null, productId: S.C11.productId, lifeLeftM: S.C11.lifeLeftM };
  }
  var SCENARIOS = [
    { id: 'C1', nuance: 'P1', changes: 'nothing', wants: 'P1', icon: 'fa-soap', page: 'cleaning', hash: function () { return S.C1.frm + '>' + S.C1.to; },
      title: 'Deep colour, then a pale product',
      desc: function () { return S.C1.frm + ' runs before ' + S.C1.to + ': the matrix calls for a ' + gradeName(S.C1.grade).toLowerCase() + ' of ' + S.C1.hours + ' h, not a setup time. ' + S.C1.why + '.'; },
      run: function () { } },
    { id: 'C2', nuance: 'P2', changes: 'schedule', wants: 'P2', icon: 'fa-flask-vial', page: 'batches', hash: function () { return S.C2.productId; },
      title: 'The campaign that ends short',
      desc: function () { return S.C2.productId + ' assays low across the campaign (' + pct(S.C2.shortTo) + ' against a mean of ' + pct(S.C2.yieldMean) + '). The batch count was an estimate; now it needs a top-up after the train has been broken down.'; },
      run: function () { addWhatif({ type: 'yieldShort', productId: S.C2.productId, to: S.C2.shortTo }); },
      next: ['C2b'] },
    { id: 'C3', nuance: 'P3', changes: 'schedule', wants: 'P3', icon: 'fa-hourglass-half', page: 'stages', hash: function () { return c3Op().productId; },
      title: 'The intermediate that spoils',
      desc: function () { var q = c3Op(); return 'The hold window before ' + (q.label ? q.label.toLowerCase() : q.op) + ' on ' + q.productId +
        ' tightens from ' + q.maxLagH + ' h to ' + q.tightenTo + ' h — inside the ' + (q.lagH != null ? Math.round(q.lagH) : q.maxLagH) +
        ' h the plan is taking today. That stage must now follow the one before it sooner, or the intermediate is out of specification.'; },
      run: function () { var q = c3Op(); addWhatif({ type: 'holdTighten', productId: q.productId, op: q.op, hours: q.tightenTo }); } },
    { id: 'C4', nuance: 'P4', changes: 'schedule', wants: 'P4', icon: 'fa-temperature-arrow-down', page: 'utilities', hash: 'BRINE',
      title: 'Three exotherms in one hour',
      desc: function () { var u = byId.utils[S.C4.utility]; return 'The brine plant derates to ' + c4Derate() + ' ' + (u ? u.unit : 'TR') + '. ' + S.C4.productIds.join(', ') + ' all draw brine at their peak — they can no longer all run together.'; },
      run: function () { addWhatif({ type: 'derate', utility: S.C4.utility, cap: c4Derate() }); } },
    { id: 'C5', nuance: 'P5', changes: 'schedule', wants: 'P5', icon: 'fa-recycle', page: 'effluent', hash: 'ETP',
      title: 'Two heavy-effluent campaigns back to back',
      desc: function () { return 'The effluent plant is cut to ' + c5Cap() + ' m³ a day. ' + S.C5.productIds.join(' and ') + ' are the heaviest loads in the book: the treatment plant decides when they can run.'; },
      run: function () { addWhatif({ type: 'wasteCut', waste: S.C5.waste, cap: c5Cap() }); } },
    { id: 'C6', nuance: 'P6', changes: 'schedule', wants: 'P6', icon: 'fa-triangle-exclamation', page: 'tanks', hash: function () { return S.C6.tankId; },
      title: 'A delivery that breaches the licence',
      desc: function () { return 'The flammable licence is cut to ' + c6Licence() + ' kL. Tanker ' + S.C6.deliveryId + ' (' + S.C6.kl + ' kL into ' + S.C6.tankId + ') is refused at the gate — by the licence, not by the tank.'; },
      run: function () { addWhatif({ type: 'licenceCut', haz: S.C6.haz, kl: c6Licence() }); } },
    { id: 'C7', nuance: 'P7', changes: 'allocation', wants: 'P7', icon: 'fa-flask', page: 'lots', hash: function () { return c7Line(); },
      title: 'Three batches blended into one lot',
      desc: function () { var q = c7Spec(); return 'Line ' + q.lineId + ' tightens its impurity limit to ' + q.impMax + '%, below the ' +
        (q.was != null ? q.was + '% the blend serving it carries today' : 'blend serving it today') + '. Assay cannot be blended upwards; impurity can be blended down, and this is where that arithmetic has to be shown.'; },
      run: function () { var q = c7Spec(); addWhatif({ type: 'tightSpec', lineId: q.lineId, impMax: q.impMax, assayMin: null }); } },   // the engine tightens against the product's own assay spread
    { id: 'C8', nuance: 'S1', changes: 'sop', wants: 'S1', icon: 'fa-chart-pie', page: 'capacity', hash: 'mix',
      title: 'Same plant, a different mix',
      desc: function () { return 'Shift ' + pct(S.C8.shift, 0) + ' of the plan from ' + S.C8.fromProduct + ' to ' + S.C8.toProduct + '. The single tonnage number does not survive it, and the bottleneck moves off the ' + String(S.C8.binding || '').toLowerCase() + '.'; },
      run: function () { addWhatif({ type: 'mix', fromProduct: S.C8.fromProduct, toProduct: S.C8.toProduct, shift: S.C8.shift }); } },
    { id: 'C9', nuance: 'S2', changes: 'nothing', wants: 'S2', icon: 'fa-ranking-star', page: 'capacity', hash: 'margin',
      title: 'Margin per tonne against margin per bottleneck hour',
      desc: function () { return S.C9.perTonneWinner + ' wins on margin per tonne; ' + S.C9.perHourWinner + ' wins on margin per hour of the ' + String(S.C9.binding || '').toLowerCase() + '. Two of the products never touch the bottleneck at all.'; },
      run: function () { } },
    { id: 'C10', nuance: 'S4', changes: 'sop', wants: 'S4', icon: 'fa-arrows-split-up-and-left', page: 'capacity', hash: 'coproduct',
      title: 'A co-product that fills the tank',
      desc: function () { return 'Every tonne of ' + S.C10.productId + ' makes ' + S.C10.ratio + ' t of ' + S.C10.coprodId + '. Cut the storage ceiling to ' + S.C10.capCutTo + ' kL and the co-product caps the main product.'; },
      run: function () { addWhatif({ type: 'coprodCap', productId: S.C10.productId, kl: S.C10.capCutTo }); } },
    { id: 'C11', nuance: 'S6', changes: 'allocation', wants: 'S6', icon: 'fa-clock-rotate-left', page: 'stock', hash: function () { return c11Lot().lotId; },
      title: 'A lot too old for this customer',
      desc: function () { var q = c11Lot(); return 'Lot ' + q.lotId + ' has ' + q.lifeLeftM + ' months left. ' + custName(S.C11.customerId) + ' insists on ' + S.C11.minLifeM + ' on receipt, so the stock is there and still cannot be shipped.'; },
      run: function () { addWhatif({ type: 'lotAge', lotId: c11Lot().lotId, monthsLeft: 1 }); } },
    { id: 'C12', nuance: 'S7', changes: 'nothing', wants: 'S7', icon: 'fa-building-shield', page: 'sourcing', hash: 'sites',
      title: 'A site the customer has not approved',
      desc: function () { return custName(S.C12.customerId) + ' has qualified ' + S.C12.sites.join(', ') + ' only. Moving their order to another site costs ' + S.C12.qualWeeks + ' weeks of filing and validation first.'; },
      run: function () { } },
    { id: 'C13', nuance: 'S8', changes: 'sop', wants: 'S8', icon: 'fa-calendar-xmark', page: 'stock', hash: 'prebuild',
      title: 'A pre-build before the shutdown',
      desc: function () { return 'The statutory shutdown takes ' + S.C13.shutdownDays + ' days out of ' + S.C13.shutdownMonth + '. What has to be built early, and which products have the shelf life to be built early at all?'; },
      run: function () { addWhatif({ type: 'prebuild', month: S.C13.shutdownMonth }); },
      next: ['C13b', 'C13c'] },
    // follow-ons: reached from inside C2 and C13, because these nuances compound rather than stand alone
    { id: 'C2b', nuance: 'S3', changes: 'sop', wants: 'S3', icon: 'fa-handshake', page: 'sourcing', hash: 'maketoll', follow: true,
      title: 'Cover the shortfall: make, buy or toll',
      desc: function () { return 'The ' + S.C2.productId + ' shortfall has to come from somewhere. Three options, each valued against an hour of the bottleneck rather than against a cost per kg.'; },
      run: function () { addWhatif({ type: 'sourcing', productId: S.C2b.productId, mode: 'toll' }); } },
    { id: 'C13b', nuance: 'S5', changes: 'sop', wants: 'S5', icon: 'fa-truck-ramp-box', page: 'sourcing', hash: 'rm', follow: true,
      title: 'Book the raw-material block',
      desc: function () { var r = byId.raws[S.C13b.rmId]; return (r ? r.name : S.C13b.rmId) + ' comes in blocks of ' + (r ? r.minBlock + ' ' + r.unit : 'one tanker') + ' with a ' + (r ? r.leadDays : 30) + '-day lead time, and the contract price resets on a lag.'; },
      run: function () { addWhatif({ type: 'rmBlock', rmId: S.C13b.rmId }); } },
    { id: 'C13c', nuance: 'S9', changes: 'sop', wants: 'S9', icon: 'fa-boxes-packing', page: 'stock', hash: 'pack', follow: true,
      title: 'Hold it as bulk, pack it late',
      desc: function () { return 'Hold ' + S.C13c.productId + ' as bulk and decide the pack and the label to order. The same stock then serves more than one customer.'; },
      run: function () { addWhatif({ type: 'pack', productId: S.C13c.productId }); } }
  ];
  var TOURS = [
    { id: 'plant', label: 'The plant head\'s story', cards: ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7'],
      note: 'Seven things a generic scheduler does not see, in the order they hit the floor.' },
    { id: 'sop', label: 'The S&OP head\'s story', cards: ['C8', 'C9', 'C10', 'C11', 'C12', 'C13'],
      note: 'What the same constraints mean a quarter out, when the question is mix and sourcing rather than sequence.' }
  ];
  function scen(id) { return SCENARIOS.filter(function (s) { return s.id === id; })[0]; }
  function scenText(s, key) { var v = s[key]; return typeof v === 'function' ? v() : v; }
  function runScenario(id, cb) {
    var s = scen(id); if (!s) return;
    replan(function () { s.run(); State.set('lastScenario', id); }, 'Running ' + id, function (r) {
      go(s.page, scenText(s, 'hash') || '');
      if (cb) cb(r);
    });
  }

  headerMode();
  window.CHMX = {
    D: D, E: E, NU: NU, BASE: BASE, ASOF: ASOF, END: END, isHost: isHost, by: byId, COLOR: COLOR, CLS_LABEL: CLS_LABEL,
    State: State, SCENARIOS: SCENARIOS, TOURS: TOURS, scen: scen, scenText: scenText, runScenario: runScenario,
    dateOf: dateOf, minOf: minOf, isoLocal: isoLocal, fmt: fmt, fmtD: fmtD, fmtDM: fmtDM, fmtT: fmtT, dur: dur, hrs: hrs,
    days: days, shiftOf: shiftOf, monthOf: monthOf,
    n: n, kg: kg, t: t, kl: kl, m3: m3, assay: assay, pct: pct, rs: rs, esc: esc, cls: cls, clsName: clsName, badge: badge, toast: toast,
    textOn: textOn, prov: prov,
    settings: settings, role: role, go: go, withPlan: withPlan, whenPlanChanges: whenPlanChanges, replan: replan,
    addWhatif: addWhatif, removeWhatif: removeWhatif, whatifLabel: whatifLabel,
    cachedPlan: cached, computePlan: compute, busy: busy, headerMode: headerMode,
    hashParam: function () { return decodeURIComponent((location.hash || '').slice(1)); },
    product: product, pname: pname, unit: unit, custName: custName, famName: famName, famColor: famColor,
    gradeName: gradeName, gradeHours: gradeHours, line: line,
    nu: nu, nuLabel: nuLabel, nuChip: nuChip, nuOf: nuOf,
    c3Op: c3Op, c5Cap: c5Cap, c6Licence: c6Licence, c7Line: c7Line, c7Spec: c7Spec, c11Lot: c11Lot,
    gantt: gantt, pager: pager, xlsx: xlsx,
    // host-side API (the tab host computes once; tabs read)
    _cached: function (st) { var ov = mastersOverlay(); return C.plans[planKey(st, JSON.stringify(ov))] || null; },
    _compute: function (st) { return computeLocal(st); },
    model: function () { var h = hostX(); if (h) return h.model(); var ov = mastersOverlay(); return modelFor(JSON.stringify(ov), ov); },
    hist: function () { var h = hostX(); return h ? h.hist() : histOf(); }
  };
})();
