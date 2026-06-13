/* Contrôleur du mini-site : charge la page Markdown courante et la rend dans #doc-article.
   Template réutilisable : copier tel quel dans <output_dir>/assets/. Ne pas éditer par projet.

   Routage par hash : "#/slug" → fetch pages/slug.md. "#/" (ou rien) → pages/home.md.
   Une ancre simple (ex. "#top") n'est PAS une route : on laisse le navigateur défiler.
   Le Markdown vit dans pages/*.md ; le navigateur exige un serveur (file:// est bloqué). */
(function () {
  var ARTICLE = document.getElementById('doc-article');
  if (!ARTICLE) return;
  var PAGES = 'pages/';
  var DEFAULT = 'home';

  function routeSlug() {
    var h = location.hash || '';
    if (h.indexOf('#/') === 0) return h.slice(2).replace(/[?].*$/, '') || DEFAULT;
    return null;
  }

  function markedParse(md) {
    if (window.marked) return window.marked.parse ? window.marked.parse(md) : window.marked(md);
    return '<pre>' + md.replace(/[&<>]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c];
    }) + '</pre>';
  }

  // "> [!note] …" → encart .note ; un blockquote nu reste un encart (CSS).
  function calloutize(scope) {
    [].forEach.call(scope.querySelectorAll('blockquote'), function (bq) {
      var first = bq.firstElementChild;
      if (!first) return;
      var m = first.textContent.match(/^\s*\[!(\w+)\]\s*/);
      if (m) {
        bq.classList.add('note');
        first.innerHTML = first.innerHTML.replace(/^\s*\[!\w+\]\s*/, '');
      }
    });
  }

  // ```mermaid … ``` → <div class="diagram"><pre class="mermaid">…</pre></div>
  function mermaidize(scope) {
    [].forEach.call(scope.querySelectorAll('pre > code.language-mermaid'), function (code) {
      var pre = code.parentNode;
      var holder = document.createElement('div');
      holder.className = 'diagram';
      var m = document.createElement('pre');
      m.className = 'mermaid';
      m.textContent = code.textContent;
      holder.appendChild(m);
      pre.parentNode.replaceChild(holder, pre);
    });
  }

  function setActive(s) {
    [].forEach.call(document.querySelectorAll('.sidenav a'), function (a) {
      var href = a.getAttribute('href') || '';
      var target = href.indexOf('#/') === 0 ? (href.slice(2) || DEFAULT) : null;
      if (target === s) a.setAttribute('aria-current', 'page');
      else a.removeAttribute('aria-current');
    });
  }

  function project() {
    var el = document.querySelector('.masthead__title');
    return el ? el.textContent.trim() : '';
  }

  function setTitle(scope) {
    var h1 = scope.querySelector('h1');
    document.title = (h1 ? h1.textContent + ' — ' : '') + project();
  }

  function showError(html) { ARTICLE.innerHTML = '<div class="doc-error">' + html + '</div>'; }

  function serverHint() {
    var esc = function (s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); };
    var dir = decodeURIComponent(location.pathname).replace(/[^/]*$/, '');
    var cmd = 'bash "' + esc(dir) + 'serve.sh" 8001';
    showError(
      '<h2>Ouvre la doc via un petit serveur</h2>' +
      '<p>Le navigateur interdit à une page <code>file://</code> de lire les fichiers Markdown voisins. Lance la commande avec le <strong>chemin absolu</strong> (garde les guillemets — le chemin peut contenir des espaces) et choisis le <strong>port localhost</strong> en fin de ligne :</p>' +
      '<pre>' + cmd + '</pre>' +
      '<p>…puis ouvre <code>http://localhost:8001/</code> (le numéro doit correspondre au port choisi).</p>'
    );
  }

  function load() {
    var s = routeSlug();
    if (s === null) {
      if (!location.hash) s = DEFAULT; else return; // ancre simple → on laisse défiler
    }
    if (location.protocol === 'file:') { serverHint(); return; }
    fetch(PAGES + s + '.md').then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.text();
    }).then(function (md) {
      ARTICLE.innerHTML = markedParse(md);
      calloutize(ARTICLE);
      mermaidize(ARTICLE);
      if (window.PWDoc) {
        PWDoc.renderMindmaps(ARTICLE);
        PWDoc.renderMermaid(ARTICLE);
      }
      setActive(s);
      setTitle(ARTICLE);
      window.scrollTo(0, 0);
    }).catch(function () {
      showError('<h2>Page introuvable</h2><p>Aucune page « ' + s +
        ' » dans <code>pages/</code>. <a href="#/">Retour à l’accueil</a>.</p>');
    });
  }

  window.addEventListener('hashchange', load);
  load();
})();
