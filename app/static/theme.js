// static/theme.js
(function () {
  const key = "theme";
  const root = document.documentElement;
  const validThemes = ["system", "light", "dark"];

  function normalizeTheme(mode) {
    return validThemes.includes(mode) ? mode : "system";
  }

  function systemPrefersDark() {
    return window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  function apply(mode) {
    mode = normalizeTheme(mode);

    const useDark = mode === "dark" || (mode === "system" && systemPrefersDark());

    root.classList.toggle("dark", useDark);
    root.dataset.theme = mode;
  }

  function getSaved() {
    return normalizeTheme(localStorage.getItem(key) || "system");
  }

  function setSaved(mode) {
    mode = normalizeTheme(mode);

    localStorage.setItem(key, mode);
    apply(mode);

    document.dispatchEvent(
      new CustomEvent("mlo:themechange", {
        detail: { mode: mode }
      })
    );

    return mode;
  }

  // Apply ASAP
  apply(getSaved());

  // Keep system mode synced when OS/browser theme changes
  if (window.matchMedia) {
    const media = window.matchMedia("(prefers-color-scheme: dark)");

    const onSystemThemeChange = function () {
      if (getSaved() === "system") {
        apply("system");

        document.dispatchEvent(
          new CustomEvent("mlo:themechange", {
            detail: { mode: "system" }
          })
        );
      }
    };

    if (media.addEventListener) {
      media.addEventListener("change", onSystemThemeChange);
    } else if (media.addListener) {
      media.addListener(onSystemThemeChange);
    }
  }

  window.__setTheme = function (mode) {
    return setSaved(mode);
  };

  window.__getTheme = function () {
    return getSaved();
  };

  window.__toggleTheme = function () {
    const cur = getSaved();
    const next = cur === "system" ? "light" : cur === "light" ? "dark" : "system";
    return setSaved(next);
  };
})();