/* When a page loads inside index.html (as an iframe tab), render content only — hide its own header and sidebar — and
   route in-content links to the host's tabs. Standalone: leave the page untouched. Needs chm-nav.js first. */
(function () {
  if (window.self === window.top) return;
  document.documentElement.className += ' embedded';
  var s = document.createElement('style');
  s.textContent = '.embedded .bm-header,.embedded .bm-sidebar{display:none!important}' +
                  '.embedded .bm-layout{height:100vh!important}' +
                  '.embedded .bm-content{padding-top:12px}';
  (document.head || document.documentElement).appendChild(s);
  document.addEventListener('click', function (e) {
    var a = e.target.closest ? e.target.closest('a[href]') : null;
    if (!a) return;
    var raw = a.getAttribute('href') || '', href = raw.split('#')[0].split('?')[0], hash = raw.split('#')[1] || '';
    var id = href.replace(/\.html$/, '');
    if (window.CHM_PAGES && window.CHM_PAGES[id]) {
      try { if (window.parent && window.parent.CHMHost) { e.preventDefault(); window.parent.CHMHost.open(id, hash); } } catch (err) {}
    }
  }, true);
})();
