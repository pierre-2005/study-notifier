(function () {
  "use strict";

  const root = document.documentElement;
  const THEME_KEY = "theme";
  const SIDEBAR_KEY = "mlo.sidebar.collapsed";
  const NAV_KEY = "mlo.navigation.v1";
  const validThemes = ["system", "light", "dark"];
  const optionalNavKeys = ["todos", "courses", "items", "schedule", "finance", "expenses", "jobs"];

  function safeGet(key, fallback) {
    try {
      const value = localStorage.getItem(key);
      return value === null ? fallback : value;
    } catch (_) {
      return fallback;
    }
  }

  function safeSet(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch (_) {}
  }

  function systemPrefersDark() {
    return !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
  }

  function normalizeTheme(mode) {
    return validThemes.includes(mode) ? mode : "system";
  }

  function applyTheme(mode) {
    mode = normalizeTheme(mode);
    const dark = mode === "dark" || (mode === "system" && systemPrefersDark());
    root.classList.toggle("dark", dark);
    root.dataset.theme = mode;
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", dark ? "#191919" : "#fbfbfa");
    return mode;
  }

  function getTheme() {
    return normalizeTheme(safeGet(THEME_KEY, "system"));
  }

  function setTheme(mode) {
    mode = applyTheme(mode);
    safeSet(THEME_KEY, mode);
    renderThemeControls();
    document.dispatchEvent(new CustomEvent("mlo:themechange", { detail: { mode } }));
    return mode;
  }

  function renderThemeControls() {
    const current = getTheme();
    document.querySelectorAll("[data-theme-choice]").forEach((button) => {
      const active = button.dataset.themeChoice === current;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  window.__setTheme = setTheme;
  window.__getTheme = getTheme;
  window.__toggleTheme = function () {
    const current = getTheme();
    return setTheme(current === "system" ? "light" : current === "light" ? "dark" : "system");
  };

  applyTheme(getTheme());

  if (window.matchMedia) {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      if (getTheme() === "system") applyTheme("system");
      renderThemeControls();
    };
    if (media.addEventListener) media.addEventListener("change", onChange);
    else if (media.addListener) media.addListener(onChange);
  }

  function getNavPrefs() {
    try {
      const parsed = JSON.parse(safeGet(NAV_KEY, "{}"));
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch (_) {
      return {};
    }
  }

  function setNavPrefs(prefs) {
    safeSet(NAV_KEY, JSON.stringify(prefs));
    applyNavPrefs();
  }

  function isNavVisible(key, prefs) {
    if (key === "dashboard" || key === "settings") return true;
    return prefs[key] !== false;
  }

  function applyNavPrefs() {
    const prefs = getNavPrefs();
    document.querySelectorAll("[data-nav-key]").forEach((el) => {
      const key = el.dataset.navKey;
      el.hidden = !isNavVisible(key, prefs);
    });
    document.querySelectorAll("[data-nav-setting]").forEach((input) => {
      input.checked = isNavVisible(input.dataset.navSetting, prefs);
    });
  }

  function setNavVisible(key, visible) {
    if (!optionalNavKeys.includes(key)) return;
    const prefs = getNavPrefs();
    prefs[key] = !!visible;
    setNavPrefs(prefs);
  }

  function resetNav() {
    safeSet(NAV_KEY, "{}");
    applyNavPrefs();
  }

  function setSidebarCollapsed(collapsed) {
    document.documentElement.classList.toggle("sidebar-collapsed", collapsed);
    safeSet(SIDEBAR_KEY, collapsed ? "1" : "0");
    document.querySelectorAll("[data-sidebar-collapse]").forEach((button) => {
      button.setAttribute("aria-label", collapsed ? "Expand sidebar" : "Collapse sidebar");
      button.title = collapsed ? "Expand sidebar" : "Collapse sidebar";
    });
  }

  function closeMobileSidebar() {
    document.documentElement.classList.remove("mobile-sidebar-open");
    const overlay = document.querySelector("[data-sidebar-overlay]");
    if (overlay) overlay.hidden = true;
  }

  function openMobileSidebar() {
    document.documentElement.classList.add("mobile-sidebar-open");
    const overlay = document.querySelector("[data-sidebar-overlay]");
    if (overlay) overlay.hidden = false;
  }

  function closeMobileMore() {
    const sheet = document.querySelector("[data-mobile-more-sheet]");
    const button = document.querySelector("[data-mobile-more]");
    if (sheet) sheet.hidden = true;
    if (button) button.setAttribute("aria-expanded", "false");
  }

  function toggleMobileMore() {
    const sheet = document.querySelector("[data-mobile-more-sheet]");
    const button = document.querySelector("[data-mobile-more]");
    if (!sheet || !button) return;
    const willOpen = sheet.hidden;
    sheet.hidden = !willOpen;
    button.setAttribute("aria-expanded", willOpen ? "true" : "false");
  }

  function setDialog(selector, open) {
    const dialog = document.querySelector(selector);
    if (!dialog) return;
    dialog.hidden = !open;
    document.documentElement.classList.toggle("dialog-open", open || !!document.querySelector(".dialog-backdrop:not([hidden])"));
    if (open) {
      const focusTarget = dialog.querySelector("input, button, a");
      if (focusTarget) requestAnimationFrame(() => focusTarget.focus());
    }
  }

  function openCustomize() {
    closeMobileMore();
    applyNavPrefs();
    setDialog("[data-customize-dialog]", true);
  }

  function closeCustomize() {
    setDialog("[data-customize-dialog]", false);
  }

  function openCommand() {
    closeMobileMore();
    setDialog("[data-command-dialog]", true);
    const input = document.querySelector("[data-command-input]");
    if (input) {
      input.value = "";
      filterCommands("");
      requestAnimationFrame(() => input.focus());
    }
  }

  function closeCommand() {
    setDialog("[data-command-dialog]", false);
  }

  function filterCommands(query) {
    const q = String(query || "").trim().toLowerCase();
    document.querySelectorAll("[data-command-item]").forEach((item) => {
      const haystack = `${item.dataset.search || ""} ${item.textContent || ""}`.toLowerCase();
      item.hidden = !!q && !haystack.includes(q);
    });
  }

  function setupQuickAdd() {
    const toggle = document.querySelector("[data-quick-add-toggle]");
    const menu = document.querySelector("[data-quick-add-menu]");
    if (!toggle || !menu) return;

    const close = () => {
      menu.hidden = true;
      toggle.setAttribute("aria-expanded", "false");
    };

    toggle.addEventListener("click", (event) => {
      event.stopPropagation();
      const open = menu.hidden;
      menu.hidden = !open;
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });

    document.addEventListener("click", (event) => {
      if (!menu.contains(event.target) && event.target !== toggle) close();
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    renderThemeControls();
    applyNavPrefs();
    setSidebarCollapsed(safeGet(SIDEBAR_KEY, "0") === "1");
    setupQuickAdd();

    document.querySelectorAll("[data-theme-choice]").forEach((button) => {
      button.addEventListener("click", () => setTheme(button.dataset.themeChoice));
    });

    document.querySelectorAll("[data-nav-setting]").forEach((input) => {
      input.addEventListener("change", () => setNavVisible(input.dataset.navSetting, input.checked));
    });

    document.querySelectorAll("[data-nav-reset]").forEach((button) => button.addEventListener("click", resetNav));
    document.querySelectorAll("[data-sidebar-collapse]").forEach((button) => button.addEventListener("click", () => {
      setSidebarCollapsed(!document.documentElement.classList.contains("sidebar-collapsed"));
    }));

    document.querySelectorAll("[data-mobile-menu]").forEach((button) => button.addEventListener("click", openMobileSidebar));
    document.querySelectorAll("[data-sidebar-overlay]").forEach((overlay) => overlay.addEventListener("click", closeMobileSidebar));
    document.querySelectorAll(".app-sidebar a").forEach((link) => link.addEventListener("click", closeMobileSidebar));

    document.querySelectorAll("[data-mobile-more]").forEach((button) => button.addEventListener("click", toggleMobileMore));

    document.querySelectorAll("[data-customize-open]").forEach((button) => button.addEventListener("click", openCustomize));
    document.querySelectorAll("[data-customize-close]").forEach((button) => button.addEventListener("click", closeCustomize));
    document.querySelectorAll("[data-command-open]").forEach((button) => button.addEventListener("click", openCommand));

    const commandInput = document.querySelector("[data-command-input]");
    if (commandInput) commandInput.addEventListener("input", () => filterCommands(commandInput.value));

    document.querySelectorAll(".dialog-backdrop").forEach((backdrop) => {
      backdrop.addEventListener("mousedown", (event) => {
        if (event.target === backdrop) {
          backdrop.hidden = true;
          document.documentElement.classList.remove("dialog-open");
        }
      });
    });

    document.addEventListener("keydown", (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        openCommand();
        return;
      }
      if (event.key === "Escape") {
        closeCommand();
        closeCustomize();
        closeMobileSidebar();
        closeMobileMore();
      }
    });
  });
})();
