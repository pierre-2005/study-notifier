// static/theme.js
(function () {
  const key = "theme"; // "light" | "dark" | "system"
  const root = document.documentElement;

  function systemPrefersDark() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  function apply(mode) {
    const useDark = (mode === "dark") || (mode === "system" && systemPrefersDark());
    root.classList.toggle("dark", useDark);
    root.dataset.theme = mode;
  }

  function getSaved() {
    return localStorage.getItem(key) || "system";
  }

  function setSaved(mode) {
    localStorage.setItem(key, mode);
    apply(mode);
  }

  // apply ASAP (prevents flash)
  apply(getSaved());

  // keep system mode in sync
  if (window.matchMedia) {
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
      if (getSaved() === "system") apply("system");
    });
  }

  // global helper (used by the button)
  window.__toggleTheme = function () {
    const cur = getSaved();
    const next = cur === "system" ? "light" : cur === "light" ? "dark" : "system";
    setSaved(next);
    return next;
  };
})();
