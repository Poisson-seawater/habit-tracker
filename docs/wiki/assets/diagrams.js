/* Rendu des diagrammes (carte mentale markmap + flowcharts mermaid), accordé au thème.
   Template réutilisable : copier tel quel dans <output_dir>/assets/.
   Expose window.PWDoc.renderMindmaps(scope) et window.PWDoc.renderMermaid(scope),
   appelés par render.js (pages SPA) et par mindmap.html (plein écran). */
(function () {
  window.PWDoc = window.PWDoc || {};

  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      if (document.querySelector('script[data-pwdoc="' + src + '"]')) { resolve(); return; }
      var s = document.createElement('script');
      s.src = src; s.async = true;
      s.setAttribute('data-pwdoc', src);
      s.onload = function () { resolve(); };
      s.onerror = function () { reject(new Error('load failed: ' + src)); };
      document.head.appendChild(s);
    });
  }

  /* ---- Carte mentale (markmap) ----
     Cible chaque <svg class="markmap" data-mindmap="pages/_mindmap.md">.
     Le Markdown est récupéré une fois puis transformé. Les couleurs suivent le thème
     via les variables CSS de styles.css (pas de re-render au changement de thème). */
  PWDoc.renderMindmaps = function (scope) {
    scope = scope || document;
    var mm = window.markmap;
    if (!mm || !mm.Transformer || !mm.Markmap) return;
    var svgs = scope.querySelectorAll('svg.markmap[data-mindmap]');
    [].forEach.call(svgs, function (svg) {
      if (svg.getAttribute('data-rendered') === '1') return;
      var src = svg.getAttribute('data-mindmap');
      fetch(src).then(function (r) {
        if (!r.ok) throw new Error(r.status);
        return r.text();
      }).then(function (md) {
        var t = new mm.Transformer();
        var res = t.transform(md);
        var opts = mm.deriveOptions ? mm.deriveOptions(res.frontmatter && res.frontmatter.markmap) : undefined;
        mm.Markmap.create(svg, opts, res.root);
        svg.setAttribute('data-rendered', '1');
      }).catch(function () {
        svg.outerHTML = '<p class="mindmap-hint">Carte mentale indisponible (' + src + ').</p>';
      });
    });
  };

  /* ---- Flowcharts mermaid (chargés à la demande seulement si la page en contient) ---- */
  var MERMAID_CDN = 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js';
  function mermaidTheme() {
    return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'default';
  }
  function runMermaid(blocks) {
    window.mermaid.initialize({
      startOnLoad: false,
      theme: mermaidTheme(),
      securityLevel: 'loose',
      fontFamily: 'Public Sans, system-ui, sans-serif'
    });
    blocks.forEach(function (b) {
      b.removeAttribute('data-processed');
      b.innerHTML = b.getAttribute('data-src');
    });
    try { window.mermaid.run({ nodes: blocks }); } catch (e) {}
  }
  PWDoc.renderMermaid = function (scope) {
    scope = scope || document;
    var blocks = [].slice.call(scope.querySelectorAll('pre.mermaid'));
    if (!blocks.length) return;
    blocks.forEach(function (b) {
      if (!b.getAttribute('data-src')) b.setAttribute('data-src', b.textContent.trim());
    });
    function go() {
      runMermaid(blocks);
      if (!PWDoc._mermaidBound) {
        PWDoc._mermaidBound = true;
        document.addEventListener('pwdoc:theme', function () {
          var all = [].slice.call(document.querySelectorAll('pre.mermaid[data-src]'));
          if (all.length && window.mermaid) runMermaid(all);
        });
      }
    }
    if (window.mermaid) go();
    else loadScript(MERMAID_CDN).then(go).catch(function () {});
  };
})();
