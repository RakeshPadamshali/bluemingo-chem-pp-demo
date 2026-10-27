/* The ONE navigation definition. index.html builds its sidebar and tab map from it, chm-chrome.js builds the standalone
   sidebar from it, and chm-embed.js routes in-page links to host tabs with it — so the three can never disagree.

   Each entry: [id, label, icon, role]. `role` drives the header's Plant head / S&OP head toggle, which REORDERS and DIMS
   the sidebar rather than hiding anything: a plant head can still open an S&OP page, it just is not their first stop. */
window.CHM_NAV = [
  ['Plan', [
    ['home', 'PP Dashboard', 'fa-gauge-high', 'both'],
    ['studio', 'Plan Studio', 'fa-code-compare', 'both'],
    ['orders', 'Order Book & Promise', 'fa-file-invoice', 'both']]],
  ['Schedule', [
    ['schedule', 'Block Schedule', 'fa-chart-gantt', 'plant'],
    ['cleaning', 'Cleaning & Campaigns', 'fa-soap', 'plant'],
    ['stages', 'Multi-stage & Hold Times', 'fa-hourglass-half', 'plant']]],
  ['Shared limits', [
    ['utilities', 'Utilities & Thermal Duty', 'fa-bolt', 'plant'],
    ['effluent', 'Effluent & Solvent Recovery', 'fa-recycle', 'plant'],
    ['tanks', 'Tank Farm & Hazard Licence', 'fa-oil-well', 'plant']]],
  ['Execution', [
    ['batches', 'Batch Record & Yield', 'fa-flask-vial', 'plant'],
    ['lots', 'Lots, Blending & Allocation', 'fa-flask', 'plant'],
    ['report', 'Production Plan Report', 'fa-table-list', 'both']]],
  ['Sales & operations planning', [
    ['capacity', 'Capacity, Mix & Margin', 'fa-chart-pie', 'sop'],
    ['sourcing', 'Sourcing & Supply', 'fa-handshake', 'sop'],
    ['stock', 'Stock, Shelf Life & Pack', 'fa-boxes-stacked', 'sop']]],
  ['Masters', [
    ['masters', 'Master Data', 'fa-database', 'both']]]
];
window.CHM_PAGES = {};
window.CHM_NAV.forEach(function (sec) {
  sec[1].forEach(function (it) { window.CHM_PAGES[it[0]] = { label: it[1], icon: it[2], role: it[3], href: it[0] + '.html', group: sec[0] }; });
});
window.CHM_ROLES = [['both', 'Both'], ['plant', 'Plant head'], ['sop', 'S&OP head']];
