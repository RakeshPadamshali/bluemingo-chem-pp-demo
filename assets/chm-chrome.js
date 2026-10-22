/* Injects the standalone header and sidebar into a content page (both hidden again when the page is embedded as a tab in
   index.html). Each page sets window.CHM_PAGE / CHM_TITLE / CHM_ICON before loading this. Needs chm-nav.js. */
(function () {
  var cur = window.CHM_PAGE || '';
  var layout = document.querySelector('.bm-layout');
  if (!layout) return;
  var meta = window.CHM_META || {};
  var h = document.createElement('header');
  h.className = 'bm-header';
  h.innerHTML =
    '<div class="logo"><img src="assets/img/bluemingo-logo.png" alt="Bluemingo"><span class="t">PP</span>' +
    '<span class="sub">Specialty Chemicals &amp; APIs</span></div>' +
    '<div class="module-name"><i class="fa-solid ' + (window.CHM_ICON || 'fa-diagram-project') + '"></i>' + (window.CHM_TITLE || 'Production Planning') + '</div>' +
    '<div class="spacer"></div>' +
    '<div class="roles" id="chm-roles"></div>' +
    '<div class="plant-switch"><button class="active"><i class="fa-solid fa-industry" style="margin-right:4px"></i>' + (meta.site || 'API Site') + '</button></div>' +
    '<div class="right"><span class="plan-mode" id="chm-mode"></span><span class="asof" id="chm-asof"></span>' +
    '<button class="btn-reset" id="chm-reset" title="Clear every live-demo action and reload"><i class="fa-solid fa-rotate-left"></i> Reset demo</button>' +
    '<div class="avatar">RP</div></div>';
  document.body.insertBefore(h, layout);

  var side = document.createElement('aside');
  side.className = 'bm-sidebar';
  side.id = 'chm-sidebar';
  layout.insertBefore(side, layout.firstChild);
  window.CHM_paintNav = function (role) {
    var html = '';
    (window.CHM_NAV || []).forEach(function (sec) {
      html += '<div class="nav-label">' + sec[0] + '</div>';
      sec[1].forEach(function (it) {
        var dim = role && role !== 'both' && it[3] !== 'both' && it[3] !== role;
        html += '<a href="' + it[0] + '.html" class="' + (it[0] === cur ? 'active ' : '') + (dim ? 'dim' : '') + '"' +
                (dim ? ' title="' + it[1] + ' — not this role\'s first stop, still open to them"' : '') + '>' +
                '<i class="fa-solid ' + it[2] + '"></i>' + it[1] + '</a>';
      });
    });
    html += '<div class="powered">Bluemingo Production Planning<img src="assets/img/bluemingo-logo.png" alt="Bluemingo"></div>';
    side.innerHTML = html;
  };
  // the shared runtime painted its header chips before this header existed, so paint them again now that it does
  if (window.CHMX) CHMX.headerMode(); else window.CHM_paintNav(window.CHMState ? CHMState.get('role', 'both') : 'both');
  var rb = document.getElementById('chm-reset');
  if (rb) rb.addEventListener('click', function () { if (window.CHMState) { CHMState.reset(); location.reload(); } });
})();
