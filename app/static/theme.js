(function () {
  "use strict";

  const root = document.documentElement;
  const THEME_KEY = "theme";
  const PALETTE_KEY = "mlo.palette";
  const PALETTE_STYLE_KEY = "mlo.palette.style";
  const SIDEBAR_KEY = "mlo.sidebar.collapsed";
  const NAV_KEY = "mlo.navigation.v2";
  const validThemes = ["system", "light", "dark"];
  const validPalettes = ["neutral", "ocean", "sage", "rose", "amber", "lavender"];
  const validPaletteStyles = ["independent", "full"];
  const optionalNavKeys = ["todos", "courses", "items", "schedule", "finance", "expenses", "jobs", "timers"];

  function safeGet(key, fallback) {
    try {
      const value = localStorage.getItem(key);
      return value === null ? fallback : value;
    } catch (_) { return fallback; }
  }

  function safeSet(key, value) {
    try { localStorage.setItem(key, value); } catch (_) {}
  }

  function systemPrefersDark() {
    return !!(window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);
  }

  function normalizeTheme(mode) { return validThemes.includes(mode) ? mode : "system"; }
  function normalizePalette(palette) { return validPalettes.includes(palette) ? palette : "neutral"; }
  function normalizePaletteStyle(style) { return validPaletteStyles.includes(style) ? style : "independent"; }

  function applyTheme(mode) {
    mode = normalizeTheme(mode);
    const dark = mode === "dark" || (mode === "system" && systemPrefersDark());
    root.classList.toggle("dark", dark);
    root.dataset.theme = mode;
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", dark ? "#191919" : "#fbfbfa");
    return mode;
  }

  function applyPalette(palette) {
    palette = normalizePalette(palette);
    root.dataset.palette = palette;
    return palette;
  }

  function applyPaletteStyle(style) {
    style = normalizePaletteStyle(style);
    root.dataset.paletteStyle = style;
    return style;
  }

  function getTheme() { return normalizeTheme(safeGet(THEME_KEY, "system")); }
  function getPalette() { return normalizePalette(safeGet(PALETTE_KEY, "neutral")); }
  function getPaletteStyle() { return normalizePaletteStyle(safeGet(PALETTE_STYLE_KEY, "independent")); }

  function setTheme(mode) {
    mode = applyTheme(mode);
    safeSet(THEME_KEY, mode);
    renderAppearanceControls();
    document.dispatchEvent(new CustomEvent("mlo:themechange", { detail: { mode, palette: getPalette() } }));
    return mode;
  }

  function setPalette(palette) {
    palette = applyPalette(palette);
    safeSet(PALETTE_KEY, palette);
    renderAppearanceControls();
    document.dispatchEvent(new CustomEvent("mlo:palettechange", { detail: { mode: getTheme(), palette, style: getPaletteStyle() } }));
    return palette;
  }

  function setPaletteStyle(style) {
    style = applyPaletteStyle(style);
    safeSet(PALETTE_STYLE_KEY, style);
    renderAppearanceControls();
    document.dispatchEvent(new CustomEvent("mlo:palettestylechange", { detail: { mode: getTheme(), palette: getPalette(), style } }));
    return style;
  }

  function renderAppearanceControls() {
    const theme = getTheme();
    const palette = getPalette();
    const paletteStyle = getPaletteStyle();
    document.querySelectorAll("[data-theme-choice]").forEach((button) => {
      const active = button.dataset.themeChoice === theme;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });
    document.querySelectorAll("[data-palette-choice]").forEach((button) => {
      const active = button.dataset.paletteChoice === palette;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });
    document.querySelectorAll("[data-palette-style-choice]").forEach((button) => {
      const active = button.dataset.paletteStyleChoice === paletteStyle;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  window.__setTheme = setTheme;
  window.__getTheme = getTheme;
  window.__setPalette = setPalette;
  window.__getPalette = getPalette;
  window.__setPaletteStyle = setPaletteStyle;
  window.__getPaletteStyle = getPaletteStyle;

  applyTheme(getTheme());
  applyPalette(getPalette());
  applyPaletteStyle(getPaletteStyle());

  if (window.matchMedia) {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => { if (getTheme() === "system") applyTheme("system"); renderAppearanceControls(); };
    if (media.addEventListener) media.addEventListener("change", onChange);
    else if (media.addListener) media.addListener(onChange);
  }

  function getNavPrefs() {
    try {
      const parsed = JSON.parse(safeGet(NAV_KEY, "{}"));
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch (_) { return {}; }
  }

  function isNavVisible(key, prefs) {
    if (["dashboard", "settings", "sections", "admin"].includes(key)) return true;
    return prefs[key] !== false;
  }

  function applyNavPrefs() {
    const prefs = getNavPrefs();
    document.querySelectorAll("[data-nav-key]").forEach((el) => {
      const visible = isNavVisible(el.dataset.navKey, prefs);
      el.hidden = !visible;
      el.setAttribute("aria-hidden", visible ? "false" : "true");
    });
    document.querySelectorAll("[data-nav-setting]").forEach((input) => {
      input.checked = isNavVisible(input.dataset.navSetting, prefs);
    });
  }

  function setNavVisible(key, visible) {
    if (!optionalNavKeys.includes(key)) return;
    const prefs = getNavPrefs();
    prefs[key] = !!visible;
    safeSet(NAV_KEY, JSON.stringify(prefs));
    applyNavPrefs();
  }

  function resetNav() { safeSet(NAV_KEY, "{}"); applyNavPrefs(); }

  function setSidebarCollapsed(collapsed) {
    root.classList.toggle("sidebar-collapsed", collapsed);
    safeSet(SIDEBAR_KEY, collapsed ? "1" : "0");
    document.querySelectorAll("[data-sidebar-collapse]").forEach((button) => {
      button.setAttribute("aria-label", collapsed ? "Expand sidebar" : "Collapse sidebar");
      button.title = collapsed ? "Expand sidebar" : "Collapse sidebar";
    });
  }

  function closeMobileSidebar() {
    root.classList.remove("mobile-sidebar-open");
    const overlay = document.querySelector("[data-sidebar-overlay]");
    if (overlay) overlay.hidden = true;
  }

  function openMobileSidebar() {
    closeMobileMore();
    root.classList.add("mobile-sidebar-open");
    const overlay = document.querySelector("[data-sidebar-overlay]");
    if (overlay) overlay.hidden = false;
  }

  function closeMobileMore() {
    const sheet = document.querySelector("[data-mobile-more-sheet]");
    const button = document.querySelector("[data-mobile-more]");
    if (sheet) sheet.hidden = true;
    if (button) button.setAttribute("aria-expanded", "false");
  }

  function toggleMobileMore(event) {
    if (event) event.stopPropagation();
    const sheet = document.querySelector("[data-mobile-more-sheet]");
    const button = document.querySelector("[data-mobile-more]");
    if (!sheet || !button) return;
    const opening = sheet.hidden;
    if (opening) closeMobileSidebar();
    sheet.hidden = !opening;
    button.setAttribute("aria-expanded", opening ? "true" : "false");
  }

  function goBack(button) {
    const fallback = (button && button.dataset.backFallback) || "/";
    let canGoBackInsideApp = false;
    try {
      if (document.referrer) {
        const previous = new URL(document.referrer, window.location.href);
        canGoBackInsideApp = previous.origin === window.location.origin && window.history.length > 1;
      }
    } catch (_) {}

    if (canGoBackInsideApp) window.history.back();
    else window.location.assign(fallback);
  }

  function updateDialogOpenState() {
    root.classList.toggle("dialog-open", !!document.querySelector(".dialog-backdrop:not([hidden])"));
  }

  function setDialog(selector, open) {
    const dialog = document.querySelector(selector);
    if (!dialog) return;
    dialog.hidden = !open;
    updateDialogOpenState();
    if (open) {
      const focusTarget = dialog.querySelector("input, button, a");
      if (focusTarget) requestAnimationFrame(() => focusTarget.focus());
    }
  }

  function openCustomize() { closeMobileMore(); applyNavPrefs(); setDialog("[data-customize-dialog]", true); }
  function closeCustomize() { setDialog("[data-customize-dialog]", false); }
  function openCommand() {
    closeMobileMore();
    setDialog("[data-command-dialog]", true);
    const input = document.querySelector("[data-command-input]");
    if (input) { input.value = ""; filterCommands(""); requestAnimationFrame(() => input.focus()); }
  }
  function closeCommand() { setDialog("[data-command-dialog]", false); }

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
    const close = () => { menu.hidden = true; toggle.setAttribute("aria-expanded", "false"); };
    toggle.addEventListener("click", (event) => {
      event.stopPropagation();
      const opening = menu.hidden;
      menu.hidden = !opening;
      toggle.setAttribute("aria-expanded", opening ? "true" : "false");
    });
    document.addEventListener("click", (event) => { if (!menu.contains(event.target) && !toggle.contains(event.target)) close(); });
  }

  function formatClock(totalSeconds) {
    totalSeconds = Math.max(0, Math.floor(Number(totalSeconds) || 0));
    const h = Math.floor(totalSeconds / 3600);
    const m = Math.floor((totalSeconds % 3600) / 60);
    const s = totalSeconds % 60;
    return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}` : `${m}:${String(s).padStart(2, "0")}`;
  }

  function setupTimers() {
    const timers = Array.from(document.querySelectorAll("[data-timer-container], [data-sidebar-timer]"));
    if (!timers.length) return;
    const completed = new Set();
    const tick = () => {
      const now = Date.now();
      timers.forEach((timer) => {
        const display = timer.querySelector("[data-timer-display]");
        if (!display) return;
        let remaining = Number(timer.dataset.timerRemaining || 0);
        const status = timer.dataset.timerStatus || "paused";
        const started = timer.dataset.timerStarted ? Date.parse(timer.dataset.timerStarted) : NaN;
        if (status === "running" && Number.isFinite(started)) remaining = Math.max(0, remaining - Math.floor((now - started) / 1000));
        display.textContent = formatClock(remaining);
        timer.classList.toggle("timer-finished", remaining <= 0);
        const id = timer.dataset.timerId || timer.dataset.timerEndpoint || "timer";
        if (remaining <= 0 && status === "running" && !completed.has(id)) {
          completed.add(id);
          const endpoint = timer.dataset.timerEndpoint;
          if (endpoint) fetch(endpoint, { method: "POST", headers: { "X-Requested-With": "fetch" } }).catch(() => {});
          if ("Notification" in window && Notification.permission === "granted") {
            try { new Notification("Timer finished", { body: timer.dataset.timerLabel || "Your timer is complete." }); } catch (_) {}
          }
        }
      });
    };
    tick();
    window.setInterval(tick, 1000);
    document.querySelectorAll("[data-notification-permission]").forEach((button) => {
      button.addEventListener("click", async () => {
        if (!("Notification" in window)) return;
        const result = await Notification.requestPermission();
        button.textContent = result === "granted" ? "Notifications enabled" : "Notifications blocked";
      });
    });
  }

  function budgetAnnualMultiplier(frequency) {
    return ({ "Annually": 1, "Quarterly": 4, "Semi-annually": 2, "Monthly": 12, "Biweekly": 26, "Weekly": 52 })[frequency] || 12;
  }

  function setupBudgetChart() {
    const chart = document.querySelector("[data-budget-chart]");
    if (!chart) return;
    const colors = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)", "var(--chart-6)"];
    const groupOrder = ["Housing", "Essentials", "Transportation", "Living", "Personal spending", "Savings"];
    const fmt = new Intl.NumberFormat(undefined, { style: "currency", currency: "CAD", maximumFractionDigits: 0 });

    function recalc() {
      const totals = Object.fromEntries(groupOrder.map((g) => [g, 0]));
      let income = 0;
      document.querySelectorAll("[data-budget-row]").forEach((row) => {
        const amountInput = row.querySelector("[data-budget-amount]");
        const frequencyInput = row.querySelector("[data-budget-frequency]");
        const amount = Math.max(0, Number(String(amountInput?.value || "0").replace(/[$,]/g, "")) || 0);
        const annual = amount * budgetAnnualMultiplier(frequencyInput?.value || "Monthly");
        if (row.dataset.budgetKind === "income") income += annual;
        const group = row.dataset.budgetGroup;
        if (group && Object.prototype.hasOwnProperty.call(totals, group)) totals[group] += annual;
      });
      const total = groupOrder.reduce((sum, g) => sum + totals[g], 0);
      let cursor = 0;
      const stops = [];
      groupOrder.forEach((group, index) => {
        const pct = total > 0 ? (totals[group] / total) * 100 : 0;
        const start = cursor;
        cursor += pct;
        if (pct > 0) stops.push(`${colors[index]} ${start}% ${cursor}%`);
        const line = Array.from(chart.querySelectorAll("[data-chart-group]")).find((el) => el.dataset.chartGroup === group);
        if (line) {
          const pctEl = line.querySelector("[data-chart-percent]");
          const amountEl = line.querySelector("[data-chart-amount]");
          if (pctEl) pctEl.textContent = `${Math.round(pct)}%`;
          if (amountEl) amountEl.textContent = fmt.format(totals[group]);
          line.classList.toggle("is-zero", totals[group] <= 0);
        }
      });
      const donut = chart.querySelector("[data-budget-donut]");
      if (donut) donut.style.background = stops.length ? `conic-gradient(${stops.join(",")})` : "var(--panel3)";
      const incomeEl = chart.querySelector("[data-chart-income]");
      const expensesEl = chart.querySelector("[data-chart-expenses]");
      const leftEl = chart.querySelector("[data-chart-left]");
      if (incomeEl) incomeEl.textContent = fmt.format(income);
      if (expensesEl) expensesEl.textContent = fmt.format(total);
      if (leftEl) leftEl.textContent = fmt.format(income - total);
    }

    document.querySelectorAll("[data-budget-amount], [data-budget-frequency]").forEach((el) => {
      el.addEventListener("input", recalc);
      el.addEventListener("change", recalc);
    });
    recalc();
  }

  document.addEventListener("DOMContentLoaded", function () {
    renderAppearanceControls();
    applyNavPrefs();
    setSidebarCollapsed(safeGet(SIDEBAR_KEY, "0") === "1");
    setupQuickAdd();
    setupTimers();
    setupBudgetChart();

    document.querySelectorAll("[data-theme-choice]").forEach((button) => button.addEventListener("click", () => setTheme(button.dataset.themeChoice)));
    document.querySelectorAll("[data-palette-choice]").forEach((button) => button.addEventListener("click", () => setPalette(button.dataset.paletteChoice)));
    document.querySelectorAll("[data-palette-style-choice]").forEach((button) => button.addEventListener("click", () => setPaletteStyle(button.dataset.paletteStyleChoice)));
    document.querySelectorAll("[data-nav-setting]").forEach((input) => input.addEventListener("change", () => setNavVisible(input.dataset.navSetting, input.checked)));
    document.querySelectorAll("[data-nav-reset]").forEach((button) => button.addEventListener("click", resetNav));
    document.querySelectorAll("[data-sidebar-collapse]").forEach((button) => button.addEventListener("click", () => setSidebarCollapsed(!root.classList.contains("sidebar-collapsed"))));
    document.querySelectorAll("[data-mobile-menu]").forEach((button) => button.addEventListener("click", openMobileSidebar));
    document.querySelectorAll("[data-sidebar-overlay]").forEach((overlay) => overlay.addEventListener("click", closeMobileSidebar));
    document.querySelectorAll(".app-sidebar a").forEach((link) => link.addEventListener("click", closeMobileSidebar));
    document.querySelectorAll("[data-mobile-more]").forEach((button) => button.addEventListener("click", toggleMobileMore));
    document.querySelectorAll("[data-global-back]").forEach((button) => button.addEventListener("click", () => goBack(button)));
    document.querySelectorAll("[data-customize-open]").forEach((button) => button.addEventListener("click", openCustomize));
    document.querySelectorAll("[data-customize-close]").forEach((button) => button.addEventListener("click", closeCustomize));
    document.querySelectorAll("[data-command-open]").forEach((button) => button.addEventListener("click", openCommand));

    const commandInput = document.querySelector("[data-command-input]");
    if (commandInput) commandInput.addEventListener("input", () => filterCommands(commandInput.value));

    document.querySelectorAll(".dialog-backdrop").forEach((backdrop) => {
      backdrop.addEventListener("mousedown", (event) => {
        if (event.target === backdrop) { backdrop.hidden = true; updateDialogOpenState(); }
      });
    });

    document.addEventListener("click", (event) => {
      const sheet = document.querySelector("[data-mobile-more-sheet]");
      const button = document.querySelector("[data-mobile-more]");
      if (sheet && !sheet.hidden && !sheet.contains(event.target) && !button?.contains(event.target)) closeMobileMore();
    });

    document.addEventListener("keydown", (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") { event.preventDefault(); openCommand(); return; }
      if (event.key === "Escape") { closeCommand(); closeCustomize(); closeMobileSidebar(); closeMobileMore(); }
    });
  });
})();
