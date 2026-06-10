/* Rendu des diagrammes Mermaid, accordé au thème clair/sombre du site.
   Template réutilisable : copier dans <output_dir>/assets/ pour les pages qui contiennent des diagrammes.
   À charger APRÈS le CDN mermaid ET après theme.js (qui émet l'événement pwdoc:theme à chaque bascule). */
(function () {
  if (typeof mermaid === "undefined") return;

  var blocks = [].slice.call(document.querySelectorAll(".mermaid"));
  if (!blocks.length) return;

  // Mermaid remplace le contenu de chaque bloc par du SVG : on mémorise la source pour pouvoir re-rendre.
  blocks.forEach(function (b) { b.setAttribute("data-src", b.textContent.trim()); });

  function themeName() {
    return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "default";
  }

  function render() {
    mermaid.initialize({
      startOnLoad: false,
      theme: themeName(),
      securityLevel: "loose",
      fontFamily: "Public Sans, system-ui, sans-serif"
    });
    blocks.forEach(function (b) {
      b.removeAttribute("data-processed");
      b.innerHTML = b.getAttribute("data-src");
    });
    try { mermaid.run({ nodes: blocks }); } catch (e) {}
  }

  render();
  document.addEventListener("pwdoc:theme", render);
})();
