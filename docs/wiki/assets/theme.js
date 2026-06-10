/* Bascule thème clair/sombre, persistée dans localStorage (clé pwdoc-theme).
   Template réutilisable : à copier tel quel dans <output_dir>/assets/.
   Le thème initial est posé avant le rendu par le script inline du <head> de chaque page. */
(function () {
  var KEY = "pwdoc-theme";
  var root = document.documentElement;

  function current() {
    return root.getAttribute("data-theme") === "dark" ? "dark" : "light";
  }

  function sync(theme) {
    root.setAttribute("data-theme", theme);
    var dark = theme === "dark";
    var toggles = document.querySelectorAll("[data-theme-toggle]");
    for (var i = 0; i < toggles.length; i++) {
      var btn = toggles[i];
      var icon = btn.querySelector(".theme-toggle__icon");
      var label = btn.querySelector(".theme-toggle__label");
      if (icon) icon.textContent = dark ? "☀️" : "🌙";
      if (label) label.textContent = dark ? "Clair" : "Sombre";
      btn.setAttribute("aria-pressed", String(dark));
    }
    document.dispatchEvent(new CustomEvent("pwdoc:theme", { detail: theme }));
  }

  sync(current());

  document.addEventListener("click", function (e) {
    var btn = e.target.closest && e.target.closest("[data-theme-toggle]");
    if (!btn) return;
    var next = current() === "dark" ? "light" : "dark";
    try { localStorage.setItem(KEY, next); } catch (err) {}
    sync(next);
  });
})();
