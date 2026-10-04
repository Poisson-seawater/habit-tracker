document.addEventListener("DOMContentLoaded", () => {
  // Config
  const API_BASE = "/api/v1";

  function getPaleColor(hex) {
    if (!hex) return "rgba(255, 255, 255, 0.15)";
    if (hex.startsWith("#")) {
      const cleanHex = hex.replace("#", "");
      let r = parseInt(cleanHex.substring(0, 2), 16);
      let g = parseInt(cleanHex.substring(2, 4), 16);
      let b = parseInt(cleanHex.substring(4, 6), 16);
      return `rgba(${r}, ${g}, ${b}, 0.2)`;
    }
    return hex;
  }

  // Keep API calls same-origin so HttpOnly auth cookies are sent automatically.
  const originalFetch = window.fetch;
  window.fetch = async function(url, options = {}) {
    options.credentials = options.credentials || "same-origin";
    const response = await originalFetch(url, options);
    const urlString = typeof url === "string" ? url : (url?.url || "");
    if (response.status === 401 && !urlString.includes("/auth/")) {
      showLoginScreen();
    }
    return response;
  };

  // Navigation Tabs
  const navTabs = document.querySelectorAll(".nav-tab");
  const tabContents = document.querySelectorAll(".tab-content");
  const perspectiveButtons = document.querySelectorAll(".perspective-view-button");
  const perspectiveViews = document.querySelectorAll(".perspective-view");
  let activePerspective = "goal-calendar-tab";

  function loadActivePerspective() {
    if (activePerspective === "life-weeks-tab") {
      loadLifeWeeks();
    } else {
      loadGoalCalendar();
    }
  }

  perspectiveButtons.forEach(button => {
    button.addEventListener("click", () => {
      activePerspective = button.dataset.perspective;
      perspectiveButtons.forEach(item => {
        item.setAttribute("aria-pressed", String(item === button));
      });
      perspectiveViews.forEach(view => {
        view.hidden = view.id !== activePerspective;
      });
      loadActivePerspective();
    });
  });

  navTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const targetTab = tab.getAttribute("data-tab");
      if (!targetTab) return;

      navTabs.forEach(t => t.classList.remove("active"));
      tabContents.forEach(c => c.classList.remove("active"));

      tab.classList.add("active");
      const targetElement = document.getElementById(targetTab);
      if (targetElement) {
        targetElement.classList.add("active");
      }

      // Context-aware refreshes
      if (targetTab === "goals-tab") {
        fetchGoals();
      } else if (targetTab === "settings-tab") {
        loadSettingsThresholds();
        loadCycleSettings();
        loadBioZoneSettings();
        loadAuthAdminSettings();
      } else if (targetTab === "softskills-tab") {
        fetchSoftskills();
      } else if (targetTab === "rewards-tab") {
        fetchRewards();
      } else if (targetTab === "perspectives-tab") {
        loadActivePerspective();
      } else if (targetTab === "jar-tab") {
        loadJarWeek();
      }
    });
  });

  // Profile and Dashboard Elements
  const charLevel = document.getElementById("char-level");
  const badgeStatus = document.getElementById("badge-status");
  const dayTypeStatus = document.getElementById("day-type-status");
  const feelOffBtn = document.getElementById("feel-off-btn");
  let activeDayType = "regular";
  const questsPanelTitle = document.getElementById("quests-panel-title");
  const questsListContainer = document.getElementById("quests-list-container");
  const questDaySummary = document.getElementById("quest-day-summary");
  const questArchivesPanel = document.getElementById("quest-archives-panel");
  const questArchivesList = document.getElementById("quest-archives-list");
  const questArchivesCount = document.getElementById("quest-archives-count");
  const toggleQuestAgendaBtn = document.getElementById("toggle-quest-agenda-btn");
  const toggleQuestArchivesBtn = document.getElementById("toggle-quest-archives-btn");
  const questBankPanel = document.getElementById("quest-bank-panel");
  const questBankList = document.getElementById("quest-bank-list");
  const questBankCount = document.getElementById("quest-bank-count");
  const toggleQuestBankBtn = document.getElementById("toggle-quest-bank-btn");
  let allHabitsCache = [];
  let questTagCatalog = null;
  const questTagEditorReady = { new: false, edit: false };
  let questPanelMode = "agenda";
  let showTodayBounties = true;
  const toastNotification = document.getElementById("toast-notification");

  // Daily quest view and template settings
  let loadedTemplates = {};
  let biologicalZonesCache = null;
  const toggleAddBlockBtn = document.getElementById("toggle-add-block-btn");
  const addBlockFormContainer = document.getElementById("add-block-form-container");
  const cancelAddBlockBtn = document.getElementById("cancel-add-block-btn");
  const saveBlockBtn = document.getElementById("save-block-btn");
  const blockTitleInput = document.getElementById("block-title");
  const blockStartInput = document.getElementById("block-start");
  const blockEndInput = document.getElementById("block-end");
  const blockCategorySelect = document.getElementById("block-category");
  const blockOverlapWarning = document.getElementById("block-overlap-warning");
  const agendaDateInput = document.getElementById("agenda-date-input");
  const agendaYesterdayBtn = document.getElementById("agenda-yesterday-btn");
  const agendaTodayBtn = document.getElementById("agenda-today-btn");
  const agendaRefreshBtn = document.getElementById("agenda-refresh-btn");
  const agendaDayTypeBadge = document.getElementById("agenda-day-type-badge");
  let questAgendaState = null;
  let directProgressInputActive = false;
  let trackedQuestId = null;
  let questTrackingTrigger = null;
  const questProgressMutationQueues = new Map();

  const bioZoneMeta = {
    deep_focus: { label: "Focus profond", emoji: "🧠", color: "#8b5cf6" },
    physical_peak: { label: "Pic physique", emoji: "💪", color: "#06b6d4" },
    creative: { label: "Créatif", emoji: "🎨", color: "#eab308" },
    rest: { label: "Repos", emoji: "🧘", color: "#22c55e" },
    social: { label: "Social", emoji: "🤝", color: "#f97316" },
    sleep: { label: "Sommeil", emoji: "😴", color: "#475569" }
  };

  // Show a glowing premium toast alert
  function showToast(message, isError = false) {
    toastNotification.textContent = message;
    toastNotification.style.display = "block";
    toastNotification.style.border = isError ? "1px solid var(--accent-red)" : "1px solid var(--accent-cyan)";
    toastNotification.style.boxShadow = isError ? "0 8px 24px rgba(239, 68, 68, 0.4)" : "0 8px 24px var(--accent-cyan-glow)";

    setTimeout(() => {
      toastNotification.style.display = "none";
    }, 4500);
  }

  function getBioZoneMeta(zoneType) {
    return bioZoneMeta[zoneType] || { label: zoneType || "Zone", emoji: "•", color: "#94a3b8" };
  }

  function todayDateString() {
    const now = new Date();
    const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 10);
  }

  // Jar of Life is an explicit weekly plan. It never edits quests or To-dos.
  const jarGrid = document.getElementById("jar-grid");
  const jarItems = document.getElementById("jar-items");
  const jarCandidatesEl = document.getElementById("jar-candidates");
  const jarStatus = document.getElementById("jar-status");
  const jarSave = document.getElementById("jar-save");
  const JAR_PARTS = [
    ["morning", "Matin"], ["afternoon", "Après-midi"], ["evening", "Soir"]
  ];
  const JAR_CATEGORIES = { rock: "Gros caillou", pebble: "Galet", sand: "Sable" };
  let jarWeekStart = jarMonday(todayDateString());
  let jarPlan = null;
  let jarCandidates = [];
  let jarDirty = false;
  let jarRevision = 0;
  let jarLoadToken = 0;

  function jarDate(value) {
    return new Date(`${value}T12:00:00`);
  }

  function jarDateString(date) {
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  }

  function jarMonday(value) {
    const date = jarDate(value);
    date.setDate(date.getDate() - (date.getDay() + 6) % 7);
    return jarDateString(date);
  }

  function jarShiftWeek(value, days) {
    const date = jarDate(value);
    date.setDate(date.getDate() + days);
    return jarDateString(date);
  }

  function setJarStatus(message, error = false) {
    jarStatus.textContent = message;
    jarStatus.classList.toggle("jar-error", error);
  }

  function markJarDirty() {
    jarDirty = true;
    jarRevision += 1;
    jarSave.disabled = false;
    setJarStatus("Modifications à enregistrer.");
    renderJar();
  }

  function jarNewId() {
    if (window.crypto?.randomUUID) return window.crypto.randomUUID();
    return `jar-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  }

  function jarRockCount() {
    return jarPlan.items.filter(item => item.category === "rock").length;
  }

  function renderJar() {
    if (!jarPlan) return;
    const first = jarDate(jarWeekStart);
    const last = jarDate(jarShiftWeek(jarWeekStart, 6));
    const dateLabel = date => new Intl.DateTimeFormat("fr-CA", { day: "numeric", month: "short" }).format(date);
    document.getElementById("jar-week-label").textContent = `${dateLabel(first)} – ${dateLabel(last)}`;
    const available = new Set(jarPlan.available_blocks);
    const used = Object.keys(jarPlan.placements).length;
    const protectedRocks = new Set(Object.values(jarPlan.placements).filter(id =>
      jarPlan.items.some(item => item.id === id && item.category === "rock")));
    const unplacedRocks = jarPlan.items.filter(item => item.category === "rock" && !protectedRocks.has(item.id));
    const summary = document.getElementById("jar-summary");
    summary.innerHTML = `<span><strong>${available.size}</strong> bloc${available.size > 1 ? "s" : ""} disponible${available.size > 1 ? "s" : ""}</span>
      <span><strong>${used}</strong> réservé${used > 1 ? "s" : ""}</span>
      <span><strong>${available.size - used}</strong> libre${available.size - used > 1 ? "s" : ""} pour la marge</span>
      <span>Gros cailloux protégés <strong>${protectedRocks.size}/${jarRockCount()}</strong></span>`;
    if (unplacedRocks.length) {
      summary.innerHTML += `<p class="jar-warning">${unplacedRocks.length} gros caillou${unplacedRocks.length > 1 ? "x" : ""} sans bloc.</p>`;
    }

    const itemOptions = jarPlan.items.map(item =>
      `<option value="${escapeHtml(item.id)}">${JAR_CATEGORIES[item.category]} · ${escapeHtml(item.title)}</option>`
    ).join("");
    jarGrid.innerHTML = Array.from({ length: 7 }, (_, dayIndex) => {
      const date = jarDate(jarShiftWeek(jarWeekStart, dayIndex));
      const dayLabel = new Intl.DateTimeFormat("fr-CA", { weekday: "long", day: "numeric", month: "short" }).format(date);
      const slots = JAR_PARTS.map(([part, partLabel]) => {
        const block = `${dayIndex}-${part}`;
        const enabled = available.has(block);
        const selected = jarPlan.placements[block] || "";
        return `<div class="jar-block ${enabled ? "jar-block-available" : ""} ${selected ? "jar-block-planned" : ""}">
          <label><input type="checkbox" class="jar-available" data-block="${block}" ${enabled ? "checked" : ""}> ${partLabel}</label>
          <select class="jar-placement" data-block="${block}" aria-label="Focus ${escapeHtml(dayLabel)} ${partLabel}" ${enabled ? "" : "disabled"}>
            <option value="">${enabled ? "Garder libre" : "Indisponible"}</option>
            ${itemOptions}
          </select>
        </div>`.replace(`<option value="${escapeHtml(selected)}">`, `<option value="${escapeHtml(selected)}" selected>`);
      }).join("");
      return `<section class="jar-day"><h4>${escapeHtml(dayLabel)}</h4>${slots}</section>`;
    }).join("");

    jarItems.innerHTML = ["rock", "pebble", "sand"].map(category => {
      const rows = jarPlan.items.filter(item => item.category === category).map(item => {
        const slots = Object.values(jarPlan.placements).filter(id => id === item.id).length;
        return `<div class="jar-item" data-id="${escapeHtml(item.id)}">
          <span><strong>${escapeHtml(item.title)}</strong>${item.source_type ? ` <small>(${item.source_type === "habit" ? "Quête" : "To-do"})</small>` : ""}<small>${slots} bloc${slots > 1 ? "s" : ""}</small></span>
          <label class="jar-sr-only" for="jar-category-${escapeHtml(item.id)}">Classement de ${escapeHtml(item.title)}</label>
          <select id="jar-category-${escapeHtml(item.id)}" class="jar-item-category" data-id="${escapeHtml(item.id)}">
            ${Object.entries(JAR_CATEGORIES).map(([value, label]) => `<option value="${value}" ${value === category ? "selected" : ""}>${label}</option>`).join("")}
          </select>
          <button type="button" class="jar-item-delete" data-id="${escapeHtml(item.id)}" aria-label="Retirer ${escapeHtml(item.title)}">×</button>
        </div>`;
      }).join("");
      return `<div class="jar-item-group"><h4>${JAR_CATEGORIES[category]}${category === "rock" ? ` (${jarRockCount()}/3)` : ""}</h4>${rows || `<p class="jar-hint">Aucun élément.</p>`}</div>`;
    }).join("");

    jarCandidatesEl.innerHTML = jarCandidates.length ? jarCandidates.map((candidate, index) => {
      const imported = jarPlan.items.some(item => item.source_type === candidate.source_type && item.source_id === candidate.source_id);
      const days = candidate.days.map(day => new Intl.DateTimeFormat("fr-CA", { weekday: "short" }).format(jarDate(day))).join(", ");
      return `<div class="jar-candidate">
        <span><strong>${escapeHtml(candidate.title)}</strong><small>${candidate.source_type === "habit" ? "Quête" : "To-do"} · ${escapeHtml(days)}</small></span>
        <select class="jar-import-category" data-index="${index}" aria-label="Classement de ${escapeHtml(candidate.title)}">
          <option value="rock">Gros caillou</option><option value="pebble" selected>Galet</option><option value="sand">Sable</option>
        </select>
        <button type="button" class="jar-import" data-index="${index}" ${imported ? "disabled" : ""}>${imported ? "Ajouté" : "Ajouter"}</button>
      </div>`;
    }).join("") : `<p class="jar-hint">Aucune quête ni To-do datée cette semaine.</p>`;
  }

  async function loadJarWeek() {
    if (jarPlan && jarDirty) return;
    const token = ++jarLoadToken;
    setJarStatus("Chargement de la semaine…");
    jarSave.disabled = true;
    try {
      const response = await fetch(`${API_BASE}/jar-of-life/${jarWeekStart}`);
      if (!response.ok) throw new Error("La semaine n'a pas pu être chargée.");
      const data = await response.json();
      if (token !== jarLoadToken) return;
      jarPlan = data.plan;
      jarCandidates = data.candidates || [];
      jarDirty = false;
      renderJar();
      setJarStatus("Choisis tes priorités et tes blocs, puis enregistre la semaine.");
    } catch (error) {
      if (token === jarLoadToken) setJarStatus(error.message, true);
    }
  }

  async function saveJarWeek() {
    if (!jarPlan || !jarDirty) return;
    const savedWeek = jarWeekStart;
    const savedRevision = jarRevision;
    const body = JSON.stringify({
      available_blocks: jarPlan.available_blocks,
      items: jarPlan.items,
      placements: jarPlan.placements
    });
    jarSave.disabled = true;
    setJarStatus("Enregistrement…");
    try {
      const response = await fetch(`${API_BASE}/jar-of-life/${savedWeek}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body
      });
      if (!response.ok) throw new Error("L'enregistrement a échoué.");
      if (savedWeek !== jarWeekStart) return;
      const savedPlan = await response.json();
      if (savedRevision !== jarRevision) {
        jarSave.disabled = false;
        setJarStatus("De nouvelles modifications restent à enregistrer.");
        return;
      }
      jarPlan = savedPlan;
      jarDirty = false;
      renderJar();
      setJarStatus("Semaine enregistrée.");
    } catch (error) {
      jarSave.disabled = false;
      setJarStatus(error.message, true);
    }
  }

  function navigateJarWeek(days, thisWeek = false) {
    if (jarDirty && !window.confirm("Quitter cette semaine sans enregistrer les modifications ?")) return;
    jarWeekStart = thisWeek ? jarMonday(todayDateString()) : jarShiftWeek(jarWeekStart, days);
    jarPlan = null;
    loadJarWeek();
  }

  document.getElementById("jar-prev")?.addEventListener("click", () => navigateJarWeek(-7));
  document.getElementById("jar-next")?.addEventListener("click", () => navigateJarWeek(7));
  document.getElementById("jar-today")?.addEventListener("click", () => navigateJarWeek(0, true));
  jarSave?.addEventListener("click", saveJarWeek);

  document.getElementById("jar-add-form")?.addEventListener("submit", event => {
    event.preventDefault();
    if (!jarPlan) return;
    const titleInput = document.getElementById("jar-item-title");
    const title = titleInput.value.trim();
    const category = document.getElementById("jar-item-category").value;
    if (!title) return;
    if (category === "rock" && jarRockCount() >= 3) {
      setJarStatus("Trois gros cailloux maximum par semaine.", true);
      return;
    }
    jarPlan.items.push({ id: jarNewId(), title, category, source_type: null, source_id: null });
    titleInput.value = "";
    markJarDirty();
  });

  jarGrid?.addEventListener("change", event => {
    if (!jarPlan) return;
    const block = event.target.dataset.block;
    if (!block) return;
    if (event.target.classList.contains("jar-available")) {
      if (event.target.checked) jarPlan.available_blocks.push(block);
      else {
        jarPlan.available_blocks = jarPlan.available_blocks.filter(value => value !== block);
        delete jarPlan.placements[block];
      }
    } else if (event.target.classList.contains("jar-placement")) {
      if (event.target.value) jarPlan.placements[block] = event.target.value;
      else delete jarPlan.placements[block];
    }
    markJarDirty();
  });

  jarItems?.addEventListener("change", event => {
    if (!jarPlan || !event.target.classList.contains("jar-item-category")) return;
    const item = jarPlan.items.find(entry => entry.id === event.target.dataset.id);
    if (!item) return;
    if (event.target.value === "rock" && item.category !== "rock" && jarRockCount() >= 3) {
      setJarStatus("Trois gros cailloux maximum par semaine.", true);
      renderJar();
      return;
    }
    item.category = event.target.value;
    markJarDirty();
  });

  jarItems?.addEventListener("click", event => {
    const button = event.target.closest(".jar-item-delete");
    if (!jarPlan || !button) return;
    const id = button.dataset.id;
    jarPlan.items = jarPlan.items.filter(item => item.id !== id);
    Object.keys(jarPlan.placements).forEach(block => {
      if (jarPlan.placements[block] === id) delete jarPlan.placements[block];
    });
    markJarDirty();
  });

  jarCandidatesEl?.addEventListener("click", event => {
    const button = event.target.closest(".jar-import");
    if (!jarPlan || !button) return;
    const index = Number(button.dataset.index);
    const candidate = jarCandidates[index];
    const category = jarCandidatesEl.querySelector(`.jar-import-category[data-index="${index}"]`)?.value;
    if (!candidate || !JAR_CATEGORIES[category]) return;
    if (category === "rock" && jarRockCount() >= 3) {
      setJarStatus("Trois gros cailloux maximum par semaine.", true);
      return;
    }
    jarPlan.items.push({
      id: jarNewId(), title: candidate.title.slice(0, 120), category,
      source_type: candidate.source_type, source_id: candidate.source_id
    });
    markJarDirty();
  });

  // Perspective views share goal data; only explicit Gantt choices write to the API.
  const lifeWeeksForm = document.getElementById("life-weeks-form");
  const lifeWeeksBirthdate = document.getElementById("life-weeks-birthdate");
  const lifeWeeksHorizon = document.getElementById("life-weeks-horizon");
  const lifeWeeksError = document.getElementById("life-weeks-error");
  const lifeWeeksView = document.getElementById("life-weeks-view");
  const lifeWeeksGrid = document.getElementById("life-weeks-grid");
  const lifeWeeksPlanList = document.getElementById("life-weeks-plan-list");
  const lifeWeeksSummary = document.getElementById("life-weeks-summary");
  const LIFE_WEEKS_STORAGE_KEY = "habit-tracker-life-weeks";
  const LIFE_WEEKS_DEFAULTS = { birthdate: "2001-01-01", horizon: 90 };
  const WEEK_MS = 7 * 24 * 60 * 60 * 1000;
  let lifeWeeksSettings = { ...LIFE_WEEKS_DEFAULTS };
  let lifeWeeksGoals = [];
  let lifeWeeksLoadError = false;

  function monthNumber(value) {
    const [year, month] = value.slice(0, 7).split("-").map(Number);
    return year * 12 + month - 1;
  }

  function monthValue(number) {
    return `${Math.floor(number / 12).toString().padStart(4, "0")}-${String(number % 12 + 1).padStart(2, "0")}`;
  }

  function parseLifeWeeksBirthdate(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
    const [year, month, day] = value.split("-").map(Number);
    const date = new Date(Date.UTC(year, month - 1, day));
    if (year < 1900 || date.getUTCFullYear() !== year ||
        date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) return null;
    return date;
  }

  function lifeWeeksAnniversary(birthdate, age) {
    // For a 29 February birth, the anniversary falls on 1 March in non-leap years.
    return Date.UTC(birthdate.getUTCFullYear() + age,
      birthdate.getUTCMonth(), birthdate.getUTCDate());
  }

  function validLifeWeeksSettings(settings) {
    const birthdate = parseLifeWeeksBirthdate(settings.birthdate);
    const horizon = settings.horizon;
    const now = new Date();
    const today = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
    return birthdate && birthdate.getTime() <= today &&
      Number.isInteger(horizon) && horizon >= 1 && horizon <= 120 &&
      lifeWeeksAnniversary(birthdate, horizon) > today;
  }

  function planLifeWeeks(goals, birthdate, horizon, today) {
    const birth = birthdate.getTime();
    const horizonEnd = lifeWeeksAnniversary(birthdate, horizon);
    const totalWeeks = Math.ceil((horizonEnd - birth) / WEEK_MS);
    const firstFutureWeek = Math.floor((today - birth) / WEEK_MS) + 1;
    const candidates = [];
    const manual = [];
    const seen = new Set();
    for (const goal of goals) {
      for (const substep of goal.substeps || []) {
        if (seen.has(substep.id) || (substep.completed && !substep.life_chosen_start_month) ||
            !substep.life_duration_months || !substep.life_earliest_month ||
            !substep.life_latest_month) continue;
        seen.add(substep.id);
        const durationWeeks = Math.max(1, Math.round(
          substep.life_duration_months * 365.2425 / 12 / 7
        ));
        const earliest = Date.parse(`${substep.life_earliest_month.slice(0, 7)}-01T00:00:00Z`);
        const [year, month] = substep.life_latest_month.slice(0, 7).split("-").map(Number);
        const latestExclusive = Date.UTC(year, month, 1);
        const item = {
          goal, substep, durationWeeks,
          earliestIndex: Math.max(firstFutureWeek, Math.ceil((earliest - birth) / WEEK_MS)),
          endIndex: Math.min(totalWeeks, Math.floor((latestExclusive - birth) / WEEK_MS))
        };
        if (substep.life_chosen_start_month) manual.push(item);
        else candidates.push(item);
      }
    }
    // Narrower deadlines get the first chance; the result is illustrative.
    candidates.sort((a, b) => a.endIndex - b.endIndex ||
      a.earliestIndex - b.earliestIndex || a.goal.id - b.goal.id ||
      a.substep.execution_order - b.substep.execution_order || a.substep.id - b.substep.id);
    const occupied = new Uint8Array(totalWeeks);
    const byWeek = new Map();
    const placed = [];
    const unplaced = [];
    for (const item of manual) {
      const startMonth = monthNumber(item.substep.life_chosen_start_month);
      const start = Date.parse(`${monthValue(startMonth)}-01T00:00:00Z`);
      const end = Date.parse(`${monthValue(startMonth + item.substep.life_duration_months)}-01T00:00:00Z`);
      item.startIndex = Math.floor((start - birth) / WEEK_MS);
      item.durationWeeks = Math.ceil((end - birth) / WEEK_MS) - item.startIndex;
      item.manual = true;
      placed.push(item);
      for (let week = Math.max(0, item.startIndex);
           week < Math.min(totalWeeks, item.startIndex + item.durationWeeks); week++) {
        occupied[week] = 1;
        if (!byWeek.has(week)) byWeek.set(week, []);
        byWeek.get(week).push(item);
      }
    }
    for (const item of candidates) {
      let chosen = -1;
      for (let start = item.earliestIndex;
           start + item.durationWeeks <= item.endIndex; start++) {
        let free = true;
        for (let week = start; week < start + item.durationWeeks; week++) {
          if (occupied[week]) { free = false; break; }
        }
        if (free) { chosen = start; break; }
      }
      if (chosen < 0) {
        unplaced.push(item);
        continue;
      }
      item.startIndex = chosen;
      placed.push(item);
      for (let week = chosen; week < chosen + item.durationWeeks; week++) {
        occupied[week] = 1;
        if (!byWeek.has(week)) byWeek.set(week, []);
        byWeek.get(week).push(item);
      }
    }
    placed.sort((a, b) => a.startIndex - b.startIndex);
    return { placed, unplaced, byWeek };
  }

  async function openLifeWeekSubstep(item) {
    activeGoalId = item.goal.id;
    document.querySelector('.nav-tab[data-tab="goals-tab"]').click();
    const goals = await fetchGoals();
    const goal = goals.find(entry => entry.id === item.goal.id);
    const substep = goal?.substeps.find(entry => entry.id === item.substep.id);
    if (substep) openDrawer("edit-substep", null, substep, goal.substeps);
  }

  function renderLifeWeeksPlanList(plan, birthdate) {
    lifeWeeksPlanList.replaceChildren();
    if (lifeWeeksLoadError) {
      lifeWeeksPlanList.textContent = "Impossible de charger les objectifs pour cette vue.";
      return;
    }
    if (!plan.placed.length && !plan.unplaced.length) {
      lifeWeeksPlanList.textContent = "Aucune sous-étape avec durée et fenêtre possible. Configure-en une dans Objectifs & Graphes.";
      return;
    }
    const monthLabel = new Intl.DateTimeFormat("fr-CA", {
      month: "long", year: "numeric", timeZone: "UTC"
    });
    for (const item of plan.placed) {
      const start = item.manual
        ? Date.parse(`${item.substep.life_chosen_start_month.slice(0, 7)}-01T00:00:00Z`)
        : birthdate.getTime() + item.startIndex * WEEK_MS;
      const end = item.manual
        ? Date.parse(`${monthValue(monthNumber(item.substep.life_chosen_start_month) + item.substep.life_duration_months - 1)}-01T00:00:00Z`)
        : start + item.durationWeeks * WEEK_MS - 1;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "life-weeks-plan-item";
      const possibleStart = monthLabel.format(Date.parse(`${item.substep.life_earliest_month.slice(0, 7)}-01T00:00:00Z`));
      const possibleEnd = monthLabel.format(Date.parse(`${item.substep.life_latest_month.slice(0, 7)}-01T00:00:00Z`));
      button.textContent = `${item.substep.title} · ${item.goal.title} · ${item.manual ? "choisi" : "suggestion"} ${monthLabel.format(start)}–${monthLabel.format(end)} · possible de ${possibleStart} à ${possibleEnd}`;
      button.title = "Ouvrir la sous-étape";
      button.addEventListener("click", () => openLifeWeekSubstep(item));
      lifeWeeksPlanList.appendChild(button);
    }
    for (const item of plan.unplaced) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "life-weeks-plan-item life-weeks-unplaced";
      button.textContent = `${item.substep.title} · ${item.durationWeeks} semaines · aucune place automatique trouvée avant ${monthLabel.format(Date.parse(`${item.substep.life_latest_month.slice(0, 7)}-01T00:00:00Z`))}`;
      button.addEventListener("click", () => openLifeWeekSubstep(item));
      lifeWeeksPlanList.appendChild(button);
    }
  }

  async function loadLifeWeeks() {
    try {
      const response = await fetch(`${API_BASE}/goals`);
      if (!response.ok) throw new Error("Goals unavailable");
      lifeWeeksGoals = await response.json();
      lifeWeeksLoadError = false;
    } catch (error) {
      lifeWeeksGoals = [];
      lifeWeeksLoadError = true;
    }
    renderLifeWeeks();
  }

  function renderLifeWeeks() {
    if (!lifeWeeksForm) return;
    const birthdate = parseLifeWeeksBirthdate(lifeWeeksSettings.birthdate);
    const horizon = lifeWeeksSettings.horizon;
    const now = new Date();
    const today = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
    const plan = planLifeWeeks(lifeWeeksGoals, birthdate, horizon, today);
    renderLifeWeeksPlanList(plan, birthdate);

    const fragment = document.createDocumentFragment();
    const formatDate = new Intl.DateTimeFormat("fr-CA", {
      day: "numeric", month: "long", year: "numeric", timeZone: "UTC"
    });
    let weekStart = birthdate.getTime();
    let lived = 0;
    let future = 0;
    let weekIndex = 0;
    for (let age = 0; age < horizon; age++) {
      const nextAnniversary = lifeWeeksAnniversary(birthdate, age + 1);
      const row = document.createElement("div");
      row.className = "life-weeks-row";
      const label = document.createElement("span");
      label.className = "life-weeks-age";
      label.textContent = `${age} ans`;
      row.appendChild(label);
      const cells = document.createElement("div");
      cells.className = "life-weeks-cells";
      while (weekStart < nextAnniversary) {
        const cell = document.createElement("span");
        const state = weekStart + WEEK_MS <= today ? "lived" :
          weekStart <= today ? "current" : "future";
        const adventures = plan.byWeek.get(weekIndex) || [];
        cell.className = `life-week life-week-${adventures.length ? adventures.some(item => item.manual) ? "chosen" : "planned" : state}`;
        if (adventures.length > 1) cell.classList.add("life-week-overlap");
        cell.title = adventures.length
          ? `${adventures.map(item => `${item.substep.title} (${item.manual ? "choisi" : "suggestion"})`).join(" · ")} · semaine du ${formatDate.format(weekStart)}`
          : `Semaine du ${formatDate.format(weekStart)}`;
        if (adventures.length === 1) cell.addEventListener("click", () => openLifeWeekSubstep(adventures[0]));
        cells.appendChild(cell);
        if (state === "lived") lived++;
        if (state === "future") future++;
        weekStart += WEEK_MS;
        weekIndex++;
      }
      row.appendChild(cells);
      fragment.appendChild(row);
    }
    lifeWeeksGrid.replaceChildren(fragment);
    lifeWeeksSummary.textContent = `${lived.toLocaleString("fr-CA")} semaines traversées · Cette semaine en cours · ${future.toLocaleString("fr-CA")} semaines à venir jusqu'à ${horizon} ans`;
    lifeWeeksView.hidden = false;
  }

  if (lifeWeeksForm) {
    lifeWeeksBirthdate.max = todayDateString();
    try {
      const saved = JSON.parse(localStorage.getItem(LIFE_WEEKS_STORAGE_KEY) || "null");
      if (saved && validLifeWeeksSettings(saved)) lifeWeeksSettings = saved;
    } catch (error) {
      // Use defaults when browser storage is unavailable or invalid.
    }
    lifeWeeksBirthdate.value = lifeWeeksSettings.birthdate;
    lifeWeeksHorizon.value = lifeWeeksSettings.horizon;
    lifeWeeksForm.addEventListener("submit", event => {
      event.preventDefault();
      const nextSettings = {
        birthdate: lifeWeeksBirthdate.value,
        horizon: Number(lifeWeeksHorizon.value)
      };
      if (!validLifeWeeksSettings(nextSettings)) {
        lifeWeeksError.textContent = "Entre une date de naissance valide et un âge de référence situé après aujourd'hui (1 à 120 ans).";
        lifeWeeksError.hidden = false;
        return;
      }
      lifeWeeksError.hidden = true;
      lifeWeeksSettings = nextSettings;
      renderLifeWeeks();
      try {
        localStorage.setItem(LIFE_WEEKS_STORAGE_KEY, JSON.stringify(lifeWeeksSettings));
      } catch (error) {
        // Display still works without persistence.
      }
    });
    document.getElementById("life-weeks-reset").addEventListener("click", () => {
      lifeWeeksSettings = { ...LIFE_WEEKS_DEFAULTS };
      lifeWeeksBirthdate.value = lifeWeeksSettings.birthdate;
      lifeWeeksHorizon.value = lifeWeeksSettings.horizon;
      lifeWeeksError.hidden = true;
      renderLifeWeeks();
      try {
        localStorage.removeItem(LIFE_WEEKS_STORAGE_KEY);
      } catch (error) {
        // Defaults still work without browser storage.
      }
    });
    document.getElementById("life-weeks-settings-link").addEventListener("click", () => {
      document.querySelector('.nav-tab[data-tab="settings-tab"]').click();
      lifeWeeksBirthdate.focus();
    });
  }

  const goalCalendarView = document.getElementById("goal-calendar-view");
  const goalCalendarStatus = document.getElementById("goal-calendar-status");
  const goalCalendarFilter = document.getElementById("goal-calendar-filter");
  const currentMonth = new Date();
  let goalCalendarStart = currentMonth.getFullYear() * 12 + currentMonth.getMonth() - 3;
  let goalCalendarGoals = [];
  function calendarLabel(month) {
    const [year, number] = monthValue(month).split("-");
    return `${number}/${year}`;
  }

  function calendarPeriodLabel(first, last) {
    return first === last ? calendarLabel(first) : `${calendarLabel(first)} → ${calendarLabel(last)}`;
  }

  function appendCalendarBar(track, first, last, kind, busyMonths = []) {
    const visibleFirst = Math.max(first, goalCalendarStart);
    const visibleLast = Math.min(last, goalCalendarStart + 23);
    if (visibleFirst > visibleLast) return;
    const bar = document.createElement("div");
    bar.className = `goal-calendar-bar goal-calendar-${kind}`;
    bar.style.gridColumn = `${visibleFirst - goalCalendarStart + 1} / ${visibleLast - goalCalendarStart + 2}`;
    const period = calendarPeriodLabel(first, last);
    const name = kind === "possible" ? "Fenêtre possible" : "Période choisie";
    bar.title = `${name} : ${period}`;
    if (first < visibleFirst || last > visibleLast) {
      bar.classList.add("goal-calendar-clipped");
      bar.title += " · période partiellement visible";
    }
    if (busyMonths.length) {
      bar.classList.add("goal-calendar-busy");
      bar.title += ` · Chevauchement : ${busyMonths.map(calendarLabel).join(", ")}`;
    }
    bar.setAttribute("aria-label", bar.title);
    const dates = document.createElement("span");
    dates.textContent = period;
    bar.appendChild(dates);
    track.appendChild(bar);
  }

  function calendarButton(label, action) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.addEventListener("click", action);
    return button;
  }

  function renderGoalCalendar() {
    if (!goalCalendarView) return;
    goalCalendarView.replaceChildren();
    const seen = new Set();
    const entries = [];
    const visibleGoals = goalCalendarGoals.filter(goal =>
      !goalCalendarFilter.value || String(goal.id) === goalCalendarFilter.value
    );
    for (const goal of visibleGoals) {
      const steps = [];
      for (const substep of goal.substeps || []) {
        if (seen.has(substep.id)) continue;
        seen.add(substep.id);
        steps.push(substep);
        entries.push({ goal, substep });
      }
      goal._calendarSteps = steps;
    }
    if (!entries.length) {
      goalCalendarStatus.textContent = goalCalendarFilter.value
        ? "Aucune sous-étape pour cet objectif. Ajoute ses étapes dans Objectifs & Graphes."
        : "Aucune sous-étape. Crée un objectif et ses étapes dans Objectifs & Graphes.";
      return;
    }
    const counts = new Map();
    for (const { substep } of entries) {
      if (!substep.life_chosen_start_month || !substep.life_duration_months) continue;
      const start = monthNumber(substep.life_chosen_start_month);
      for (let month = start; month < start + substep.life_duration_months; month++) {
        counts.set(month, (counts.get(month) || 0) + 1);
      }
    }
    for (const goal of visibleGoals) {
      if (!goal._calendarSteps.length) continue;
      const heading = document.createElement("h3");
      heading.className = "goal-calendar-goal";
      heading.textContent = goal.title;
      goalCalendarView.appendChild(heading);
      for (const substep of goal._calendarSteps) {
        const row = document.createElement("div");
        row.className = "goal-calendar-row";
        const label = document.createElement("div");
        label.className = "goal-calendar-label";
        label.appendChild(calendarButton(substep.title, () => openLifeWeekSubstep({ goal, substep })));
        if (substep.completed) label.classList.add("goal-calendar-completed");
        row.appendChild(label);
        const hasWindow = Boolean(substep.life_duration_months && substep.life_earliest_month && substep.life_latest_month);
        const first = hasWindow ? monthNumber(substep.life_earliest_month) : -1;
        const last = hasWindow ? monthNumber(substep.life_latest_month) : -1;
        const chosen = substep.life_chosen_start_month ? monthNumber(substep.life_chosen_start_month) : -1;
        const track = document.createElement("div");
        track.className = "goal-calendar-track";
        const todayOffset = currentMonth.getFullYear() * 12 + currentMonth.getMonth() - goalCalendarStart;
        if (todayOffset >= 0 && todayOffset < 24) {
          const marker = document.createElement("span");
          marker.className = "goal-calendar-current";
          marker.style.gridColumn = `${todayOffset + 1}`;
          marker.title = `Mois actuel : ${calendarLabel(goalCalendarStart + todayOffset)}`;
          marker.setAttribute("aria-label", marker.title);
          track.appendChild(marker);
        }
        if (hasWindow) appendCalendarBar(track, first, last, "possible");
        const busyMonths = [];
        if (chosen >= 0 && substep.life_duration_months) {
          const chosenEnd = chosen + substep.life_duration_months - 1;
          for (let month = chosen; month <= chosenEnd; month++) {
            if ((counts.get(month) || 0) > 1) busyMonths.push(month);
          }
          appendCalendarBar(track, chosen, chosenEnd, "chosen", busyMonths);
        }
        row.appendChild(track);
        goalCalendarView.appendChild(row);
        const controls = document.createElement("div");
        controls.className = "goal-calendar-placement";
        if (!hasWindow || last - first + 1 < substep.life_duration_months) {
          controls.append(hasWindow
            ? "La durée dépasse la fenêtre possible. "
            : "Ajoute d'abord une durée et une fenêtre possible. ");
          controls.appendChild(calendarButton("Configurer", () => openLifeWeekSubstep({ goal, substep })));
        } else {
          const possible = document.createElement("span");
          possible.textContent = `Possible : ${calendarPeriodLabel(first, last)} · durée ${substep.life_duration_months} mois`;
          controls.appendChild(possible);
          if (chosen >= 0) {
            const period = document.createElement("span");
            period.textContent = `Choisi : ${calendarPeriodLabel(chosen, chosen + substep.life_duration_months - 1)}`;
            controls.appendChild(period);
          }
          if (busyMonths.length) {
            const warning = document.createElement("span");
            warning.className = "goal-calendar-overlap";
            warning.textContent = `Chevauchement · ${busyMonths.length} mois`;
            warning.title = busyMonths.map(calendarLabel).join(", ");
            controls.appendChild(warning);
          }
          const form = document.createElement("form");
          form.className = "goal-calendar-form";
          const inputLabel = document.createElement("label");
          inputLabel.textContent = "Début choisi ";
          const input = document.createElement("input");
          input.type = "month";
          input.required = true;
          input.min = monthValue(first);
          input.max = monthValue(last - substep.life_duration_months + 1);
          input.value = substep.life_chosen_start_month?.slice(0, 7) || "";
          inputLabel.appendChild(input);
          form.appendChild(inputLabel);
          form.appendChild(calendarButton("Enregistrer", () => form.requestSubmit()));
          if (substep.life_chosen_start_month) {
            form.appendChild(calendarButton("Retirer le choix", () => saveGoalCalendarPlacement(substep, null)));
          }
          form.addEventListener("submit", event => {
            event.preventDefault();
            saveGoalCalendarPlacement(substep, `${input.value}-01`);
          });
          controls.appendChild(form);
        }
        goalCalendarView.appendChild(controls);
      }
    }
    goalCalendarStatus.textContent = `Vue : ${calendarPeriodLabel(goalCalendarStart, goalCalendarStart + 23)}. Les périodes qui se chevauchent parmi les objectifs affichés sont bordées d'ambre.`;
  }

  async function saveGoalCalendarPlacement(substep, chosenStart) {
    try {
      const response = await fetch(`${API_BASE}/substeps/${substep.id}/life-placement`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chosen_start_month: chosenStart })
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(typeof error.detail === "string" ? error.detail : "Période invalide");
      }
      substep.life_chosen_start_month = chosenStart;
      for (const goal of goalCalendarGoals) {
        for (const linkedStep of goal.substeps || []) {
          if (linkedStep.id === substep.id) linkedStep.life_chosen_start_month = chosenStart;
        }
      }
      lifeWeeksGoals = goalCalendarGoals;
      renderGoalCalendar();
      renderLifeWeeks();
      showToast(chosenStart ? "Période choisie enregistrée" : "Période choisie retirée");
    } catch (error) {
      showToast(error.message || "Impossible d'enregistrer la période", true);
    }
  }

  async function loadGoalCalendar() {
    try {
      const response = await fetch(`${API_BASE}/goals`);
      if (!response.ok) throw new Error("Objectifs indisponibles");
      goalCalendarGoals = await response.json();
      const selectedGoal = goalCalendarFilter.value;
      goalCalendarFilter.replaceChildren(new Option("Tous les objectifs", ""));
      for (const goal of goalCalendarGoals) {
        goalCalendarFilter.add(new Option(goal.title, String(goal.id)));
      }
      goalCalendarFilter.value = goalCalendarGoals.some(goal => String(goal.id) === selectedGoal)
        ? selectedGoal : "";
      renderGoalCalendar();
    } catch (error) {
      goalCalendarStatus.textContent = "Impossible de charger le calendrier des objectifs.";
      goalCalendarView.replaceChildren();
    }
  }

  if (goalCalendarView) {
    goalCalendarFilter.addEventListener("change", renderGoalCalendar);
    document.getElementById("goal-calendar-prev").addEventListener("click", () => {
      goalCalendarStart -= 12;
      renderGoalCalendar();
    });
    document.getElementById("goal-calendar-next").addEventListener("click", () => {
      goalCalendarStart += 12;
      renderGoalCalendar();
    });
    document.getElementById("goal-calendar-today").addEventListener("click", () => {
      goalCalendarStart = currentMonth.getFullYear() * 12 + currentMonth.getMonth() - 3;
      renderGoalCalendar();
    });
    document.getElementById("goal-calendar-jump-btn").addEventListener("click", () => {
      const value = document.getElementById("goal-calendar-jump").value;
      if (!value) return;
      goalCalendarStart = monthNumber(value) - 3;
      renderGoalCalendar();
    });
  }

  function yesterdayDateString() {
    const date = new Date();
    date.setDate(date.getDate() - 1);
    const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 10);
  }

  function getAgendaDate() {
    if (agendaDateInput && agendaDateInput.value) return agendaDateInput.value;
    return todayDateString();
  }

  function isCorrectableAgendaDate(date = getAgendaDate()) {
    return date === todayDateString() || date === yesterdayDateString();
  }

  function getQuestProgressMode(item) {
    return item?.daily_progress?.mode || item?.progress_mode || "standard";
  }

  function getQuestTypeForDate(item) {
    return item?.type_for_date || item?.type || "binary";
  }

  function getQuestUnitForDate(item) {
    return item?.daily_progress?.unit || item?.unit_for_date || item?.unit || "unités";
  }

  function getQuestTargetForDate(item) {
    return Number(item?.daily_target_for_date || item?.daily_target || 1);
  }

  function getQuestCounterValue(item) {
    const value = item?.daily_progress?.counter_value;
    return Number.isSafeInteger(Number(value)) ? Number(value) : 0;
  }

  function getQuestChecklistItems(item) {
    const configured = Array.isArray(item?.checklist_items) ? item.checklist_items : [];
    const daily = Array.isArray(item?.daily_progress?.checklist_items)
      ? item.daily_progress.checklist_items
      : [];
    const dailyById = new Map(daily.map(entry => [String(entry.id ?? entry.item_id), entry]));
    const source = daily.length > 0 ? daily : configured;
    return source.map((entry, index) => {
      const dailyEntry = dailyById.get(String(entry.id ?? entry.item_id)) || entry;
      return {
        id: entry.id ?? entry.item_id ?? dailyEntry.id ?? dailyEntry.item_id,
        label: entry.label || dailyEntry.label || `Élément ${index + 1}`,
        checked: Boolean(dailyEntry.checked)
      };
    });
  }

  function isQuestProgressReadonly(item) {
    return !isCorrectableAgendaDate() || item.status === "failed" || item.status === "skipped";
  }

  function questProgressSummary(item) {
    const mode = getQuestProgressMode(item);
    if (mode === "free_counter") {
      const unit = getQuestUnitForDate(item) || "reps";
      return `${getQuestCounterValue(item)} ${unit}`;
    }
    if (mode === "checklist") {
      const items = getQuestChecklistItems(item);
      return `${items.filter(entry => entry.checked).length}/${items.length}`;
    }
    return "";
  }

  function questProgressButtonLabel(item) {
    const mode = getQuestProgressMode(item);
    const summary = questProgressSummary(item);
    return mode === "checklist" ? `☑ Checklist ${summary}` : `# Compteur ${summary}`;
  }

  async function refreshProgressSurfaces(habitId = null) {
    await loadQuestAgenda(true);
    if (questPanelMode !== "agenda") await loadCurrentQuestPanel(false);
    if (trackedQuestId !== null && (habitId === null || String(trackedQuestId) === String(habitId))) {
      const refreshed = agendaQuestById(trackedQuestId);
      if (refreshed) openQuestTrackingDrawer(refreshed);
    }
  }

  function enqueueQuestProgressMutation(habitId, mutation) {
    const key = String(habitId);
    const previous = questProgressMutationQueues.get(key) || Promise.resolve();
    const current = previous.catch(() => {}).then(mutation);
    questProgressMutationQueues.set(key, current);
    current.finally(() => {
      if (questProgressMutationQueues.get(key) === current) {
        questProgressMutationQueues.delete(key);
      }
    });
    return current;
  }

  function updateQuestCounter(habitId, value) {
    const parsed = typeof value === "string" && value.trim() === "" ? NaN : Number(value);
    if (!Number.isSafeInteger(parsed) || parsed < 0) {
      showToast("Le compteur doit être un entier positif ou nul.", true);
      return Promise.resolve(false);
    }
    const targetDate = getAgendaDate();
    return enqueueQuestProgressMutation(habitId, async () => {
      try {
        const response = await fetch(`${API_BASE}/habits/${habitId}/counter/${targetDate}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ value: parsed })
        });
        if (!response.ok) throw new Error((await response.json()).detail || "Compteur refusé");
        await refreshProgressSurfaces(habitId);
        return true;
      } catch (error) {
        console.error(error);
        showToast(error.message || "Erreur lors de la mise à jour du compteur", true);
        return false;
      }
    });
  }

  function updateQuestChecklistItem(habitId, itemId, checked) {
    const targetDate = getAgendaDate();
    return enqueueQuestProgressMutation(habitId, async () => {
      try {
        const encodedItemId = encodeURIComponent(String(itemId));
        const response = await fetch(`${API_BASE}/habits/${habitId}/checklist/${targetDate}/items/${encodedItemId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ checked: Boolean(checked) })
        });
        if (!response.ok) throw new Error((await response.json()).detail || "Checklist refusée");
        await refreshProgressSurfaces(habitId);
        return true;
      } catch (error) {
        console.error(error);
        showToast(error.message || "Erreur lors de la mise à jour de la checklist", true);
        return false;
      }
    });
  }

  function createQuestProgressControl(item, { inDrawer = false } = {}) {
    const mode = getQuestProgressMode(item);
    if (mode === "standard") return null;

    const readonly = isQuestProgressReadonly(item);
    const control = document.createElement("div");
    control.className = `agenda-progress-control ${readonly ? "readonly" : ""}`;
    control.addEventListener("click", event => event.stopPropagation());
    control.addEventListener("pointerdown", event => event.stopPropagation());
    const heading = document.createElement("strong");
    heading.className = "agenda-progress-control-title";
    heading.textContent = mode === "checklist" ? "Checklist du jour" : "Compteur du jour";
    control.appendChild(heading);

    if (mode === "free_counter") {
      const counter = document.createElement("div");
      counter.className = "agenda-counter-control";
      const decrement = document.createElement("button");
      decrement.type = "button";
      decrement.className = "agenda-counter-step";
      decrement.textContent = "−";
      decrement.setAttribute("aria-label", "Retirer une répétition");
      const input = document.createElement("input");
      input.type = "number";
      input.min = "0";
      input.max = String(Number.MAX_SAFE_INTEGER);
      input.step = "1";
      input.inputMode = "numeric";
      input.className = "agenda-counter-value";
      input.value = String(getQuestCounterValue(item));
      input.setAttribute("aria-label", `Valeur du compteur pour ${item.name}`);
      const increment = document.createElement("button");
      increment.type = "button";
      increment.className = "agenda-counter-step";
      increment.textContent = "+";
      increment.setAttribute("aria-label", "Ajouter une répétition");
      decrement.disabled = readonly || getQuestCounterValue(item) === 0;
      input.disabled = readonly;
      increment.disabled = readonly || getQuestCounterValue(item) >= Number.MAX_SAFE_INTEGER;

      decrement.addEventListener("click", async () => {
        decrement.disabled = true;
        input.disabled = true;
        increment.disabled = true;
        const current = Number(input.value);
        const previous = Number.isSafeInteger(current) && current >= 0 ? current : 0;
        const updated = await updateQuestCounter(item.habit_id, Math.max(0, previous - 1));
        if (!updated) {
          input.value = String(previous);
        }
        const currentValue = updated ? Math.max(0, previous - 1) : previous;
        input.value = String(currentValue);
        decrement.disabled = readonly || currentValue === 0;
        input.disabled = readonly;
        increment.disabled = readonly || currentValue >= Number.MAX_SAFE_INTEGER;
      });
      increment.addEventListener("click", async () => {
        decrement.disabled = true;
        input.disabled = true;
        increment.disabled = true;
        const current = Number(input.value);
        const previous = Number.isSafeInteger(current) && current >= 0 ? current : 0;
        const updated = await updateQuestCounter(item.habit_id, previous + 1);
        if (!updated) {
          input.value = String(previous);
        }
        const currentValue = updated ? previous + 1 : previous;
        input.value = String(currentValue);
        decrement.disabled = readonly || currentValue === 0;
        input.disabled = readonly;
        increment.disabled = readonly || currentValue >= Number.MAX_SAFE_INTEGER;
      });
      input.addEventListener("focus", () => {
        directProgressInputActive = true;
        input.dataset.previousValue = input.value;
      });
      input.addEventListener("keydown", event => {
        if (event.key === "Enter") input.blur();
        if (event.key === "Escape") {
          event.stopPropagation();
          input.value = input.dataset.previousValue || String(getQuestCounterValue(item));
          input.blur();
        }
      });
      input.addEventListener("blur", async () => {
        const previous = Number(input.dataset.previousValue);
        const next = input.value.trim() === "" ? NaN : Number(input.value);
        directProgressInputActive = false;
        if (Number.isSafeInteger(next) && next >= 0 && next !== previous) {
          const updated = await updateQuestCounter(item.habit_id, next);
          if (!updated) input.value = String(Number.isSafeInteger(previous) ? previous : 0);
        } else if (!Number.isSafeInteger(next) || next < 0) {
          input.value = String(Number.isSafeInteger(previous) ? previous : 0);
          showToast("Le compteur doit être un entier positif ou nul.", true);
        }
      });

      const unit = document.createElement("span");
      unit.className = "agenda-progress-unit";
      unit.textContent = getQuestUnitForDate(item) || "reps";
      counter.append(decrement, input, increment, unit);
      control.appendChild(counter);
    } else {
      const list = document.createElement("div");
      list.className = "agenda-checklist-control";
      getQuestChecklistItems(item).forEach(entry => {
        const label = document.createElement("label");
        label.className = `agenda-checklist-item ${entry.checked ? "checked" : ""}`;
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = entry.checked;
        checkbox.disabled = readonly || entry.id === undefined || entry.id === null;
        checkbox.addEventListener("change", async () => {
          checkbox.disabled = true;
          const updated = await updateQuestChecklistItem(item.habit_id, entry.id, checkbox.checked);
          if (!updated) {
            checkbox.checked = !checkbox.checked;
          }
          checkbox.disabled = readonly;
        });
        const text = document.createElement("span");
        text.textContent = entry.label;
        label.append(checkbox, text);
        list.appendChild(label);
      });
      control.appendChild(list);
    }

    if (readonly) {
      const note = document.createElement("span");
      note.className = "agenda-progress-readonly-note";
      note.textContent = item.status === "failed"
        ? "Lecture seule : quête ratée."
        : item.status === "skipped"
          ? "Lecture seule : quête passée."
          : "Modifiable seulement aujourd’hui ou hier.";
      control.appendChild(note);
    } else if (item.status === "done" && !inDrawer) {
      control.title = "Le suivi auxiliaire reste modifiable après validation finale.";
    }
    return control;
  }

  function openQuestTrackingDrawer(item, trigger = questTrackingTrigger) {
    const overlay = document.getElementById("quest-tracking-overlay");
    const drawer = document.getElementById("quest-tracking-drawer");
    const content = document.getElementById("quest-tracking-content");
    if (!overlay || !drawer || !content) return;
    trackedQuestId = item.habit_id;
    questTrackingTrigger = trigger;
    document.getElementById("quest-tracking-title").textContent = item.name;
    document.getElementById("quest-tracking-date").textContent = `Suivi auxiliaire · ${formatDateFr(dateFromInput(getAgendaDate()))}`;
    content.innerHTML = "";
    const control = createQuestProgressControl(item, { inDrawer: true });
    if (control) content.appendChild(control);
    overlay.classList.add("open");
    drawer.classList.add("open");
  }

  function closeQuestTrackingDrawer() {
    document.getElementById("quest-tracking-overlay")?.classList.remove("open");
    document.getElementById("quest-tracking-drawer")?.classList.remove("open");
    trackedQuestId = null;
    questTrackingTrigger?.focus();
    questTrackingTrigger = null;
  }

  document.getElementById("close-quest-tracking-btn")?.addEventListener("click", closeQuestTrackingDrawer);
  document.getElementById("quest-tracking-overlay")?.addEventListener("click", closeQuestTrackingDrawer);
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && document.getElementById("quest-tracking-drawer")?.classList.contains("open")) {
      closeQuestTrackingDrawer();
    }
  });

  function updateAgendaDateSwitch() {
    const date = getAgendaDate();
    agendaYesterdayBtn?.classList.toggle("active", date === yesterdayDateString());
    agendaTodayBtn?.classList.toggle("active", date === todayDateString());
  }

  async function showAgendaDate(date) {
    if (agendaDateInput) agendaDateInput.value = date;
    updateAgendaDateSwitch();
    await Promise.all([loadQuestAgenda(true), fetchNoTodos()]);
    if (questPanelMode !== "agenda") await loadCurrentQuestPanel(false);
  }

  function monthlyAnchorDay(value, fallbackDate = new Date()) {
    const parsed = parseInt(String(value || "").split(",")[0], 10);
    const fallbackDay = fallbackDate instanceof Date && !isNaN(fallbackDate)
      ? fallbackDate.getDate()
      : new Date().getDate();
    const day = Number.isInteger(parsed) && parsed >= 1 ? parsed : fallbackDay;
    return Math.min(day, 30);
  }

  function dateFromInput(value) {
    if (!value) return new Date();
    const parts = value.split("-").map(part => parseInt(part, 10));
    if (parts.length !== 3 || parts.some(part => isNaN(part))) return new Date();
    return new Date(parts[0], parts[1] - 1, parts[2]);
  }

  function nextMonthlyOccurrence(anchorDay, fromDate = new Date()) {
    for (let offset = 0; offset < 14; offset += 1) {
      const candidate = new Date(fromDate.getFullYear(), fromDate.getMonth() + offset, 1);
      const lastDay = new Date(candidate.getFullYear(), candidate.getMonth() + 1, 0).getDate();
      const dueDay = Math.min(anchorDay, lastDay);
      candidate.setDate(dueDay);
      candidate.setHours(0, 0, 0, 0);
      const today = new Date(fromDate);
      today.setHours(0, 0, 0, 0);
      if (candidate >= today) return candidate;
    }
    return fromDate;
  }

  function formatDateFr(date) {
    return date.toLocaleDateString("fr-CA", {
      day: "numeric",
      month: "long",
      year: "numeric"
    });
  }

  function monthlyFrequencyNote(anchorDay) {
    const next = nextMonthlyOccurrence(anchorDay, dateFromInput(getAgendaDate()));
    return `Chaque mois le ${anchorDay}. Prochaine occurrence : ${formatDateFr(next)}.`;
  }

  function updateFrequencyNote(selectEl, noteEl, anchorValue = null) {
    if (!selectEl || !noteEl) return;
    if (selectEl.value !== "monthly") {
      noteEl.textContent = "";
      return;
    }
    noteEl.textContent = monthlyFrequencyNote(monthlyAnchorDay(anchorValue));
  }

  function isHabitDueOnDate(habit, dateValue = new Date()) {
    const frequency = habit.frequency || "daily";
    if (frequency === "monthly") {
      const lastDay = new Date(dateValue.getFullYear(), dateValue.getMonth() + 1, 0).getDate();
      return dateValue.getDate() === Math.min(monthlyAnchorDay(habit.scheduled_days, dateValue), lastDay);
    }
    if (frequency === "daily" || frequency === "specific_days" || frequency === "custom") {
      const modelDay = dateValue.getDay();
      const days = (habit.scheduled_days || "")
        .split(",")
        .map(s => parseInt(s.trim(), 10))
        .filter(n => !isNaN(n));
      return days.includes(modelDay);
    }
    return false;
  }

  async function fetchBiologicalZones(forceRefresh = false) {
    if (biologicalZonesCache && !forceRefresh) {
      return biologicalZonesCache;
    }

    const response = await fetch(`${API_BASE}/biological-zones`);
    if (!response.ok) {
      throw new Error("Erreur de chargement de la journée biologique");
    }
    biologicalZonesCache = await response.json();
    return biologicalZonesCache;
  }

  async function loadBioTimeline(forceRefresh = false) {
    const bars = [
      document.getElementById("bio-timeline-bar"),
      document.getElementById("bio-timeline-bar-settings")
    ].filter(el => el !== null);

    try {
      const zones = await fetchBiologicalZones(forceRefresh);
      renderBioTimeline(zones);
    } catch (error) {
      console.error(error);
      bars.forEach(bar => {
        bar.innerHTML = `<div class="bio-timeline-empty">Impossible de charger la journée biologique.</div>`;
      });
    }
  }

  function buildBioTimelineSegments(zones) {
    const segments = [];
    zones.forEach(zone => {
      const startMin = timeToMinutes(zone.start_time);
      const endMin = timeToMinutes(zone.end_time);
      if (startMin === endMin) return;

      if (endMin > startMin) {
        segments.push({
          zone,
          startMin,
          endMin,
          startLabel: zone.start_time,
          endLabel: zone.end_time
        });
      } else {
        segments.push({
          zone,
          startMin,
          endMin: 1440,
          startLabel: zone.start_time,
          endLabel: "24:00"
        });
        segments.push({
          zone,
          startMin: 0,
          endMin,
          startLabel: "00:00",
          endLabel: zone.end_time
        });
      }
    });
    return segments.sort((a, b) => a.startMin - b.startMin || a.endMin - b.endMin);
  }

  function renderBioTimeline(zones) {
    const bars = [
      document.getElementById("bio-timeline-bar"),
      document.getElementById("bio-timeline-bar-settings")
    ].filter(el => el !== null);

    if (bars.length === 0) return;

    bars.forEach(bar => {
      bar.innerHTML = "";

      if (!zones || zones.length === 0) {
        bar.innerHTML = `<div class="bio-timeline-empty">Aucune zone biologique configurée.</div>`;
        return;
      }

      const segments = buildBioTimelineSegments(zones);
      let cursor = 0;

      segments.forEach(segment => {
        if (segment.startMin > cursor) {
          const gap = document.createElement("div");
          gap.className = "bio-zone-gap";
          gap.style.width = `${((segment.startMin - cursor) / 1440) * 100}%`;
          gap.title = `Transition libre (${minutesToTime(cursor)} - ${minutesToTime(segment.startMin)})`;
          bar.appendChild(gap);
        }

        const zone = segment.zone;
        const meta = getBioZoneMeta(zone.zone_type);
        const duration = segment.endMin - segment.startMin;
        const pct = (duration / 1440) * 100;
        const block = document.createElement("div");
        block.className = `bio-zone-block bio-zone-${zone.zone_type}`;
        block.style.width = `${pct}%`;
        if (zone.color) {
          block.style.background = zone.color;
        }
        block.title = `${meta.emoji} ${zone.zone_name} - ${meta.label} (${segment.startLabel} - ${segment.endLabel})`;

        if (pct > 4) {
          const label = document.createElement("span");
          label.className = "bio-zone-label";
          label.textContent = pct > 8 ? `${meta.emoji} ${zone.zone_name}` : meta.emoji;
          block.appendChild(label);
        }

        bar.appendChild(block);
        cursor = Math.max(cursor, segment.endMin);
      });

      if (cursor < 1440) {
        const gap = document.createElement("div");
        gap.className = "bio-zone-gap";
        gap.style.width = `${((1440 - cursor) / 1440) * 100}%`;
        gap.title = `Transition libre (${minutesToTime(cursor)} - 24:00)`;
        bar.appendChild(gap);
      }
    });
  }

  // ==============================================
  // FETCH PROFILE & DAILY DASHBOARD               //
  // ==============================================
  const dayTypeLabels = {
    rest: "Repos",
    regular: "Normal",
    hustle: "Hustle"
  };

  function renderDayTypeState(data) {
    activeDayType = data.active_template || "regular";
    if (!dayTypeStatus || !feelOffBtn) return;
    if (data.feel_off_active) {
      dayTypeStatus.textContent = "Repos exceptionnel · Feel off";
      feelOffBtn.textContent = "Revenir au planning prévu";
      feelOffBtn.dataset.action = "restore";
      feelOffBtn.style.display = "inline-flex";
      return;
    }
    const label = dayTypeLabels[data.scheduled_template || activeDayType] || "Normal";
    dayTypeStatus.textContent = `${label} · planning automatique`;
    feelOffBtn.dataset.action = "feel-off";
    feelOffBtn.textContent = "Feel off today";
    feelOffBtn.style.display = activeDayType === "rest" ? "none" : "inline-flex";
  }

  async function toggleFeelOff() {
    if (!feelOffBtn) return;
    const restoring = feelOffBtn.dataset.action === "restore";
    feelOffBtn.disabled = true;
    try {
      const response = await fetch(`${API_BASE}/profile/feel-off`, {
        method: restoring ? "DELETE" : "POST"
      });
      if (!response.ok) throw new Error(await readApiError(response));
      showToast(restoring ? "Planning automatique restauré." : "Journée passée en repos exceptionnel.");
      refreshAll();
      await showAgendaDate(getAgendaDate());
    } catch (error) {
      console.error(error);
      showToast(error.message || "Impossible de modifier la journée.", true);
    } finally {
      feelOffBtn.disabled = false;
    }
  }

  feelOffBtn?.addEventListener("click", toggleFeelOff);

  async function fetchProfile() {
    try {
      const response = await fetch(`${API_BASE}/profile`);
      if (!response.ok) {
        if (response.status === 401 || response.status === 403 || response.status === 404) {
          showLoginScreen();
          return;
        }
        throw new Error("Erreur profile API");
      }
      const data = await response.json();

      // Update RPG Level & XP Bar dynamically
      const charName = document.getElementById("char-name");
      if (charName && data.username) {
        charName.textContent = data.username;
      }
      charLevel.textContent = `LV.${data.level}`;
      const xpFill = document.getElementById("char-xp-fill");
      const xpText = document.getElementById("char-xp-text");

      // Level formula XP needed (L -> L+1) is 10 * 2^(L-1)
      const xpNeeded = 10 * Math.pow(2, data.level - 1);
      const xpPercent = Math.min((data.xp / xpNeeded) * 100, 100);
      if (xpFill && xpText) {
        xpFill.style.width = `${xpPercent}%`;
        xpText.textContent = `${data.xp} / ${xpNeeded} XP`;
      }

      // Update gold balance display
      const topGoldVal = document.getElementById("top-gold-val");
      const charGoldVal = document.getElementById("char-gold-val");
      if (topGoldVal) topGoldVal.textContent = `💰 ${data.gold} Gold`;
      if (charGoldVal) charGoldVal.textContent = data.gold;

      renderDayTypeState(data);

      // Update Daily Status Badge
      badgeStatus.textContent = data.scores.status === "NoMust" ? "○ Aucun Must aujourd'hui" : data.scores.perfect_day_validated ? "🏆 Perfect Day !" : "🟥 Journée Incomplète";
      badgeStatus.className = "badge badge-status";
      if (data.scores.status === "Failed") {
        badgeStatus.classList.add("failed");
      }

      renderRecapPanel(data);
    } catch (error) {
      console.error(error);
      showToast("Erreur lors du chargement du profil", true);
    }
  }

  // ==============================================
  // ACTIVE QUESTS (HABITS CHECK-INS)             //
  // ==============================================
  function closeQuestInlineForm() {
    const questForm = document.getElementById("quest-inline-form");
    const openQuestBtn = document.getElementById("open-quest-inline-btn");
    if (questForm) {
      questForm.style.display = "none";
      questForm.classList.remove("recap-quest-form");
      questForm.removeAttribute("role");
      questForm.removeAttribute("aria-modal");
      questForm.removeAttribute("aria-label");
    }
    document.getElementById("recap-quest-form-overlay")?.classList.remove("open");
    const questList = document.getElementById("quests-list-container");
    const overlay = document.getElementById("recap-quest-form-overlay");
    if (questList && questForm && overlay && questForm.parentElement === document.body) {
      questList.before(questForm, overlay);
    }
    if (openQuestBtn) openQuestBtn.textContent = "+ Quête";
  }

  async function openFocusQuestForm(role, targetId, title) {
    const questForm = document.getElementById("quest-inline-form");
    if (!questForm) return;
    document.getElementById("new-quest-focus-role").value = role;
    try {
      await Promise.all([
        renderQuestTagEditor("new", [], true),
        populateFocusTargets("new", targetId)
      ]);
    } catch (error) {
      showToast(error.message || "Impossible d'ouvrir le réglage de la quête.", true);
      return;
    }
    document.getElementById("new-quest-name").value = `Pratiquer : ${title}`;
    const overlay = document.getElementById("recap-quest-form-overlay");
    document.body.append(overlay, questForm);
    questForm.classList.add("recap-quest-form");
    questForm.setAttribute("role", "dialog");
    questForm.setAttribute("aria-modal", "true");
    questForm.setAttribute("aria-label", `Créer la quête liée à ${title}`);
    questForm.style.display = "flex";
    overlay.classList.add("open");
    document.getElementById("new-quest-name").focus();
  }

  function updateQuestPanelShell() {
    const isAgenda = questPanelMode === "agenda";
    const isBank = questPanelMode === "bank";
    const isArchives = questPanelMode === "archives";

    if (questsPanelTitle) {
      questsPanelTitle.textContent = isBank
        ? "✅ Banque des Must"
        : isArchives
          ? "✅ Archives Must"
          : getAgendaDate() === todayDateString()
            ? "✅ Must du jour"
            : `✅ Must du ${getAgendaDate()}`;
    }

    if (questsListContainer) questsListContainer.hidden = !isAgenda;
    if (questDaySummary) questDaySummary.hidden = !isAgenda;
    if (questBankPanel) questBankPanel.hidden = !isBank;
    if (questArchivesPanel) questArchivesPanel.hidden = !isArchives;

    toggleQuestAgendaBtn?.classList.toggle("active", isAgenda);
    toggleQuestBankBtn?.classList.toggle("active", isBank);
    toggleQuestArchivesBtn?.classList.toggle("active", isArchives);

    const openQuestBtn = document.getElementById("open-quest-inline-btn");
    if (openQuestBtn) openQuestBtn.hidden = !isAgenda;
    if (!isAgenda) closeQuestInlineForm();
  }

  async function loadCurrentQuestPanel(showErrors = false) {
    updateQuestPanelShell();
    if (questPanelMode === "bank") {
      return loadQuestBank();
    }
    if (questPanelMode === "archives") {
      return loadQuestArchives();
    }
    return loadQuestAgenda(showErrors);
  }

  async function setQuestPanelMode(mode, options = {}) {
    const { reload = true } = options;
    questPanelMode = ["agenda", "bank", "archives"].includes(mode) ? mode : "agenda";
    updateQuestPanelShell();
    if (reload) {
      await loadCurrentQuestPanel(true);
    }
  }

  async function fetchQuests() {
    try {
      const habitsResponse = await fetch(`${API_BASE}/habits`);
      if (!habitsResponse.ok) throw new Error("Erreur habits API");
      const habits = await habitsResponse.json();
      allHabitsCache = habits;
      if (!directProgressInputActive) {
        await loadCurrentQuestPanel(false);
      }
    } catch (error) {
      console.error(error);
      questsListContainer.innerHTML = `<p style="color: var(--accent-red); font-size: 0.9rem; text-align: center;">Erreur de chargement des quêtes.</p>`;
    }
  }

  async function loadQuestTagCatalog(force = false) {
    if (questTagCatalog && !force) return questTagCatalog;
    const [goalsResponse, softskillsResponse] = await Promise.all([
      fetch(`${API_BASE}/goals`),
      fetch(`${API_BASE}/softskills`)
    ]);
    if (!goalsResponse.ok || !softskillsResponse.ok) {
      throw new Error("Impossible de charger les objectifs et softskills.");
    }
    const goals = await goalsResponse.json();
    const softskills = await softskillsResponse.json();
    questTagCatalog = {
      goals: goals || [],
      branches: Object.entries(softskills.branches || {}).map(([key, value]) => ({
        key,
        ...(value || {})
      }))
    };
    return questTagCatalog;
  }

  function renderQuestTagOptions(containerId, kind, options, selectedValues, prefix) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const selected = new Set((selectedValues || []).map(value => String(value)));
    container.innerHTML = "";
    options.forEach(option => {
      const label = document.createElement("label");
      label.className = "quest-tag-option";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.value = String(option.value);
      checkbox.dataset.kind = kind;
      checkbox.dataset.label = option.label;
      if (option.color) checkbox.dataset.color = option.color;
      checkbox.checked = selected.has(String(option.value));
      checkbox.addEventListener("change", () => updateQuestTagPreview(prefix));
      const text = document.createElement("span");
      text.textContent = option.label;
      label.append(checkbox, text);
      container.appendChild(label);
    });
  }

  async function renderQuestTagEditor(prefix, tags = [], force = false) {
    questTagEditorReady[prefix] = false;
    const summary = document.getElementById(`${prefix}-quest-tags-summary`);
    if (summary?.parentElement) summary.parentElement.open = false;
    try {
      const catalog = await loadQuestTagCatalog(force);
      const goalTagIds = tags
        .filter(tag => tag.kind === "goal")
        .map(tag => tag.ref);
      const branchTagKeys = tags
        .filter(tag => tag.kind === "softskill_branch")
        .map(tag => tag.ref);
      const goalOptions = catalog.goals.map(goal => ({
        value: goal.id,
        label: goal.title
      }));
      renderQuestTagOptions(
        `${prefix}-quest-tag-goals`,
        "goal",
        goalOptions,
        goalTagIds,
        prefix
      );
      renderQuestTagOptions(
        `${prefix}-quest-tag-branches`,
        "softskill_branch",
        catalog.branches.map(branch => ({
          value: branch.key,
          label: branch.key.replaceAll("_", " "),
          color: branch.color
        })),
        branchTagKeys,
        prefix
      );
      questTagEditorReady[prefix] = true;
      updateQuestTagPreview(prefix);
    } catch (error) {
      console.error(error);
      ["tag-goals", "tag-branches"].forEach(suffix => {
        const container = document.getElementById(`${prefix}-quest-${suffix}`);
        if (container) container.innerHTML = `<span class="form-helper-text">Chargement impossible.</span>`;
      });
    }
  }

  function selectedQuestTags(prefix) {
    return Array.from(document.querySelectorAll(
      `#${prefix}-quest-tag-goals input:checked, #${prefix}-quest-tag-branches input:checked`
    )).map(input => ({
      kind: input.dataset.kind,
      ref: input.value,
      label: input.dataset.label || input.value,
      color: input.dataset.color || null
    }));
  }

  function collectQuestTags(prefix) {
    if (!questTagEditorReady[prefix]) return null;
    return selectedQuestTags(prefix).map(tag => ({ kind: tag.kind, ref: tag.ref }));
  }

  function questTagBadges(tags) {
    if (!tags?.length) return null;

    const container = document.createElement("div");
    container.className = "quest-tag-badges";
    tags.forEach(tag => {
      const badge = document.createElement("span");
      badge.className = "quest-tag-badge";
      badge.textContent = `# ${tag.label || tag.ref}`;
      if (tag.color) badge.style.borderColor = tag.color;
      container.appendChild(badge);
    });
    return container;
  }

  function appendQuestTagBadges(parent, tags) {
    const badges = questTagBadges(tags);
    if (badges) parent.appendChild(badges);
  }

  function updateQuestTagPreview(prefix) {
    const tags = selectedQuestTags(prefix);
    const preview = document.getElementById(`${prefix}-quest-tags-preview`);
    const summary = document.getElementById(`${prefix}-quest-tags-summary`);
    if (summary) summary.textContent = tags.length ? `Choisir les tags · ${tags.length}` : "Choisir les tags";
    if (!preview) return;
    preview.innerHTML = "";
    const badges = questTagBadges(tags);
    if (badges) {
      preview.appendChild(badges);
    } else {
      const empty = document.createElement("span");
      empty.className = "quest-tags-empty";
      empty.textContent = "Aucun tag";
      preview.appendChild(empty);
    }
  }

  function normalizedQuestArchiveKey(name) {
    const { baseName } = splitQuestVersionName(name || "");
    return baseName
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, " ")
      .trim();
  }

  function formatArchivedAt(value) {
    if (!value) return "date inconnue";
    const parsed = new Date(value);
    if (isNaN(parsed.getTime())) return value;
    return parsed.toLocaleDateString("fr-CA", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit"
    });
  }

  function formatDateOnly(value) {
    if (!value) return "date inconnue";
    const parts = String(value).split("T")[0].split("-");
    if (parts.length === 3) return `${parts[2]}/${parts[1]}`;
    return value;
  }

  function questFrequencyLabel(habit) {
    const frequency = habit.frequency || "daily";
    if (frequency === "monthly") return "mensuel";
    if (frequency === "specific_days") return "jours fixes";
    return "quotidien";
  }

  function renderQuestArchives(habits) {
    if (!questArchivesList) return;
    const archived = habits
      .filter((habit) => habit.archived_at)
      .sort((a, b) => new Date(b.archived_at || 0) - new Date(a.archived_at || 0));
    if (questArchivesCount) questArchivesCount.textContent = String(archived.length);

    questArchivesList.innerHTML = "";
    if (archived.length === 0) {
      questArchivesList.innerHTML = `<p class="agenda-empty">Aucune quête archivée.</p>`;
      return;
    }

    const activeKeys = new Set(
      habits
        .filter((habit) => !habit.archived_at && habit.is_active !== false)
        .map((habit) => normalizedQuestArchiveKey(habit.name))
        .filter(Boolean)
    );
    const groups = new Map();
    archived.forEach((habit) => {
      const key = normalizedQuestArchiveKey(habit.name) || String(habit.id);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(habit);
    });

    Array.from(groups.entries())
      .sort((a, b) => {
        const left = splitQuestVersionName(a[1][0].name).baseName.toLowerCase();
        const right = splitQuestVersionName(b[1][0].name).baseName.toLowerCase();
        return left.localeCompare(right, "fr");
      })
      .forEach(([key, items]) => {
        const group = document.createElement("div");
        group.className = "quest-archive-group";

        const title = document.createElement("div");
        title.className = "quest-archive-group-title";
        const base = document.createElement("span");
        base.textContent = splitQuestVersionName(items[0].name).baseName || items[0].name;
        title.appendChild(base);

        if (items.length > 1) {
          const badge = document.createElement("span");
          badge.className = "quest-archive-badge";
          badge.textContent = `${items.length} archives`;
          title.appendChild(badge);
        }
        if (activeKeys.has(key)) {
          const activeBadge = document.createElement("span");
          activeBadge.className = "quest-archive-badge";
          activeBadge.textContent = "actif aussi";
          title.appendChild(activeBadge);
        }
        group.appendChild(title);

        items.forEach((habit) => {
          const row = document.createElement("div");
          row.className = "quest-archive-row";

          const main = document.createElement("div");
          main.className = "quest-archive-main";
          const name = document.createElement("strong");
          name.textContent = habit.name;
          main.appendChild(name);

          const description = (habit.description || "").trim();
          if (description) {
            const desc = document.createElement("p");
            desc.className = "quest-archive-description";
            desc.textContent = description;
            main.appendChild(desc);
          }

          const source = habit.source_label || (habit.source_type === "manual" ? "manuel" : habit.source_type || "manuel");
          const meta = document.createElement("div");
          meta.className = "quest-archive-meta";
          [formatArchivedAt(habit.archived_at), questFrequencyLabel(habit), source]
            .filter(Boolean)
            .forEach((value) => {
              const item = document.createElement("span");
              item.textContent = value;
              meta.appendChild(item);
            });
          main.appendChild(meta);
          appendQuestTagBadges(main, habit.tags);

          const action = document.createElement("button");
          action.type = "button";
          action.className = "quest-archive-action";
          action.textContent = "Désarchiver";
          action.addEventListener("click", async () => {
            await unarchiveQuestFromArchives(habit.id, habit.source_type);
          });

          row.append(main, action);
          group.appendChild(row);
        });

        questArchivesList.appendChild(group);
      });
  }

  async function loadQuestArchives() {
    if (!questArchivesList) return [];
    try {
      questArchivesList.innerHTML = `<p class="agenda-empty">Chargement des archives...</p>`;
      const response = await fetch(`${API_BASE}/habits?include_archived=true&include_all_versions=true`);
      if (!response.ok) throw new Error((await response.json()).detail || "Erreur archives");
      const habits = await response.json();
      renderQuestArchives(habits);
      return habits;
    } catch (error) {
      console.error(error);
      questArchivesList.innerHTML = `<p class="agenda-empty error">Erreur de chargement des archives.</p>`;
      return [];
    }
  }

  function renderQuestBank(data) {
    if (!questBankList) return;
    const hidden = data.hidden_quests || [];
    if (questBankCount) questBankCount.textContent = String(hidden.length);

    questBankList.innerHTML = "";
    if (hidden.length === 0) {
      questBankList.innerHTML = `<p class="agenda-empty">Toutes les quêtes actives sont visibles pour cette date.</p>`;
      return;
    }

    hidden.forEach((quest) => {
      const row = document.createElement("div");
      row.className = "quest-bank-row";

      const main = document.createElement("div");
      main.className = "quest-bank-main";
      const name = document.createElement("strong");
      name.textContent = quest.name;
      main.appendChild(name);

      const descriptionText = (quest.description || "").trim();
      if (descriptionText) {
        const desc = document.createElement("p");
        desc.className = "quest-bank-description";
        desc.textContent = descriptionText;
        main.appendChild(desc);
      }

      const meta = document.createElement("div");
      meta.className = "quest-bank-meta";
      (quest.bank_reasons || []).forEach((reason) => {
        const item = document.createElement("span");
        item.className = "quest-bank-reason";
        item.textContent = reason.label || "Hors agenda";
        item.title = reason.detail || "";
        meta.appendChild(item);
      });
      if (quest.next_visible_date) {
        const next = document.createElement("span");
        next.textContent = `Prochaine: ${formatDateOnly(quest.next_visible_date)}`;
        meta.appendChild(next);
      }
      [
        questFrequencyLabel(quest),
        quest.source_label || (quest.source_type === "manual" ? "manuel" : quest.source_type || "manuel")
      ]
        .filter(Boolean)
        .forEach((value) => {
          const item = document.createElement("span");
          item.textContent = value;
          meta.appendChild(item);
        });
      main.appendChild(meta);
      appendQuestTagBadges(main, quest.tags);

      const actions = document.createElement("div");
      actions.className = "quest-bank-actions";
      const edit = document.createElement("button");
      edit.type = "button";
      edit.className = "quest-bank-action";
      edit.textContent = "Modifier";
      edit.addEventListener("click", () => openEditQuestModal(questConfigForAgendaItem(quest), quest));

      const stats = document.createElement("button");
      stats.type = "button";
      stats.className = "quest-bank-action";
      stats.textContent = "Stats";
      stats.addEventListener("click", () => {
        const habitObj = allHabitsCache.find(h => String(h.id) === String(quest.habit_id)) || questFromAgendaItem(quest);
        openHabitDetailModal(habitObj);
      });

      const archive = document.createElement("button");
      archive.type = "button";
      archive.className = "quest-bank-action archive";
      archive.textContent = "Archiver";
      archive.addEventListener("click", () => archiveQuestFromBank(quest.habit_id, quest.source_type));
      actions.append(edit, stats, archive);

      row.append(main, actions);
      questBankList.appendChild(row);
    });
  }

  async function loadQuestBank() {
    if (!questBankList) return null;
    try {
      questBankList.innerHTML = `<p class="agenda-empty">Chargement de la banque...</p>`;
      const date = getAgendaDate();
      const response = await fetch(`${API_BASE}/habits/bank?date=${encodeURIComponent(date)}`);
      if (!response.ok) throw new Error((await response.json()).detail || "Erreur banque");
      const data = await response.json();
      renderQuestBank(data);
      return data;
    } catch (error) {
      console.error(error);
      questBankList.innerHTML = `<p class="agenda-empty error">Erreur de chargement de la banque.</p>`;
      return null;
    }
  }

  // Les anciennes quêtes auto-générées restent détachables à la désarchivation.
  function questSourceKindLabel(sourceType) {
    if (sourceType === "substep" || sourceType === "goal") return "sous-étape";
    if (sourceType === "softskill") return "compétence";
    return null;
  }

  function confirmQuestArchiveAction(sourceType, archived) {
    const kind = questSourceKindLabel(sourceType);
    if (!archived || !kind) return true;
    return confirm(
      `Cette ancienne quête générée sera détachée de sa ${kind} et deviendra une quête indépendante.`
    );
  }

  function questArchiveToast(data, archived) {
    if (archived) {
      return data?.detached ? "Quête désarchivée et détachée de sa source." : "Quête désarchivée.";
    }
    return "Quête archivée.";
  }

  async function archiveQuestFromBank(habitId, sourceType) {
    if (!habitId) return;
    if (!confirmQuestArchiveAction(sourceType, false)) return;
    try {
      const response = await fetch(`${API_BASE}/habits/${habitId}/archive`, { method: "POST" });
      if (!response.ok) throw new Error((await response.json()).detail || "Erreur");
      showToast(questArchiveToast(await response.json(), false));
      await refreshQuestSurfaces();
      fetchProfile();
      fetchHistory();
      updateDailyBudgetGauge();
    } catch (error) {
      console.error(error);
      showToast(error.message, true);
    }
  }

  async function refreshQuestSurfaces() {
    await fetchQuests();
  }

  async function unarchiveQuestFromArchives(habitId, sourceType) {
    if (!habitId) return;
    if (!confirmQuestArchiveAction(sourceType, true)) return;
    try {
      const response = await fetch(`${API_BASE}/habits/${habitId}/unarchive`, { method: "POST" });
      if (!response.ok) throw new Error((await response.json()).detail || "Erreur");
      showToast(questArchiveToast(await response.json(), true));
      await refreshQuestSurfaces();
      fetchProfile();
      updateDailyBudgetGauge();
    } catch (error) {
      console.error(error);
      showToast(error.message, true);
    }
  }

  async function createQuestVersion(habitId, sourceDescription) {
    try {
      const response = await fetch(`${API_BASE}/habits/${habitId}/versions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_description: sourceDescription.trim(),
          description: ""
        })
      });

      if (!response.ok) {
        const errBody = await response.json();
        throw new Error(errBody.detail || "Erreur de création");
      }

      const data = await response.json();
      showToast(`${data.name} ajoutée !`);
      return data;
    } catch (error) {
      console.error(error);
      showToast("Erreur: " + error.message, true);
      return null;
    }
  }

  async function submitQuestLog(habitId, logType, amount = null, targetDate = getAgendaDate()) {
    if (!isCorrectableAgendaDate(targetDate)) {
      showToast("Les corrections sont limitées à aujourd'hui et hier.", true);
      return;
    }
    try {
      const response = await fetch(`${API_BASE}/logs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          habit_id: parseInt(habitId),
          log_type: logType,
          amount: amount,
          target_date: targetDate
        })
      });

      if (!response.ok) throw new Error((await response.json()).detail || "Erreur de validation");
      showToast(targetDate === todayDateString()
        ? "Quête quotidienne mise à jour."
        : "Quête corrigée pour hier.");
      refreshAll();
    } catch (error) {
      console.error(error);
      showToast(error.message || "Erreur lors de l'enregistrement de l'habitude", true);
    }
  }

  async function setHabitFailure(habitId, undo = false) {
    if (getAgendaDate() !== todayDateString()) {
      showToast("Une quête peut seulement être déclarée ratée aujourd'hui.", true);
      return;
    }
    try {
      const response = await fetch(`${API_BASE}/habits/${habitId}/fail`, {
        method: undo ? "DELETE" : "POST"
      });
      if (!response.ok) throw new Error((await response.json()).detail || "Action refusée");
      const result = await response.json();
      const xpAmount = undo ? result.xp_restored : result.xp_penalty_applied;
      const xpMessage = xpAmount
        ? undo ? ` +${xpAmount} XP restaurés.` : ` -${xpAmount} XP.`
        : "";
      showToast(
        undo
          ? `Échec annulé pour aujourd'hui.${xpMessage}`
          : `Quête déclarée ratée pour aujourd'hui.${xpMessage}`,
        !undo
      );
      refreshAll();
    } catch (error) {
      console.error(error);
      showToast(error.message || "Erreur lors de la mise à jour de la quête", true);
    }
  }

  // ==============================================
  // HABIT DETAILS & CALENDAR DRAWER               //
  // ==============================================
  let activeHabitForCalendar = null;
  let calendarYear = new Date().getFullYear();
  let calendarMonth = new Date().getMonth() + 1; // 1-12

  async function openHabitDetailModal(habit, year = null, month = null) {
    activeHabitForCalendar = habit;
    if (year !== null) calendarYear = year;
    if (month !== null) calendarMonth = month;

    document.getElementById("habit-detail-overlay").classList.add("open");
    document.getElementById("habit-detail-drawer").classList.add("open");

    const emoji = getStreakEmoji(habit.current_streak || 0);
    const emojiPrefix = emoji ? `${emoji} ` : "";
    document.getElementById("habit-detail-title-val").textContent = `${emojiPrefix}${habit.name}`;
    document.getElementById("habit-detail-desc-val").textContent = habit.description || "Aucune description.";

    const actionBtn = document.getElementById("deactivate-reactivate-habit-btn");
    if (habit.is_active) {
      actionBtn.textContent = "Désactiver la Quête";
      actionBtn.className = "quest-action-btn";
      actionBtn.style.cssText = "flex: 1; padding: 12px; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.5); color: #ef4444; cursor: pointer; border-radius: 8px; font-weight: 600;";
    } else {
      actionBtn.textContent = "Réactiver la Quête";
      actionBtn.className = "quest-action-btn submit-btn";
      actionBtn.style.cssText = "flex: 1; padding: 12px; background: rgba(34, 197, 94, 0.15); border: 1px solid rgba(34, 197, 94, 0.5); color: var(--accent-green); cursor: pointer; border-radius: 8px; font-weight: 600;";
    }

    await fetchAndRenderHabitCalendar(habit.id, calendarYear, calendarMonth);
  }

  async function fetchAndRenderHabitCalendar(habitId, year, month) {
    try {
      const response = await fetch(`${API_BASE}/habits/${habitId}/calendar?year=${year}&month=${month}`);
      if (!response.ok) throw new Error("Erreur de récupération du calendrier");
      const data = await response.json();

      const monthNames = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"];
      document.getElementById("habit-calendar-month-title").textContent = `${monthNames[month - 1]} ${year}`;

      document.getElementById("habit-detail-current-streak").textContent = `${data.current_streak} jours`;
      document.getElementById("habit-detail-max-streak").textContent = `${data.max_streak} jours`;

      const gridContainer = document.getElementById("habit-detail-calendar-grid");
      gridContainer.innerHTML = "";

      const firstDayDate = new Date(year, month - 1, 1);
      const jsDay = firstDayDate.getDay();
      const offset = (jsDay + 6) % 7;

      for (let i = 0; i < offset; i++) {
        const emptyCell = document.createElement("div");
        emptyCell.className = "calendar-day-empty";
        gridContainer.appendChild(emptyCell);
      }

      const totalDays = Object.keys(data.days).length;
      for (let day = 1; day <= totalDays; day++) {
        const cell = document.createElement("div");
        cell.className = "calendar-day-box";
        cell.textContent = day;

        const status = data.days[day];
        if (status) {
          cell.classList.add(status);

          const stateLabels = {
            completed: "Fait",
            skipped: "Passé (Skip)",
            missed: "Manqué",
            "non-scheduled": "Non planifié",
            "pre-creation": "Avant création",
            future: "Futur"
          };
          cell.title = `Jour ${day}: ${stateLabels[status] || status}`;
        }

        gridContainer.appendChild(cell);
      }
    } catch (err) {
      console.error(err);
      document.getElementById("habit-detail-calendar-grid").innerHTML = `<p style="color:var(--accent-red);font-size:0.8rem;grid-column: span 7;text-align:center;">Erreur calendrier.</p>`;
    }
  }

  function closeHabitDetail() {
    document.getElementById("habit-detail-overlay").classList.remove("open");
    document.getElementById("habit-detail-drawer").classList.remove("open");
    activeHabitForCalendar = null;
  }

  document.getElementById("close-habit-detail-btn").addEventListener("click", closeHabitDetail);
  document.getElementById("habit-detail-overlay").addEventListener("click", closeHabitDetail);

  document.getElementById("habit-calendar-prev-btn").addEventListener("click", () => {
    if (!activeHabitForCalendar) return;
    calendarMonth--;
    if (calendarMonth < 1) {
      calendarMonth = 12;
      calendarYear--;
    }
    fetchAndRenderHabitCalendar(activeHabitForCalendar.id, calendarYear, calendarMonth);
  });

  document.getElementById("habit-calendar-next-btn").addEventListener("click", () => {
    if (!activeHabitForCalendar) return;
    calendarMonth++;
    if (calendarMonth > 12) {
      calendarMonth = 1;
      calendarYear++;
    }
    fetchAndRenderHabitCalendar(activeHabitForCalendar.id, calendarYear, calendarMonth);
  });

  document.getElementById("deactivate-reactivate-habit-btn").addEventListener("click", async () => {
    if (!activeHabitForCalendar) return;
    const newActiveState = !activeHabitForCalendar.is_active;
    const confirmMsg = newActiveState
      ? "Voulez-vous réactiver cette quête ?"
      : "Voulez-vous vraiment désactiver cette quête ? Elle ne s'affichera plus dans vos quêtes actives.";
    if (!confirm(confirmMsg)) return;

    try {
      const response = await fetch(`${API_BASE}/habits/${activeHabitForCalendar.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_active: newActiveState })
      });
      if (!response.ok) throw new Error("Erreur de mise à jour");

      showToast(newActiveState ? "Quête réactivée ! ✨" : "Quête désactivée !");
      activeHabitForCalendar.is_active = newActiveState;
      closeHabitDetail();
      fetchQuests();
    } catch (err) {
      console.error(err);
      alert("Erreur lors de la mise à jour de l'état.");
    }
  });

  // ==============================================
  // DAILY SCORES BUDGET GAUGE CALCULATION         //
  // ==============================================
  async function updateDailyBudgetGauge() {
    return loadQuestAgenda();
    try {
      const [templatesResp, profileResp, habitsResp, goalsResp] = await Promise.all([
        fetch(`${API_BASE}/templates`),
        fetch(`${API_BASE}/profile`),
        fetch(`${API_BASE}/habits`),
        fetch(`${API_BASE}/goals`)
      ]);

      if (!templatesResp.ok || !profileResp.ok || !habitsResp.ok || !goalsResp.ok) {
        console.error("Erreur lors de la récupération des données pour la jauge Perfect Day");
        return;
      }

      const templates = await templatesResp.json();
      loadedTemplates = templates; // Save globally so we can add/delete blocks
      const profile = await profileResp.json();
      const habits = await habitsResp.json();
      const goals = await goalsResp.json();

      const rawActiveTemplate = profile.active_template || "regular";
      const tMap = {
        "normal": "regular",
        "regular": "regular",
        "semaine": "regular",
        "week": "regular",
        "weekend": "regular",
        "repos": "rest",
        "rest": "rest",
        "recovery": "rest",
        "recup": "rest",
        "hustle": "hustle",
        "rush": "hustle",
        "sick": "rest",
        "malade": "rest",
        "default": "regular"
      };
      const activeTemplateName = tMap[rawActiveTemplate.toLowerCase()] || "regular";
      const activeTemplate = templates[activeTemplateName] || {
        focus_hours: activeTemplateName === "hustle" ? 9.0 : (activeTemplateName === "rest" ? 2.0 : 6.0),
        min_rest_hours: activeTemplateName === "hustle" ? 6.0 : (activeTemplateName === "rest" ? 10.0 : 8.0),
        ceilings: null,
        agenda_json: []
      };

      const ceilings = activeTemplate.ceilings || {};

      const targetFocus = activeTemplate.focus_hours;
      const minRest = activeTemplate.min_rest_hours;

      const effortCeilings = {
        musculaire: ceilings.musculaire !== undefined ? ceilings.musculaire : (activeTemplateName === "hustle" ? 4.0 : (activeTemplateName === "rest" ? 1.0 : 2.0)),
        cerveau: ceilings.cerveau !== undefined ? ceilings.cerveau : (activeTemplateName === "hustle" ? 4.0 : (activeTemplateName === "rest" ? 1.0 : 2.0)),
        emotionnel_social: ceilings.emotionnel_social !== undefined ? ceilings.emotionnel_social : (activeTemplateName === "hustle" ? 4.0 : (activeTemplateName === "rest" ? 1.0 : 2.0)),
        creatif_divergent: ceilings.creatif_divergent !== undefined ? ceilings.creatif_divergent : (activeTemplateName === "hustle" ? 4.0 : (activeTemplateName === "rest" ? 1.0 : 2.0)),
        total: ceilings.total !== undefined ? ceilings.total : 10.0
      };

      const plannedHabits = habits.filter(habit => isHabitDueOnDate(habit, dateFromInput(getAgendaDate())));

      const pinnedSubIds = profile.pinned_substeps || [];
      const plannedSubsteps = [];
      pinnedSubIds.forEach(subId => {
        for (const g of goals) {
          const s = g.substeps.find(sub => sub.id === subId);
          if (s) {
            plannedSubsteps.push(s);
            break;
          }
        }
      });

      const effortSums = {
        musculaire: 0.0,
        cerveau: 0.0,
        emotionnel_social: 0.0,
        creatif_divergent: 0.0,
        repos: 0.0
      };

      plannedHabits.forEach(h => {
        if (h.effort_type && effortSums[h.effort_type] !== undefined) {
          effortSums[h.effort_type] += (h.effort_duration !== undefined ? h.effort_duration : 1.0);
        }
      });

      plannedSubsteps.forEach(s => {
        if (s.effort_type && effortSums[s.effort_type] !== undefined) {
          effortSums[s.effort_type] += (s.effort_duration !== undefined ? s.effort_duration : 1.0);
        }
      });

      const totalPlannedEffort = ["musculaire", "cerveau", "emotionnel_social", "creatif_divergent"]
        .reduce((sum, key) => sum + effortSums[key], 0.0);
      const unplannedTime = Math.max(16.0 - totalPlannedEffort, 0.0);

      const warnings = [];

      Object.keys(effortSums).forEach(cat => {
        const sum = effortSums[cat];
        const ceiling = effortCeilings[cat];
        if (sum > ceiling) {
          const catName = cat === "cerveau" ? "Cerveau" : (cat === "musculaire" ? "Musculaire" : (cat === "emotionnel_social" ? "Social/Émotionnel" : "Créatif/Divergent"));
          warnings.push(`⚠️ Dépassement de la limite ${catName} : ${sum.toFixed(1)}h planifiées (max ${ceiling.toFixed(1)}h).`);
        }
      });

      if (totalPlannedEffort > effortCeilings.total) {
        warnings.push(`⚠️ Dépassement de l'effort total maximal : ${totalPlannedEffort.toFixed(1)}h planifiées (max ${effortCeilings.total.toFixed(1)}h).`);
      }
      if (effortSums.repos < minRest) {
        warnings.push(`⚠️ Repos planifié insuffisant : ${effortSums.repos.toFixed(1)}h planifiées (min ${minRest.toFixed(1)}h).`);
      }

      let isHustleValid = true;
      if (activeTemplateName === "hustle") {
        const minUnplanned = 16.0 * 0.3; // 4.8h
        if (unplannedTime < minUnplanned) {
          isHustleValid = false;
          warnings.push(`⚠️ Journée Hustle invalide : moins de 30% de temps libre (${unplannedTime.toFixed(1)}h restantes sur 16h d'éveil, min ${minUnplanned.toFixed(1)}h requises).`);
        }
      }

      const warningsContainer = document.getElementById("effort-warnings-container");
      if (warningsContainer) {
        warningsContainer.innerHTML = "";
        if (warnings.length > 0) {
          warnings.forEach(w => {
            const warnEl = document.createElement("div");
            warnEl.style.cssText = "background: rgba(239, 68, 68, 0.1); color: var(--accent-red); border: 1px solid rgba(239, 68, 68, 0.2); padding: 8px 12px; border-radius: 8px; font-size: 0.78rem; font-weight: 500; display: flex; align-items: center; gap: 6px;";
            warnEl.textContent = w;
            warningsContainer.appendChild(warnEl);
          });
        } else {
          const okEl = document.createElement("div");
          okEl.style.cssText = "background: rgba(34, 197, 94, 0.1); color: var(--accent-green); border: 1px solid rgba(34, 197, 94, 0.2); padding: 8px 12px; border-radius: 8px; font-size: 0.78rem; font-weight: 500; display: flex; align-items: center; gap: 6px;";
          okEl.textContent = "✅ Budget d'énergie valide et équilibré.";
          warningsContainer.appendChild(okEl);
        }
      }

      const totalText = document.getElementById("effort-total-text");
      const totalBar = document.getElementById("effort-total-bar");
      if (totalText) {
        totalText.textContent = `${totalPlannedEffort.toFixed(1)}h / ${targetFocus.toFixed(1)}h`;
      }
      if (totalBar) {
        const totalPercent = Math.min((totalPlannedEffort / targetFocus) * 100, 100);
        totalBar.style.width = `${totalPercent}%`;
        if (totalPlannedEffort > effortCeilings.total || (activeTemplateName === "hustle" && !isHustleValid)) {
          totalBar.style.background = "var(--accent-red)";
        } else {
          totalBar.style.background = "linear-gradient(90deg, var(--accent-cyan), var(--accent-purple))";
        }
      }

      const unplannedText = document.getElementById("effort-unplanned-text");
      const restText = document.getElementById("effort-rest-text");
      if (unplannedText) {
        unplannedText.textContent = `Temps libre restant : ${unplannedTime.toFixed(1)}h`;
      }
      if (restText) {
        restText.textContent = `Repos requis : ${minRest.toFixed(1)}h`;
      }

      const categories = ["cerveau", "musculaire", "social", "creatif"];
      const keyMap = {
        cerveau: "cerveau",
        musculaire: "musculaire",
        social: "emotionnel_social",
        creatif: "creatif_divergent"
      };

      categories.forEach(cat => {
        const sum = effortSums[keyMap[cat]];
        const ceiling = effortCeilings[keyMap[cat]];
        const textEl = document.getElementById(`effort-${cat}-text`);
        const barEl = document.getElementById(`effort-${cat}-bar`);
        if (textEl) {
          textEl.textContent = `${sum.toFixed(1)}h / ${ceiling.toFixed(1)}h`;
        }
        if (barEl) {
          const percent = Math.min((sum / ceiling) * 100, 100);
          barEl.style.width = `${percent}%`;
          if (sum > ceiling) {
            barEl.style.background = "var(--accent-red)";
          } else {
            const defaultColors = {
              cerveau: "var(--accent-cyan)",
              musculaire: "var(--accent-red)",
              social: "var(--accent-green)",
              creatif: "var(--accent-purple)"
            };
            barEl.style.background = defaultColors[cat];
          }
        }
      });

      // The quest agenda is rendered from GET /agenda so per-date placements
      // remain the source of truth for the dashboard timeline.
    } catch (err) {
      console.error("Erreur updateDailyBudgetGauge:", err);
    }
  }

  function renderDailyRecap(templateName) {
    const templateConfig = loadedTemplates[templateName] || {};
    renderAgendaList(templateConfig.agenda_json || [], templateName);
  }

  function renderBudgetGauge() {
    return updateDailyBudgetGauge();
  }

  // ==============================================
  // DAILY QUESTS                                  //
  // ==============================================

  // Helper to convert time string to minutes
  function timeToMinutes(tStr) {
    if (!tStr) return 0;
    if (tStr === "24:00") return 1440;
    const [h, m] = tStr.split(":").map(Number);
    return (h || 0) * 60 + (m || 0);
  }

  // Helper to convert minutes to HH:MM
  function minutesToTime(mins) {
    const h = Math.floor(mins / 60).toString().padStart(2, "0");
    const m = (mins % 60).toString().padStart(2, "0");
    return `${h}:${m}`;
  }

  function agendaQuestById(habitId) {
    if (!questAgendaState) return null;
    const all = [
      ...(questAgendaState.placed_quests || []),
      ...(questAgendaState.unplaced_quests || [])
    ];
    return all.find(q => String(q.habit_id) === String(habitId));
  }

  function questFromAgendaItem(item) {
    return {
      id: item.habit_id,
      name: item.name,
      description: item.description || "",
      type: item.type || "binary",
      frequency: item.frequency || "daily",
      scheduled_days: item.scheduled_days || "0,1,2,3,4,5,6",
      effort_type: item.effort_type || "",
      effort_duration: item.effort_duration !== undefined && item.effort_duration !== null ? item.effort_duration : 1.0,
      agenda_duration_minutes: item.agenda_duration_minutes || item.duration_minutes || 60,
      source_type: item.source_type || "manual",
      source_ref: item.source_ref || null,
      source_label: item.source_label || null,
      auto_managed: !!item.auto_managed,
      archived_at: item.archived_at || null,
      agenda_placeable: item.agenda_placeable !== false,
      is_active: true,
      unit: item.unit || "",
      daily_target: item.daily_target || null,
      // The editor must use the current quest configuration, never an older
      // per-day snapshot displayed while correcting yesterday.
      progress_mode: item.progress_mode || "standard",
      checklist_items: Array.isArray(item.checklist_items) ? item.checklist_items : [],
      daily_progress: item.daily_progress || null,
      tags: item.tags || [],
      version_history: []
    };
  }

  function questConfigForAgendaItem(item) {
    const habitId = item?.habit_id ?? item?.id;
    return allHabitsCache.find(habit => String(habit.id) === String(habitId))
      || questFromAgendaItem(item);
  }

  function getStreakEmoji(streak) {
    if (streak >= 180) return "🥇";
    if (streak >= 90) return "🥈";
    if (streak >= 30) return "🥉";
    return "";
  }

  function renderAgendaQuestCard(item) {
    const isDone = item.status === "done";
    const isSkipped = item.status === "skipped";
    const isFailed = item.status === "failed";
    const isToday = getAgendaDate() === todayDateString();
    const statusClass = isDone ? "quest-done" : isSkipped ? "quest-skipped" : isFailed ? "quest-failed" : "";
    const card = document.createElement("div");
    card.className = `agenda-quest-card ${item.needs_configuration ? "needs-config" : ""} ${statusClass}`;
    card.dataset.habitId = item.habit_id;

    const effortLabels = {
      musculaire: "Musculaire",
      cerveau: "Cerveau",
      emotionnel_social: "Social",
      creatif_divergent: "Créatif",
      repos: "Repos"
    };
    const effortLabel = item.effort_type
      ? effortLabels[item.effort_type] || item.effort_type.replace("_", " ")
      : "";
    const sourceLabel = item.source_label || (item.source_type && item.source_type !== "manual" ? item.source_type : "");

    const emoji = getStreakEmoji(item.current_streak || 0);
    const emojiPrefix = emoji ? `${emoji} ` : "";

    // Checkbox for logging the habit
    const checkboxWrap = document.createElement("div");
    checkboxWrap.className = "agenda-quest-check";
    const checkbox = document.createElement("button");
    checkbox.type = "button";
    checkbox.className = `quest-log-checkbox ${isDone ? "checked" : ""} ${isSkipped ? "skipped" : ""} ${isFailed ? "failed" : ""}`;
    checkbox.title = isDone ? "Fait" : isSkipped ? "Passé" : isFailed ? "Ratée" : "Marquer comme fait";
    checkbox.innerHTML = isDone ? "✓" : isSkipped ? "⏭" : isFailed ? "×" : "";
    checkbox.addEventListener("click", async (event) => {
      event.stopPropagation();
      if (isDone || isSkipped || isFailed) return;
      const habitType = getQuestTypeForDate(item);
      if (habitType === "quantitative") {
        const amount = prompt(`Combien de ${getQuestUnitForDate(item)} ?`);
        if (amount === null) return;
        const parsed = parseFloat(amount);
        if (isNaN(parsed) || parsed <= 0) { showToast("Quantité invalide", true); return; }
        await submitQuestLog(item.habit_id, "log", parsed);
      } else {
        await submitQuestLog(item.habit_id, "done");
      }
    });
    checkboxWrap.appendChild(checkbox);

    const targetForDate = getQuestTargetForDate(item);
    const targetSuffix = targetForDate > 1
      ? ` (${item.today_count || 0}/${targetForDate})`
      : "";
    const main = document.createElement("div");
    main.className = "agenda-quest-main";
    const title = document.createElement("strong");
    title.textContent = `${emojiPrefix}${item.name}${targetSuffix}`;
    main.appendChild(title);
    if (sourceLabel) {
      const source = document.createElement("span");
      source.className = "agenda-quest-source";
      source.textContent = sourceLabel;
      main.appendChild(source);
    }
    const descriptionText = (item.description || "").trim();
    if (descriptionText) {
      const description = document.createElement("p");
      description.className = "agenda-quest-description";
      description.textContent = descriptionText;
      description.title = descriptionText;
      main.appendChild(description);
    }
    appendQuestTagBadges(main, item.tags);

    const meta = document.createElement("div");
    meta.className = "agenda-quest-meta";
    if (effortLabel) {
      const effort = document.createElement("span");
      effort.textContent = effortLabel;
      meta.appendChild(effort);
    }
    if (isDone) {
      const doneBadge = document.createElement("span");
      doneBadge.className = "agenda-status-badge done";
      doneBadge.textContent = "✅ Fait";
      meta.appendChild(doneBadge);
    } else if (isSkipped) {
      const skipBadge = document.createElement("span");
      skipBadge.className = "agenda-status-badge skipped";
      skipBadge.textContent = "⏭️ Passé";
      meta.appendChild(skipBadge);
    } else if (isFailed) {
      const failedBadge = document.createElement("span");
      failedBadge.className = "agenda-status-badge failed";
      failedBadge.textContent = "Ratée";
      meta.appendChild(failedBadge);
    } else {
      const pendingBadge = document.createElement("span");
      pendingBadge.className = "agenda-status-badge pending";
      pendingBadge.textContent = "À faire";
      meta.appendChild(pendingBadge);
    }
    if (item.needs_configuration) {
      const config = document.createElement("span");
      config.className = "agenda-config-flag";
      config.textContent = "à configurer";
      meta.appendChild(config);
    }

    const actions = document.createElement("div");
    actions.className = "agenda-quest-actions";
    const editBtn = document.createElement("button");
    editBtn.type = "button";
    editBtn.className = "agenda-small-btn agenda-edit-quest";
    editBtn.title = "Modifier la quête";
    editBtn.textContent = "Modifier";
    const statsBtn = document.createElement("button");
    statsBtn.type = "button";
    statsBtn.className = "agenda-small-btn agenda-stats-quest";
    statsBtn.title = "Statistiques de la quête";
    statsBtn.textContent = "Stats";
    actions.append(editBtn, statsBtn);
    const progressMode = getQuestProgressMode(item);
    if (progressMode !== "standard") {
      const progressBtn = document.createElement("button");
      progressBtn.type = "button";
      progressBtn.className = "agenda-small-btn agenda-progress-quest";
      progressBtn.title = "Afficher le suivi quotidien";
      progressBtn.textContent = questProgressButtonLabel(item);
      progressBtn.addEventListener("click", (event) => {
        event.stopPropagation();
        openQuestTrackingDrawer(item, progressBtn);
      });
      actions.appendChild(progressBtn);
    }
    if (isToday && !isDone && !isSkipped) {
      const failBtn = document.createElement("button");
      failBtn.type = "button";
      failBtn.className = `agenda-small-btn agenda-fail-quest ${isFailed ? "undo" : ""}`;
      failBtn.title = isFailed ? "Annuler l'échec" : "Déclarer la quête ratée";
      failBtn.setAttribute("aria-label", failBtn.title);
      failBtn.textContent = isFailed ? "↶" : "×";
      actions.appendChild(failBtn);
    }
    card.append(checkboxWrap, main, meta, actions);

    card.querySelector(".agenda-edit-quest")?.addEventListener("click", (event) => {
      event.stopPropagation();
      openEditQuestModal(questConfigForAgendaItem(item), item);
    });
    card.querySelector(".agenda-stats-quest")?.addEventListener("click", (event) => {
      event.stopPropagation();
      const habitObj = allHabitsCache.find(h => String(h.id) === String(item.habit_id)) || questFromAgendaItem(item);
      openHabitDetailModal(habitObj);
    });
    card.querySelector(".agenda-fail-quest")?.addEventListener("click", async (event) => {
      event.stopPropagation();
      await setHabitFailure(item.habit_id, isFailed);
    });
    return card;
  }

  function renderAgendaLists(data) {
    if (questsListContainer) {
      questsListContainer.innerHTML = "";
      const quests = [...(data.placed_quests || []), ...(data.unplaced_quests || [])];
      quests.sort((a, b) => {
        const aFinished = ["done", "skipped", "failed"].includes(a.status);
        const bFinished = ["done", "skipped", "failed"].includes(b.status);
        return Number(aFinished) - Number(bFinished) || a.name.localeCompare(b.name, "fr");
      });
      if (quests.length === 0) {
        questsListContainer.innerHTML = `<p class="agenda-empty">Aucune quête prévue pour ce jour.</p>`;
      } else {
        quests.forEach(item => questsListContainer.appendChild(renderAgendaQuestCard(item)));
      }
      const completed = quests.filter(item => ["done", "skipped"].includes(item.status)).length;
      const failed = quests.filter(item => item.status === "failed").length;
      if (questDaySummary) {
        questDaySummary.textContent = `${completed}/${quests.length} faites ou passées${failed ? ` · ${failed} ratée${failed > 1 ? "s" : ""}` : ""}`;
      }
    }
  }

  function renderQuestAgenda(data) {
    questAgendaState = data;
    const modelDay = document.getElementById("model-day-segments");
    if (modelDay) {
      modelDay.replaceChildren();
      const segments = [...(data.segments || [])].sort((a, b) => a.start.localeCompare(b.start));
      let previousEnd = "00:00";
      const addRow = (label, start, end, free = false) => {
        const row = document.createElement("div");
        row.className = free ? "model-day-free" : "model-day-segment";
        const time = document.createElement("span");
        time.textContent = `${start}–${end}`;
        const title = document.createElement("span");
        title.textContent = label;
        row.append(time, title);
        modelDay.appendChild(row);
      };
      segments.forEach(segment => {
        if (segment.start > previousEnd) addRow("Temps libre", previousEnd, segment.start, true);
        addRow(segment.title, segment.start, segment.end);
        if (segment.end > previousEnd) previousEnd = segment.end;
      });
      if (segments.length && previousEnd < "23:59") addRow("Temps libre", previousEnd, "23:59", true);
      if (!segments.length) modelDay.textContent = "Aucun horaire défini pour cette journée type.";
    }
    if (agendaDateInput) agendaDateInput.value = data.date || getAgendaDate();
    updateAgendaDateSwitch();
    if (agendaDayTypeBadge) {
      agendaDayTypeBadge.textContent = data.day_type || "regular";
      agendaDayTypeBadge.dataset.template = data.day_type || "regular";
    }
    updateQuestPanelShell();
    renderAgendaLists(data);
  }

  async function loadQuestAgenda(showErrors = false) {
    try {
      const date = getAgendaDate();
      const response = await fetch(`${API_BASE}/agenda?date=${encodeURIComponent(date)}`);
      if (!response.ok) throw new Error((await response.json()).detail || "Erreur agenda");
      const data = await response.json();
      renderQuestAgenda(data);
      return data;
    } catch (error) {
      console.error(error);
      if (showErrors) showToast(error.message, true);
      if (questsListContainer) {
        questsListContainer.innerHTML = `<p class="agenda-empty error">Erreur de chargement des quêtes du jour.</p>`;
      }
      return null;
    }
  }

  // Render the horizontal timeline bar
  function renderTimeline(agenda) {
    const bar = document.getElementById("timeline-bar");
    if (!bar) return;
    bar.innerHTML = "";

    if (!agenda || agenda.length === 0) {
      bar.innerHTML = `<div style="width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; color: var(--text-muted);">Aucun bloc planifié</div>`;
      return;
    }

    // Sort blocks by start time
    const sorted = [...agenda].sort((a, b) => timeToMinutes(a.start) - timeToMinutes(b.start));

    let currentMin = 0;
    const timelineBlocks = [];

    sorted.forEach(block => {
      const startMin = timeToMinutes(block.start);
      const endMin = timeToMinutes(block.end);

      if (startMin > currentMin) {
        // Gap block
        timelineBlocks.push({
          title: "Temps libre",
          category: "unplanned",
          start: minutesToTime(currentMin),
          end: block.start,
          duration: startMin - currentMin
        });
      }

      if (endMin > startMin) {
        timelineBlocks.push({
          ...block,
          duration: endMin - startMin
        });
        currentMin = endMin;
      }
    });

    if (currentMin < 1440) {
      timelineBlocks.push({
        title: "Temps libre",
        category: "unplanned",
        start: minutesToTime(currentMin),
        end: "24:00",
        duration: 1440 - currentMin
      });
    }

    // Render blocks
    timelineBlocks.forEach(b => {
      const pct = (b.duration / 1440) * 100;
      const el = document.createElement("div");
      el.className = `timeline-block block-${b.category}`;
      el.style.width = `${pct}%`;

      // Category colors
      if (b.category === "unplanned") {
        el.style.background = "rgba(255, 255, 255, 0.03)";
        el.style.borderRight = "1px dashed rgba(255,255,255,0.05)";
      }

      // Tooltip / title on hover
      const hours = (b.duration / 60).toFixed(1);
      el.title = `${b.title} (${b.start} - ${b.end}, ${hours}h)`;

      // Show title if block is wide enough
      if (pct > 7) {
        const textSpan = document.createElement("span");
        textSpan.style.cssText = "font-size: 0.65rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 0 4px;";
        textSpan.textContent = b.title;
        el.appendChild(textSpan);
      } else if (pct > 3) {
        const emojiSpan = document.createElement("span");
        emojiSpan.textContent = b.category === "sleep" ? "💤" : (b.category === "focus" ? "🎯" : (b.category === "routine" ? "⚙️" : (b.category === "relax" ? "🍃" : "")));
        el.appendChild(emojiSpan);
      }

      bar.appendChild(el);
    });
  }

  // Render the list of blocks
  function renderAgendaList(agenda, activeTemplateName) {
    const listContainer = document.getElementById("agenda-blocks-list");
    if (!listContainer) return;
    listContainer.innerHTML = "";

    if (!agenda || agenda.length === 0) {
      listContainer.innerHTML = `<p style="text-align: center; font-size: 0.8rem; color: var(--text-muted); padding: 1rem;">Aucun bloc planifié pour cette journée type. Ajoutez un premier bloc pour construire votre recap.</p>`;
      return;
    }

    // Sort chronologically
    const sorted = [...agenda].sort((a, b) => timeToMinutes(a.start) - timeToMinutes(b.start));

    sorted.forEach(block => {
      const item = document.createElement("div");
      item.className = "agenda-item";

      // Time pill
      const timeSpan = document.createElement("div");
      timeSpan.className = "agenda-time";
      timeSpan.textContent = `${block.start} - ${block.end}`;

      // Details column
      const details = document.createElement("div");
      details.className = "agenda-details";

      const title = document.createElement("div");
      title.className = "agenda-title";
      title.textContent = block.title;

      const meta = document.createElement("div");
      meta.className = "agenda-meta";

      // Effort type badge (stat-like badge from spec 009)
      const effortLabels = {
        musculaire: "💪 Musculaire",
        cerveau: "🧠 Cerveau",
        emotionnel_social: "🤝 Social",
        creatif_divergent: "🎨 Créatif"
      };
      const effortType = block.effort_type || "none";
      if (block.effort_type && effortLabels[block.effort_type]) {
        const effortBadge = document.createElement("span");
        effortBadge.className = `effort-badge effort-${effortType}`;
        effortBadge.textContent = `${effortLabels[block.effort_type]} (+${block.effort_duration || 1} pts)`;
        meta.appendChild(effortBadge);
      }

      // Category badge
      const catBadge = document.createElement("span");
      catBadge.className = `badge-category ${block.category}`;
      const catLabels = {
        focus: "FOCUS",
        routine: "ROUTINE",
        relax: "RELAX",
        sleep: "SLEEP"
      };
      catBadge.textContent = catLabels[block.category] || block.category;
      meta.appendChild(catBadge);

      details.appendChild(title);
      details.appendChild(meta);

      // Delete button
      const deleteBtn = document.createElement("button");
      deleteBtn.className = "btn-delete";
      deleteBtn.title = "Supprimer ce bloc";
      deleteBtn.innerHTML = "&times;";
      deleteBtn.addEventListener("click", () => deleteAgendaBlock(block.id, activeTemplateName, agenda));

      item.appendChild(timeSpan);
      item.appendChild(details);
      item.appendChild(deleteBtn);

      listContainer.appendChild(item);
    });
  }

  // Delete a block from agenda
  async function deleteAgendaBlock(blockId, templateName, currentAgenda) {
    if (!confirm("Voulez-vous vraiment supprimer ce bloc ?")) return;

    const updatedAgenda = currentAgenda.filter(b => b.id !== blockId);

    const templateConfig = loadedTemplates[templateName] || {};
    const payload = {
      template_name: templateName,
      focus_hours: templateConfig.focus_hours !== undefined ? templateConfig.focus_hours : (templateName === "hustle" ? 9.0 : (templateName === "rest" ? 2.0 : 6.0)),
      min_rest_hours: templateConfig.min_rest_hours !== undefined ? templateConfig.min_rest_hours : (templateName === "hustle" ? 6.0 : (templateName === "rest" ? 10.0 : 8.0)),
      ceilings: templateConfig.ceilings || null,
      agenda_json: updatedAgenda
    };

    try {
      const response = await fetch(`${API_BASE}/templates`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-User-ID": localStorage.getItem("habit_user_id") || "1"
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) throw new Error();

      showToast("Bloc supprimé avec succès !");
      updateDailyBudgetGauge();
    } catch (e) {
      console.error(e);
      showToast("Erreur lors de la suppression du bloc", true);
    }
  }

  // Add block form toggles
  if (toggleAddBlockBtn) {
    toggleAddBlockBtn.addEventListener("click", () => {
      const isHidden = addBlockFormContainer.style.display === "none";
      addBlockFormContainer.style.display = isHidden ? "flex" : "none";
      blockOverlapWarning.style.display = "none";
    });
  }

  if (cancelAddBlockBtn) {
    cancelAddBlockBtn.addEventListener("click", () => {
      addBlockFormContainer.style.display = "none";
      blockOverlapWarning.style.display = "none";
      blockTitleInput.value = "";
    });
  }

  // Check overlap condition helper
  function checkTimeOverlap(start, end, agenda) {
    const newStart = timeToMinutes(start);
    const newEnd = timeToMinutes(end);

    for (const block of agenda) {
      const bStart = timeToMinutes(block.start);
      const bEnd = timeToMinutes(block.end);

      if (newStart < bEnd && newEnd > bStart) {
        return true;
      }
    }
    return false;
  }

  function reevaluateOverlapWarning() {
    const activeTemplateName = activeDayType;
    const templateConfig = loadedTemplates[activeTemplateName] || {};
    const currentAgenda = templateConfig.agenda_json || [];
    const start = blockStartInput.value;
    const end = blockEndInput.value;

    if (checkTimeOverlap(start, end, currentAgenda)) {
      blockOverlapWarning.style.display = "block";
    } else {
      blockOverlapWarning.style.display = "none";
    }
  }

  if (blockStartInput) blockStartInput.addEventListener("change", reevaluateOverlapWarning);
  if (blockEndInput) blockEndInput.addEventListener("change", reevaluateOverlapWarning);

  // Add a block to agenda
  if (saveBlockBtn) {
    saveBlockBtn.addEventListener("click", async () => {
      const title = blockTitleInput.value.trim();
      const start = blockStartInput.value;
      const end = blockEndInput.value;
      const category = blockCategorySelect.value;

      if (!title) {
        showToast("Le titre de l'activité ne peut pas être vide.", true);
        return;
      }

      const activeTemplateName = activeDayType;
      const templateConfig = loadedTemplates[activeTemplateName] || {};
      const currentAgenda = templateConfig.agenda_json || [];

      // Check overlap
      if (checkTimeOverlap(start, end, currentAgenda)) {
        blockOverlapWarning.style.display = "block";
        showToast("⚠️ Conflit d'horaire avec un bloc existant.", true);
        return;
      } else {
        blockOverlapWarning.style.display = "none";
      }

      const newId = currentAgenda.length > 0 ? Math.max(...currentAgenda.map(b => b.id)) + 1 : 1;
      const updatedAgenda = [...currentAgenda, { id: newId, title, start, end, category }];

      const payload = {
        template_name: activeTemplateName,
        focus_hours: templateConfig.focus_hours !== undefined ? templateConfig.focus_hours : (activeTemplateName === "hustle" ? 9.0 : (activeTemplateName === "rest" ? 2.0 : 6.0)),
        min_rest_hours: templateConfig.min_rest_hours !== undefined ? templateConfig.min_rest_hours : (activeTemplateName === "hustle" ? 6.0 : (activeTemplateName === "rest" ? 10.0 : 8.0)),
        ceilings: templateConfig.ceilings || null,
        agenda_json: updatedAgenda
      };

      try {
        const response = await fetch(`${API_BASE}/templates`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-User-ID": localStorage.getItem("habit_user_id") || "1"
          },
          body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error();

        showToast("Bloc type ajouté !");
        addBlockFormContainer.style.display = "none";
        blockTitleInput.value = "";
        updateDailyBudgetGauge();
      } catch (e) {
        console.error(e);
        showToast("Erreur lors de l'ajout du bloc", true);
      }
    });
  }

  // ==============================================
  // HISTORICAL Dot Calendar (30 Days)             //
  // ==============================================
  function normalizeTemplateName(templateName) {
    return (templateName || "").trim().toLowerCase();
  }

  function isRestTemplate(templateName) {
    return ["rest", "recup", "recovery", "sick", "malade"].includes(normalizeTemplateName(templateName));
  }

  function isHustleTemplate(templateName) {
    return normalizeTemplateName(templateName) === "hustle";
  }

  function historyStatusLabel(day) {
    if (day.status === "future") return "À venir";
    if (day.status === "perfect") return "Perfect Day ! (+5 XP) 🏆";
    if (day.status === "broken") return "Brisée : Perfect côté quêtes, No-Todo brisé ⚠️";
    return "Échec / Incomplet ❌";
  }

  function appendHistoryWeekSummary(container, weekDays) {
    if (!container || !weekDays.length) return;

    const referenceDay = weekDays[weekDays.length - 1] || weekDays[0];
    const rec = referenceDay.cycle_recommendation || {};
    const label = rec.label || (referenceDay.cycle_week_type === "chill" ? "Semaine chill" : "Semaine normale");
    const policyIds = new Set(weekDays.map(day => day.cycle_policy_id).filter(Boolean));
    const weekTypes = new Set(weekDays.map(day => day.cycle_week_type).filter(Boolean));
    const adjusted = policyIds.size > 1 || weekTypes.size > 1 ? " · cycle ajusté" : "";
    const visibleDays = weekDays.filter(day => day.status !== "future");
    const hustleCount = visibleDays.filter(day => isHustleTemplate(day.template)).length;
    const restCount = visibleDays.filter(day => isRestTemplate(day.template)).length;
    const hustleTarget = rec.hustle_max || rec.hustle || "-";
    const restTarget = rec.rest_max || rec.rest || "-";

    const summary = document.createElement("div");
    summary.className = "calendar-week-summary";
    summary.textContent = `${label}${adjusted} · 🔥 ${hustleCount}/${hustleTarget} · 💤 ${restCount}/${restTarget}`;
    container.appendChild(summary);
  }

  async function fetchHistory() {
    try {
      const response = await fetch(`${API_BASE}/history`);
      if (!response.ok) throw new Error("Erreur history API");
      const history = await response.json();

      const calendarContainer = document.getElementById("calendar-grid-container");
      if (calendarContainer) {
        calendarContainer.innerHTML = "";

        const days = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"];
        days.forEach(day => {
          const header = document.createElement("div");
          header.className = "calendar-day-header";
          header.textContent = day;
          calendarContainer.appendChild(header);
        });

        let cellsInWeek = 0;
        let currentWeekDays = [];
        if (history.length > 0) {
          const firstDayOffset = history[0].weekday;
          for (let i = 0; i < firstDayOffset; i++) {
            const emptySlot = document.createElement("div");
            emptySlot.className = "calendar-day-empty";
            calendarContainer.appendChild(emptySlot);
            cellsInWeek++;
          }
        }

        history.forEach(day => {
          const box = document.createElement("div");
          box.className = `calendar-day-box ${day.status}`;

          const statusText = historyStatusLabel(day);
          const templateName = day.template || "default";
          box.title = `${day.date} : ${statusText} · ${templateName}`;
          box.innerHTML = `<span class="calendar-day-number">${day.label}</span><span class="calendar-day-template">${day.template_emoji || "⚖️"}</span>`;
          calendarContainer.appendChild(box);
          currentWeekDays.push(day);
          cellsInWeek++;

          if (cellsInWeek === 7) {
            appendHistoryWeekSummary(calendarContainer, currentWeekDays);
            currentWeekDays = [];
            cellsInWeek = 0;
          }
        });

        if (cellsInWeek > 0) {
          while (cellsInWeek < 7) {
            const emptySlot = document.createElement("div");
            emptySlot.className = "calendar-day-empty";
            calendarContainer.appendChild(emptySlot);
            cellsInWeek++;
          }
          appendHistoryWeekSummary(calendarContainer, currentWeekDays);
        }
      }
    } catch (error) {
      console.error(error);
    }
  }

  // ==============================================
  // BOUNTIES (TODOS / PRIMES)                     //
  // ==============================================
  let activeEditBounty = null;

  async function fetchBounties() {
    try {
      const response = await fetch(`${API_BASE}/todos`);
      if (!response.ok) throw new Error("Erreur Todos API");
      const bounties = await response.json();

      const container = document.getElementById("bounties-list-container");
      if (!container) return;

      container.innerHTML = "";

      const todayObj = new Date();
      const yyyy = todayObj.getFullYear();
      const mm = String(todayObj.getMonth() + 1).padStart(2, '0');
      const dd = String(todayObj.getDate()).padStart(2, '0');
      const todayStr = `${yyyy}-${mm}-${dd}`;

      const visibleBounties = bounties.filter(b => {
        const hasDoDate = !!b.do_date;
        const isToday = hasDoDate ? b.do_date <= todayStr : (!b.due_date || b.due_date <= todayStr);
        return showTodayBounties ? isToday : !isToday;
      });

      const toggleBountiesBtn = document.getElementById("toggle-bounties-view-btn");
      const bountiesPanelTitle = document.getElementById("bounties-panel-title");
      if (bountiesPanelTitle) {
        bountiesPanelTitle.textContent = showTodayBounties ? "⚔️ Tableau des Primes (Aujourd'hui)" : "⚔️ Tableau des Primes (Autres jours)";
      }
      if (toggleBountiesBtn) {
        toggleBountiesBtn.textContent = showTodayBounties ? "➡️" : "⬅️";
        toggleBountiesBtn.title = showTodayBounties ? "Voir les primes des autres jours" : "Retour aux primes d'aujourd'hui";
      }

      if (visibleBounties.length === 0) {
        const noBountiesMsg = showTodayBounties ? "Aucune prime active pour aujourd'hui." : "Aucune prime planifiée pour les autres jours.";
        container.innerHTML = `<p style="color: var(--text-secondary); font-size: 0.85rem; text-align: center; padding: 1.5rem 0;">${noBountiesMsg}</p>`;
        return;
      }

      visibleBounties.forEach(b => {
        const item = document.createElement("div");
        item.className = "bounty-card";

        let dateInfo = [];
        if (b.do_date) {
          const parts = b.do_date.split("-");
          const dateStr = parts.length === 3 ? `${parts[2]}/${parts[1]}` : b.do_date;
          dateInfo.push(`📅 Planifié : ${dateStr}`);
        }
        if (b.due_date) {
          const parts = b.due_date.split("-");
          const dateStr = parts.length === 3 ? `${parts[2]}/${parts[1]}` : b.due_date;
          dateInfo.push(`🚨 Limite : ${dateStr}`);
        }
        const info = document.createElement("div");
        info.className = "bounty-info";
        const title = document.createElement("span");
        title.className = "bounty-title";
        title.textContent = b.title;
        const xp = document.createElement("span");
        xp.className = "bounty-xp-tag";
        xp.textContent = `🏆 +${b.xp_reward} XP`;
        info.append(title, xp);
        if (b.linked_goal_id) {
          const linked = document.createElement("span");
          linked.className = "bounty-xp-tag";
          linked.textContent = "🎯 Objectif lié";
          info.appendChild(linked);
        }
        if (dateInfo.length > 0) {
          const dateEl = document.createElement("span");
          dateEl.style.cssText = "font-size: 0.78rem; color: var(--text-muted); margin-top: 4px; display: inline-flex; gap: 8px;";
          dateEl.textContent = dateInfo.join(" | ");
          info.appendChild(dateEl);
        }

        const actions = document.createElement("div");
        actions.className = "bounty-card-actions";
        const editBtn = document.createElement("button");
        editBtn.type = "button";
        editBtn.className = "bounty-edit-btn";
        editBtn.dataset.id = b.id;
        editBtn.title = "Modifier la prime";
        editBtn.setAttribute("aria-label", "Modifier la prime");
        editBtn.textContent = "✏️";
        const claimBtn = document.createElement("button");
        claimBtn.className = `substep-btn-check ${b.is_completed ? "completed" : ""}`;
        claimBtn.dataset.id = b.id;
        claimBtn.disabled = Boolean(b.is_completed);
        claimBtn.textContent = b.is_completed ? "Réclamée" : "Réclamer";
        actions.append(editBtn, claimBtn);
        item.append(info, actions);

        item.querySelector(".bounty-edit-btn")?.addEventListener("click", () => openEditBountyModal(b));

        if (!b.is_completed) {
          const btn = item.querySelector(".substep-btn-check");
          btn.addEventListener("click", () => claimBounty(b.id));
        }

        container.appendChild(item);
      });

    } catch (error) {
      console.error(error);
    }
  }

  async function fetchNoTodos() {
    const selectedDate = getAgendaDate();
    const container = document.getElementById("notodos-list-container");
    if (!container) return;
    if (!isCorrectableAgendaDate(selectedDate)) {
      container.innerHTML = `<p class="agenda-empty">Les corrections No-Todo sont disponibles pour aujourd'hui et hier seulement.</p>`;
      return;
    }
    try {
      const response = await fetch(`${API_BASE}/notodos?target_date=${encodeURIComponent(selectedDate)}`);
      if (!response.ok) throw new Error("Erreur NoTodos API");
      const notodos = await response.json();
      const dateLabel = selectedDate === todayDateString() ? "aujourd'hui" : "hier";

      container.innerHTML = "";
      if (notodos.length === 0) {
        container.innerHTML = `<p style="color: var(--text-secondary); font-size: 0.85rem; text-align: center; padding: 1.5rem 0;">Aucune règle stricte configurée.</p>`;
        return;
      }

      notodos.forEach(n => {
        const failedOnDate = Boolean(n.failed_on_date);
        const item = document.createElement("li");
        item.className = "bounty-card";

        if (failedOnDate) {
          item.style.borderColor = "rgba(239, 68, 68, 0.6)";
          item.style.background = "rgba(239, 68, 68, 0.15)";
        } else {
          item.style.borderColor = "rgba(239, 68, 68, 0.3)";
          item.style.background = "rgba(239, 68, 68, 0.05)";
        }

        const info = document.createElement("div");
        info.className = "bounty-info";
        const title = document.createElement("span");
        title.className = "bounty-title";
        title.style.cssText = "color: #ef4444; font-size: 1.05rem;";
        title.textContent = `❌ ${n.title}`;
        const status = document.createElement("span");
        status.className = "goal-selector-meta";
        status.style.cssText = "color: rgba(255,255,255,0.7); font-size: 0.85rem; margin-top: 4px;";
        status.textContent = failedOnDate ? `Échoué ${dateLabel}` : `Respecté ${dateLabel}`;
        info.append(title, status);

        const actions = document.createElement("div");
        actions.style.cssText = "display: flex; gap: 8px; align-items: center;";
        const failBtn = document.createElement("button");
        failBtn.className = `substep-btn-check ${failedOnDate ? "completed" : ""}`;
        failBtn.dataset.id = n.id;
        failBtn.disabled = failedOnDate;
        failBtn.style.cssText = `background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; padding: 0 16px; color: #ef4444; font-family: var(--font-display); font-weight: 600; font-size: 0.85rem; cursor: ${failedOnDate ? "not-allowed" : "pointer"}; transition: var(--transition-smooth); display: inline-flex; align-items: center; justify-content: center; height: 38px; opacity: ${failedOnDate ? 0.6 : 1};`;
        failBtn.textContent = failedOnDate ? "Échoué" : "Déclarer Échec";
        if (!failedOnDate) {
          failBtn.addEventListener("mouseover", () => {
            failBtn.style.background = "rgba(239, 68, 68, 0.2)";
            failBtn.style.transform = "scale(1.02)";
          });
          failBtn.addEventListener("mouseout", () => {
            failBtn.style.background = "rgba(239, 68, 68, 0.1)";
            failBtn.style.transform = "scale(1)";
          });
        }
        const deleteBtn = document.createElement("button");
        deleteBtn.className = "notodo-delete-btn";
        deleteBtn.dataset.id = n.id;
        deleteBtn.style.cssText = "background: rgba(255, 255, 255, 0.05); border: 1px solid var(--border-glass); border-radius: 8px; width: 38px; height: 38px; display: inline-flex; align-items: center; justify-content: center; color: var(--text-muted); cursor: pointer; transition: var(--transition-smooth);";
        deleteBtn.title = "Supprimer la règle";
        deleteBtn.textContent = "🗑️";
        deleteBtn.addEventListener("mouseover", () => {
          deleteBtn.style.background = "rgba(239, 68, 68, 0.15)";
          deleteBtn.style.color = "#ef4444";
          deleteBtn.style.transform = "scale(1.02)";
        });
        deleteBtn.addEventListener("mouseout", () => {
          deleteBtn.style.background = "rgba(255, 255, 255, 0.05)";
          deleteBtn.style.color = "var(--text-muted)";
          deleteBtn.style.transform = "scale(1)";
        });
        actions.append(failBtn, deleteBtn);
        item.append(info, actions);

        if (!failedOnDate) {
          const btn = item.querySelector(".substep-btn-check");
          btn.addEventListener("click", () => failNoTodo(n.id, selectedDate));
        }

        deleteBtn.addEventListener("click", () => deleteNoTodo(n.id));

        container.appendChild(item);
      });

    } catch (error) {
      console.error(error);
    }
  }

  async function failNoTodo(id, targetDate = getAgendaDate()) {
    try {
      const response = await fetch(`${API_BASE}/notodos/${id}/fail`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_date: targetDate })
      });
      if (!response.ok) throw new Error((await response.json()).detail || "Erreur fail notodo");

      showToast(targetDate === todayDateString()
        ? "Échec de la règle enregistré pour aujourd'hui."
        : "Échec de la règle enregistré pour hier.", true);
      refreshAll();
    } catch (error) {
      console.error(error);
      showToast("Erreur lors de la déclaration d'échec", true);
    }
  }

  async function deleteNoTodo(id) {
    if (!confirm("Voulez-vous vraiment supprimer définitivement cette règle ?")) return;
    try {
      const response = await fetch(`${API_BASE}/notodos/${id}`, { method: "DELETE" });
      if (!response.ok) throw new Error("Erreur suppression notodo");

      showToast("Règle No-Todo supprimée avec succès !");
      refreshAll();
    } catch (error) {
      console.error(error);
      showToast("Erreur lors de la suppression de la règle", true);
    }
  }


  async function claimBounty(id) {
    try {
      const response = await fetch(`${API_BASE}/todos/${id}/complete`, { method: "POST" });
      if (!response.ok) throw new Error("Erreur claim bounty");
      const data = await response.json();

      showToast(`Prime réclamée avec succès ! +${data.xp_rewarded} XP ! 🎉`);
      if (data.levels_gained > 0) {
        showToast(`LEVEL UP! Félicitations pour le Niveau ${data.new_level}! 🚀`);
      }
      refreshAll();
    } catch (error) {
      console.error(error);
      showToast("Erreur lors de la réclamation", true);
    }
  }

  function openEditBountyModal(bounty) {
    activeEditBounty = bounty;
    document.getElementById("edit-bounty-link-goal-btn").hidden = Boolean(bounty.linked_goal_id);
    document.getElementById("edit-bounty-id").value = bounty.id;
    document.getElementById("edit-bounty-title").value = bounty.title || "";
    document.getElementById("edit-bounty-xp").value = bounty.xp_reward || 10;
    document.getElementById("edit-bounty-do-date").value = bounty.do_date || "";
    document.getElementById("edit-bounty-due-date").value = bounty.due_date || "";
    document.getElementById("edit-bounty-overlay")?.classList.add("open");
    document.getElementById("edit-bounty-drawer")?.classList.add("open");
  }

  function closeEditBountyModal() {
    activeEditBounty = null;
    document.getElementById("edit-bounty-overlay")?.classList.remove("open");
    document.getElementById("edit-bounty-drawer")?.classList.remove("open");
  }

  async function saveEditBounty() {
    const id = document.getElementById("edit-bounty-id").value;
    const title = document.getElementById("edit-bounty-title").value.trim();
    const xp = parseInt(document.getElementById("edit-bounty-xp").value, 10);
    const doDate = document.getElementById("edit-bounty-do-date").value || null;
    const dueDate = document.getElementById("edit-bounty-due-date").value || null;

    if (!id || !activeEditBounty) return;
    if (!title) {
      showToast("Veuillez donner un titre à la prime !", true);
      return;
    }
    if (Number.isNaN(xp) || xp < 0 || xp > 40) {
      showToast("La récompense XP doit être entre 0 et 40.", true);
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/todos/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          xp_reward: xp,
          do_date: doDate,
          due_date: dueDate
        })
      });
      if (!response.ok) throw new Error((await response.json()).detail || "Erreur de sauvegarde");

      showToast("Prime mise à jour.");
      closeEditBountyModal();
      fetchBounties();
    } catch (error) {
      console.error(error);
      showToast(error.message || "Erreur lors de la modification de la prime", true);
    }
  }

  async function deleteBounty(id) {
    if (!confirm("Voulez-vous vraiment supprimer définitivement cette prime ?")) return;
    try {
      const response = await fetch(`${API_BASE}/todos/${id}`, {
        method: "DELETE"
      });
      if (!response.ok) throw new Error("Erreur suppression bounty");

      showToast("Prime supprimée avec succès !");
      closeEditBountyModal();
      refreshAll();
    } catch (error) {
      console.error(error);
      showToast("Erreur lors de la suppression de la prime", true);
    }
  }

  document.getElementById("close-edit-bounty-btn")?.addEventListener("click", closeEditBountyModal);
  document.getElementById("cancel-edit-bounty-btn")?.addEventListener("click", closeEditBountyModal);
  document.getElementById("edit-bounty-overlay")?.addEventListener("click", closeEditBountyModal);
  document.getElementById("save-edit-bounty-btn")?.addEventListener("click", saveEditBounty);
  document.getElementById("delete-edit-bounty-btn")?.addEventListener("click", () => {
    if (activeEditBounty) {
      deleteBounty(activeEditBounty.id);
    }
  });
  async function chooseGoalReplacement() {
    const profileResponse = await fetch(`${API_BASE}/profile`);
    if (!profileResponse.ok) throw new Error("Profil indisponible.");
    const profile = await profileResponse.json();
    const pins = profile.pinned_goals || [];
    if (pins.length < 3) return { replace_pinned_goal_id: null };
    const goalsResponse = await fetch(`${API_BASE}/goals`);
    const goals = await goalsResponse.json();
    const choices = pins.map(id => goals.find(goal => goal.id === id)).filter(Boolean);
    const selected = prompt(`Top 3 complet. ID de l'objectif à remplacer :\n${choices.map(goal => `${goal.id} — ${goal.title}`).join("\n")}`);
    if (selected === null) return null;
    const replacement = Number(selected);
    if (!pins.includes(replacement)) { showToast("Choisissez un ID du Top 3.", true); return null; }
    return { replace_pinned_goal_id: replacement };
  }
  document.getElementById("edit-bounty-link-goal-btn")?.addEventListener("click", async () => {
    if (!activeEditBounty || activeEditBounty.linked_goal_id) return;
    try {
      const replacement = await chooseGoalReplacement();
      if (!replacement) return;
      const response = await fetch(`${API_BASE}/todos/${activeEditBounty.id}/linked-goal`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(replacement) });
      if (!response.ok) throw new Error((await response.json()).detail || "Création impossible");
      showToast("Objectif lié créé.");
      closeEditBountyModal();
      refreshAll();
    } catch (error) { showToast(error.message, true); }
  });

  function setupBountiesEvents() {
    const openBountyBtn = document.getElementById("open-bounty-inline-btn");
    const bountyForm = document.getElementById("bounty-inline-form");
    const submitBountyBtn = document.getElementById("submit-bounty-btn");

    if (openBountyBtn && bountyForm) {
      openBountyBtn.addEventListener("click", () => {
        if (bountyForm.style.display === "none") {
          bountyForm.style.display = "flex";
          openBountyBtn.textContent = "Fermer Formulaire";
        } else {
          bountyForm.style.display = "none";
          openBountyBtn.textContent = "+ Prime";
        }
      });
    }

    if (submitBountyBtn) {
      submitBountyBtn.addEventListener("click", async () => {
        const titleInput = document.getElementById("new-bounty-title");
        const xpInput = document.getElementById("new-bounty-xp");

        const title = titleInput.value.trim();
        const xp = parseInt(xpInput.value) || 10;

        const doDate = document.getElementById("new-bounty-do-date").value || null;
        const dueDate = document.getElementById("new-bounty-due-date").value || null;
        const createLinkedGoal = document.getElementById("new-bounty-linked-goal").checked;

        if (!title) {
          showToast("Veuillez donner un titre à la prime !", true);
          return;
        }

        try {
          const replacement = createLinkedGoal ? await chooseGoalReplacement() : { replace_pinned_goal_id: null };
          if (!replacement) return;
          const response = await fetch(`${API_BASE}/todos`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              title: title,
              xp_reward: xp,
              do_date: doDate,
              due_date: dueDate,
              create_linked_goal: createLinkedGoal,
              ...replacement
            })
          });

          if (!response.ok) throw new Error((await response.json()).detail || "Erreur de publication");
          showToast("Nouvelle prime publiée au tableau ! ⚔️");
          titleInput.value = "";
          xpInput.value = 20;
          document.getElementById("new-bounty-do-date").value = "";
          document.getElementById("new-bounty-due-date").value = "";
          document.getElementById("new-bounty-linked-goal").checked = false;
          bountyForm.style.display = "none";
          openBountyBtn.textContent = "+ Prime";
          refreshAll();
        } catch (error) {
          console.error(error);
          showToast("Erreur lors de la création de la prime", true);
        }
      });
    }
  }

  // ==============================================
  // SCREEN 2: GOALS & SUBSTEPS DAG GRAPH           //
  // ==============================================
  let activeGoalId = null;

  window.selectGoalById = function(id) {
    activeGoalId = id;
    fetchGoals();
  };

  function getGoalById(goals, goalId) {
    if (!Array.isArray(goals)) return null;
    return goals.find(goal => goal.id === goalId) || null;
  }

  function getSubstepInGoal(goal, substepId) {
    if (!goal || !Array.isArray(goal.substeps)) return null;
    return goal.substeps.find(substep => substep.id === substepId) || null;
  }

  function buildGoalTreeViewGoal(goal, goals) {
    if (!goal) return null;

    const substeps = Array.isArray(goal.substeps) ? [...goal.substeps] : [];
    const renderedSubstepIds = new Set(substeps.map(substep => substep.id));
    const allGoals = Array.isArray(goals) ? goals : [];

    allGoals.forEach(sourceGoal => {
      if (sourceGoal.id === goal.id || !Array.isArray(sourceGoal.substeps)) return;

      sourceGoal.substeps.forEach(substep => {
        if (renderedSubstepIds.has(substep.id)) return;

        const linkedGoals = Array.isArray(substep.linked_goals) ? substep.linked_goals : [];
        const isLinkedToActiveGoal = linkedGoals.some(linkedGoal => linkedGoal.id === goal.id);
        if (!isLinkedToActiveGoal) return;

        const displayedLinks = new Map();
        displayedLinks.set(sourceGoal.id, {
          id: sourceGoal.id,
          title: sourceGoal.title
        });
        linkedGoals.forEach(linkedGoal => {
          if (linkedGoal.id !== goal.id) {
            displayedLinks.set(linkedGoal.id, linkedGoal);
          }
        });

        renderedSubstepIds.add(substep.id);
        substeps.push({
          ...substep,
          linked_goals: Array.from(displayedLinks.values()),
          is_linked_fallback: true
        });
      });
    });

    return { ...goal, substeps };
  }

  function highlightGoalSubstep(substepId) {
    const node = document.querySelector(`.tree-node[data-substep-id="${substepId}"]`);
    if (!node) return false;

    node.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
    node.style.animation = "none";
    void node.offsetHeight;
    node.style.animation = "pulse-highlight 1.5s ease-in-out 3";
    return true;
  }

  function highlightGoalSubstepAfterRender(substepId) {
    window.requestAnimationFrame(() => {
      if (!highlightGoalSubstep(substepId)) {
        setTimeout(() => highlightGoalSubstep(substepId), 150);
      }
    });
  }

  function getLinkableSourceSubsteps(sourceGoal, activeGoal) {
    if (!sourceGoal || !activeGoal) return [];

    const activeSubstepIds = new Set(
      (activeGoal.substeps || []).map(substep => substep.id)
    );
    return (sourceGoal.substeps || [])
      .filter(substep => {
        const linkedToActiveGoal = (substep.linked_goals || [])
          .some(linkedGoal => linkedGoal.id === activeGoal.id);
        return !activeSubstepIds.has(substep.id) && !linkedToActiveGoal;
      });
  }

  function renderLinkSelectOption(value, label) {
    return `<option value="${value}" style="background-color: hsl(222, 47%, 9%); color: hsl(0, 0%, 98%);">${escapeHtml(label)}</option>`;
  }

  function updateLinkSubstepOptions(goals, activeGoal) {
    const sourceSelect = document.getElementById("link-goal-select");
    const substepSelect = document.getElementById("link-substep-select");
    const submitBtn = document.getElementById("link-substep-submit-btn");
    if (!sourceSelect || !substepSelect) return;

    const sourceGoalId = parseInt(sourceSelect.value);
    const sourceGoal = getGoalById(goals, sourceGoalId);
    const linkableSubsteps = getLinkableSourceSubsteps(sourceGoal, activeGoal);

    substepSelect.innerHTML = "";
    if (linkableSubsteps.length === 0) {
      substepSelect.innerHTML = renderLinkSelectOption("", "Aucune étape disponible");
      substepSelect.disabled = true;
      if (submitBtn) submitBtn.disabled = true;
      return;
    }

    linkableSubsteps.forEach(substep => {
      substepSelect.innerHTML += renderLinkSelectOption(substep.id, substep.title);
    });
    substepSelect.disabled = false;
    if (submitBtn) submitBtn.disabled = false;
  }

  function renderGoalLinkControls(goals, activeGoal) {
    const sourceSelect = document.getElementById("link-goal-select");
    const substepSelect = document.getElementById("link-substep-select");
    const submitBtn = document.getElementById("link-substep-submit-btn");
    if (!sourceSelect || !substepSelect) return;

    const activeViewGoal = buildGoalTreeViewGoal(activeGoal, goals);
    const previousSourceGoalId = parseInt(sourceSelect.value);
    const sourceGoals = goals
      .filter(goal => activeGoal && goal.id !== activeGoal.id)
      .map(goal => ({
        goal,
        linkableSubsteps: getLinkableSourceSubsteps(goal, activeViewGoal)
      }))
      .filter(item => item.linkableSubsteps.length > 0);

    sourceSelect.innerHTML = "";
    if (!activeGoal || sourceGoals.length === 0) {
      sourceSelect.innerHTML = renderLinkSelectOption("", "Aucune source disponible");
      sourceSelect.disabled = true;
      substepSelect.innerHTML = renderLinkSelectOption("", "Aucune étape disponible");
      substepSelect.disabled = true;
      if (submitBtn) submitBtn.disabled = true;
      renderUnlinkSubstepList(activeViewGoal);
      return;
    }

    sourceGoals.forEach(({ goal, linkableSubsteps }) => {
      sourceSelect.innerHTML += renderLinkSelectOption(goal.id, `${goal.title} (${linkableSubsteps.length})`);
    });
    sourceSelect.disabled = false;
    if (sourceGoals.some(({ goal }) => goal.id === previousSourceGoalId)) {
      sourceSelect.value = String(previousSourceGoalId);
    } else {
      sourceSelect.value = String(sourceGoals[0].goal.id);
    }
    sourceSelect.onchange = () => updateLinkSubstepOptions(goals, activeViewGoal);

    updateLinkSubstepOptions(goals, activeViewGoal);
    renderUnlinkSubstepList(activeViewGoal);
  }

  function renderUnlinkSubstepList(activeGoal) {
    const list = document.getElementById("unlink-substep-list");
    if (!list) return;

    list.innerHTML = "";
    if (!activeGoal) {
      list.innerHTML = `<p style="font-size: 0.78rem; color: var(--text-muted); margin: 0;">Sélectionnez un objectif.</p>`;
      return;
    }

    const linkedSubsteps = (activeGoal.substeps || [])
      .filter(substep => (substep.linked_goals || []).length > 0);

    if (linkedSubsteps.length === 0) {
      list.innerHTML = `<p style="font-size: 0.78rem; color: var(--text-muted); margin: 0;">Aucune liaison à retirer pour cet objectif.</p>`;
      return;
    }

    linkedSubsteps.forEach(substep => {
      const row = document.createElement("div");
      row.style.cssText = "display: grid; grid-template-columns: 1fr auto; align-items: center; gap: 0.5rem; background: rgba(255,255,255,0.02); border: 1px solid var(--border-glass); border-radius: 8px; padding: 0.45rem 0.55rem;";

      const linkedGoalTitles = substep.linked_goals.map(goal => goal.title).join(" / ");
      const label = document.createElement("span");
      label.style.cssText = "font-size: 0.78rem; color: var(--text-secondary); line-height: 1.3;";
      label.textContent = `${substep.title} - lié à ${linkedGoalTitles}`;

      const button = document.createElement("button");
      button.type = "button";
      button.className = "quest-action-btn";
      button.style.cssText = "padding: 4px 8px; font-size: 0.7rem; width: auto; background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.55); color: rgb(248, 113, 113);";
      button.textContent = "Délier";
      button.addEventListener("click", () => unlinkSubstepFromActiveGoal(substep.id));

      row.appendChild(label);
      row.appendChild(button);
      list.appendChild(row);
    });
  }

  async function unlinkSubstepFromActiveGoal(substepId) {
    if (!activeGoalId) {
      showToast("Sélectionnez d'abord un objectif.", true);
      return;
    }

    try {
      const resp = await fetch(`${API_BASE}/goals/${activeGoalId}/substeps/${substepId}/link`, {
        method: "DELETE"
      });
      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.detail || "Erreur lors du retrait de la liaison");
      }

      showToast("Sous-étape déliée de l'objectif actif.");
      await fetchGoals();
    } catch (err) {
      console.error(err);
      showToast(err.message || "Erreur lors du retrait de la liaison", true);
    }
  }

  // Drawer Toggle Helpers
  function openDrawer(mode = "add", goalData = null, substepData = null, otherSubstepsInGoal = []) {
    const drawer = document.getElementById("creators-drawer");
    const overlay = document.getElementById("drawer-overlay");
    if (!drawer || !overlay) return;

    const drawerTitle = document.getElementById("drawer-title");
    const goalSubmitBtn = document.getElementById("goal-submit-btn");
    const editIdInput = document.getElementById("edit-goal-id-input");
    const titleInput = document.getElementById("goal-title-input");
    const descInput = document.getElementById("goal-desc-input");

    drawer.classList.add("open");
    overlay.classList.add("open");

    if (mode === "edit-substep" && substepData) {
      drawerTitle.textContent = "✏️ Éditer Sous-étape";

      document.getElementById("edit-substep-section").style.display = "block";
      document.getElementById("edit-goal-section").style.display = "none";
      document.getElementById("create-substep-section").style.display = "none";
      document.getElementById("links-blockers-section").style.display = "none";

      document.getElementById("edit-substep-id-input").value = substepData.id;
      document.getElementById("edit-substep-title-input").value = substepData.title;
      document.getElementById("edit-substep-desc-input").value = substepData.description || "";
      document.getElementById("edit-substep-gold-input").value = substepData.gold_reward;
      document.getElementById("edit-substep-order-input").value = substepData.execution_order || 1;
      document.getElementById("edit-substep-life-lore-input").checked = substepData.is_life_lore || false;
      document.getElementById("edit-substep-effort-type").value = substepData.effort_type || "";
      document.getElementById("edit-substep-effort-duration").value = substepData.effort_duration !== undefined && substepData.effort_duration !== null ? substepData.effort_duration : 1.0;
      document.getElementById("edit-substep-life-duration").value = substepData.life_duration_months ?? "";
      document.getElementById("edit-substep-life-earliest").value = substepData.life_earliest_month?.slice(0, 7) || "";
      document.getElementById("edit-substep-life-latest").value = substepData.life_latest_month?.slice(0, 7) || "";


      const linkedGoalsContainer = document.getElementById("edit-substep-linked-goals");
      if (linkedGoalsContainer) {
        linkedGoalsContainer.innerHTML = "";

        // Find active goal title from sidebar
        const activeGoalEl = document.querySelector(".goal-selector-item.active .goal-selector-title span");
        const activeGoalTitle = activeGoalEl ? activeGoalEl.textContent.trim().replace(/🎉/g, "").trim() : "Objectif actuel";

        // Active goal badge
        const activeBadge = document.createElement("span");
        activeBadge.className = "substep-tag";
        activeBadge.style.cssText = "background: rgba(34, 197, 94, 0.15); color: var(--accent-green); border: 1px solid rgba(34, 197, 94, 0.3); padding: 2px 6px; border-radius: 4px; font-size: 0.75rem;";
        activeBadge.textContent = activeGoalTitle;
        linkedGoalsContainer.appendChild(activeBadge);

        // Other linked goals badges
        if (substepData.linked_goals && substepData.linked_goals.length > 0) {
          substepData.linked_goals.forEach(g => {
            const badge = document.createElement("span");
            badge.className = "substep-tag";
            badge.style.cssText = "background: rgba(139, 92, 246, 0.15); color: var(--accent-purple); border: 1px solid rgba(139, 92, 246, 0.3); padding: 2px 6px; border-radius: 4px; font-size: 0.75rem;";
            badge.textContent = g.title;
            linkedGoalsContainer.appendChild(badge);
          });
        }
      }


    } else if (mode === "edit" && goalData) {
      drawerTitle.textContent = "✏️ Modifier l'Objectif";

      document.getElementById("edit-goal-section").style.display = "block";
      document.getElementById("edit-substep-section").style.display = "none";
      document.getElementById("create-substep-section").style.display = "none";
      document.getElementById("links-blockers-section").style.display = "none";

      goalSubmitBtn.textContent = "Enregistrer les modifications";
      editIdInput.value = goalData.id;
      titleInput.value = goalData.title;
      descInput.value = goalData.description || "";
      document.getElementById("goal-do-date-input").value = goalData.do_date || "";
      document.getElementById("goal-due-date-input").value = goalData.due_date || "";
    } else if (mode === "add-goal") {
      drawerTitle.textContent = "🏆 Nouvel Objectif";

      document.getElementById("edit-goal-section").style.display = "block";
      document.getElementById("edit-substep-section").style.display = "none";
      document.getElementById("create-substep-section").style.display = "none";
      document.getElementById("links-blockers-section").style.display = "none";

      goalSubmitBtn.textContent = "Forger l'Objectif";
      editIdInput.value = "";
      titleInput.value = "";
      descInput.value = "";
      document.getElementById("goal-do-date-input").value = "";
      document.getElementById("goal-due-date-input").value = "";
    } else if (mode === "add-substep") {
      drawerTitle.textContent = "⛓️ Nouvelle Sous-étape";

      document.getElementById("edit-goal-section").style.display = "none";
      document.getElementById("create-substep-section").style.display = "block";
      document.getElementById("links-blockers-section").style.display = "none";
      document.getElementById("edit-substep-section").style.display = "none";
    } else if (mode === "links") {
      drawerTitle.textContent = "🔗 Liaisons & Blocs Avancés";

      document.getElementById("edit-goal-section").style.display = "none";
      document.getElementById("create-substep-section").style.display = "none";
      document.getElementById("links-blockers-section").style.display = "block";
      document.getElementById("edit-substep-section").style.display = "none";
    } else {
      drawerTitle.textContent = "✨ Forge d'Objectif";

      document.getElementById("edit-goal-section").style.display = "block";
      document.getElementById("create-substep-section").style.display = "block";
      document.getElementById("links-blockers-section").style.display = "block";
      document.getElementById("edit-substep-section").style.display = "none";

      goalSubmitBtn.textContent = "Forger l'Objectif";
      editIdInput.value = "";
      titleInput.value = "";
      descInput.value = "";
    }
  }

  function closeDrawer() {
    const drawer = document.getElementById("creators-drawer");
    const overlay = document.getElementById("drawer-overlay");
    if (drawer) {
      drawer.classList.remove("open");
    }
    if (overlay) overlay.classList.remove("open");
  }

  // Bind Drawer Event Listeners
  document.getElementById("sidebar-add-goal-btn").addEventListener("click", () => openDrawer("add-goal"));
  document.getElementById("close-creators-drawer-btn").addEventListener("click", closeDrawer);
  document.getElementById("drawer-overlay").addEventListener("click", closeDrawer);



  // ==============================================
  // SCREEN 2: GOALS & SUBSTEPS DAG GRAPH           //
  // ==============================================
  function readLifeWindowFields(prefix) {
    const duration = document.getElementById(`${prefix}-life-duration`).value;
    const earliest = document.getElementById(`${prefix}-life-earliest`).value;
    const latest = document.getElementById(`${prefix}-life-latest`).value;
    if (!duration && !earliest && !latest) {
      return { life_duration_months: null, life_earliest_month: null, life_latest_month: null };
    }
    if (!duration || !earliest || !latest) {
      throw new Error("Renseigne la durée et les deux bornes de la fenêtre, ou laisse les trois vides.");
    }
    if (earliest > latest) {
      throw new Error("La fin possible doit suivre le début possible.");
    }
    return {
      life_duration_months: Number(duration),
      life_earliest_month: `${earliest}-01`,
      life_latest_month: `${latest}-01`
    };
  }

  async function fetchGoals() {
    try {
      await fetchProfile();
      const response = await fetch(`${API_BASE}/goals`);
      if (!response.ok) throw new Error("Erreur fetch goals");
      const goals = await response.json();

      // Check if goals count is 20 or more
      const addGoalBtn = document.getElementById("sidebar-add-goal-btn");
      if (addGoalBtn) {
        if (goals.length >= 20) {
          addGoalBtn.style.opacity = "0.3";
          addGoalBtn.style.pointerEvents = "none";
          addGoalBtn.setAttribute("title", "Limite de 20 objectifs atteinte.");
        } else {
          addGoalBtn.style.opacity = "";
          addGoalBtn.style.pointerEvents = "";
          addGoalBtn.removeAttribute("title");
        }
      }

      const selectorList = document.getElementById("goals-selector-list");
      if (!selectorList) return goals;

      selectorList.innerHTML = "";
      if (goals.length === 0) {
        selectorList.innerHTML = `<p style="color: var(--text-secondary); text-align: center; padding: 2rem 0; font-size: 0.85rem;">Aucun objectif principal. Créez-en un en cliquant sur + ! 🏆</p>`;
        renderGoalTree(null);
        return goals;
      }

      // Auto-select first goal if none or invalid activeGoalId
      const goalIds = goals.map(g => g.id);
      if (activeGoalId === null || !goalIds.includes(activeGoalId)) {
        activeGoalId = goals[0].id;
      }

      // Cache elements to update Goal/Substep creators dropdowns
      const substepGoalSelect = document.getElementById("substep-goal-select");

      // Dynamic Dropdowns Sync
      if (substepGoalSelect) substepGoalSelect.innerHTML = "";

      let activeGoal = null;

      goals.forEach(goal => {
        if (goal.id === activeGoalId) {
          activeGoal = goal;
        }

        // Dropdown additions
        if (substepGoalSelect) substepGoalSelect.innerHTML += `<option value="${goal.id}">${goal.title}</option>`;

        // Render sidebar goal item
        const item = document.createElement("div");
        item.className = `goal-selector-item ${goal.id === activeGoalId ? 'active' : ''}`;

        // Calculate progress percentage
        const totalSteps = goal.substeps.length;
        const completedSteps = goal.substeps.filter(s => s.completed).length;
        const percent = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;

        const isPinned = pinnedGoals.includes(goal.id);
        const locked = getTop3LockState();
        const starCursor = locked ? 'not-allowed' : 'pointer';
        const starTitle = locked
          ? 'Le Top 3 est verrouillé (Déverrouillez en bas de la page)'
          : (isPinned ? 'Retirer du Top 3' : 'Définir comme Top 3');
        const starHTML = `<span class="goal-pin-star ${isPinned ? 'pinned' : ''}" title="${starTitle}" style="cursor: ${starCursor}; margin-left: 0.5rem; font-size: 1.15rem; color: ${isPinned ? 'var(--accent-yellow, #ffb300)' : 'var(--text-muted, #8e9297)'}; transition: color 0.2s;">${isPinned ? '★' : '☆'}</span>`;

        let dateInfoList = [];
        if (goal.do_date) {
          const parts = goal.do_date.split("-");
          dateInfoList.push(`📅 ${parts.length === 3 ? `${parts[2]}/${parts[1]}` : goal.do_date}`);
        }
        if (goal.due_date) {
          const parts = goal.due_date.split("-");
          dateInfoList.push(`🚨 ${parts.length === 3 ? `${parts[2]}/${parts[1]}` : goal.due_date}`);
        }
        const sidebarDateInfo = dateInfoList.length > 0 ? ` • ${dateInfoList.join(" ")}` : "";

        item.innerHTML = `
          <div class="goal-selector-title" style="display: flex; align-items: center; justify-content: space-between; width: 100%;">
            <span style="display: flex; align-items: center; gap: 0.3rem;">
              <span>${goal.title} ${goal.completed ? "🎉" : ""}</span>
              ${starHTML}
            </span>
            <span style="font-size: 0.75rem; color: var(--accent-cyan); font-weight: 700;">${goal.source_todo_id ? "To-do lié" : `${percent}%`}</span>
          </div>
          <span class="goal-selector-meta">${goal.source_todo_id ? "Validation depuis To-do" : `${totalSteps} sous-étape${totalSteps > 1 ? 's' : ''}`}${sidebarDateInfo}</span>
          <div class="goal-selector-progress-track">
            <div class="goal-selector-progress-fill" style="width: ${percent}%;"></div>
          </div>
        `;

        const starBtn = item.querySelector(".goal-pin-star");
        if (starBtn) {
          starBtn.addEventListener("click", async (e) => {
            e.stopPropagation();

            const isCurrentLocked = getTop3LockState();
            if (isCurrentLocked) {
              showToast("Le Top 3 est verrouillé. Cliquez sur 'Déverrouiller le Top 3' en bas de la page pour le modifier.", true);
              return;
            }

            let newPinnedGoals = [...pinnedGoals];
            if (newPinnedGoals.includes(goal.id)) {
              newPinnedGoals = newPinnedGoals.filter(id => id !== goal.id);
              isUnlockClicked = false;
            } else {
              if (newPinnedGoals.length >= 3) {
                showToast("Vous pouvez sélectionner au maximum 3 objectifs prioritaires (Top 3) !", true);
                return;
              }
              newPinnedGoals.push(goal.id);
            }

            try {
              const resp = await fetch(`${API_BASE}/profile/pins`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  pinned_goals: newPinnedGoals,
                  pinned_substeps: pinnedSubsteps,
                  pinned_softskills: pinnedSoftskills
                })
              });

              if (!resp.ok) {
                const errData = await resp.json();
                throw new Error(errData.detail || "Erreur de sauvegarde");
              }

              showToast(isPinned ? "Objectif retiré du Top 3 🎯" : "Objectif ajouté au Top 3 ! ⭐");

              await fetchProfile();
              await fetchGoals();
            } catch (err) {
              showToast(err.message, true);
            }
          });
        }

        item.addEventListener("click", () => {
          activeGoalId = goal.id;
          document.querySelectorAll(".goal-selector-item").forEach(el => el.classList.remove("active"));
          item.classList.add("active");
          renderGoalLinkControls(goals, goal);
          renderGoalTree(buildGoalTreeViewGoal(goal, goals));
        });

        selectorList.appendChild(item);
      });
      if (substepGoalSelect && activeGoalId) {
        substepGoalSelect.value = activeGoalId;
      }
      renderGoalLinkControls(goals, activeGoal);

      // Render Active Tree
      renderGoalTree(buildGoalTreeViewGoal(activeGoal, goals));
      renderTop3LockButton();
      return goals;

    } catch (e) {
      console.error(e);
      return [];
    }
  }

  function renderGoalTree(goal) {
    const viewer = document.getElementById("skill-tree-viewer");
    if (!viewer) return;

    if (!goal) {
      viewer.innerHTML = `<p style="color: var(--text-muted); text-align: center; margin: auto;">Sélectionnez un objectif à gauche pour visualiser son arbre.</p>`;
      return;
    }

    const totalSteps = goal.substeps.length;
    const completedSteps = goal.substeps.filter(s => s.completed).length;
    const percent = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;

    let dateInfoList = [];
    if (goal.do_date) {
      const parts = goal.do_date.split("-");
      dateInfoList.push(`📅 ${parts.length === 3 ? `${parts[2]}/${parts[1]}` : goal.do_date}`);
    }
    if (goal.due_date) {
      const parts = goal.due_date.split("-");
      dateInfoList.push(`🚨 ${parts.length === 3 ? `${parts[2]}/${parts[1]}` : goal.due_date}`);
    }
    const dateText = dateInfoList.length > 0 ? ` • ${dateInfoList.join(" ")}` : "";

    // Header with actions
    let headerHTML = `
      <div class="skill-tree-header">
        <div>
          <span class="skill-tree-title">${goal.title} ${goal.completed ? "🎉" : ""}</span>
          <p style="font-size: 0.82rem; color: var(--text-muted); margin-top: 0.2rem;">${goal.source_todo_id ? "Objectif lié à un to-do : validation et titre gérés depuis To-do." : `${goal.description || 'Arbre de quêtes long terme.'} • ${percent}% complété`}${dateText}</p>
        </div>
        <div class="skill-tree-actions">
          <button class="tree-icon-btn add-step" id="btn-add-substep" title="Nouvelle Sous-étape" style="font-size: 1.1rem; color: var(--accent-cyan);">➕</button>
          <button class="tree-icon-btn link" id="btn-link-substep" title="Liaisons & Verrous avancés" style="font-size: 1.1rem; color: var(--accent-purple);">🔗</button>
          ${goal.source_todo_id ? "" : `<button class="tree-icon-btn edit" id="btn-edit-active-goal" title="Modifier l'objectif">✏️</button><button class="tree-icon-btn delete" id="btn-delete-active-goal" title="Supprimer l'objectif">🗑️</button>`}
        </div>
      </div>
    `;

    // Organize substeps by columns based strictly on execution_order
    const columnsMap = new Map();
    goal.substeps.forEach(s => {
      const order = s.execution_order || 1;
      if (!columnsMap.has(order)) {
        columnsMap.set(order, []);
      }
      columnsMap.get(order).push(s);
    });

    // Sort the execution orders ascending to create left-to-right visual progression
    const sortedOrders = Array.from(columnsMap.keys()).sort((a, b) => a - b);

    // Render tree scroll container
    let columnsHTML = "";

    // 1. Substep columns (ordered by execution_order)
    sortedOrders.forEach(order => {
      const colSubsteps = columnsMap.get(order);
      let nodesHTML = "";
      colSubsteps.forEach(s => {
        const isCompleted = s.completed;

        let stateClass = "unlocked-node";
        if (isCompleted) stateClass = "completed-node";

        const isGoalPinned = pinnedGoals.includes(goal.id) || (s.linked_goals && s.linked_goals.some(g => pinnedGoals.includes(g.id)));
        let btnHTML = "";
        if (isCompleted) {
          btnHTML = `<span style="color: var(--accent-green); font-size: 0.75rem; font-weight: 700; margin-top: 0.4rem; display: flex; align-items: center; gap: 0.2rem;">✓ Complétée</span>`;
        } else {
          if (isGoalPinned) {
            btnHTML = `<button class="tree-node-btn action-complete-substep" data-id="${s.id}">Valider</button>`;
          } else {
            btnHTML = `<button class="tree-node-btn action-complete-substep" data-id="${s.id}" disabled title="Ce sous-objectif doit appartenir à l'un de vos 3 objectifs prioritaires (Top 3) pour être validé." style="opacity: 0.45; cursor: not-allowed;">Valider (Focus requis)</button>`;
          }
        }

        const effortLabels = {
          musculaire: "Musculaire 💪",
          cerveau: "Cerveau 🧠",
          emotionnel_social: "Social 🤝",
          creatif_divergent: "Créatif 🎨"
        };
        const effortBadge = s.effort_type ? `<span class="effort-badge effort-${s.effort_type}">${effortLabels[s.effort_type]} (${s.effort_duration}h)</span>` : "";

        let linkedGoalsHTML = "";
        if (s.linked_goals && s.linked_goals.length > 0) {
          linkedGoalsHTML = `
            <div class="tree-node-links" style="font-size: 0.7rem; color: var(--accent-purple); margin-top: 0.3rem; display: flex; align-items: center; gap: 0.2rem; flex-wrap: wrap; justify-content: center; width: 100%;">
              <span style="opacity: 0.7;">🔗 Lié à :</span>
              ${s.linked_goals.map(g => `<span class="substep-tag" style="background: rgba(139, 92, 246, 0.15); color: var(--accent-purple); font-size: 0.65rem; border: 1px solid rgba(139, 92, 246, 0.3); padding: 1px 4px; border-radius: 4px; cursor: pointer; transition: all 0.2s;" onclick="window.selectGoalById(${g.id})" title="Aller à l'objectif : ${g.title.replace(/"/g, '&quot;')}">${g.title}</span>`).join(" ")}
            </div>
          `;
        }

        nodesHTML += `
          <div class="tree-node ${stateClass}" data-substep-id="${s.id}" style="position: relative; padding-top: 1.6rem;">
            <div class="tree-node-actions" style="position: absolute; top: 8px; right: 8px; display: flex; gap: 0.4rem;">
              <span class="action-edit-substep-icon" data-id="${s.id}" style="cursor: pointer; font-size: 0.75rem; opacity: 0.6; hover: opacity: 1; transition: opacity 0.2s;" title="Modifier la sous-étape">✏️</span>
            </div>
            <span class="tree-node-title" style="margin-top: 0.2rem;"><span style="color: var(--text-muted); font-size: 0.75em; margin-right: 0.2em;">[Étape ${s.execution_order || 1}]</span> ${s.title}</span>
            ${s.description ? `<span class="tree-node-desc" style="font-size: 0.72rem; color: var(--text-muted); display: block; margin-top: 0.2rem; line-height: 1.2;">${s.description}</span>` : ""}
            <span class="tree-node-gold" style="margin-top: 0.3rem; display: block;">💰 +${s.gold_reward}g</span>
            ${effortBadge ? `<div class="tree-node-stats">${effortBadge}</div>` : ""}
            ${linkedGoalsHTML}
            ${btnHTML}
          </div>
        `;
      });

      columnsHTML += `
        <div class="tree-column">
          ${nodesHTML}
        </div>
      `;
    });

    // 2. Column Last: Root Goal itself!
    const goalIsCompleted = goal.completed;
    let nodeDatesHtml = "";
    let nodeDatesList = [];
    if (goal.do_date) {
      const parts = goal.do_date.split("-");
      nodeDatesList.push(`📅 ${parts.length === 3 ? `${parts[2]}/${parts[1]}` : goal.do_date}`);
    }
    if (goal.due_date) {
      const parts = goal.due_date.split("-");
      nodeDatesList.push(`🚨 ${parts.length === 3 ? `${parts[2]}/${parts[1]}` : goal.due_date}`);
    }
    if (nodeDatesList.length > 0) {
      nodeDatesHtml = `<span class="tree-node-desc" style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.15rem; display: block;">${nodeDatesList.join(" ")}</span>`;
    }

    columnsHTML += `
      <div class="tree-column">
        <div class="tree-node ${goalIsCompleted ? 'completed-node' : 'unlocked-node'}" style="min-height: 120px;">
          <span class="substep-tag" style="background: rgba(234, 179, 8, 0.15); color: var(--accent-gold); font-size: 0.65rem;">OBJECTIF CENTRAL</span>
          <span class="tree-node-title" style="font-size: 1.1rem; color: var(--accent-green); margin-top: 0.3rem;">${goal.title}</span>
          ${nodeDatesHtml}
          <span class="tree-node-desc" style="font-size: 0.78rem; margin-top: 0.2rem;">${percent}% complété</span>
        </div>
      </div>
    `;

    viewer.innerHTML = `
      ${headerHTML}
      <div class="skill-tree-scroll-container">
        ${columnsHTML}
      </div>
    `;

    // Bind edit/delete/add handlers
    document.getElementById("btn-add-substep").addEventListener("click", () => openDrawer("add-substep"));
    document.getElementById("btn-link-substep").addEventListener("click", () => openDrawer("links"));
    document.getElementById("btn-edit-active-goal")?.addEventListener("click", () => openDrawer("edit", goal));
    document.getElementById("btn-delete-active-goal")?.addEventListener("click", () => deleteGoal(goal.id));

    // Bind edit substep handlers inside the tree
    viewer.querySelectorAll(".action-edit-substep-icon").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const subId = parseInt(btn.getAttribute("data-id"));
        const substepData = goal.substeps.find(sub => sub.id === subId);
        if (substepData) {
          openDrawer("edit-substep", null, substepData, goal.substeps);
        }
      });
    });

    // Bind Complete button handlers inside the tree
    viewer.querySelectorAll(".action-complete-substep").forEach(btn => {
      btn.addEventListener("click", async () => {
        const subId = btn.getAttribute("data-id");
        try {
          const resp = await fetch(`${API_BASE}/substeps/${subId}/complete`, { method: "POST" });
          if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || "Validation bloquée");
          }
          const data = await resp.json();
          showToast(`Félicitations ! Étape complétée : +${data.gold_awarded} Gold reçus ! 💰`);
          if (data.completed_goals.length > 0) {
            showToast(`OBJECTIF ACCOMPLI ! Arbre entièrement validé : ${data.completed_goals.join(", ")} ! 🏆`);
          }
          refreshAll();
          fetchGoals();
        } catch (e) {
          console.error(e);
          showToast(e.message || "Erreur de validation", true);
        }
      });
    });
  }

  async function deleteGoal(goalId) {
    if (!confirm("Voulez-vous vraiment détruire cet arbre d'objectifs et toutes ses liaisons ?")) return;
    try {
      const resp = await fetch(`${API_BASE}/goals/${goalId}`, { method: "DELETE" });
      if (!resp.ok) throw new Error();
      showToast("Arbre d'objectifs détruit avec succès ! 🗑️");
      activeGoalId = null;
      fetchGoals();
    } catch {
      showToast("Erreur lors de la suppression de l'objectif", true);
    }
  }

  // Bind Screen 2 Form Submissions
  document.getElementById("create-goal-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const editId = document.getElementById("edit-goal-id-input").value;
    const title = document.getElementById("goal-title-input").value.trim();
    const desc = document.getElementById("goal-desc-input").value.trim();
    const doDate = document.getElementById("goal-do-date-input").value || null;
    const dueDate = document.getElementById("goal-due-date-input").value || null;

    try {
      let resp;
      if (editId) {
        resp = await fetch(`${API_BASE}/goals/${editId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title, description: desc, do_date: doDate, due_date: dueDate })
        });
      } else {
        resp = await fetch(`${API_BASE}/goals`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title, description: desc, do_date: doDate, due_date: dueDate })
        });
      }

      if (!resp.ok) throw new Error();
      showToast(editId ? "Objectif modifié avec succès ! ✏️" : "Arbre d'Objectif principal forgé avec succès ! 🏆");
      document.getElementById("create-goal-form").reset();
      closeDrawer();
      fetchGoals();
    } catch {
      showToast(editId ? "Erreur lors de la modification de l'objectif" : "Erreur lors de la création de l'objectif", true);
    }
  });

  document.getElementById("create-substep-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const goalId = document.getElementById("substep-goal-select").value;
    const title = document.getElementById("substep-title-input").value.trim();
    const desc = document.getElementById("substep-desc-input").value.trim();
    const gold = parseInt(document.getElementById("substep-gold-input").value) || 0;
    const order = parseInt(document.getElementById("substep-order-input").value) || 1;
    const isLifeLore = document.getElementById("substep-life-lore-input").checked;

    const effortType = document.getElementById("substep-effort-type").value || null;
    const effortDuration = parseFloat(document.getElementById("substep-effort-duration").value) || 1.0;

    try {
      const lifeWindow = readLifeWindowFields("substep");
      const resp = await fetch(`${API_BASE}/goals/${goalId}/substeps`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: title,
          description: desc,
          gold_reward: gold,
          execution_order: order,
          is_life_lore: isLifeLore,
          effort_type: effortType,
          effort_duration: effortDuration,
          ...lifeWindow
        })
      });
      if (!resp.ok) throw new Error();
      showToast("Sous-étape ajoutée et verrous forgés ! ⛓️");
      document.getElementById("create-substep-form").reset();
      document.getElementById("substep-effort-duration").value = "1.0";
      closeDrawer();
      fetchGoals();
    } catch (error) {
      showToast(error.message || "Erreur lors de la création de la sous-étape", true);
    }
  });

  document.getElementById("edit-substep-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const subId = document.getElementById("edit-substep-id-input").value;
    const title = document.getElementById("edit-substep-title-input").value.trim();
    const desc = document.getElementById("edit-substep-desc-input").value.trim();
    const gold = parseInt(document.getElementById("edit-substep-gold-input").value) || 0;
    const order = parseInt(document.getElementById("edit-substep-order-input").value) || 1;
    const isLifeLore = document.getElementById("edit-substep-life-lore-input").checked;

    const effortType = document.getElementById("edit-substep-effort-type").value || null;
    const effortDuration = parseFloat(document.getElementById("edit-substep-effort-duration").value) || 1.0;

    try {
      const lifeWindow = readLifeWindowFields("edit-substep");
      const resp = await fetch(`${API_BASE}/substeps/${subId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: title,
          description: desc,
          gold_reward: gold,
          execution_order: order,
          is_life_lore: isLifeLore,
          effort_type: effortType,
          effort_duration: effortDuration,
          ...lifeWindow
        })
      });
      if (!resp.ok) throw new Error();

      // Update execution_order specifically for the active goal link
      if (activeGoalId) {
        const reorderResp = await fetch(`${API_BASE}/goals/${activeGoalId}/substeps/${subId}/reorder`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ execution_order: order })
        });
        if (!reorderResp.ok) throw new Error();
      }

      showToast("Sous-étape modifiée avec succès ! ✏️");
      closeDrawer();
      fetchGoals();
    } catch (error) {
      showToast(error.message || "Erreur lors de la modification de la sous-étape", true);
    }
  });

  document.getElementById("delete-substep-btn").addEventListener("click", async () => {
    const subId = document.getElementById("edit-substep-id-input").value;
    if (!subId) return;

    if (!confirm("Voulez-vous vraiment supprimer cette sous-étape définitivement ?")) {
      return;
    }

    try {
      const resp = await fetch(`${API_BASE}/substeps/${subId}`, {
        method: "DELETE"
      });
      if (!resp.ok) throw new Error();
      showToast("Sous-étape supprimée de l'aventure ! 🗑️");
      closeDrawer();
      fetchGoals();
    } catch {
      showToast("Erreur lors de la suppression de la sous-étape", true);
    }
  });

  document.getElementById("link-substep-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const subId = parseInt(document.getElementById("link-substep-select").value);
    const goalId = activeGoalId;
    const order = parseInt(document.getElementById("link-order-input").value) || 1;

    try {
      if (!goalId) {
        throw new Error("Sélectionnez d'abord l'objectif qui doit recevoir la sous-étape.");
      }
      if (!subId) {
        throw new Error("Sélectionnez une sous-étape à lier.");
      }

      const resp = await fetch(`${API_BASE}/substeps/link`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal_id: goalId, substep_id: subId, execution_order: order })
      });
      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.detail || "Erreur lors du partage de la sous-étape");
      }
      const data = await resp.json();
      activeGoalId = goalId;
      const goals = await fetchGoals();
      const targetGoal = getGoalById(goals, goalId);
      const linkedSubstep = getSubstepInGoal(targetGoal, subId);

      if (!targetGoal || !linkedSubstep) {
        throw new Error("Liaison enregistrée, mais /goals ne renvoie pas encore la sous-étape dans l'objectif cible.");
      }

      closeDrawer();
      if (data.status === "updated") {
        showToast(`Sous-étape déjà liée à ${targetGoal.title}; ordre mis à jour. 🔗`);
      } else {
        showToast(`Sous-étape liée à ${targetGoal.title} avec succès ! 🔗`);
      }
      highlightGoalSubstepAfterRender(subId);
    } catch (err) {
      console.error(err);
      showToast(err.message || "Erreur lors du partage de la sous-étape", true);
    }
  });


  // ==============================================
  // SCREEN 3: SETTINGS & POTENTIALS               //
  // ==============================================
  const templateEditSelect = document.getElementById("template-edit-select");
  const editThresholdsForm = document.getElementById("edit-thresholds-form");

  templateEditSelect.addEventListener("change", loadSettingsThresholds);

  function showBioZoneError(message, suggestion = null, suggestionMessage = "") {
    const errorBox = document.getElementById("bio-zone-error");
    if (!errorBox) return;
    errorBox.innerHTML = "";
    const messageEl = document.createElement("div");
    messageEl.textContent = suggestionMessage ? `${message} ${suggestionMessage}` : message;
    errorBox.appendChild(messageEl);
    if (suggestion) {
      const suggestionBtn = document.createElement("button");
      suggestionBtn.type = "button";
      suggestionBtn.className = "floating-add-btn bio-zone-suggestion-btn";
      suggestionBtn.textContent = `Utiliser ${suggestion.start_time} - ${suggestion.end_time}`;
      suggestionBtn.addEventListener("click", () => {
        document.getElementById("bio-zone-start").value = suggestion.start_time;
        document.getElementById("bio-zone-end").value = suggestion.end_time;
        clearBioZoneError();
      });
      errorBox.appendChild(suggestionBtn);
    }
    errorBox.style.display = "block";
  }

  function clearBioZoneError() {
    const errorBox = document.getElementById("bio-zone-error");
    if (!errorBox) return;
    errorBox.textContent = "";
    errorBox.style.display = "none";
  }

  async function readApiError(response) {
    try {
      const data = await response.json();
      if (Array.isArray(data.detail)) {
        return data.detail.map(item => item.msg || String(item)).join(" ");
      }
      return data.detail || "Erreur API";
    } catch {
      return "Erreur API";
    }
  }

  function clearBioZoneForm() {
    const form = document.getElementById("bio-zone-form");
    const idInput = document.getElementById("bio-zone-id");
    const submitBtn = document.getElementById("bio-zone-submit-btn");
    const cancelBtn = document.getElementById("bio-zone-cancel-btn");
    if (form) form.reset();
    if (idInput) idInput.value = "";
    const typeInput = document.getElementById("bio-zone-type");
    const colorInput = document.getElementById("bio-zone-color");
    if (typeInput) typeInput.value = "deep_focus";
    if (colorInput) colorInput.value = bioZoneMeta.deep_focus.color;
    if (submitBtn) submitBtn.textContent = "Ajouter la zone";
    if (cancelBtn) cancelBtn.style.display = "none";
    clearBioZoneError();
  }

  function populateBioZoneForm(zone) {
    document.getElementById("bio-zone-id").value = zone.id;
    document.getElementById("bio-zone-name").value = zone.zone_name;
    document.getElementById("bio-zone-type").value = zone.zone_type;
    document.getElementById("bio-zone-start").value = zone.start_time;
    document.getElementById("bio-zone-end").value = zone.end_time;
    document.getElementById("bio-zone-color").value = zone.color || getBioZoneMeta(zone.zone_type).color;
    document.getElementById("bio-zone-submit-btn").textContent = "Mettre à jour";
    document.getElementById("bio-zone-cancel-btn").style.display = "inline-flex";
    clearBioZoneError();
  }

  function getBioZonePayload() {
    const type = document.getElementById("bio-zone-type").value;
    const color = document.getElementById("bio-zone-color").value;
    return {
      zone_name: document.getElementById("bio-zone-name").value.trim(),
      zone_type: type,
      start_time: document.getElementById("bio-zone-start").value,
      end_time: document.getElementById("bio-zone-end").value,
      color: color || getBioZoneMeta(type).color
    };
  }

  async function refreshBioZonesAfterMutation(successMessage) {
    const zones = await fetchBiologicalZones(true);
    renderBioTimeline(zones);
    renderBioZoneSettings(zones);
    clearBioZoneForm();
    if (successMessage) showToast(successMessage);
  }

  function renderBioZoneSettings(zones) {
    const list = document.getElementById("bio-zone-list");
    if (!list) return;
    list.innerHTML = "";

    if (!zones || zones.length === 0) {
      list.innerHTML = `<p class="bio-zone-empty">Aucune zone biologique configurée.</p>`;
      return;
    }

    const sorted = [...zones].sort(
      (a, b) => timeToMinutes(a.start_time) - timeToMinutes(b.start_time)
    );

    sorted.forEach(zone => {
      const meta = getBioZoneMeta(zone.zone_type);
      const row = document.createElement("div");
      row.className = "bio-zone-row";

      const swatch = document.createElement("div");
      swatch.className = "bio-zone-swatch";
      swatch.style.background = zone.color || meta.color;

      const details = document.createElement("div");
      const title = document.createElement("div");
      title.className = "bio-zone-title";
      title.textContent = `${meta.emoji} ${zone.zone_name}`;
      const metaText = document.createElement("div");
      metaText.className = "bio-zone-meta";
      metaText.textContent = `${meta.label} · ${zone.start_time} - ${zone.end_time}`;
      details.appendChild(title);
      details.appendChild(metaText);

      const actions = document.createElement("div");
      actions.className = "bio-zone-actions";

      const editBtn = document.createElement("button");
      editBtn.type = "button";
      editBtn.className = "bio-zone-action-btn";
      editBtn.title = "Modifier";
      editBtn.textContent = "✏️";
      editBtn.addEventListener("click", () => populateBioZoneForm(zone));

      const deleteBtn = document.createElement("button");
      deleteBtn.type = "button";
      deleteBtn.className = "bio-zone-action-btn danger";
      deleteBtn.title = "Supprimer";
      deleteBtn.textContent = "🗑️";
      deleteBtn.addEventListener("click", () => deleteBioZone(zone.id));

      actions.appendChild(editBtn);
      actions.appendChild(deleteBtn);
      row.appendChild(swatch);
      row.appendChild(details);
      row.appendChild(actions);
      list.appendChild(row);
    });
  }

  async function loadBioZoneSettings() {
    try {
      const zones = await fetchBiologicalZones(true);
      renderBioZoneSettings(zones);
    } catch (error) {
      console.error(error);
      showBioZoneError("Impossible de charger les zones biologiques.");
    }
  }

  async function saveBioZone(event) {
    event.preventDefault();
    clearBioZoneError();
    const id = document.getElementById("bio-zone-id").value;
    const payload = getBioZonePayload();
    const url = id ? `${API_BASE}/biological-zones/${id}` : `${API_BASE}/biological-zones`;
    const method = id ? "PUT" : "POST";

    try {
      const response = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        if (errorData.code === "biological_zone_overlap") {
          showBioZoneError(
            errorData.detail || "Ce créneau chevauche une zone existante.",
            errorData.suggestion,
            errorData.suggestion_message || ""
          );
          return;
        }
        throw new Error(
          Array.isArray(errorData.detail)
            ? errorData.detail.map(item => item.msg || String(item)).join(" ")
            : errorData.detail || "Erreur API"
        );
      }
      await refreshBioZonesAfterMutation(id ? "Zone biologique mise à jour." : "Zone biologique ajoutée.");
    } catch (error) {
      console.error(error);
      showBioZoneError(error.message);
    }
  }

  async function deleteBioZone(zoneId) {
    if (!confirm("Supprimer cette zone biologique ?")) return;

    try {
      const response = await fetch(`${API_BASE}/biological-zones/${zoneId}`, {
        method: "DELETE"
      });
      if (!response.ok) {
        throw new Error(await readApiError(response));
      }
      await refreshBioZonesAfterMutation("Zone biologique supprimée.");
    } catch (error) {
      console.error(error);
      showBioZoneError(error.message);
    }
  }

  const bioZoneForm = document.getElementById("bio-zone-form");
  if (bioZoneForm) {
    bioZoneForm.addEventListener("submit", saveBioZone);
  }

  const bioZoneCancelBtn = document.getElementById("bio-zone-cancel-btn");
  if (bioZoneCancelBtn) {
    bioZoneCancelBtn.addEventListener("click", clearBioZoneForm);
  }

  const bioZoneTypeInput = document.getElementById("bio-zone-type");
  if (bioZoneTypeInput) {
    bioZoneTypeInput.addEventListener("change", () => {
      const colorInput = document.getElementById("bio-zone-color");
      if (colorInput) colorInput.value = getBioZoneMeta(bioZoneTypeInput.value).color;
    });
  }

  function formatCycleType(policy) {
    const rec = policy?.cycle_recommendation || {};
    const label = rec.label || (policy?.cycle_week_type === "chill" ? "Semaine moins intense" : "Semaine normale");
    const hustle = rec.hustle ?? rec.hustle_max ?? "-";
    const rest = rec.rest ?? rec.rest_max ?? "-";
    return `${label} · 🔥 ${hustle} · 💤 ${rest}`;
  }

  const cycleWeekdays = [
    ["monday", "Lun"],
    ["tuesday", "Mar"],
    ["wednesday", "Mer"],
    ["thursday", "Jeu"],
    ["friday", "Ven"],
    ["saturday", "Sam"],
    ["sunday", "Dim"]
  ];

  function renderCycleWeek(containerId, prefix, pattern) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = cycleWeekdays.map(([key, label]) => `
      <label class="cycle-day-field">
        <span>${label}</span>
        <select id="${prefix}-${key}" class="template-dropdown">
          <option value="rest">Repos</option>
          <option value="regular">Normal</option>
          <option value="hustle">Hustle</option>
        </select>
      </label>
    `).join("");
    cycleWeekdays.forEach(([key]) => {
      const input = document.getElementById(`${prefix}-${key}`);
      if (input) input.value = pattern?.[key] || "regular";
    });
  }

  function collectCycleWeek(prefix) {
    return Object.fromEntries(cycleWeekdays.map(([key]) => [
      key,
      document.getElementById(`${prefix}-${key}`)?.value || "regular"
    ]));
  }

  function setCycleMessage(message, isError = false) {
    const box = document.getElementById("cycle-save-message");
    if (!box) return;
    box.textContent = message || "";
    box.style.display = message ? "block" : "none";
    box.style.color = isError ? "var(--accent-red)" : "var(--accent-cyan)";
  }

  async function loadCycleSettings() {
    const anchorEl = document.getElementById("cycle-current-anchor");
    const effectiveEl = document.getElementById("cycle-current-effective");
    const typeEl = document.getElementById("cycle-current-type");
    const anchorInput = document.getElementById("cycle-anchor-input");
    const effectiveInput = document.getElementById("cycle-effective-input");
    const pendingNote = document.getElementById("cycle-pending-note");
    if (!anchorEl || !effectiveEl || !typeEl || !anchorInput || !effectiveInput) return;

    try {
      const response = await fetch(`${API_BASE}/profile/cycle`);
      if (!response.ok) throw new Error(await readApiError(response));
      const policy = await response.json();
      const editablePolicy = policy.pending_policy || policy;
      anchorEl.textContent = policy.anchor_date;
      effectiveEl.textContent = policy.effective_from;
      typeEl.textContent = formatCycleType(policy);
      anchorInput.value = editablePolicy.anchor_date;
      effectiveInput.min = todayDateString();
      effectiveInput.value = policy.pending_policy?.effective_from || todayDateString();
      renderCycleWeek("normal-week-grid", "normal-week", editablePolicy.normal_week);
      renderCycleWeek("chill-week-grid", "chill-week", editablePolicy.chill_week);
      if (pendingNote) {
        pendingNote.textContent = policy.pending_policy
          ? `Programmation à venir le ${policy.pending_policy.effective_from}. Une nouvelle sauvegarde la remplacera.`
          : "La date d'effet peut être aujourd'hui ou une date future.";
      }
      setCycleMessage("");
    } catch (error) {
      console.error(error);
      setCycleMessage(error.message || "Impossible de charger le cycle.", true);
    }
  }

  async function saveCycleSettings(event) {
    event.preventDefault();
    const anchorInput = document.getElementById("cycle-anchor-input");
    const effectiveInput = document.getElementById("cycle-effective-input");
    if (!anchorInput?.value || !effectiveInput?.value) return;

    try {
      const response = await fetch(`${API_BASE}/profile/cycle`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          anchor_date: anchorInput.value,
          effective_from: effectiveInput.value,
          normal_week: collectCycleWeek("normal-week"),
          chill_week: collectCycleWeek("chill-week")
        })
      });
      if (!response.ok) throw new Error(await readApiError(response));
      await loadCycleSettings();
      await fetchHistory();
      setCycleMessage(`Changement programmé à partir du ${effectiveInput.value}.`);
      showToast("Cycle des journées mis à jour.");
    } catch (error) {
      console.error(error);
      setCycleMessage(error.message || "Erreur lors de l'enregistrement.", true);
      showToast("Erreur lors de l'enregistrement du cycle", true);
    }
  }

  const dayCycleForm = document.getElementById("day-cycle-form");
  if (dayCycleForm) {
    dayCycleForm.addEventListener("submit", saveCycleSettings);
  }

  function updateBudgetCalculationsAndValidation() {
    const muscular = parseFloat(document.getElementById("ceiling-musculaire").value) || 0;
    const cerveau = parseFloat(document.getElementById("ceiling-cerveau").value) || 0;
    const emotionnel = parseFloat(document.getElementById("ceiling-emotionnel").value) || 0;
    const creatif = parseFloat(document.getElementById("ceiling-creatif").value) || 0;

    const total = muscular + cerveau + emotionnel + creatif;
    document.getElementById("ceiling-total").value = total;

    const focusHours = parseFloat(document.getElementById("template-focus-hours").value) || 0;
    const errorMsg = document.getElementById("budget-error-msg");
    const saveBtn = editThresholdsForm.querySelector("button[type='submit']");

    if (total > focusHours) {
      errorMsg.textContent = `⚠️ Le total des plafonds d'effort (${total}h) ne peut pas dépasser l'objectif focus (${focusHours}h).`;
      errorMsg.style.display = "block";
      if (saveBtn) saveBtn.disabled = true;
    } else {
      errorMsg.style.display = "none";
      if (saveBtn) saveBtn.disabled = false;
    }
  }

  document.getElementById("ceiling-musculaire").addEventListener("input", updateBudgetCalculationsAndValidation);
  document.getElementById("ceiling-cerveau").addEventListener("input", updateBudgetCalculationsAndValidation);
  document.getElementById("ceiling-emotionnel").addEventListener("input", updateBudgetCalculationsAndValidation);
  document.getElementById("ceiling-creatif").addEventListener("input", updateBudgetCalculationsAndValidation);
  document.getElementById("template-focus-hours").addEventListener("input", updateBudgetCalculationsAndValidation);
  document.getElementById("template-min-rest-hours").addEventListener("input", updateBudgetCalculationsAndValidation);

  async function loadSettingsThresholds() {
    try {
      const response = await fetch(`${API_BASE}/templates`);
      if (!response.ok) throw new Error();
      const templates = await response.json();

      const activeTemplate = templateEditSelect.value;
      const config = templates[activeTemplate] || {};

      document.getElementById("template-focus-hours").value = config.focus_hours !== undefined ? config.focus_hours : 6.0;
      document.getElementById("template-min-rest-hours").value = config.min_rest_hours !== undefined ? config.min_rest_hours : 8.0;

      const ceilings = config.ceilings || {};
      document.getElementById("ceiling-musculaire").value = ceilings.musculaire !== undefined ? ceilings.musculaire : 2.0;
      document.getElementById("ceiling-cerveau").value = ceilings.cerveau !== undefined ? ceilings.cerveau : 2.0;
      document.getElementById("ceiling-emotionnel").value = ceilings.emotionnel_social !== undefined ? ceilings.emotionnel_social : 2.0;
      document.getElementById("ceiling-creatif").value = ceilings.creatif_divergent !== undefined ? ceilings.creatif_divergent : 2.0;

      updateBudgetCalculationsAndValidation();
    } catch (e) {
      console.error(e);
      showToast("Erreur de récupération des templates", true);
    }
  }

  editThresholdsForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const activeTemplate = templateEditSelect.value;

    const focus_hours = parseFloat(document.getElementById("template-focus-hours").value) || 0;
    const min_rest_hours = parseFloat(document.getElementById("template-min-rest-hours").value) || 0;
    const ceilings = {
      musculaire: parseFloat(document.getElementById("ceiling-musculaire").value) || 0,
      cerveau: parseFloat(document.getElementById("ceiling-cerveau").value) || 0,
      emotionnel_social: parseFloat(document.getElementById("ceiling-emotionnel").value) || 0,
      creatif_divergent: parseFloat(document.getElementById("ceiling-creatif").value) || 0,
      total: parseFloat(document.getElementById("ceiling-total").value) || 0
    };

    if (ceilings.total > focus_hours) {
      showToast("Le total des plafonds dépasse l'objectif focus.", true);
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/templates`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          template_name: activeTemplate,
          focus_hours: focus_hours,
          min_rest_hours: min_rest_hours,
          ceilings: ceilings
        })
      });
      if (!response.ok) throw new Error();
      showToast("Budgets de Perfect Day mis à jour ! ⚙️");
      refreshAll();
    } catch (e) {
      console.error(e);
      showToast("Erreur lors de l'enregistrement", true);
    }
  });


  // ==============================================
  // EDIT / DELETE QUEST MODAL
  // ==============================================
  const editQuestOverlay = document.getElementById("edit-quest-overlay");
  const editQuestDrawer  = document.getElementById("edit-quest-drawer");
  const editFreqSelect   = document.getElementById("edit-quest-frequency");
  const editDaysGroup    = document.getElementById("edit-scheduled-days-group");
  const editDayTypesGroup = document.getElementById("edit-quest-day-types");
  const editQuestDescLabel = document.getElementById("edit-quest-desc-label");
  const editQuestDescInput = document.getElementById("edit-quest-desc");
  const editQuestVersionList = document.getElementById("edit-quest-version-list");
  const addEditQuestVersionBtn = document.getElementById("add-edit-quest-version-btn");
  const editQuestSourceMeta = document.getElementById("edit-quest-source-meta");
  const editQuestFrequencyNote = document.getElementById("edit-quest-frequency-note");
  const archiveQuestBtn = document.getElementById("archive-quest-btn");
  let activeEditQuest = null;

  function questProgressEditorElements(prefix) {
    return {
      type: document.getElementById(`${prefix}-quest-type`),
      unit: document.getElementById(`${prefix}-quest-unit`),
      target: document.getElementById(`${prefix}-quest-target`),
      counter: document.getElementById(`${prefix}-quest-free-counter`),
      checklist: document.getElementById(`${prefix}-quest-checklist-items`),
      addChecklist: document.getElementById(`${prefix}-quest-add-checklist-item`)
    };
  }

  function currentQuestProgressEditorMode(prefix) {
    const elements = questProgressEditorElements(prefix);
    if (elements.counter?.checked) return "free_counter";
    if (elements.checklist?.children.length) return "checklist";
    return "standard";
  }

  function setQuestProgressEditorMode(prefix, mode, { clearChecklist = false } = {}) {
    const elements = questProgressEditorElements(prefix);
    if (!elements.type || !elements.unit || !elements.target || !elements.counter || !elements.checklist) return;
    const enriched = mode === "free_counter" || mode === "checklist";
    elements.counter.checked = mode === "free_counter";
    if (clearChecklist) elements.checklist.innerHTML = "";
    if (enriched) {
      elements.type.value = "binary";
      elements.type.disabled = true;
      elements.target.value = "";
      elements.target.disabled = true;
    } else {
      elements.type.disabled = false;
      elements.target.disabled = false;
    }
    if (mode === "free_counter") {
      elements.unit.disabled = false;
      if (!elements.unit.value.trim()) elements.unit.value = "reps";
    } else if (mode === "checklist") {
      elements.unit.value = "";
      elements.unit.disabled = true;
    } else {
      elements.unit.disabled = false;
    }
  }

  function addQuestChecklistEditorRow(prefix, item = {}) {
    const elements = questProgressEditorElements(prefix);
    if (!elements.checklist) return null;
    const row = document.createElement("div");
    row.className = "quest-checklist-editor-row";
    if (item.id !== undefined && item.id !== null) row.dataset.itemId = String(item.id);
    const input = document.createElement("input");
    input.type = "text";
    input.className = "quest-checklist-label-input";
    input.placeholder = "ex: Échauffement terminé";
    input.value = item.label || "";
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "quest-checklist-remove-btn";
    remove.textContent = "Retirer";
    remove.addEventListener("click", () => {
      if (
        prefix === "edit"
        && activeEditQuest?.progress_mode === "checklist"
        && elements.checklist.children.length === 1
        && !confirm("Retirer la dernière étape désactivera la checklist et effacera le suivi d’aujourd’hui. Continuer ?")
      ) return;
      row.remove();
      if (elements.checklist.children.length === 0) {
        setQuestProgressEditorMode(prefix, "standard");
        elements.type.value = "binary";
        elements.unit.value = "";
      }
    });
    row.append(input, remove);
    elements.checklist.appendChild(row);
    setQuestProgressEditorMode(prefix, "checklist");
    return input;
  }

  function collectQuestChecklistEditorItems(prefix) {
    const { checklist } = questProgressEditorElements(prefix);
    return Array.from(checklist?.querySelectorAll(".quest-checklist-editor-row") || [])
      .map(row => {
        const label = row.querySelector(".quest-checklist-label-input")?.value.trim() || "";
        const item = { label };
        if (row.dataset.itemId) item.id = row.dataset.itemId;
        return item;
      })
      .filter(item => item.label);
  }

  function renderQuestChecklistEditor(prefix, items) {
    const { checklist } = questProgressEditorElements(prefix);
    if (!checklist) return;
    checklist.innerHTML = "";
    (items || []).forEach(item => addQuestChecklistEditorRow(prefix, item));
  }

  function setupQuestProgressEditor(prefix) {
    const elements = questProgressEditorElements(prefix);
    if (!elements.counter || !elements.addChecklist || !elements.type) return;

    elements.counter.addEventListener("change", () => {
      if (!elements.counter.checked) {
        if (
          prefix === "edit"
          && activeEditQuest?.progress_mode === "free_counter"
          && !confirm("Désactiver le compteur libre effacera sa configuration et le suivi d’aujourd’hui. Continuer ?")
        ) {
          elements.counter.checked = true;
          return;
        }
        setQuestProgressEditorMode(prefix, "standard");
        elements.type.value = "binary";
        elements.unit.value = "";
        return;
      }
      const currentMode = elements.checklist?.children.length ? "checklist" : "standard";
      const quantitative = elements.type.value === "quantitative";
      if ((currentMode === "checklist" || quantitative) && !confirm(
        "Activer le compteur libre effacera la configuration incompatible. Continuer ?"
      )) {
        elements.counter.checked = false;
        return;
      }
      setQuestProgressEditorMode(prefix, "free_counter", { clearChecklist: true });
    });

    elements.addChecklist.addEventListener("click", () => {
      const currentMode = currentQuestProgressEditorMode(prefix);
      const quantitative = elements.type.value === "quantitative";
      if ((currentMode === "free_counter" || quantitative) && !confirm(
        "Activer la checklist effacera la configuration incompatible. Continuer ?"
      )) return;
      if (currentMode === "free_counter") {
        elements.counter.checked = false;
        elements.unit.value = "";
      }
      const input = addQuestChecklistEditorRow(prefix);
      input?.focus();
    });

    setQuestProgressEditorMode(prefix, "standard");
  }

  function selectedDayTypes(container) {
    return Array.from(container?.querySelectorAll("input:checked") || []).map(cb => cb.value);
  }

  function splitQuestVersionName(name) {
    const cleanedName = (name || "").trim();
    for (const prefix of ["Étape ", "Etape "]) {
      if (cleanedName.startsWith(prefix)) {
        const remaining = cleanedName.slice(prefix.length);
        const separatorIndex = remaining.indexOf(" - ");
        if (separatorIndex > 0) {
          const versionIndex = parseInt(remaining.slice(0, separatorIndex), 10);
          const baseName = remaining.slice(separatorIndex + 3).trim();
          if (!isNaN(versionIndex) && baseName) {
            return { versionIndex, baseName };
          }
        }
      }
    }
    return { versionIndex: null, baseName: cleanedName };
  }

  function getQuestVersionGroup(habit) {
    if (habit.version_history && habit.version_history.length > 0) {
      return habit.version_history
        .map((version) => ({
          habit: version,
          baseName: splitQuestVersionName(version.name).baseName,
          versionIndex: version.version_index,
          displayIndex: version.version_index || 1
        }))
        .sort((a, b) => a.displayIndex - b.displayIndex || a.habit.id - b.habit.id);
    }

    const { baseName } = splitQuestVersionName(habit.name);
    return allHabitsCache
      .map((candidate) => {
        const parsed = splitQuestVersionName(candidate.name);
        return {
          habit: candidate,
          baseName: parsed.baseName,
          versionIndex: parsed.versionIndex,
          displayIndex: parsed.versionIndex || 1
        };
      })
      .filter((candidate) => candidate.baseName === baseName)
      .sort((a, b) => a.displayIndex - b.displayIndex || a.habit.id - b.habit.id);
  }

  function renderEditQuestDescriptionFields(habit) {
    const versions = getQuestVersionGroup(habit);
    const hasVersions = versions.length > 1 || versions.some((item) => item.versionIndex !== null);
    const primaryVersion = hasVersions ? versions[0] : versions.find((item) => item.habit.id === habit.id) || {
      habit,
      displayIndex: 1
    };

    editQuestDescLabel.textContent = hasVersions ? `V${primaryVersion.displayIndex} description` : "Description";
    editQuestDescInput.value = primaryVersion.habit.description || "";
    editQuestDescInput.dataset.habitId = primaryVersion.habit.id;
    editQuestVersionList.innerHTML = "";
    editQuestVersionList.style.display = hasVersions ? "flex" : "none";

    if (!hasVersions) return;

    versions
      .filter((item) => item.habit.id !== primaryVersion.habit.id)
      .forEach((item) => {
        const block = document.createElement("div");
        block.className = "quest-version-description-block";
        block.innerHTML = `
          <label>V${item.displayIndex} description</label>
          <textarea class="quest-version-description-input" data-habit-id="${item.habit.id}" rows="5"></textarea>
        `;
        const input = block.querySelector(".quest-version-description-input");
        input.value = item.habit.description || "";
        editQuestVersionList.appendChild(block);
      });
  }

  function collectQuestVersionDescriptionUpdates() {
    const updates = [{
      id: parseInt(editQuestDescInput.dataset.habitId || document.getElementById("edit-quest-id").value, 10),
      description: editQuestDescInput.value.trim()
    }];

    editQuestVersionList.querySelectorAll(".quest-version-description-input").forEach((input) => {
      updates.push({
        id: parseInt(input.dataset.habitId, 10),
        description: input.value.trim()
      });
    });

    return updates.filter((update) => !isNaN(update.id));
  }

  async function saveQuestDescriptionUpdates(descriptionUpdates, skipId = null) {
    for (const update of descriptionUpdates) {
      if (skipId !== null && String(update.id) === String(skipId)) continue;
      const updateResponse = await fetch(`${API_BASE}/habits/${update.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ description: update.description }),
      });
      if (!updateResponse.ok) throw new Error((await updateResponse.json()).detail || "Erreur");
    }
  }

  function renderEditQuestDailyProgress(habit, agendaItem = null) {
    const shell = document.getElementById("edit-quest-daily-progress-shell");
    const title = document.getElementById("edit-quest-daily-progress-title");
    const content = document.getElementById("edit-quest-daily-progress");
    if (!shell || !title || !content) return;

    content.innerHTML = "";
    const mode = habit?.progress_mode || "standard";
    if (mode === "standard") {
      shell.hidden = true;
      return;
    }

    shell.hidden = false;
    title.textContent = mode === "checklist" ? "Checklist du jour" : "Compteur du jour";
    const datedItem = agendaItem || agendaQuestById(habit.id);
    const control = datedItem ? createQuestProgressControl(datedItem, { inDrawer: true }) : null;
    if (control) {
      content.appendChild(control);
      return;
    }

    const note = document.createElement("p");
    note.className = "quest-daily-progress-note";
    note.textContent = datedItem
      ? "Ce suivi n’était pas encore actif à la date affichée."
      : "Le suivi quotidien apparaîtra dans l’Agenda une fois la quête chargée pour cette date.";
    content.appendChild(note);
  }

  async function openEditQuestModal(habit, agendaItem = null) {
    activeEditQuest = habit;
    document.getElementById("edit-quest-focus-role").value = habit.focus_role || "must";
    await populateFocusTargets("edit", habit.focus_goal_id || habit.focus_softskill_id);
    await renderQuestTagEditor("edit", habit.tags || [], true);
    document.getElementById("edit-quest-id").value        = habit.id;
    document.getElementById("edit-quest-name").value      = habit.name;
    document.getElementById("edit-quest-type").value      = habit.type || "binary";
    document.getElementById("edit-quest-unit").value      = habit.unit || "";
    document.getElementById("edit-quest-target").value    = habit.daily_target || "";
    renderQuestChecklistEditor("edit", habit.checklist_items || []);
    setQuestProgressEditorMode("edit", habit.progress_mode || "standard");
    renderEditQuestDailyProgress(habit, agendaItem);
    editFreqSelect.value = habit.frequency || "daily";
    renderEditQuestDescriptionFields(habit);

    // Populate effort
    document.getElementById("edit-quest-effort-type").value = habit.effort_type || "";
    const editDuration = habit.agenda_duration_minutes || Math.max(15, Math.round((habit.effort_duration || 1.0) * 60));
    document.getElementById("edit-quest-duration").value = editDuration;
    updateFrequencyNote(editFreqSelect, editQuestFrequencyNote, habit.scheduled_days);

    if (editQuestSourceMeta) {
      const sourceType = habit.source_type || "manual";
      if (sourceType === "manual") {
        editQuestSourceMeta.style.display = "none";
        editQuestSourceMeta.textContent = "";
      } else {
        editQuestSourceMeta.style.display = "block";
        editQuestSourceMeta.textContent = habit.source_label || `${sourceType}: ${habit.source_ref || ""}`;
      }
    }
    if (archiveQuestBtn) {
      archiveQuestBtn.textContent = habit.archived_at ? "Désarchiver" : "Archiver";
      archiveQuestBtn.dataset.archived = habit.archived_at ? "true" : "false";
      archiveQuestBtn.dataset.sourceType = habit.source_type || "manual";
    }

    // Show/hide day checkboxes
    const isSpecific = habit.frequency === "specific_days";
    editDaysGroup.style.display = isSpecific ? "block" : "none";
    const activeDays = (habit.scheduled_days || "").split(",").map(s => s.trim());
    editDaysGroup.querySelectorAll("input").forEach(cb => {
      cb.checked = activeDays.includes(cb.value);
    });
    const activeDayTypes = habit.day_types || ["rest", "regular", "hustle"];
    editDayTypesGroup?.querySelectorAll("input").forEach(cb => {
      cb.checked = activeDayTypes.includes(cb.value);
    });

    editQuestOverlay.classList.add("open");
    editQuestDrawer.classList.add("open");
  }

  function closeEditQuestModal() {
    editQuestOverlay.classList.remove("open");
    editQuestDrawer.classList.remove("open");
    activeEditQuest = null;
  }

  if (editFreqSelect) {
    editFreqSelect.addEventListener("change", () => {
      editDaysGroup.style.display = editFreqSelect.value === "specific_days" ? "block" : "none";
      updateFrequencyNote(editFreqSelect, editQuestFrequencyNote, activeEditQuest ? activeEditQuest.scheduled_days : null);
    });
  }
  document.getElementById("edit-quest-focus-role")?.addEventListener("change", () => populateFocusTargets("edit"));

  document.getElementById("close-edit-quest-btn")?.addEventListener("click", closeEditQuestModal);
  editQuestOverlay?.addEventListener("click", closeEditQuestModal);

  addEditQuestVersionBtn?.addEventListener("click", async () => {
    const id = parseInt(document.getElementById("edit-quest-id").value, 10);
    if (isNaN(id)) return;

    const activeDescriptionUpdate = collectQuestVersionDescriptionUpdates()
      .find((update) => update.id === id);
    const sourceDescription = activeDescriptionUpdate
      ? activeDescriptionUpdate.description
      : editQuestDescInput.value.trim();

    try {
      await saveQuestDescriptionUpdates(collectQuestVersionDescriptionUpdates(), id);
      const data = await createQuestVersion(id, sourceDescription);
      if (!data) return;

      await fetchQuests();
      const refreshedHabit = allHabitsCache.find((habit) => habit.id === data.id) || activeEditQuest;
      if (refreshedHabit) {
        activeEditQuest = refreshedHabit;
        document.getElementById("edit-quest-id").value = refreshedHabit.id;
        document.getElementById("edit-quest-name").value = refreshedHabit.name;
        document.getElementById("edit-quest-type").value = refreshedHabit.type || "binary";
        document.getElementById("edit-quest-unit").value = refreshedHabit.unit || "";
        document.getElementById("edit-quest-target").value = refreshedHabit.daily_target || "";
        renderQuestChecklistEditor("edit", refreshedHabit.checklist_items || []);
        setQuestProgressEditorMode("edit", refreshedHabit.progress_mode || "standard");
        renderEditQuestDailyProgress(refreshedHabit);
        editFreqSelect.value = refreshedHabit.frequency || "daily";
        updateFrequencyNote(editFreqSelect, editQuestFrequencyNote, refreshedHabit.scheduled_days);
        renderEditQuestDescriptionFields(refreshedHabit);
      }
    } catch (e) {
      showToast(e.message, true);
    }
  });

  document.getElementById("save-edit-quest-btn")?.addEventListener("click", async () => {
    const id        = document.getElementById("edit-quest-id").value;
    const frequency = editFreqSelect.value;
    let scheduled_days = "0,1,2,3,4,5,6";
    if (frequency === "specific_days") {
      const checked = Array.from(editDaysGroup.querySelectorAll("input:checked")).map(cb => cb.value);
      scheduled_days = checked.length > 0 ? checked.join(",") : "0,1,2,3,4,5,6";
    } else if (frequency === "monthly") {
      scheduled_days = String(monthlyAnchorDay(activeEditQuest ? activeEditQuest.scheduled_days : null));
    }
    const editTargetRaw = parseInt(document.getElementById("edit-quest-target").value);

    const effort_type = document.getElementById("edit-quest-effort-type").value || null;
    const agenda_duration_minutes = parseInt(document.getElementById("edit-quest-duration").value, 10) || 60;
    const effort_duration = agenda_duration_minutes / 60;
    const agenda_placeable = activeEditQuest?.agenda_placeable !== false;
    const day_types = selectedDayTypes(editDayTypesGroup);
    if (day_types.length === 0) {
      showToast("Choisissez au moins un type de journée.", true);
      return;
    }
    const descriptionUpdates = collectQuestVersionDescriptionUpdates();
    const activeDescription = descriptionUpdates.find((update) => String(update.id) === String(id));
    const progress_mode = currentQuestProgressEditorMode("edit");
    const checklist_items = progress_mode === "checklist"
      ? collectQuestChecklistEditorItems("edit")
      : [];
    if (progress_mode === "checklist" && checklist_items.length === 0) {
      showToast("Ajoutez au moins un élément non vide à la checklist.", true);
      return;
    }
    const questType = progress_mode === "standard"
      ? document.getElementById("edit-quest-type").value
      : "binary";
    const unitValue = progress_mode === "free_counter"
      ? (document.getElementById("edit-quest-unit").value.trim() || "reps")
      : progress_mode === "standard" && questType === "quantitative"
        ? (document.getElementById("edit-quest-unit").value.trim() || null)
        : null;

    let focus;
    try { focus = await selectedQuestFocus("edit"); }
    catch (error) { showToast(error.message, true); return; }
    if (!focus) return;
    const body = {
      name:           document.getElementById("edit-quest-name").value.trim(),
      description:    activeDescription ? activeDescription.description : editQuestDescInput.value.trim(),
      type:           questType,
      unit:           unitValue,
      frequency,
      scheduled_days,
      day_types,
      daily_target:   progress_mode === "standard" && editTargetRaw > 1 ? editTargetRaw : null,
      progress_mode,
      checklist_items,
      effort_type,
      effort_duration,
      agenda_duration_minutes,
      agenda_placeable,
      tags: collectQuestTags("edit"),
      ...focus,
    };
    try {
      const r = await fetch(`${API_BASE}/habits/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error((await r.json()).detail || "Erreur");
      await saveQuestDescriptionUpdates(descriptionUpdates, id);
      showToast("Quête mise à jour !");
      closeEditQuestModal();
      refreshAll();
    } catch (e) {
      showToast(e.message, true);
    }
  });

  archiveQuestBtn?.addEventListener("click", async () => {
    const id = document.getElementById("edit-quest-id").value;
    if (!id) return;
    const archived = archiveQuestBtn.dataset.archived === "true";
    const action = archived ? "unarchive" : "archive";
    if (!confirmQuestArchiveAction(archiveQuestBtn.dataset.sourceType, archived)) return;
    try {
      const r = await fetch(`${API_BASE}/habits/${id}/${action}`, { method: "POST" });
      if (!r.ok) throw new Error((await r.json()).detail || "Erreur");
      showToast(questArchiveToast(await r.json(), archived));
      closeEditQuestModal();
      await refreshQuestSurfaces();
      fetchProfile();
      fetchHistory();
      fetchBounties();
      fetchNoTodos();
      updateDailyBudgetGauge();
    } catch (e) {
      showToast(e.message, true);
    }
  });

  document.getElementById("delete-quest-btn")?.addEventListener("click", async () => {
    const id = document.getElementById("edit-quest-id").value;
    if (!confirm("Supprimer cette quête définitivement ?")) return;
    try {
      const r = await fetch(`${API_BASE}/habits/${id}`, { method: "DELETE" });
      if (!r.ok) throw new Error((await r.json()).detail || "Erreur");
      showToast("Quête supprimée.");
      closeEditQuestModal();
      refreshAll();
    } catch (e) {
      showToast(e.message, true);
    }
  });

  // Refresh helper
  function refreshAll() {
    fetchProfile();
    fetchQuests();
    fetchHistory();
    fetchBounties();
    fetchNoTodos();
    if (!directProgressInputActive) updateDailyBudgetGauge();

    const rewardsTab = document.getElementById("rewards-tab");
    if (rewardsTab && rewardsTab.classList.contains("active")) {
      fetchRewards();
    }
  }

  // Authentication & Initialization
  let appInitialized = false;
  let appEventsBound = false;
  let refreshIntervalId = null;
  checkAuthAndStart();

  async function checkAuthAndStart() {
    const status = await fetchAuthStatus();
    if (status?.authenticated) {
      hideLoginScreen();
      if (!appInitialized) {
        initializeApp();
      } else {
        refreshAll();
      }
      return;
    }
    renderAuthScreen(status);
  }

  async function showLoginScreen() {
    await checkAuthAndStart();
  }

  async function fetchAuthStatus() {
    try {
      const response = await fetch(`${API_BASE}/auth/status`);
      if (!response.ok) throw new Error("Erreur auth");
      return await response.json();
    } catch (error) {
      return {
        authenticated: false,
        bootstrap_required: false,
        device_status: "error",
        error: error.message,
      };
    }
  }

  function hideLoginScreen() {
    const overlay = document.getElementById("login-overlay");
    if (overlay) overlay.style.display = "none";
  }

  function authShell(title, message, bodyHtml) {
    const overlay = document.getElementById("login-overlay");
    const titleEl = document.getElementById("login-title");
    const messageEl = document.getElementById("login-message");
    const usersContainer = document.getElementById("login-users-container");
    const errorEl = document.getElementById("login-error");
    if (overlay) overlay.style.display = "flex";
    if (titleEl) titleEl.textContent = title;
    if (messageEl) messageEl.textContent = message;
    if (errorEl) {
      errorEl.style.display = "none";
      errorEl.textContent = "";
    }
    if (usersContainer) usersContainer.innerHTML = bodyHtml;
  }

  function showAuthError(message) {
    const errorEl = document.getElementById("login-error");
    if (errorEl) {
      errorEl.textContent = message;
      errorEl.style.display = "block";
    }
  }

  function renderAuthScreen(status) {
    if (!status || status.device_status === "error") {
      authShell(
        "Connexion indisponible",
        "Impossible de joindre le serveur d'authentification.",
        `<button id="auth-retry-btn" class="quest-action-btn">Réessayer</button>`
      );
      document.getElementById("auth-retry-btn")?.addEventListener("click", checkAuthAndStart);
      return;
    }
    if (status.bootstrap_required) {
      renderBootstrapScreen(status);
      return;
    }
    if (status.device_status === "revoked") {
      renderDeviceRequest(status);
      return;
    }
    renderPasswordLogin(status);
  }

  function renderBootstrapScreen(status) {
    const disabled = status.bootstrap_configured ? "" : "disabled";
    authShell(
      "Initialisation sécurisée",
      status.bootstrap_configured
        ? "Crée le mot de passe admin et approuve cet appareil."
        : "AUTH_BOOTSTRAP_CODE doit être défini dans l'environnement serveur.",
      `
        <form id="auth-bootstrap-form" class="auth-form">
          <input type="text" id="auth-bootstrap-code" placeholder="Code bootstrap" autocomplete="one-time-code" ${disabled} required>
          <input type="password" id="auth-bootstrap-password" placeholder="Mot de passe admin" autocomplete="new-password" ${disabled} required minlength="8">
          <input type="text" id="auth-device-name" placeholder="Nom de cet appareil" ${disabled}>
          <button type="submit" class="quest-action-btn" ${disabled}>Activer la sécurité</button>
        </form>
      `
    );
    document.getElementById("auth-bootstrap-form")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      try {
        const response = await fetch(`${API_BASE}/auth/bootstrap`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            bootstrap_code: document.getElementById("auth-bootstrap-code").value,
            password: document.getElementById("auth-bootstrap-password").value,
            device_name: document.getElementById("auth-device-name").value || navigator.userAgent.slice(0, 80),
          }),
        });
        if (!response.ok) throw new Error((await response.json()).detail || "Erreur bootstrap");
        await checkAuthAndStart();
      } catch (error) {
        showAuthError(error.message);
      }
    });
  }

  function renderDeviceRequest(status) {
    const isPending = status.device_status === "pending";
    const isRevoked = status.device_status === "revoked";
    authShell(
      isPending ? "Appareil en attente" : isRevoked ? "Appareil révoqué" : "Nouvel appareil",
      isPending
        ? "Valide cet appareil depuis un ordinateur ou téléphone déjà approuvé."
        : isRevoked
          ? "Cet appareil a été révoqué. Efface les cookies ou utilise un autre navigateur pour refaire une demande."
          : "Demande l'accès depuis cet appareil, puis approuve-le depuis un appareil déjà autorisé.",
      `
        <form id="auth-device-form" class="auth-form" style="${isPending || isRevoked ? "display:none;" : ""}">
          <input type="text" id="auth-device-request-name" placeholder="Nom de cet appareil">
          <button type="submit" class="quest-action-btn">Demander l'accès</button>
        </form>
        <button id="auth-refresh-btn" class="floating-add-btn">Rafraîchir</button>
      `
    );
    document.getElementById("auth-device-form")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      try {
        const response = await fetch(`${API_BASE}/auth/devices/request`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            device_name: document.getElementById("auth-device-request-name").value || navigator.userAgent.slice(0, 80),
          }),
        });
        if (!response.ok) throw new Error((await response.json()).detail || "Erreur appareil");
        await checkAuthAndStart();
      } catch (error) {
        showAuthError(error.message);
      }
    });
    document.getElementById("auth-refresh-btn")?.addEventListener("click", checkAuthAndStart);
  }

  async function renderPasswordLogin(status) {
    let users = status.users || [];
    if (!users.length) {
      try {
        const response = await fetch(`${API_BASE}/auth/users`);
        if (response.ok) users = await response.json();
      } catch (error) {
        users = [];
      }
    }
    const userField = users.length
      ? `<select id="auth-login-username" required>${users
        .map(user => `<option value="${escapeHtml(user.username)}">${escapeHtml(user.username)}</option>`)
        .join("")}</select>`
      : `<input type="text" id="auth-login-username" placeholder="Nom du compte" autocomplete="username" required>`;
    const reconnecting = status.device_status !== "approved";
    authShell(
      "Connexion",
      reconnecting
        ? "Session expirée ou nouvel appareil. Reconnecte-toi."
        : "Entre le mot de passe du compte à ouvrir.",
      `
        <form id="auth-login-form" class="auth-form">
          ${userField}
          <input type="password" id="auth-login-password" placeholder="Mot de passe" autocomplete="current-password" required>
          <button type="submit" class="quest-action-btn">Se connecter</button>
        </form>
      `
    );
    document.getElementById("auth-login-form")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      try {
        const response = await fetch(`${API_BASE}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            username: document.getElementById("auth-login-username").value,
            password: document.getElementById("auth-login-password").value,
            device_name: status.device?.display_name || navigator.userAgent.slice(0, 80),
          }),
        });
        if (!response.ok) throw new Error((await response.json()).detail || "Connexion refusée");
        await checkAuthAndStart();
      } catch (error) {
        showAuthError(error.message);
      }
    });
  }

  async function loadAuthAdminSettings() {
    const adminPanel = document.getElementById("auth-admin-panel");
    const deviceList = document.getElementById("auth-device-list");
    const userSelect = document.getElementById("auth-admin-user");
    if (!adminPanel || !deviceList) return;

    const status = await fetchAuthStatus();
    const isAdmin = Boolean(status?.user?.is_admin);
    adminPanel.style.display = isAdmin ? "block" : "none";
    if (!isAdmin) return;

    try {
      const [devicesResp, usersResp] = await Promise.all([
        fetch(`${API_BASE}/auth/devices`),
        fetch(`${API_BASE}/auth/users`),
      ]);
      if (!devicesResp.ok) throw new Error((await devicesResp.json()).detail || "Erreur appareils");
      const devices = await devicesResp.json();
      const users = usersResp.ok ? await usersResp.json() : [];
      if (userSelect) {
        userSelect.innerHTML = users
          .map(user => `<option value="${user.id}">${escapeHtml(user.username)}</option>`)
          .join("");
      }
      renderAuthDeviceList(devices);
    } catch (error) {
      deviceList.innerHTML = `<p class="bio-zone-error" style="display:block;">${error.message}</p>`;
    }
  }

  function renderAuthDeviceList(devices) {
    const deviceList = document.getElementById("auth-device-list");
    if (!deviceList) return;
    if (!devices.length) {
      deviceList.innerHTML = `<p class="bio-zone-empty">Aucun appareil enregistré.</p>`;
      return;
    }
    deviceList.innerHTML = devices.map(device => {
      const name = escapeHtml(device.display_name || "Appareil sans nom");
      const userAgent = escapeHtml(device.user_agent || "");
      const seen = device.last_seen_at ? new Date(device.last_seen_at).toLocaleString("fr-CA") : "jamais";
      const expires = device.expires_at ? new Date(device.expires_at).toLocaleDateString("fr-CA") : "inconnue";
      const canRevoke = device.status !== "revoked";
      return `
        <div class="auth-device-item" data-device-id="${device.id}">
          <div>
            <div class="auth-device-name">
              ${name}
              <span class="auth-status-badge ${device.status}">${device.status}</span>
            </div>
            <div class="auth-device-meta">Dernière activité : ${seen}</div>
            <div class="auth-device-meta">Expiration : ${expires}</div>
            <div class="auth-device-meta">${userAgent}</div>
          </div>
          <div class="auth-device-actions">
            ${canRevoke ? `<button type="button" class="floating-add-btn auth-device-revoke">Révoquer</button>` : ""}
          </div>
        </div>
      `;
    }).join("");
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function setupToggleEvents() {
    toggleQuestAgendaBtn?.addEventListener("click", () => setQuestPanelMode("agenda"));
    toggleQuestBankBtn?.addEventListener("click", () => setQuestPanelMode("bank"));
    toggleQuestArchivesBtn?.addEventListener("click", () => setQuestPanelMode("archives"));

    const toggleBountiesBtn = document.getElementById("toggle-bounties-view-btn");
    if (toggleBountiesBtn) {
      toggleBountiesBtn.addEventListener("click", () => {
        showTodayBounties = !showTodayBounties;
        fetchBounties();
      });
    }
  }

  function setupAgendaEvents() {
    if (agendaDateInput && !agendaDateInput.value) {
      agendaDateInput.value = todayDateString();
    }
    updateAgendaDateSwitch();
    agendaDateInput?.addEventListener("change", async () => {
      await showAgendaDate(getAgendaDate());
    });
    agendaYesterdayBtn?.addEventListener("click", () => showAgendaDate(yesterdayDateString()));
    agendaTodayBtn?.addEventListener("click", () => showAgendaDate(todayDateString()));
    agendaRefreshBtn?.addEventListener("click", () => showAgendaDate(getAgendaDate()));
  }

  function initializeApp() {
    if (appInitialized) {
      refreshAll();
      return;
    }
    appInitialized = true;
    biologicalZonesCache = null;
    if (!appEventsBound) {
      setupAgendaEvents();
      setupToggleEvents();
      setupBountiesEvents();
      setupQuestsEvents();
      setupNoTodosEvents();
      setupRewardsEvents();
      appEventsBound = true;
    }
    loadBioTimeline();
    refreshAll();
    // Auto-sync dashboard every 12 seconds
    if (refreshIntervalId) {
      clearInterval(refreshIntervalId);
    }
    refreshIntervalId = setInterval(refreshAll, 12000);
  }

  // ==============================================
  // QUESTS (HABITS) & NO-TODOS FORMS
  // ==============================================
  async function populateFocusTargets(prefix, selectedId = null) {
    const role = document.getElementById(`${prefix}-quest-focus-role`)?.value || "must";
    const wrap = document.getElementById(`${prefix}-quest-focus-target-wrap`);
    const select = document.getElementById(`${prefix}-quest-focus-target`);
    if (!wrap || !select) return;
    wrap.hidden = role === "must";
    select.replaceChildren();
    if (role === "must") return;
    const response = await fetch(`${API_BASE}/${role === "goal" ? "goals" : "softskills"}`);
    if (!response.ok) throw new Error("Impossible de charger les liens de focus.");
    const data = await response.json();
    const items = role === "goal" ? data.filter(goal => !goal.completed) : (data.skills || []).filter(skill => !skill.progress?.completed);
    for (const item of items) {
      const option = document.createElement("option");
      option.value = item.id;
      option.textContent = item.title || item.name;
      select.appendChild(option);
    }
    const createOption = document.createElement("option");
    createOption.value = "__create__";
    createOption.textContent = role === "goal" ? "+ Créer un objectif" : "+ Créer une compétence";
    select.appendChild(createOption);
    if (selectedId != null) select.value = String(selectedId);
  }

  async function selectedQuestFocus(prefix) {
    const role = document.getElementById(`${prefix}-quest-focus-role`)?.value || "must";
    if (role === "must") return { focus_role: "must", focus_goal_id: null, focus_softskill_id: null };
    let id = document.getElementById(`${prefix}-quest-focus-target`)?.value;
    if (id === "__create__") {
      const title = prompt(role === "goal" ? "Nom du nouvel objectif" : "Nom de la nouvelle compétence")?.trim();
      if (!title) return null;
      if (role === "goal") {
        const response = await fetch(`${API_BASE}/goals`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title }) });
        if (!response.ok) throw new Error((await response.json()).detail || "Création impossible");
        id = String((await response.json()).goal.id);
      } else {
        const skillsResponse = await fetch(`${API_BASE}/softskills`);
        const skillsData = await skillsResponse.json();
        const branches = Object.keys(skillsData.branches || {});
        const branch = prompt(branches.length ? `Branche de la compétence (${branches.join(", ")}). Une nouvelle valeur crée une branche.` : "Nom de la branche à créer")?.trim();
        if (!branch) return null;
        if (!branches.includes(branch)) {
          if (!confirm(`Créer la branche « ${branch} » pour la compétence « ${title} » ?`)) return null;
          const createdBranch = await fetch(`${API_BASE}/softskills/branches`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ key: branch, color: "#8b5cf6", pale_color: "#ddd6fe" }) });
          if (!createdBranch.ok) throw new Error((await createdBranch.json()).detail || "Branche impossible à créer");
        }
        const skillId = `skill_${Date.now()}`;
        const response = await fetch(`${API_BASE}/softskills/skills`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id: skillId, name: title, description: "", branch, prerequisites: [], related: [], execution_order: 1 }) });
        if (!response.ok) throw new Error((await response.json()).detail || "Création impossible");
        id = skillId;
      }
      await populateFocusTargets(prefix, id);
    }
    if (!id) { showToast("Choisissez un objectif ou une compétence.", true); return null; }
    return role === "goal" ? { focus_role: role, focus_goal_id: Number(id), focus_softskill_id: null } : { focus_role: role, focus_goal_id: null, focus_softskill_id: id };
  }

  function setupQuestsEvents() {
    const openQuestBtn = document.getElementById("open-quest-inline-btn");
    const questForm = document.getElementById("quest-inline-form");
    const submitQuestBtn = document.getElementById("submit-quest-btn");
    const newDayTypesGroup = document.getElementById("new-quest-day-types");
    const newFocusRole = document.getElementById("new-quest-focus-role");
    newFocusRole?.addEventListener("change", () => populateFocusTargets("new"));

    setupQuestProgressEditor("new");
    setupQuestProgressEditor("edit");
    document.getElementById("close-recap-quest-form-btn")?.addEventListener("click", closeQuestInlineForm);
    document.getElementById("recap-quest-form-overlay")?.addEventListener("click", closeQuestInlineForm);

    if (openQuestBtn && questForm) {
      openQuestBtn.addEventListener("click", async () => {
        if (questForm.style.display === "none") {
          await renderQuestTagEditor("new", [], true);
          await populateFocusTargets("new");
          questForm.style.display = "flex";
          openQuestBtn.textContent = "Fermer Formulaire";
        } else {
          closeQuestInlineForm();
        }
      });
    }

    // Show/hide day checkboxes based on frequency selection
    const freqSelect = document.getElementById("new-quest-frequency");
    const daysGroup = document.getElementById("scheduled-days-group");
    const newQuestFrequencyNote = document.getElementById("new-quest-frequency-note");
    if (freqSelect && daysGroup) {
      freqSelect.addEventListener("change", () => {
        daysGroup.style.display = freqSelect.value === "specific_days" ? "block" : "none";
        updateFrequencyNote(freqSelect, newQuestFrequencyNote);
      });
      updateFrequencyNote(freqSelect, newQuestFrequencyNote);
    }

    if (submitQuestBtn) {
      submitQuestBtn.addEventListener("click", async () => {
        const title = document.getElementById("new-quest-name").value.trim();
        const desc = document.getElementById("new-quest-desc").value.trim();
        const type = document.getElementById("new-quest-type").value;
        const progress_mode = currentQuestProgressEditorMode("new");
        const checklist_items = progress_mode === "checklist"
          ? collectQuestChecklistEditorItems("new")
          : [];
        if (progress_mode === "checklist" && checklist_items.length === 0) {
          showToast("Ajoutez au moins un élément non vide à la checklist.", true);
          return;
        }
        const effectiveType = progress_mode === "standard" ? type : "binary";
        const rawUnit = document.getElementById("new-quest-unit").value.trim();
        const unit = progress_mode === "free_counter"
          ? (rawUnit || "reps")
          : progress_mode === "standard" && effectiveType === "quantitative"
            ? (rawUnit || null)
            : null;
        const targetRaw = parseInt(document.getElementById("new-quest-target").value);
        const daily_target = progress_mode === "standard" && targetRaw > 1 ? targetRaw : null;
        const frequency = freqSelect ? freqSelect.value : "daily";

        let scheduled_days = "0,1,2,3,4,5,6";
        if (frequency === "specific_days") {
          const checked = Array.from(document.querySelectorAll("#new-quest-days input:checked")).map(cb => cb.value);
          scheduled_days = checked.length > 0 ? checked.join(",") : "0,1,2,3,4,5,6";
        } else if (frequency === "monthly") {
          scheduled_days = String(monthlyAnchorDay(null));
        }

        const effort_type = document.getElementById("new-quest-effort-type").value || null;
        const agenda_duration_minutes = parseInt(document.getElementById("new-quest-duration").value, 10) || 60;
        const effort_duration = agenda_duration_minutes / 60;
        const agenda_placeable = true;
        const day_types = selectedDayTypes(newDayTypesGroup);
        let focus;
        try { focus = await selectedQuestFocus("new"); }
        catch (error) { showToast(error.message, true); return; }
        if (!focus) return;

        if (!title) {
          showToast("Veuillez donner un titre à la quête !", true);
          return;
        }
        if (day_types.length === 0) {
          showToast("Choisissez au moins un type de journée.", true);
          return;
        }

        try {
          const response = await fetch(`${API_BASE}/habits`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              name: title,
              description: desc,
              type: effectiveType,
              unit,
              frequency: frequency,
              scheduled_days: scheduled_days,
              day_types: day_types,
              daily_target: daily_target,
              progress_mode,
              checklist_items,
              effort_type: effort_type,
              effort_duration: effort_duration,
              agenda_duration_minutes: agenda_duration_minutes,
              agenda_placeable: agenda_placeable,
              tags: collectQuestTags("new") || undefined,
              ...focus,
            })
          });

          if (!response.ok) {
            const errBody = await response.json();
            throw new Error(errBody.detail || "Erreur de création");
          }
          showToast("Nouvelle quête forgée ! 🎯");

          document.getElementById("new-quest-name").value = "";
          document.getElementById("new-quest-desc").value = "";
          document.getElementById("new-quest-effort-type").value = "";
          document.getElementById("new-quest-duration").value = "60";
          document.getElementById("new-quest-unit").value = "";
          document.getElementById("new-quest-target").value = "";
          document.getElementById("new-quest-type").value = "binary";
          renderQuestChecklistEditor("new", []);
          setQuestProgressEditorMode("new", "standard");
          if (freqSelect) freqSelect.value = "daily";
          if (daysGroup) { daysGroup.style.display = "none"; daysGroup.querySelectorAll("input").forEach(cb => cb.checked = false); }
          newDayTypesGroup?.querySelectorAll("input").forEach(cb => { cb.checked = true; });
          updateFrequencyNote(freqSelect, newQuestFrequencyNote);
          await renderQuestTagEditor("new", []);

          closeQuestInlineForm();
          refreshAll();
        } catch (error) {
          console.error(error);
          showToast("Erreur: " + error.message, true);
        }
      });
    }
  }

  function setupNoTodosEvents() {
    const openNoTodoBtn = document.getElementById("open-notodo-inline-btn");
    const noTodoForm = document.getElementById("notodo-inline-form");
    const submitNoTodoBtn = document.getElementById("submit-notodo-btn");

    if (openNoTodoBtn && noTodoForm) {
      openNoTodoBtn.addEventListener("click", () => {
        if (noTodoForm.style.display === "none") {
          noTodoForm.style.display = "flex";
          openNoTodoBtn.textContent = "Fermer";
        } else {
          noTodoForm.style.display = "none";
          openNoTodoBtn.textContent = "+ Règle";
        }
      });
    }

    if (submitNoTodoBtn) {
      submitNoTodoBtn.addEventListener("click", async () => {
        const title = document.getElementById("new-notodo-title").value.trim();

        if (!title) {
          showToast("Veuillez donner un titre à la règle !", true);
          return;
        }

        try {
          const response = await fetch(`${API_BASE}/notodos`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              title: title
            })
          });

          if (!response.ok) throw new Error("Erreur de création");
          showToast("Nouvelle règle ajoutée ! 🚫");

          document.getElementById("new-notodo-title").value = "";

          noTodoForm.style.display = "none";
          openNoTodoBtn.textContent = "+ Règle";
          refreshAll();
        } catch (error) {
          console.error(error);
          showToast("Erreur lors de l'ajout de la règle", true);
        }
      });
    }
  }

  // ==============================================
  // SOFTSKILL PROGRESS TREE                       //
  // ==============================================
  let softskillsData = null; // cached response
  let activeSoftskillId = null;
  let activeBranchHighlight = null;
  let activeBranchKey = "global";

  async function fetchSoftskills() {
    try {
      const response = await fetch(`${API_BASE}/softskills`);
      if (!response.ok) throw new Error("Erreur softskills API");
      softskillsData = await response.json();

      const branchKeys = Object.keys(softskillsData.branches || {});
      if (activeBranchKey === null || (!branchKeys.includes(activeBranchKey) && activeBranchKey !== "global")) {
        activeBranchKey = "global";
      }

      renderSoftskillTree(softskillsData);
    } catch (error) {
      console.error(error);
      const container = document.getElementById("softskills-tree-container");
      if (container) {
        container.innerHTML = `<p style="color: var(--accent-red); text-align: center; padding: 2rem;">Erreur de chargement de l'arbre de compétences.</p>`;
      }
    }
  }

  function showSoftskillDrawerSection(sectionId, title = "🌳 Détail Softskill") {
    document.getElementById("softskill-detail-title").textContent = title;
    const sections = [
      "softskill-view-section",
      "softskill-edit-form",
      "softskill-create-form",
      "softskill-branch-form"
    ];
    sections.forEach(s => {
      const el = document.getElementById(s);
      if (el) el.style.display = s === sectionId ? "flex" : "none";
    });

    const overlay = document.getElementById("softskill-detail-overlay");
    const drawer = document.getElementById("softskill-detail-drawer");
    if (overlay) overlay.classList.add("open");
    if (drawer) drawer.classList.add("open");
  }

  function populateBranchSelect(selectId, activeBranch) {
    const select = document.getElementById(selectId);
    if (!select || !softskillsData) return;
    select.innerHTML = "";
    Object.keys(softskillsData.branches || {}).forEach(key => {
      const opt = document.createElement("option");
      opt.value = key;
      opt.textContent = key;
      if (key === activeBranch) opt.selected = true;
      select.appendChild(opt);
    });
  }

  function addDependencyRow(containerId, activeSkillId, selectedSkillId = "") {
    const container = document.getElementById(containerId);
    if (!container || !softskillsData) return;

    const row = document.createElement("div");
    row.className = "dependency-row";
    row.style.display = "flex";
    row.style.gap = "0.5rem";
    row.style.alignItems = "center";
    row.style.width = "100%";

    let activeBranch = "";
    if (containerId.includes("edit")) {
      const branchEl = document.getElementById("edit-softskill-branch");
      if (branchEl) activeBranch = branchEl.value;
    } else if (containerId.includes("create")) {
      const branchEl = document.getElementById("create-softskill-branch");
      if (branchEl) activeBranch = branchEl.value;
    }

    // Branch select
    const branchSelect = document.createElement("select");
    branchSelect.style.flex = "1";
    branchSelect.style.padding = "6px 10px";
    branchSelect.style.background = "rgba(255,255,255,0.03)";
    branchSelect.style.border = "1px solid var(--border-glass)";
    branchSelect.style.borderRadius = "8px";
    branchSelect.style.color = "var(--text-primary)";
    branchSelect.style.outline = "none";
    branchSelect.style.fontSize = "0.85rem";

    const defaultOpt = document.createElement("option");
    defaultOpt.value = "";
    defaultOpt.textContent = "-- Catégorie --";
    defaultOpt.style.background = "#18181b";
    branchSelect.appendChild(defaultOpt);

    const branches = Object.keys(softskillsData.branches || {});
    branches.forEach(branchKey => {
      if (containerId.includes("prereqs") && branchKey === activeBranch) {
        return;
      }
      if (containerId.includes("related") && branchKey === activeBranch) {
        return;
      }
      const opt = document.createElement("option");
      opt.value = branchKey;
      opt.textContent = branchKey;
      opt.style.background = "#18181b";
      branchSelect.appendChild(opt);
    });

    // Skill select
    const skillSelect = document.createElement("select");
    skillSelect.className = "skill-select";
    skillSelect.style.flex = "1";
    skillSelect.style.padding = "6px 10px";
    skillSelect.style.background = "rgba(255,255,255,0.03)";
    skillSelect.style.border = "1px solid var(--border-glass)";
    skillSelect.style.borderRadius = "8px";
    skillSelect.style.color = "var(--text-primary)";
    skillSelect.style.outline = "none";
    skillSelect.style.fontSize = "0.85rem";
    skillSelect.style.display = "none";

    const defaultSkillOpt = document.createElement("option");
    defaultSkillOpt.value = "";
    defaultSkillOpt.textContent = "-- Compétence --";
    defaultSkillOpt.style.background = "#18181b";
    skillSelect.appendChild(defaultSkillOpt);

    // Delete button
    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.textContent = "🗑️";
    deleteBtn.style.background = "rgba(239, 68, 68, 0.15)";
    deleteBtn.style.border = "1px solid rgba(239, 68, 68, 0.3)";
    deleteBtn.style.borderRadius = "8px";
    deleteBtn.style.color = "#ef4444";
    deleteBtn.style.cursor = "pointer";
    deleteBtn.style.padding = "6px 10px";
    deleteBtn.style.fontSize = "0.85rem";
    deleteBtn.style.height = "100%";
    deleteBtn.onclick = () => row.remove();

    row.appendChild(branchSelect);
    row.appendChild(skillSelect);
    row.appendChild(deleteBtn);
    container.appendChild(row);

    // Helper to populate skills select based on branch
    function populateSkills(branchKey, selectVal = "") {
      skillSelect.innerHTML = "";
      const defaultOpt = document.createElement("option");
      defaultOpt.value = "";
      defaultOpt.textContent = "-- Compétence --";
      defaultOpt.style.background = "#18181b";
      skillSelect.appendChild(defaultOpt);

      if (!branchKey) {
        skillSelect.style.display = "none";
        return;
      }

      const filtered = (softskillsData.skills || []).filter(
        s => s.branch === branchKey && s.id !== activeSkillId
      );

      filtered.forEach(s => {
        const opt = document.createElement("option");
        opt.value = s.id;
        opt.textContent = s.name;
        opt.style.background = "#18181b";
        if (s.id === selectVal) opt.selected = true;
        skillSelect.appendChild(opt);
      });

      skillSelect.style.display = "block";
    }

    branchSelect.addEventListener("change", (e) => {
      populateSkills(e.target.value);
    });

    if (selectedSkillId) {
      const matchingSkill = (softskillsData.skills || []).find(s => s.id === selectedSkillId);
      if (matchingSkill) {
        branchSelect.value = matchingSkill.branch;
        populateSkills(matchingSkill.branch, selectedSkillId);
      }
    }
  }

  function populateSkillDependencies(containerId, activeSkillId, selectedIds) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = "";
    selectedIds.forEach(id => {
      addDependencyRow(containerId, activeSkillId, id);
    });
  }

  function scrollToSkillNode(skillId) {
    const node = document.querySelector(`.hex-wrapper[data-id="${skillId}"], .softskill-node[data-id="${skillId}"]`);
    if (node) {
      node.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
      node.style.transform = "scale(1.15)";
      node.style.zIndex = "10";
      setTimeout(() => {
        node.style.transform = "";
        node.style.zIndex = "";
      }, 1000);
    }
  }

  function openBranchEdit(branchKey, branchVal) {
    showSoftskillDrawerSection("softskill-branch-form", "✏️ Modifier la branche");
    document.getElementById("edit-branch-old-key").value = branchKey;
    document.getElementById("edit-branch-key").value = branchKey;
    document.getElementById("edit-branch-color").value = branchVal.color || "#8b5cf6";
    document.getElementById("edit-branch-do-date").value = branchVal.do_date || "";
    document.getElementById("edit-branch-due-date").value = branchVal.due_date || "";
    document.getElementById("delete-branch-btn").style.display = "block";
  }

  function renderSoftskillTree(data) {
    const container = document.getElementById("softskills-tree-container");
    const svgEl = document.getElementById("softskills-svg-lines");
    if (!container || !svgEl) return;

    // Clear only dynamically created nodes, leaving the SVG element intact
    container.querySelectorAll(".softskill-node, .hex-wrapper, .tree-node, .tree-column, p").forEach(el => el.remove());
    if (svgEl) {
      svgEl.style.display = "none";
      svgEl.innerHTML = "";
    }

    const branches = data.branches || {};
    const skills = data.skills || [];

    const completedSet = new Set();
    skills.forEach(s => {
      if (s.progress && s.progress.completed) completedSet.add(s.id);
    });

    // Render left sidebar menu
    const selectorList = document.getElementById("softskills-selector-list");
    if (selectorList) {
      selectorList.innerHTML = "";

      // 1. Add "Vue Globale" item at the very top of selectorList
      const totalAllSkills = skills.length;
      const completedAllSkills = skills.filter(s => s.progress && s.progress.completed).length;
      const percentAll = totalAllSkills > 0 ? Math.round((completedAllSkills / totalAllSkills) * 100) : 0;

      const globalItem = document.createElement("div");
      globalItem.className = `goal-selector-item ${activeBranchKey === "global" ? 'active' : ''}`;
      globalItem.innerHTML = `
        <div class="goal-selector-title">
          <span style="display: flex; align-items: center; gap: 0.5rem;">
            <span class="softskill-branch-dot" style="background-color: var(--accent-cyan); box-shadow: 0 0 6px var(--accent-cyan)66;"></span>
            Vue Globale
          </span>
          <span style="font-size: 0.75rem; color: var(--accent-cyan); font-weight: 700;">${percentAll}%</span>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.2rem;">
          <span class="goal-selector-meta">${totalAllSkills} compétences au total</span>
        </div>
        <div class="goal-selector-progress-track" style="margin-top: 0.4rem;">
          <div class="goal-selector-progress-fill" style="width: ${percentAll}%; background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple));"></div>
        </div>
      `;
      globalItem.addEventListener("click", () => {
        activeBranchKey = "global";
        document.querySelectorAll("#softskills-selector-list .goal-selector-item").forEach(el => el.classList.remove("active"));
        globalItem.classList.add("active");
        renderSoftskillTree(data);
      });
      selectorList.appendChild(globalItem);

      Object.entries(branches).forEach(([branchKey, branchVal]) => {
        const branchColor = branchVal.color || "#8b5cf6";
        const branchSkills = skills.filter(s => s.branch === branchKey);

        const totalSkills = branchSkills.length;
        const completedSkills = branchSkills.filter(s => s.progress && s.progress.completed).length;
        const percent = totalSkills > 0 ? Math.round((completedSkills / totalSkills) * 100) : 0;

        let bDateList = [];
        if (branchVal.do_date) {
          const parts = branchVal.do_date.split("-");
          bDateList.push(`📅 ${parts.length === 3 ? `${parts[2]}/${parts[1]}` : branchVal.do_date}`);
        }
        if (branchVal.due_date) {
          const parts = branchVal.due_date.split("-");
          bDateList.push(`🚨 ${parts.length === 3 ? `${parts[2]}/${parts[1]}` : branchVal.due_date}`);
        }
        const bDateStr = bDateList.length > 0 ? ` • ${bDateList.join(" ")}` : "";

        const item = document.createElement("div");
        item.className = `goal-selector-item ${branchKey === activeBranchKey ? 'active' : ''}`;
        item.innerHTML = `
          <div class="goal-selector-title">
            <span style="display: flex; align-items: center; gap: 0.5rem;">
              <span class="softskill-branch-dot" style="background-color: ${branchColor}; box-shadow: 0 0 6px ${branchColor}66;"></span>
              ${branchKey}
            </span>
            <span style="font-size: 0.75rem; color: var(--accent-cyan); font-weight: 700;">${percent}%</span>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.2rem;">
            <span class="goal-selector-meta">${totalSkills} compétence${totalSkills > 1 ? 's' : ''}${bDateStr}</span>
            <button class="softskill-branch-edit-btn" data-branch="${branchKey}" style="margin: 0; padding: 2px 6px; font-size: 0.75rem;">✏️</button>
          </div>
          <div class="goal-selector-progress-track" style="margin-top: 0.4rem;">
            <div class="goal-selector-progress-fill" style="width: ${percent}%; background: ${branchColor};"></div>
          </div>
        `;

        item.addEventListener("click", (e) => {
          if (e.target.closest(".softskill-branch-edit-btn")) {
            e.stopPropagation();
            openBranchEdit(branchKey, branchVal);
            return;
          }
          activeBranchKey = branchKey;
          document.querySelectorAll("#softskills-selector-list .goal-selector-item").forEach(el => el.classList.remove("active"));
          item.classList.add("active");
          renderSoftskillTree(data);
        });

        selectorList.appendChild(item);
      });
    }

    if (!activeBranchKey) {
      container.insertAdjacentHTML("beforeend", `<p style="color: var(--text-muted); text-align: center; margin: auto; padding: 3rem 0;">Créez ou sélectionnez une branche à gauche.</p>`);
      return;
    }

    if (activeBranchKey === "global") {
      // 2. Render absolute coordinate-based layout for all skills
      container.className = "skill-tree-absolute-container";
      container.style.position = "relative";
      container.style.width = "100%";
      container.style.display = "block";
      container.style.gap = "";
      container.style.alignItems = "";
      container.style.justifyContent = "";
      container.style.overflow = "auto";

      let maxX = 800;
      let maxY = 500;
      skills.forEach(s => {
        if (s.x > maxX) maxX = s.x;
        if (s.y > maxY) maxY = s.y;
      });
      container.style.minWidth = `${maxX + 220}px`;
      container.style.minHeight = `${maxY + 150}px`;

      if (svgEl) {
        svgEl.style.display = "block";
        svgEl.style.width = "100%";
        svgEl.style.height = "100%";
      }

      let nodesHTML = "";
      skills.forEach(s => {
        const branchVal = branches[s.branch] || {};
        const branchColor = branchVal.color || "#8b5cf6";
        const isCompleted = s.progress && s.progress.completed;
        const prereqsMet = (s.prerequisites || []).every(pid => {
          const prereqSkill = skills.find(sk => sk.id === pid);
          return prereqSkill && prereqSkill.progress && prereqSkill.progress.completed;
        });

        let stateClass = "locked-node";
        if (isCompleted) stateClass = "completed-node";
        else if (prereqsMet) stateClass = "unlocked-node";

        const doneIcon = isCompleted ? "✓" : "✔";
        const doneCompletedClass = isCompleted ? "is-completed" : "";

        nodesHTML += `
          <div class="hex-wrapper ${stateClass}" data-id="${s.id}" style="position: absolute; left: ${s.x}px; top: ${s.y}px; --hex-border-color: ${isCompleted || prereqsMet ? branchColor : 'rgba(255,255,255,0.15)'};">
            <span class="hex-action-edit action-edit-softskill-icon" data-id="${s.id}" title="Modifier">✏️</span>
            <button class="hex-action-done action-complete-softskill ${doneCompletedClass}" data-id="${s.id}" title="${isCompleted ? 'Complété' : 'Valider'}">${doneIcon}</button>
            <div class="tree-node" data-id="${s.id}">
              <span class="tree-node-title">${s.name}</span>
            </div>
          </div>
        `;
      });
      container.insertAdjacentHTML("beforeend", nodesHTML);

      if (svgEl) {
        let svgLines = "";
        skills.forEach(s => {
          const sX = s.x + 50;
          const sY = s.y + 56;

          (s.prerequisites || []).forEach(pid => {
            const parent = skills.find(sk => sk.id === pid);
            if (parent) {
              const pX = parent.x + 50;
              const pY = parent.y + 56;
              const parentBranchColor = (branches[parent.branch] || {}).color || "#8b5cf6";
              const lineCompleted = (s.progress && s.progress.completed) && (parent.progress && parent.progress.completed);
              const strokeColor = lineCompleted ? parentBranchColor : (s.progress && s.progress.completed ? parentBranchColor : "rgba(255, 255, 255, 0.15)");
              const strokeWidth = lineCompleted ? 3 : 2;

              svgLines += `<line x1="${pX}" y1="${pY}" x2="${sX}" y2="${sY}" stroke="${strokeColor}" stroke-width="${strokeWidth}" />`;
            }
          });

          (s.related || []).forEach(rid => {
            const rel = skills.find(sk => sk.id === rid);
            if (rel) {
              if (s.id < rel.id) {
                const rX = rel.x + 50;
                const rY = rel.y + 56;
                const strokeColor = "rgba(255, 255, 255, 0.12)";
                svgLines += `<line x1="${sX}" y1="${sY}" x2="${rX}" y2="${rY}" stroke="${strokeColor}" stroke-dasharray="4 4" stroke-width="1.5" />`;
              }
            }
          });
        });
        svgEl.innerHTML = svgLines;
      }
    } else {
      // 3. Render branch column-based layout
      const branchSkills = skills.filter(s => s.branch === activeBranchKey);
      const branchVal = branches[activeBranchKey] || {};
      const branchColor = branchVal.color || "#8b5cf6";

      container.className = "skill-tree-scroll-container";
      container.style.minWidth = "";
      container.style.minHeight = "";
      container.style.width = "100%";
      container.style.height = "auto";
      container.style.display = "flex";
      container.style.gap = "4rem";
      container.style.alignItems = "center";
      container.style.justifyContent = "flex-start";
      container.style.overflowX = "auto";
      container.style.position = "relative";

      const columnsMap = new Map();
      branchSkills.forEach(s => {
        const order = s.execution_order || 1;
        if (!columnsMap.has(order)) {
          columnsMap.set(order, []);
        }
        columnsMap.get(order).push(s);
      });

      const sortedOrders = Array.from(columnsMap.keys()).sort((a, b) => a - b);

      let columnsHTML = "";
      sortedOrders.forEach(order => {
        const colSkills = columnsMap.get(order);
        let nodesHTML = "";
        colSkills.forEach(s => {
          const isCompleted = s.progress && s.progress.completed;
          const prereqsMet = (s.prerequisites || []).every(pid => {
            const prereqSkill = skills.find(sk => sk.id === pid);
            return prereqSkill && prereqSkill.progress && prereqSkill.progress.completed;
          });

          let stateClass = "locked-node";
          if (isCompleted) stateClass = "completed-node";
          else if (prereqsMet) stateClass = "unlocked-node";

          const doneIcon = isCompleted ? "✓" : "✔";
          const doneCompletedClass = isCompleted ? "is-completed" : "";

          nodesHTML += `
            <div class="hex-wrapper ${stateClass}" data-id="${s.id}" style="--hex-border-color: ${isCompleted || prereqsMet ? branchColor : 'rgba(255,255,255,0.15)'};">
              <span class="hex-action-edit action-edit-softskill-icon" data-id="${s.id}" title="Modifier">✏️</span>
              <button class="hex-action-done action-complete-softskill ${doneCompletedClass}" data-id="${s.id}" title="${isCompleted ? 'Complété' : 'Valider'}">${doneIcon}</button>
              <div class="tree-node" data-id="${s.id}">
                <span class="tree-node-title"><span style="color: var(--text-muted); font-size: 0.7em; display: block; margin-bottom: 0.15em;">[Étape ${s.execution_order || 1}]</span>${s.name}</span>
              </div>
            </div>
          `;
        });

        columnsHTML += `
          <div class="tree-column">
            ${nodesHTML}
          </div>
        `;

      });

      const totalSkills = branchSkills.length;
      const completedSkills = branchSkills.filter(s => s.progress && s.progress.completed).length;
      const percent = totalSkills > 0 ? Math.round((completedSkills / totalSkills) * 100) : 0;
      const branchCompleted = totalSkills > 0 && completedSkills === totalSkills;

      let branchDateInfo = [];
      if (branchVal.do_date) {
        const parts = branchVal.do_date.split("-");
        branchDateInfo.push(`📅 ${parts.length === 3 ? `${parts[2]}/${parts[1]}` : branchVal.do_date}`);
      }
      if (branchVal.due_date) {
        const parts = branchVal.due_date.split("-");
        branchDateInfo.push(`🚨 ${parts.length === 3 ? `${parts[2]}/${parts[1]}` : branchVal.due_date}`);
      }
      const branchDateHtml = branchDateInfo.length > 0
        ? `<div style="font-size: 0.62rem; color: var(--text-muted); margin-top: 0.15rem; display: flex; gap: 0.3rem; justify-content: center;">${branchDateInfo.join(" ")}</div>`
        : "";

      columnsHTML += `
        <div class="tree-column">
          <div class="hex-wrapper ${branchCompleted ? 'completed-node' : 'unlocked-node'}" style="--hex-border-color: ${branchColor}; width: 120px; height: 134px;">
            <div class="tree-node">
              <span class="substep-tag" style="background: ${branchColor}22; color: ${branchColor}; font-size: 0.55rem; padding: 2px 6px; border-radius: 4px;">BRANCHE MAÎTRESSE</span>
              <span class="tree-node-title" style="font-size: 0.7rem; color: ${branchColor};">${activeBranchKey.toUpperCase()}</span>
              ${branchDateHtml}
              <span class="tree-node-desc" style="font-size: 0.72rem;">${percent}% complété</span>
            </div>
          </div>
        </div>
      `;

      container.insertAdjacentHTML("beforeend", columnsHTML);
    }

    // Attach click listeners to cards
    container.querySelectorAll(".hex-wrapper").forEach(node => {
      node.addEventListener("click", (e) => {
        if (e.target.closest(".action-complete-softskill") || e.target.closest(".action-edit-softskill-icon") || e.target.closest(".tree-node-btn")) return;
        const skillId = node.getAttribute("data-id");
        if (skillId) {
          const skill = skills.find(s => s.id === skillId);
          if (skill) openSoftskillDetail(skill);
        }
      });
    });

    // Attach edit icon listeners
    container.querySelectorAll(".action-edit-softskill-icon").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const skillId = btn.getAttribute("data-id");
        const skill = skills.find(s => s.id === skillId);
        if (skill) {
          showSoftskillDrawerSection("softskill-edit-form", "✏️ Modifier le Softskill");
          document.getElementById("edit-softskill-id-hidden").value = skill.id;
          document.getElementById("edit-softskill-name").value = skill.name;
          document.getElementById("edit-softskill-desc").value = skill.description;
          populateBranchSelect("edit-softskill-branch", skill.branch);
          populateSkillDependencies("edit-softskill-prereqs-container", skill.id, skill.prerequisites || []);
          populateSkillDependencies("edit-softskill-related-container", skill.id, skill.related || []);
          document.getElementById("edit-softskill-execution-order").value = skill.execution_order || 1;
        }
      });
    });

    // Attach completion action listeners
    container.querySelectorAll(".action-complete-softskill").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const skillId = btn.getAttribute("data-id");
        const skill = skills.find(s => s.id === skillId);
        if (!skill) return;
        const isCurrentlyCompleted = skill.progress && skill.progress.completed;
        try {
          const response = await fetch(`${API_BASE}/softskills/${skillId}/complete`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-User-ID": localStorage.getItem("user_id") || "1"
            },
            body: JSON.stringify({ completed: !isCurrentlyCompleted })
          });
          if (!response.ok) {
            const errData = await response.json();
            showToast(errData.detail || "Prérequis non remplis", true);
            return;
          }
          showToast(isCurrentlyCompleted ? "Softskill réinitialisé" : "Softskill complété ! 🎉");
          await fetchSoftskills();
        } catch (error) {
          console.error(error);
          showToast("Erreur lors de la mise à jour", true);
        }
      });
    });
  }

  // Detail modal logic
  function openSoftskillDetail(skill) {
    activeSoftskillId = skill.id;
    showSoftskillDrawerSection("softskill-view-section", `🌳 ${skill.name}`);

    const branches = softskillsData ? softskillsData.branches : {};
    const branch = branches[skill.branch] || {};
    const progress = skill.progress || {};
    const isCompleted = progress.completed || false;

    document.getElementById("softskill-detail-desc").textContent = skill.description;
    document.getElementById("softskill-detail-branch").innerHTML = `<strong>Branche :</strong> <span style="color: ${branch.color || "#fff"};">${skill.branch}</span>`;

    const prereqNames = (skill.prerequisites || []).map(pid => {
      const s = (softskillsData.skills || []).find(sk => sk.id === pid);
      return s ? s.name : pid;
    });
    document.getElementById("softskill-detail-prereqs").innerHTML = prereqNames.length > 0
      ? `<strong>Prérequis :</strong> ${prereqNames.join(", ")}`
      : `<strong>Prérequis :</strong> Aucun`;

    const relatedNames = (skill.related || []).map(rid => {
      const s = (softskillsData.skills || []).find(sk => sk.id === rid);
      return s ? s.name : rid;
    });
    document.getElementById("softskill-detail-related").innerHTML = relatedNames.length > 0
      ? `<strong>En relation avec :</strong> ${relatedNames.join(", ")}`
      : "";

    const statusEl = document.getElementById("softskill-detail-status");
    if (isCompleted) {
      statusEl.innerHTML = `<span style="color: var(--accent-green);">✅ Complété</span>`;
    } else {
      const prereqsMet = (skill.prerequisites || []).every(pid => {
        const s = (softskillsData.skills || []).find(sk => sk.id === pid);
        return s && s.progress && s.progress.completed;
      });
      statusEl.innerHTML = prereqsMet
        ? `<span style="color: var(--accent-cyan);">🔓 Disponible</span>`
        : `<span style="color: var(--text-muted);">🔒 Verrouillé — prérequis manquants</span>`;
    }

    document.getElementById("softskill-test-input").value = progress.success_criteria_test || "";

    const completeBtn = document.getElementById("toggle-softskill-complete-btn");
    if (isCompleted) {
      completeBtn.textContent = "↩️ Réinitialiser";
      completeBtn.style.background = "rgba(239, 68, 68, 0.15)";
      completeBtn.style.borderColor = "rgba(239, 68, 68, 0.5)";
      completeBtn.style.color = "#ef4444";
    } else {
      completeBtn.textContent = "✅ Marquer comme Complété";
      completeBtn.style.background = "";
      completeBtn.style.borderColor = "";
      completeBtn.style.color = "";
    }

    // Bind Edit Button
    const editBtn = document.getElementById("edit-softskill-btn");
    if (editBtn) {
      editBtn.onclick = () => {
        showSoftskillDrawerSection("softskill-edit-form", "✏️ Modifier le Softskill");
        document.getElementById("edit-softskill-id-hidden").value = skill.id;
        document.getElementById("edit-softskill-name").value = skill.name;
        document.getElementById("edit-softskill-desc").value = skill.description;
        populateBranchSelect("edit-softskill-branch", skill.branch);
        populateSkillDependencies("edit-softskill-prereqs-container", skill.id, skill.prerequisites || []);
        populateSkillDependencies("edit-softskill-related-container", skill.id, skill.related || []);
        document.getElementById("edit-softskill-execution-order").value = skill.execution_order || 1;
        document.getElementById("edit-softskill-validation-criterion").value = skill.success_criteria_test || "";
      };
    }
  }

  function closeSoftskillDetail() {
    const overlay = document.getElementById("softskill-detail-overlay");
    const drawer = document.getElementById("softskill-detail-drawer");
    if (overlay) overlay.classList.remove("open");
    if (drawer) drawer.classList.remove("open");
    activeSoftskillId = null;

    // Clear sidebar highlighting if not highlighting branch
    document.querySelectorAll(".softskill-sidebar-skill-item").forEach(i => i.classList.remove("active"));
  }

  // Bind static UI actions
  const closeSoftskillBtn = document.getElementById("close-softskill-detail-btn");
  if (closeSoftskillBtn) closeSoftskillBtn.addEventListener("click", closeSoftskillDetail);

  const softskillOverlay = document.getElementById("softskill-detail-overlay");
  if (softskillOverlay) softskillOverlay.addEventListener("click", closeSoftskillDetail);

  // Edit skill Cancel
  const cancelEditSkillBtn = document.getElementById("cancel-edit-softskill-btn");
  if (cancelEditSkillBtn) cancelEditSkillBtn.addEventListener("click", () => showSoftskillDrawerSection("softskill-view-section"));

  // Create skill Cancel
  const cancelCreateSkillBtn = document.getElementById("cancel-create-softskill-btn");
  if (cancelCreateSkillBtn) cancelCreateSkillBtn.addEventListener("click", closeSoftskillDetail);

  // Branch Cancel
  const cancelBranchBtn = document.getElementById("cancel-branch-btn");
  if (cancelBranchBtn) cancelBranchBtn.addEventListener("click", closeSoftskillDetail);

  // Bind creation buttons
  const addBranchBtn = document.getElementById("add-softskill-branch-btn");
  if (addBranchBtn) {
    addBranchBtn.addEventListener("click", () => {
      showSoftskillDrawerSection("softskill-branch-form", "✨ Forger une branche");
      document.getElementById("edit-branch-old-key").value = "";
      document.getElementById("edit-branch-key").value = "";
      document.getElementById("edit-branch-color").value = "#8b5cf6";
      const paleColorEl = document.getElementById("edit-branch-pale-color");
      if (paleColorEl) paleColorEl.value = "#dddddd";
      document.getElementById("edit-branch-do-date").value = "";
      document.getElementById("edit-branch-due-date").value = "";
      document.getElementById("delete-branch-btn").style.display = "none";
    });
  }

  const addNodeBtn = document.getElementById("add-softskill-node-btn");
  if (addNodeBtn) {
    addNodeBtn.addEventListener("click", () => {
      showSoftskillDrawerSection("softskill-create-form", "✨ Forger une compétence");
      document.getElementById("create-softskill-id").value = "";
      document.getElementById("create-softskill-name").value = "";
      document.getElementById("create-softskill-desc").value = "";
      populateBranchSelect("create-softskill-branch", activeBranchKey || "");
      populateSkillDependencies("create-softskill-prereqs-container", "", []);
      populateSkillDependencies("create-softskill-related-container", "", []);
      document.getElementById("create-softskill-execution-order").value = "1";
      document.getElementById("create-softskill-validation-criterion").value = "";
    });
  }

  // Bind plus buttons for dynamic dependency rows
  const addEditPrereqBtn = document.getElementById("add-edit-prereq-btn");
  if (addEditPrereqBtn) {
    addEditPrereqBtn.addEventListener("click", () => {
      const activeSkillId = document.getElementById("edit-softskill-id-hidden").value;
      addDependencyRow("edit-softskill-prereqs-container", activeSkillId);
    });
  }

  const addEditRelatedBtn = document.getElementById("add-edit-related-btn");
  if (addEditRelatedBtn) {
    addEditRelatedBtn.addEventListener("click", () => {
      const activeSkillId = document.getElementById("edit-softskill-id-hidden").value;
      addDependencyRow("edit-softskill-related-container", activeSkillId);
    });
  }

  const addCreatePrereqBtn = document.getElementById("add-create-prereq-btn");
  if (addCreatePrereqBtn) {
    addCreatePrereqBtn.addEventListener("click", () => {
      addDependencyRow("create-softskill-prereqs-container", "");
    });
  }

  const addCreateRelatedBtn = document.getElementById("add-create-related-btn");
  if (addCreateRelatedBtn) {
    addCreateRelatedBtn.addEventListener("click", () => {
      addDependencyRow("create-softskill-related-container", "");
    });
  }

  // Edit form submit
  const editSkillForm = document.getElementById("softskill-edit-form");
  if (editSkillForm) {
    editSkillForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const skillId = document.getElementById("edit-softskill-id-hidden").value;
      const name = document.getElementById("edit-softskill-name").value.trim();
      const desc = document.getElementById("edit-softskill-desc").value.trim();
      const branch = document.getElementById("edit-softskill-branch").value;
      const order = parseInt(document.getElementById("edit-softskill-execution-order").value) || 1;
      const validationCriterion = document.getElementById("edit-softskill-validation-criterion").value.trim();

      const prereqs = Array.from(document.querySelectorAll("#edit-softskill-prereqs-container .skill-select"))
        .map(select => select.value)
        .filter(val => val !== "");
      const related = Array.from(document.querySelectorAll("#edit-softskill-related-container .skill-select"))
        .map(select => select.value)
        .filter(val => val !== "");

      // Check that prerequisites are not in the same branch
      const sameBranchPrereqs = prereqs.filter(pid => {
        const s = (softskillsData.skills || []).find(sk => sk.id === pid);
        return s && s.branch === branch;
      });
      if (sameBranchPrereqs.length > 0) {
        const invalidNames = sameBranchPrereqs.map(pid => {
          const s = (softskillsData.skills || []).find(sk => sk.id === pid);
          return s ? s.name : pid;
        }).join(", ");
        showToast(`Impossible d'enregistrer : la compétence prérequise "${invalidNames}" ne peut pas être dans la même branche (${branch}).`, true);
        return;
      }

      // Check that related skills are not in the same branch
      const sameBranchRelated = related.filter(rid => {
        const s = (softskillsData.skills || []).find(sk => sk.id === rid);
        return s && s.branch === branch;
      });
      if (sameBranchRelated.length > 0) {
        const invalidNames = sameBranchRelated.map(rid => {
          const s = (softskillsData.skills || []).find(sk => sk.id === rid);
          return s ? s.name : rid;
        }).join(", ");
        showToast(`Impossible d'enregistrer : la compétence "${invalidNames}" est dans la même branche (${branch}) que la compétence en cours d'édition.`, true);
        return;
      }

      try {
        const resp = await fetch(`${API_BASE}/softskills/skills/${skillId}`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            "X-User-ID": localStorage.getItem("user_id") || "1"
          },
          body: JSON.stringify({ name, description: desc, branch, prerequisites: prereqs, related, execution_order: order, success_criteria_test: validationCriterion })
        });
        if (!resp.ok) {
          const err = await resp.json();
          throw new Error(err.detail || "Erreur de modification");
        }
        showToast("Softskill modifié avec succès ! ✏️");
        closeSoftskillDetail();
        await fetchSoftskills();
      } catch (err) {
        showToast(err.message, true);
      }
    });
  }

  // Delete skill button
  const deleteSkillBtn = document.getElementById("delete-softskill-btn");
  if (deleteSkillBtn) {
    deleteSkillBtn.addEventListener("click", async () => {
      const skillId = document.getElementById("edit-softskill-id-hidden").value;
      if (!skillId) return;
      if (!confirm("Voulez-vous vraiment détruire ce softskill et toute sa progression ?")) return;
      try {
        const resp = await fetch(`${API_BASE}/softskills/skills/${skillId}`, {
          method: "DELETE",
          headers: { "X-User-ID": localStorage.getItem("user_id") || "1" }
        });
        if (!resp.ok) throw new Error("Erreur de suppression");
        showToast("Softskill détruit ! 🗑️");
        closeSoftskillDetail();
        await fetchSoftskills();
      } catch (err) {
        showToast(err.message, true);
      }
    });
  }

  // Create form submit
  const createSkillForm = document.getElementById("softskill-create-form");
  if (createSkillForm) {
    createSkillForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const name = document.getElementById("create-softskill-name").value.trim();
      const desc = document.getElementById("create-softskill-desc").value.trim();
      const branch = document.getElementById("create-softskill-branch").value;
      const order = parseInt(document.getElementById("create-softskill-execution-order").value) || 1;
      const validationCriterion = document.getElementById("create-softskill-validation-criterion").value.trim();

      // Auto-generate unique slug ID
      const skillId = name
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "") // Remove accents
        .replace(/[^a-z0-9_]/g, "_")    // Replace non-alphanumeric with _
        .replace(/__+/g, "_")            // Replace multiple underscores with one
        .replace(/^_+|_+$/g, "");        // Trim underscores

      if (!skillId) {
        showToast("Le nom de la compétence est invalide pour générer un identifiant.", true);
        return;
      }

      const prereqs = Array.from(document.querySelectorAll("#create-softskill-prereqs-container .skill-select"))
        .map(select => select.value)
        .filter(val => val !== "");
      const related = Array.from(document.querySelectorAll("#create-softskill-related-container .skill-select"))
        .map(select => select.value)
        .filter(val => val !== "");

      // Check that prerequisites are not in the same branch
      const sameBranchPrereqs = prereqs.filter(pid => {
        const s = (softskillsData.skills || []).find(sk => sk.id === pid);
        return s && s.branch === branch;
      });
      if (sameBranchPrereqs.length > 0) {
        const invalidNames = sameBranchPrereqs.map(pid => {
          const s = (softskillsData.skills || []).find(sk => sk.id === pid);
          return s ? s.name : pid;
        }).join(", ");
        showToast(`Impossible de forger : la compétence prérequise "${invalidNames}" ne peut pas être dans la même branche (${branch}).`, true);
        return;
      }

      // Check that related skills are not in the same branch
      const sameBranchRelated = related.filter(rid => {
        const s = (softskillsData.skills || []).find(sk => sk.id === rid);
        return s && s.branch === branch;
      });
      if (sameBranchRelated.length > 0) {
        const invalidNames = sameBranchRelated.map(rid => {
          const s = (softskillsData.skills || []).find(sk => sk.id === rid);
          return s ? s.name : rid;
        }).join(", ");
        showToast(`Impossible de forger : la compétence "${invalidNames}" est dans la même branche (${branch}) que la compétence en cours de création.`, true);
        return;
      }

      try {
        const resp = await fetch(`${API_BASE}/softskills/skills`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-User-ID": localStorage.getItem("user_id") || "1"
          },
          body: JSON.stringify({ id: skillId, name, description: desc, branch, prerequisites: prereqs, related, execution_order: order, success_criteria_test: validationCriterion })
        });
        if (!resp.ok) {
          const err = await resp.json();
          throw new Error(err.detail || "Erreur de création");
        }
        showToast("Nouveau softskill forgé ! 🌳");
        closeSoftskillDetail();
        await fetchSoftskills();
      } catch (err) {
        showToast(err.message, true);
      }
    });
  }

  // Branch form submit
  const branchForm = document.getElementById("softskill-branch-form");
  if (branchForm) {
    branchForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const oldKey = document.getElementById("edit-branch-old-key").value;
      const newKey = document.getElementById("edit-branch-key").value.trim();
      const color = document.getElementById("edit-branch-color").value;
      const paleColor = getPaleColor(color);
      const doDate = document.getElementById("edit-branch-do-date").value || null;
      const dueDate = document.getElementById("edit-branch-due-date").value || null;

      try {
        let resp;
        if (oldKey) {
          resp = await fetch(`${API_BASE}/softskills/branches/${oldKey}`, {
            method: "PUT",
            headers: {
              "Content-Type": "application/json",
              "X-User-ID": localStorage.getItem("user_id") || "1"
            },
            body: JSON.stringify({ new_key: newKey, color, pale_color: paleColor, do_date: doDate, due_date: dueDate })
          });
        } else {
          resp = await fetch(`${API_BASE}/softskills/branches`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-User-ID": localStorage.getItem("user_id") || "1"
            },
            body: JSON.stringify({ key: newKey, color, pale_color: paleColor, do_date: doDate, due_date: dueDate })
          });
        }
        if (!resp.ok) {
          const err = await resp.json();
          throw new Error(err.detail || "Erreur sur la branche");
        }
        showToast(oldKey ? "Branche modifiée avec succès !" : "Nouvelle branche créée !");
        closeSoftskillDetail();
        await fetchSoftskills();
      } catch (err) {
        showToast(err.message, true);
      }
    });
  }

  // Delete branch button
  const deleteBranchBtn = document.getElementById("delete-branch-btn");
  if (deleteBranchBtn) {
    deleteBranchBtn.addEventListener("click", async () => {
      const branchKey = document.getElementById("edit-branch-old-key").value;
      if (!branchKey) return;
      if (!confirm(`ATTENTION: Supprimer la branche '${branchKey}' supprimera TOUS ses softskills associés et leur progression ! Continuer ?`)) return;
      try {
        const resp = await fetch(`${API_BASE}/softskills/branches/${branchKey}`, {
          method: "DELETE",
          headers: { "X-User-ID": localStorage.getItem("user_id") || "1" }
        });
        if (!resp.ok) throw new Error("Erreur de suppression de la branche");
        showToast("Branche et ses compétences supprimées.");
        closeSoftskillDetail();
        await fetchSoftskills();
      } catch (err) {
        showToast(err.message, true);
      }
    });
  }

  // Save success test
  const saveTestBtn = document.getElementById("save-softskill-test-btn");
  if (saveTestBtn) {
    saveTestBtn.addEventListener("click", async () => {
      if (!activeSoftskillId) return;
      const testVal = document.getElementById("softskill-test-input").value.trim();
      try {
        const response = await fetch(`${API_BASE}/softskills/${activeSoftskillId}/test`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-User-ID": localStorage.getItem("user_id") || "1"
          },
          body: JSON.stringify({ success_criteria_test: testVal })
        });
        if (!response.ok) throw new Error("Erreur de sauvegarde");
        showToast("Test de succès mis à jour");
        await fetchSoftskills();
      } catch (error) {
        console.error(error);
        showToast("Erreur lors de la sauvegarde", true);
      }
    });
  }

  // Toggle completion
  const toggleCompleteBtn = document.getElementById("toggle-softskill-complete-btn");
  if (toggleCompleteBtn) {
    toggleCompleteBtn.addEventListener("click", async () => {
      if (!activeSoftskillId) return;
      const skill = (softskillsData.skills || []).find(s => s.id === activeSoftskillId);
      if (!skill) return;
      const isCurrentlyCompleted = skill.progress && skill.progress.completed;

      try {
        const response = await fetch(`${API_BASE}/softskills/${activeSoftskillId}/complete`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-User-ID": localStorage.getItem("user_id") || "1"
          },
          body: JSON.stringify({ completed: !isCurrentlyCompleted })
        });
        if (!response.ok) {
          const errData = await response.json();
          showToast(errData.detail || "Prérequis non remplis", true);
          return;
        }
        showToast(isCurrentlyCompleted ? "Softskill réinitialisé" : "Softskill complété ! 🎉");
        closeSoftskillDetail();
        await fetchSoftskills();
      } catch (error) {
        console.error(error);
        showToast("Erreur lors de la mise à jour", true);
      }
    });
  }

  // ==============================================
  // REWARD SHOP (BOUTIQUE) ACTIONS & RENDERING
  // ==============================================

  async function populateRewardFormDropdowns() {
    try {
      // 1. Populate softskills dropdown
      const softskillsResp = await fetch(`${API_BASE}/softskills`);
      if (softskillsResp.ok) {
        const data = await softskillsResp.json();
        const skills = data.skills || [];
        const select = document.getElementById("reward-form-softskill");
        if (select) {
          select.innerHTML = '<option value="">Aucun prérequis</option>';
          skills.forEach(s => {
            const opt = document.createElement("option");
            opt.value = s.id;
            opt.textContent = `${s.name} (${s.branch})`;
            select.appendChild(opt);
          });
        }
      }

      // 2. Populate goals dropdown
      const goalsResp = await fetch(`${API_BASE}/goals`);
      if (goalsResp.ok) {
        const goals = await goalsResp.json();
        const select = document.getElementById("reward-form-goal");
        if (select) {
          select.innerHTML = '<option value="">Aucun prérequis</option>';
          goals.forEach(g => {
            const opt = document.createElement("option");
            opt.value = g.id;
            opt.textContent = g.title;
            select.appendChild(opt);
          });
        }
      }
    } catch (err) {
      console.error("Error populating reward form dropdowns:", err);
    }
  }

  async function openRewardDrawer(reward = null) {
    const drawer = document.getElementById("reward-drawer");
    const overlay = document.getElementById("drawer-overlay");
    if (!drawer || !overlay) return;

    await populateRewardFormDropdowns();

    drawer.classList.add("open");
    overlay.classList.add("open");

    const drawerTitle = document.getElementById("reward-drawer-title");
    const deleteBtn = document.getElementById("delete-reward-btn");

    const categorySelect = document.getElementById("reward-form-category");
    const costInput = document.getElementById("reward-form-cost");
    const oneTimeCheckbox = document.getElementById("reward-form-onetime");

    function updateCategoryDisabledStates() {
      if (!categorySelect) return;
      const val = categorySelect.value;
      const costGrid = document.getElementById("reward-form-cost-grid");
      const softskillGroup = document.getElementById("reward-form-softskill-group");
      const goalGroup = document.getElementById("reward-form-goal-group");

      if (val === "allostasis_daily" || val === "allostasis_weekly") {
        costInput.value = "0";
        costInput.disabled = true;
        oneTimeCheckbox.checked = false;
        oneTimeCheckbox.disabled = true;

        if (costGrid) costGrid.style.display = "none";
        if (softskillGroup) {
          softskillGroup.style.display = "none";
          const ssSelect = document.getElementById("reward-form-softskill");
          if (ssSelect) ssSelect.value = "";
        }
        if (goalGroup) {
          goalGroup.style.display = "none";
          const gSelect = document.getElementById("reward-form-goal");
          if (gSelect) gSelect.value = "";
        }
      } else {
        costInput.disabled = false;
        oneTimeCheckbox.disabled = false;

        if (costGrid) costGrid.style.display = "grid";
        if (softskillGroup) softskillGroup.style.display = "block";
        if (goalGroup) goalGroup.style.display = "block";
      }
    }

    if (reward) {
      drawerTitle.textContent = "✏️ Modifier la Récompense";
      deleteBtn.style.display = "block";

      document.getElementById("reward-form-id").value = reward.id;
      document.getElementById("reward-form-title").value = reward.title;
      document.getElementById("reward-form-desc").value = reward.description || "";
      document.getElementById("reward-form-cost").value = reward.gold_cost;
      document.getElementById("reward-form-onetime").checked = reward.is_one_time || false;
      document.getElementById("reward-form-softskill").value = reward.required_softskill_id || "";
      document.getElementById("reward-form-goal").value = reward.required_goal_id || "";
      if (categorySelect) categorySelect.value = reward.category || "regular";
    } else {
      drawerTitle.textContent = "🏪 Créer une Récompense";
      deleteBtn.style.display = "none";

      document.getElementById("reward-form-id").value = "";
      document.getElementById("reward-form-title").value = "";
      document.getElementById("reward-form-desc").value = "";
      document.getElementById("reward-form-cost").value = "0";
      document.getElementById("reward-form-onetime").checked = false;
      document.getElementById("reward-form-softskill").value = "";
      document.getElementById("reward-form-goal").value = "";
      if (categorySelect) categorySelect.value = "regular";
    }
    updateCategoryDisabledStates();
  }

  function closeRewardDrawer() {
    const drawer = document.getElementById("reward-drawer");
    const overlay = document.getElementById("drawer-overlay");
    if (drawer) drawer.classList.remove("open");
    if (overlay) overlay.classList.remove("open");
  }

  async function fetchRewards() {
    try {
      const profileResp = await fetch(`${API_BASE}/profile`);
      if (profileResp.ok) {
        const profileData = await profileResp.json();
        const topGoldVal = document.getElementById("top-gold-val");
        const charGoldVal = document.getElementById("char-gold-val");
        const shopGoldVal = document.getElementById("shop-gold-val");
        if (topGoldVal) topGoldVal.textContent = `💰 ${profileData.gold} Gold`;
        if (charGoldVal) charGoldVal.textContent = profileData.gold;
        if (shopGoldVal) shopGoldVal.textContent = `💰 ${profileData.gold} Gold`;
      }

      const response = await fetch(`${API_BASE}/rewards`);
      if (!response.ok) throw new Error("Erreur fetch rewards");
      const rewards = await response.json();

      const dailyGrid = document.getElementById("rewards-grid-allostasis-daily");
      const weeklyGrid = document.getElementById("rewards-grid-allostasis-weekly");
      const standardGrid = document.getElementById("rewards-grid");
      const dailySection = document.getElementById("allostasis-daily-section");
      const weeklySection = document.getElementById("allostasis-weekly-section");
      const standardHeader = document.getElementById("standard-rewards-header");

      if (dailyGrid) dailyGrid.innerHTML = "";
      if (weeklyGrid) weeklyGrid.innerHTML = "";
      if (standardGrid) standardGrid.innerHTML = "";

      const activeFilterBtn = document.querySelector(".shop-filter-btn.active");
      const filter = activeFilterBtn ? activeFilterBtn.getAttribute("data-filter") : "all";

      const filteredRewards = rewards.filter(r => {
        if (filter === "unlocked") return r.unlocked;
        if (filter === "locked") return !r.unlocked;
        return true;
      });

      if (filteredRewards.length === 0) {
        if (standardGrid) {
          standardGrid.innerHTML = `<p style="grid-column: 1 / -1; color: var(--text-secondary); text-align: center; padding: 2rem 0; font-size: 0.9rem;">Aucune récompense à afficher.</p>`;
        }
        if (dailySection) dailySection.style.display = "none";
        if (weeklySection) weeklySection.style.display = "none";
        if (standardHeader) standardHeader.style.display = "none";
        return;
      }

      let dailyCount = 0;
      let weeklyCount = 0;
      let regularCount = 0;

      filteredRewards.forEach(r => {
        const isAllostasis = r.category === "allostasis_daily" || r.category === "allostasis_weekly";

        let buyBtnText = "";
        let buyDisabled = false;
        let cardClass = "";

        if (isAllostasis) {
          const isCompleted = !r.is_available;
          buyBtnText = isCompleted ? "✓ Validé" : "Valider";
          buyDisabled = isCompleted || !r.unlocked;
          cardClass = `reward-card reward-card-allostasis ${!r.unlocked ? 'locked' : ''} ${isCompleted ? 'completed-allostasis' : ''}`;
        } else {
          const isOnetimeOwned = r.is_one_time && r.purchased_count > 0;
          buyBtnText = isOnetimeOwned ? "Déjà acquis" : `Acheter (💰 ${r.gold_cost} Or)`;
          buyDisabled = !r.unlocked || isOnetimeOwned;
          cardClass = `reward-card ${!r.unlocked ? 'locked' : ''} ${isOnetimeOwned ? 'owned' : ''}`;
        }

        let requirementsHTML = "";
        if (!r.unlocked && r.lock_reason) {
          requirementsHTML = `
            <div class="reward-card-requirements">
              <span class="reward-req-badge unmet">🔒 ${r.lock_reason}</span>
            </div>
          `;
        } else if (r.required_softskill_id || r.required_goal_id) {
          requirementsHTML = `
            <div class="reward-card-requirements">
              <span class="reward-req-badge met">✓ Prérequis remplis</span>
            </div>
          `;
        }

        let purchasedCountHTML = "";
        if (isAllostasis) {
          purchasedCountHTML = r.purchased_count > 0
            ? `<span class="reward-card-purchased-badge">Validations : ${r.purchased_count} fois</span>`
            : "";
        } else {
          purchasedCountHTML = r.purchased_count > 0
            ? `<span class="reward-card-purchased-badge">Acheté : ${r.purchased_count} fois</span>`
            : "";
        }

        const costHTML = isAllostasis
          ? `<span class="reward-card-cost free" style="color: var(--accent-cyan); font-weight: 700;">Gratuit</span>`
          : `<span class="reward-card-cost">💰 ${r.gold_cost} Or</span>`;

        const card = document.createElement("div");
        card.className = cardClass;
        card.innerHTML = `
          <div class="reward-card-header">
            <h3 class="reward-card-title">${r.title}</h3>
            ${costHTML}
          </div>
          <p class="reward-card-desc">${r.description || 'Aucune description.'}</p>
          ${requirementsHTML}
          <div>
            ${purchasedCountHTML}
            <div class="reward-card-actions">
              <button class="reward-buy-btn" data-id="${r.id}" ${buyDisabled ? 'disabled' : ''}>
                ${buyBtnText}
              </button>
              <button class="reward-edit-btn" data-reward='${JSON.stringify(r)}'>✏️</button>
            </div>
          </div>
        `;

        card.querySelector(".reward-buy-btn").addEventListener("click", () => buyReward(r.id));
        card.querySelector(".reward-edit-btn").addEventListener("click", () => openRewardDrawer(r));

        if (r.category === "allostasis_daily") {
          if (dailyGrid) {
            dailyGrid.appendChild(card);
            dailyCount++;
          }
        } else if (r.category === "allostasis_weekly") {
          if (weeklyGrid) {
            weeklyGrid.appendChild(card);
            weeklyCount++;
          }
        } else {
          if (standardGrid) {
            standardGrid.appendChild(card);
            regularCount++;
          }
        }
      });

      if (dailySection) dailySection.style.display = dailyCount > 0 ? "block" : "none";
      if (weeklySection) weeklySection.style.display = weeklyCount > 0 ? "block" : "none";
      if (standardHeader) standardHeader.style.display = (dailyCount > 0 || weeklyCount > 0) && regularCount > 0 ? "block" : "none";

      if (dailyCount === 0 && weeklyCount === 0 && regularCount === 0) {
        if (standardGrid) {
          standardGrid.innerHTML = `<p style="grid-column: 1 / -1; color: var(--text-secondary); text-align: center; padding: 2rem 0; font-size: 0.9rem;">Aucune récompense à afficher.</p>`;
        }
      }
    } catch (err) {
      console.error(err);
      showToast("Erreur lors de la récupération des récompenses", true);
    }
  }

  async function buyReward(rewardId) {
    try {
      const response = await fetch(`${API_BASE}/rewards/${rewardId}/purchase`, {
        method: "POST"
      });
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Erreur lors de l'achat");
      }
      const data = await response.json();
      showToast(`Achat réussi ! Or dépensé : ${data.gold_spent} Or 💸`);
      await fetchRewards();
    } catch (err) {
      showToast(err.message, true);
    }
  }

  function setupRewardsEvents() {
    const openBtn = document.getElementById("open-reward-modal-btn");
    const closeBtn = document.getElementById("close-reward-drawer-btn");
    const form = document.getElementById("reward-form");
    const deleteBtn = document.getElementById("delete-reward-btn");
    const overlay = document.getElementById("drawer-overlay");

    if (openBtn) {
      openBtn.addEventListener("click", () => openRewardDrawer(null));
    }
    if (closeBtn) {
      closeBtn.addEventListener("click", closeRewardDrawer);
    }
    if (overlay) {
      overlay.addEventListener("click", closeRewardDrawer);
    }

    const filterBtns = document.querySelectorAll(".shop-filter-btn");
    filterBtns.forEach(btn => {
      btn.addEventListener("click", () => {
        filterBtns.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        fetchRewards();
      });
    });

    const categorySelect = document.getElementById("reward-form-category");
    const costInput = document.getElementById("reward-form-cost");
    const oneTimeCheckbox = document.getElementById("reward-form-onetime");

    if (categorySelect) {
      categorySelect.addEventListener("change", () => {
        const val = categorySelect.value;
        const costGrid = document.getElementById("reward-form-cost-grid");
        const softskillGroup = document.getElementById("reward-form-softskill-group");
        const goalGroup = document.getElementById("reward-form-goal-group");

        if (val === "allostasis_daily" || val === "allostasis_weekly") {
          costInput.value = "0";
          costInput.disabled = true;
          oneTimeCheckbox.checked = false;
          oneTimeCheckbox.disabled = true;

          if (costGrid) costGrid.style.display = "none";
          if (softskillGroup) {
            softskillGroup.style.display = "none";
            const ssSelect = document.getElementById("reward-form-softskill");
            if (ssSelect) ssSelect.value = "";
          }
          if (goalGroup) {
            goalGroup.style.display = "none";
            const gSelect = document.getElementById("reward-form-goal");
            if (gSelect) gSelect.value = "";
          }
        } else {
          costInput.disabled = false;
          oneTimeCheckbox.disabled = false;

          if (costGrid) costGrid.style.display = "grid";
          if (softskillGroup) softskillGroup.style.display = "block";
          if (goalGroup) goalGroup.style.display = "block";
        }
      });
    }

    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const id = document.getElementById("reward-form-id").value;
        const title = document.getElementById("reward-form-title").value.trim();
        const desc = document.getElementById("reward-form-desc").value.trim();
        const cost = parseInt(document.getElementById("reward-form-cost").value) || 0;
        const onetime = document.getElementById("reward-form-onetime").checked;
        const softskill = document.getElementById("reward-form-softskill").value || null;
        const category = document.getElementById("reward-form-category").value || "regular";

        const goalVal = document.getElementById("reward-form-goal").value;
        const goal = goalVal ? parseInt(goalVal) : null;

        const payload = {
          title: title,
          description: desc,
          gold_cost: cost,
          required_softskill_id: softskill,
          required_goal_id: goal,
          is_one_time: onetime,
          category: category
        };

        try {
          const method = id ? "PUT" : "POST";
          const url = id ? `${API_BASE}/rewards/${id}` : `${API_BASE}/rewards`;

          const response = await fetch(url, {
            method: method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });

          if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || "Erreur de sauvegarde");
          }

          showToast(id ? "Récompense modifiée avec succès !" : "Nouvelle récompense créée ! ✨");
          closeRewardDrawer();
          await fetchRewards();
        } catch (err) {
          showToast(err.message, true);
        }
      });
    }

    if (deleteBtn) {
      deleteBtn.addEventListener("click", async () => {
        const id = document.getElementById("reward-form-id").value;
        if (!id) return;
        if (!confirm("Voulez-vous vraiment supprimer cette récompense ?")) return;

        try {
          const response = await fetch(`${API_BASE}/rewards/${id}`, {
            method: "DELETE"
          });
          if (!response.ok) throw new Error("Erreur lors de la suppression");

          showToast("Récompense supprimée.");
          closeRewardDrawer();
          await fetchRewards();
        } catch (err) {
          showToast(err.message, true);
        }
      });
    }
  }

  // ==============================================
  // 3-3-3 RECAP PANEL & DRAWER                    //
  // ==============================================
  let allostasisViewMode = "daily"; // "daily" or "weekly"
  let pinnedSubsteps = [];
  let pinnedSoftskills = [];
  let pinnedGoals = [];
  let isUnlockClicked = false;

  function getTop3LockState() {
    if (pinnedGoals.length < 3) {
      return false;
    }
    return !isUnlockClicked;
  }

  function getRecapLevel(value) {
    const level = parseInt(value, 10);
    return Number.isFinite(level) && level > 0 ? level : 1;
  }

  function getUnlockedLevels(items, getLevel, isCompleted) {
    const levels = Array.from(new Set(items.map(item => getRecapLevel(getLevel(item)))))
      .sort((a, b) => a - b);
    const unlockedLevels = new Set();
    if (levels.length === 0) return unlockedLevels;

    unlockedLevels.add(levels[0]);
    for (let index = 1; index < levels.length; index++) {
      const previousLevel = levels[index - 1];
      const previousLevelHasCompletion = items.some(item =>
        getRecapLevel(getLevel(item)) === previousLevel && isCompleted(item)
      );
      if (!previousLevelHasCompletion) break;
      unlockedLevels.add(levels[index]);
    }

    return unlockedLevels;
  }

  function getUnlockedGoalLevels(goal) {
    const substeps = Array.isArray(goal?.substeps) ? goal.substeps : [];
    return getUnlockedLevels(
      substeps,
      substep => substep.execution_order,
      substep => Boolean(substep.completed)
    );
  }

  function getPinnedGoalSubstepContexts(goals, subId) {
    if (!Array.isArray(goals)) return [];
    const contexts = [];
    const seenGoalIds = new Set();

    goals.forEach(goal => {
      if (!pinnedGoals.includes(goal.id) || !Array.isArray(goal.substeps)) return;
      const sub = goal.substeps.find(item => item.id === subId);
      if (!sub) return;
      contexts.push({ goal, sub });
      seenGoalIds.add(goal.id);
    });

    goals.forEach(sourceGoal => {
      if (!Array.isArray(sourceGoal.substeps)) return;
      const sourceSub = sourceGoal.substeps.find(item => item.id === subId);
      if (!sourceSub) return;

      (sourceSub.linked_goals || []).forEach(linkedGoalRef => {
        if (!pinnedGoals.includes(linkedGoalRef.id) || seenGoalIds.has(linkedGoalRef.id)) return;
        const linkedGoal = goals.find(goal => goal.id === linkedGoalRef.id);
        const linkedSub = linkedGoal?.substeps?.find(item => item.id === subId);
        if (linkedGoal && linkedSub) {
          contexts.push({ goal: linkedGoal, sub: linkedSub });
          seenGoalIds.add(linkedGoal.id);
        }
      });
    });

    return contexts;
  }

  function getVisibleSubstepRecapContext(goals, subId) {
    const contexts = getPinnedGoalSubstepContexts(goals, subId);
    return contexts.find(({ goal, sub }) => (
      getUnlockedGoalLevels(goal).has(getRecapLevel(sub.execution_order))
    )) || null;
  }

  function getEligibleRecapSubsteps(goals) {
    const eligibleBySubstep = new Map();

    (Array.isArray(goals) ? goals : []).forEach(goal => {
      if (!pinnedGoals.includes(goal.id) || !Array.isArray(goal.substeps)) return;
      const unlockedLevels = getUnlockedGoalLevels(goal);

      goal.substeps.forEach(sub => {
        const level = getRecapLevel(sub.execution_order);
        if (!unlockedLevels.has(level)) return;
        if (sub.completed && !pinnedSubsteps.includes(sub.id)) return;

        const existing = eligibleBySubstep.get(sub.id);
        if (existing) {
          existing.goalRefs.set(goal.id, goal.title);
          existing.levels.set(goal.id, level);
          return;
        }

        eligibleBySubstep.set(sub.id, {
          sub,
          goalRefs: new Map([[goal.id, goal.title]]),
          levels: new Map([[goal.id, level]])
        });
      });
    });

    return Array.from(eligibleBySubstep.values())
      .sort((a, b) => {
        const firstPinnedIndex = Math.min(
          ...Array.from(a.goalRefs.keys()).map(goalId => pinnedGoals.indexOf(goalId))
        );
        const secondPinnedIndex = Math.min(
          ...Array.from(b.goalRefs.keys()).map(goalId => pinnedGoals.indexOf(goalId))
        );
        if (firstPinnedIndex !== secondPinnedIndex) return firstPinnedIndex - secondPinnedIndex;
        const firstLevel = Math.min(...Array.from(a.levels.values()));
        const secondLevel = Math.min(...Array.from(b.levels.values()));
        if (firstLevel !== secondLevel) return firstLevel - secondLevel;
        return a.sub.title.localeCompare(b.sub.title, "fr");
      });
  }

  function getUnlockedSkillLevelsByBranch(skills) {
    const levelsByBranch = new Map();
    const skillsByBranch = new Map();

    (Array.isArray(skills) ? skills : []).forEach(skill => {
      const branchKey = skill.branch || "__global";
      if (!skillsByBranch.has(branchKey)) {
        skillsByBranch.set(branchKey, []);
      }
      skillsByBranch.get(branchKey).push(skill);
    });

    skillsByBranch.forEach((branchSkills, branchKey) => {
      levelsByBranch.set(branchKey, getUnlockedLevels(
        branchSkills,
        skill => skill.execution_order,
        skill => Boolean(skill.progress && skill.progress.completed)
      ));
    });

    return levelsByBranch;
  }

  function isSkillLevelUnlocked(skill, levelsByBranch) {
    const branchKey = skill.branch || "__global";
    const unlockedLevels = levelsByBranch.get(branchKey) || new Set();
    return unlockedLevels.has(getRecapLevel(skill.execution_order));
  }

  function getEligibleRecapSkills(skills) {
    const levelsByBranch = getUnlockedSkillLevelsByBranch(skills);
    return (Array.isArray(skills) ? skills : [])
      .filter(skill => isSkillLevelUnlocked(skill, levelsByBranch))
      .filter(skill => !(skill.progress && skill.progress.completed) || pinnedSoftskills.includes(skill.id))
      .sort((a, b) => {
        const branchCompare = String(a.branch || "").localeCompare(String(b.branch || ""), "fr");
        if (branchCompare !== 0) return branchCompare;
        const levelCompare = getRecapLevel(a.execution_order) - getRecapLevel(b.execution_order);
        if (levelCompare !== 0) return levelCompare;
        return a.name.localeCompare(b.name, "fr");
      });
  }

  // Helper to open/close the pin drawer
  function openRecapPinDrawer() {
    const overlay = document.getElementById("drawer-overlay");
    const drawer = document.getElementById("recap-pin-drawer");
    if (overlay && drawer) {
      overlay.classList.add("open");
      drawer.classList.add("open");
      populatePinDrawerOptions();
    }
  }

  function closeRecapPinDrawer() {
    const overlay = document.getElementById("drawer-overlay");
    const drawer = document.getElementById("recap-pin-drawer");
    if (overlay && drawer) {
      overlay.classList.remove("open");
      drawer.classList.remove("open");
    }
  }

  // Populate checklist checkboxes in the pin drawer
  async function populatePinDrawerOptions() {
    const goalsListContainer = document.getElementById("recap-pin-goals-list");
    const skillsListContainer = document.getElementById("recap-pin-skills-list");
    if (!goalsListContainer || !skillsListContainer) return;

    goalsListContainer.innerHTML = `<p style="font-size: 0.8rem; color: var(--text-muted); margin: 0;">Chargement des objectifs...</p>`;
    skillsListContainer.innerHTML = `<p style="font-size: 0.8rem; color: var(--text-muted); margin: 0;">Chargement des compétences...</p>`;

    try {
      // 1. Fetch Goals & Substeps
      const goalsResp = await fetch(`${API_BASE}/goals`);
      if (!goalsResp.ok) throw new Error("Failed to load goals");
      const goals = await goalsResp.json();

      goalsListContainer.replaceChildren();
      goals.filter(goal => !goal.completed).forEach(goal => {
        const label = document.createElement("label");
        label.className = "recap-checkbox-container";
        const input = document.createElement("input");
        input.type = "checkbox";
        input.name = "pin-goal-checkbox";
        input.value = goal.id;
        input.checked = pinnedGoals.includes(goal.id);
        const title = document.createElement("span");
        title.textContent = goal.title;
        label.append(input, title);
        goalsListContainer.appendChild(label);
      });
      if (!goalsListContainer.children.length) goalsListContainer.textContent = "Aucun objectif actif.";

      // 2. Fetch Softskills
      const skillsResp = await fetch(`${API_BASE}/softskills`);
      if (!skillsResp.ok) throw new Error("Failed to load softskills");
      const skillsData = await skillsResp.json();
      const skills = skillsData.skills || [];

      // Show only currently unlocked skill levels, keeping already pinned completed skills visible.
      const eligibleSkills = getEligibleRecapSkills(skills);
      let skillsHtml = "";
      if (eligibleSkills.length > 0) {
        eligibleSkills.forEach(skill => {
          const isChecked = pinnedSoftskills.includes(skill.id) ? "checked" : "";
          const level = getRecapLevel(skill.execution_order);
          skillsHtml += `
            <label class="recap-checkbox-container">
              <input type="checkbox" name="pin-skill-checkbox" value="${skill.id}" ${isChecked}>
              <span style="font-size: 0.8rem;"><strong>${skill.branch}</strong>: <span style="color: var(--text-muted);">Niv. ${level}</span> · ${skill.name}</span>
            </label>
          `;
        });
        skillsListContainer.innerHTML = skillsHtml;
      } else {
        skillsListContainer.innerHTML = `<p style="font-size: 0.8rem; color: var(--text-muted); margin: 0;">Aucune compétence active.</p>`;
      }

      // Add selection limits (max 3)
      setupCheckboxLimit("pin-goal-checkbox");
      setupCheckboxLimit("pin-skill-checkbox");

    } catch (err) {
      goalsListContainer.innerHTML = `<p style="font-size: 0.8rem; color: var(--accent-red); margin: 0;">Erreur de chargement.</p>`;
      skillsListContainer.innerHTML = `<p style="font-size: 0.8rem; color: var(--accent-red); margin: 0;">Erreur de chargement.</p>`;
    }
  }

  // Disable extra checkboxes if 3 are checked
  function setupCheckboxLimit(checkboxName) {
    const checkboxes = document.querySelectorAll(`input[name="${checkboxName}"]`);

    const updateStates = () => {
      const checkedCount = document.querySelectorAll(`input[name="${checkboxName}"]:checked`).length;
      checkboxes.forEach(cb => {
        if (!cb.checked) {
          cb.disabled = checkedCount >= 3;
        } else {
          cb.disabled = false;
        }
      });
    };

    checkboxes.forEach(cb => {
      cb.addEventListener("change", updateStates);
    });

    updateStates();
  }

  // Save pinned items to database
  async function savePinnedItems() {
    const checkedGoals = Array.from(document.querySelectorAll('input[name="pin-goal-checkbox"]:checked')).map(cb => parseInt(cb.value));
    const checkedSkills = Array.from(document.querySelectorAll('input[name="pin-skill-checkbox"]:checked')).map(cb => cb.value);

    try {
      const resp = await fetch(`${API_BASE}/profile/pins`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pinned_goals: checkedGoals,
          pinned_substeps: [],
          pinned_softskills: checkedSkills
        })
      });

      if (!resp.ok) throw new Error("Erreur de sauvegarde de l'API");
      pinnedGoals = checkedGoals;
      showToast("Épingles 3-3-3 sauvegardées ! 📌");
      closeRecapPinDrawer();
      fetchProfile(); // Reload dashboard profile and recap panel
      updateDailyBudgetGauge();
    } catch (err) {
      showToast(err.message, true);
    }
  }

  function renderTop3LockButton() {
    const container = document.getElementById("top3-lock-btn-container");
    if (!container) return;

    container.innerHTML = "";
    const locked = getTop3LockState();

    if (pinnedGoals.length === 3) {
      if (locked) {
        const btn = document.createElement("button");
        btn.id = "unlock-top3-btn";
        btn.className = "quest-action-btn";
        btn.style.cssText = "padding: 6px 12px; font-size: 0.75rem; background: rgba(239, 68, 68, 0.15); border-color: rgba(239, 68, 68, 0.4); color: #f87171; font-weight: bold; cursor: pointer; transition: all 0.2s;";
        btn.innerHTML = "🔓 Déverrouiller le Top 3";
        btn.addEventListener("click", () => {
          isUnlockClicked = true;
          showToast("Top 3 déverrouillé ! Vous pouvez modifier vos objectifs prioritaires.");
          renderTop3LockButton();
          fetchGoals(); // Re-render goals sidebar to refresh star buttons/tooltip
        });
        container.appendChild(btn);
      } else {
        const btn = document.createElement("button");
        btn.id = "lock-top3-btn";
        btn.className = "quest-action-btn";
        btn.style.cssText = "padding: 6px 12px; font-size: 0.75rem; background: rgba(16, 185, 129, 0.15); border-color: rgba(16, 185, 129, 0.4); color: #34d399; font-weight: bold; cursor: pointer; transition: all 0.2s;";
        btn.innerHTML = "🔒 Verrouiller le Top 3";
        btn.addEventListener("click", () => {
          isUnlockClicked = false;
          showToast("Top 3 verrouillé ! 🎯");
          renderTop3LockButton();
          fetchGoals();
        });
        container.appendChild(btn);
      }
    } else {
      const remaining = 3 - pinnedGoals.length;
      container.innerHTML = `<span style="font-size: 0.72rem; color: var(--text-muted); font-style: italic;">Sélectionnez encore ${remaining} objectif${remaining > 1 ? 's' : ''}</span>`;
    }
  }

  // Render the recap panel content
  function renderFocusRecapRow(list, title, habit, role, targetId) {
    const li = document.createElement("li");
    li.className = `recap-item ${habit && habit.today_count >= (habit.daily_target || 1) ? "completed" : ""}`;
    const name = document.createElement("button");
    name.type = "button";
    name.className = "recap-item-text";
    name.textContent = title;
    name.title = habit ? `Modifier la quête : ${habit.name}` : "Créer une quête liée";
    name.addEventListener("click", async () => {
      if (habit) openEditQuestModal(habit);
      else await openFocusQuestForm(role, targetId, title);
    });
    const settings = document.createElement("button");
    settings.type = "button";
    settings.className = "recap-quest-settings-btn";
    settings.textContent = "+";
    settings.title = habit ? `Régler la quête de ${title}` : `Créer la quête de ${title}`;
    settings.setAttribute("aria-label", settings.title);
    settings.addEventListener("click", () => {
      if (habit) openEditQuestModal(habit);
      else openFocusQuestForm(role, targetId, title);
    });
    const action = document.createElement("button");
    action.type = "button";
    action.className = "recap-claim-btn";
    action.textContent = habit ? (habit.today_count >= (habit.daily_target || 1) ? "✓ Fait" : habit.focus_due_today ? "Valider" : "Hors planning") : "Valider";
    action.disabled = !habit || !habit.focus_due_today || habit.today_count >= (habit.daily_target || 1);
    if (!habit) action.title = "Créez d'abord une quête avec le bouton +";
    action.addEventListener("click", async () => {
      if (habit.type === "quantitative") {
        const amount = Number(prompt(`Combien de ${habit.unit || "unités"} ?`));
        if (!Number.isFinite(amount) || amount <= 0) return;
        await submitQuestLog(habit.id, "log", amount, todayDateString());
      } else {
        await submitQuestLog(habit.id, "done", null, todayDateString());
      }
    });
    const actions = document.createElement("span");
    actions.className = "recap-item-actions";
    actions.append(settings, action);
    li.append(name, actions);
    list.appendChild(li);
  }

  async function renderRecapPanel(profileData) {
    const goalsList = document.getElementById("recap-goals-list");
    const skillsList = document.getElementById("recap-skills-list");
    const allostasisList = document.getElementById("recap-allostasis-list");
    const allostasisTitle = document.getElementById("recap-allostasis-title");

    if (!goalsList || !skillsList || !allostasisList) return;

    pinnedSubsteps = profileData.pinned_substeps || [];
    pinnedSoftskills = profileData.pinned_softskills || [];
    pinnedGoals = profileData.pinned_goals || [];
    renderTop3LockButton();

    // 1. Render Goals
    try {
      const goalsResp = await fetch(`${API_BASE}/goals`);
      const goals = await goalsResp.json();
      goalsList.innerHTML = "";

      const habitsResponse = await fetch(`${API_BASE}/habits`);
      const habits = await habitsResponse.json();
      pinnedGoals.slice(0, 3).forEach(goalId => {
        const goal = goals.find(item => item.id === goalId && !item.completed);
        if (goal) renderFocusRecapRow(goalsList, goal.title, habits.find(habit => habit.focus_role === "goal" && habit.focus_goal_id === goalId && habit.is_active), "goal", goalId);
      });
      if (!goalsList.children.length) goalsList.innerHTML = `<li class="recap-list-placeholder">Aucun objectif épinglé.</li>`;
    } catch (err) {
      goalsList.innerHTML = `<li class="recap-list-placeholder" style="font-size: 0.8rem; color: var(--accent-red);">Erreur objectifs.</li>`;
    }

    // 2. Render Softskills
    try {
      const skillsResp = await fetch(`${API_BASE}/softskills`);
      const skillsData = await skillsResp.json();
      const skills = skillsData.skills || [];
      const unlockedSkillLevelsByBranch = getUnlockedSkillLevelsByBranch(skills);
      skillsList.innerHTML = "";

      const habitsResponse = await fetch(`${API_BASE}/habits`);
      const habits = await habitsResponse.json();
      let skillsRendered = 0;
      pinnedSoftskills.forEach(skillId => {
        const skill = skills.find(s => s.id === skillId);
        if (skill && isSkillLevelUnlocked(skill, unlockedSkillLevelsByBranch)) {
          if (!skill.progress?.completed) {
            skillsRendered++;
            renderFocusRecapRow(skillsList, skill.name, habits.find(habit => habit.focus_role === "skill" && habit.focus_softskill_id === skillId && habit.is_active), "skill", skillId);
          }
        }
      });

      if (skillsRendered === 0) {
        skillsList.innerHTML = `<li class="recap-list-placeholder" style="font-size: 0.8rem; color: var(--text-muted);">Aucune compétence épinglée. ✏️</li>`;
      }
    } catch (err) {
      skillsList.innerHTML = `<li class="recap-list-placeholder" style="font-size: 0.8rem; color: var(--accent-red);">Erreur compétences.</li>`;
    }

    // 3. Render Allostasis
    try {
      const rewardsResp = await fetch(`${API_BASE}/rewards`);
      const rewards = await rewardsResp.json();
      allostasisList.innerHTML = "";

      const targetCat = allostasisViewMode === "daily" ? "allostasis_daily" : "allostasis_weekly";
      allostasisTitle.textContent = allostasisViewMode === "daily" ? "🩹 Allostasie (Jour)" : "🩹 Allostasie (Sem.)";

      const listItems = rewards.filter(r => r.category === targetCat);

      listItems.forEach(item => {
        const li = document.createElement("li");
        const isCompleted = !item.is_available;
        li.className = `recap-item ${isCompleted ? 'completed' : ''}`;

        let actionHTML = "";
        if (isCompleted) {
          actionHTML = `<span class="recap-item-status-icon" style="color: var(--accent-green);">✓ Fait</span>`;
        } else {
          actionHTML = `<button class="recap-claim-btn" data-id="${item.id}">Valider</button>`;
        }

        li.innerHTML = `
          <span class="recap-item-text" title="${item.title}">${item.title}</span>
          ${actionHTML}
        `;

        const btn = li.querySelector(".recap-claim-btn");
        if (btn) {
          btn.addEventListener("click", async (e) => {
            e.stopPropagation();
            btn.disabled = true;
            btn.textContent = "...";

            try {
              const purchaseResp = await fetch(`${API_BASE}/rewards/${item.id}/purchase`, { method: "POST" });
              if (!purchaseResp.ok) {
                const errData = await purchaseResp.json();
                throw new Error(errData.detail || "Validation échouée");
              }
              showToast(`Allostasie validée : ${item.title} ! 🎉`);
              fetchProfile();
            } catch (err) {
              showToast(err.message, true);
              btn.disabled = false;
              btn.textContent = "Valider";
            }
          });
        }

        allostasisList.appendChild(li);
      });

      if (listItems.length === 0) {
        allostasisList.innerHTML = `<li class="recap-list-placeholder" style="font-size: 0.8rem; color: var(--text-muted);">Aucune activité créée dans la boutique.</li>`;
      }
    } catch (err) {
      allostasisList.innerHTML = `<li class="recap-list-placeholder" style="font-size: 0.8rem; color: var(--accent-red);">Erreur allostasie.</li>`;
    }
  }

  // Register Event Listeners for Pinned Recap Panel Actions
  const editGoalsBtn = document.getElementById("recap-edit-goals-btn");
  const editSkillsBtn = document.getElementById("recap-edit-skills-btn");
  const closePinDrawerBtn = document.getElementById("close-recap-pin-drawer-btn");
  const savePinsBtn = document.getElementById("save-recap-pins-btn");
  const toggleAllostasisBtn = document.getElementById("recap-toggle-allostasis-btn");

  if (editGoalsBtn) editGoalsBtn.addEventListener("click", openRecapPinDrawer);
  if (editSkillsBtn) editSkillsBtn.addEventListener("click", openRecapPinDrawer);
  if (closePinDrawerBtn) closePinDrawerBtn.addEventListener("click", closeRecapPinDrawer);
  if (savePinsBtn) savePinsBtn.addEventListener("click", savePinnedItems);

  if (toggleAllostasisBtn) {
    toggleAllostasisBtn.addEventListener("click", () => {
      allostasisViewMode = allostasisViewMode === "daily" ? "weekly" : "daily";
      fetchProfile();
    });
  }

  // Logout Logic
  const switchProfileBtn = document.getElementById("switch-profile-btn");
  if (switchProfileBtn) {
    switchProfileBtn.addEventListener("click", async () => {
      await fetch(`${API_BASE}/auth/logout`, { method: "POST" });
      if (refreshIntervalId) {
        clearInterval(refreshIntervalId);
        refreshIntervalId = null;
      }
      appInitialized = false;
      showLoginScreen();
    });
  }

  const authPasswordForm = document.getElementById("auth-password-form");
  if (authPasswordForm) {
    authPasswordForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      try {
        const response = await fetch(`${API_BASE}/auth/password`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            current_password: document.getElementById("auth-current-password").value,
            new_password: document.getElementById("auth-new-password").value,
          }),
        });
        if (!response.ok) throw new Error((await response.json()).detail || "Erreur mot de passe");
        authPasswordForm.reset();
        showToast("Mot de passe mis à jour.");
      } catch (error) {
        showToast(error.message, true);
      }
    });
  }

  const authAdminPasswordForm = document.getElementById("auth-admin-password-form");
  if (authAdminPasswordForm) {
    authAdminPasswordForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const targetUserId = document.getElementById("auth-admin-user").value;
      try {
        const response = await fetch(`${API_BASE}/auth/users/${targetUserId}/password`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            new_password: document.getElementById("auth-admin-new-password").value,
          }),
        });
        if (!response.ok) throw new Error((await response.json()).detail || "Erreur mot de passe");
        authAdminPasswordForm.reset();
        showToast("Mot de passe du compte mis à jour.");
      } catch (error) {
        showToast(error.message, true);
      }
    });
  }

  const authDeviceList = document.getElementById("auth-device-list");
  if (authDeviceList) {
    authDeviceList.addEventListener("click", async (event) => {
      const item = event.target.closest(".auth-device-item");
      if (!item) return;
      const revoke = event.target.closest(".auth-device-revoke");
      if (!revoke) return;
      try {
        const response = await fetch(`${API_BASE}/auth/devices/${item.dataset.deviceId}/revoke`, {
          method: "POST",
        });
        if (!response.ok) throw new Error((await response.json()).detail || "Erreur appareil");
        showToast("Appareil révoqué.");
        loadAuthAdminSettings();
      } catch (error) {
        showToast(error.message, true);
      }
    });
  }

  // --- Life Lore Modal Logic ---
  const avatarContainer = document.querySelector(".avatar-container");
  const lifeLoreModal = document.getElementById("life-lore-modal");
  const closeLifeLoreBtn = document.getElementById("close-life-lore-btn");
  const lifeLoreContent = document.getElementById("life-lore-content");

  if (avatarContainer && lifeLoreModal && closeLifeLoreBtn && lifeLoreContent) {
    avatarContainer.addEventListener("click", async () => {
      // Clear content and show modal
      lifeLoreContent.innerHTML = `<p style="text-align: center; color: var(--text-muted); padding: 2rem;">Chargement du Grimoire de Vie... 📖</p>`;
      lifeLoreModal.style.display = "flex";

      try {
        const response = await fetch(`${API_BASE}/profile/life-lore`);
        if (!response.ok) throw new Error("Erreur de récupération");
        const substeps = await response.json();

        if (substeps.length === 0) {
          lifeLoreContent.innerHTML = `<p style="text-align: center; color: var(--text-muted); padding: 2.5rem; line-height: 1.5;">Aucun fragment de Life Lore n'est gravé dans le marbre pour le moment.<br><br>Cochez la case "Life Lore" dans les paramètres d'une sous-étape et accomplissez-la pour commencer à écrire votre histoire ! 📖</p>`;
          return;
        }

        lifeLoreContent.innerHTML = substeps.map(s => {
          const dateStr = s.completed_at ? new Date(s.completed_at).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' }) : 'Date inconnue';
          return `
            <div class="glass-card" style="padding: 1.2rem; background: rgba(255, 255, 255, 0.015); border-color: rgba(255, 255, 255, 0.05); display: flex; flex-direction: column; gap: 0.5rem;">
              <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem;">
                <h4 style="font-family: var(--font-display); font-size: 1.1rem; color: var(--accent-gold); margin: 0;">${s.title}</h4>
                <span style="font-size: 0.75rem; color: var(--text-muted); white-space: nowrap;">📅 ${dateStr}</span>
              </div>
              ${s.description ? `<p style="font-size: 0.88rem; color: var(--text-secondary); margin: 0; line-height: 1.4;">${s.description}</p>` : ""}
              <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.5rem; border-top: 1px solid rgba(255, 255, 255, 0.03); padding-top: 0.5rem;">
                <span style="font-size: 0.8rem; color: var(--accent-cyan); font-weight: 600;">💰 +${s.gold_reward} Gold</span>
              </div>
            </div>
          `;
        }).join("");

      } catch (err) {
        console.error(err);
        lifeLoreContent.innerHTML = `<p style="text-align: center; color: var(--accent-red); padding: 2rem;">Impossible de charger les chroniques du Grimoire.</p>`;
      }
    });

    // Close on button click
    closeLifeLoreBtn.addEventListener("click", () => {
      lifeLoreModal.style.display = "none";
    });

    // Close on overlay click
    lifeLoreModal.addEventListener("click", (e) => {
      if (e.target === lifeLoreModal) {
        lifeLoreModal.style.display = "none";
      }
    });
  }

  // ==============================================
  // GOOGLE CALENDAR & TASKS INTEGRATION FRONTEND
  // ==============================================

  async function fetchGoogleStatus() {
    const badge = document.getElementById("google-status-badge");
    const actionsDisconnected = document.getElementById("google-actions-disconnected");
    const actionsConnected = document.getElementById("google-actions-connected");
    const calIdEl = document.getElementById("google-cal-id");
    const tasksIdEl = document.getElementById("google-tasks-id");
    const connectLink = document.getElementById("google-connect-link");

    if (!badge) return;

    try {
      const response = await fetch(`${API_BASE}/auth/google/status`, {
        headers: {
          "X-User-ID": localStorage.getItem("user_id") || "1"
        }
      });
      if (!response.ok) throw new Error("Status check failed");
      const data = await response.json();

      if (data.is_connected) {
        badge.textContent = "🟢 Connecté";
        badge.style.background = "rgba(16, 185, 129, 0.15)";
        badge.style.color = "#34d399";
        badge.style.borderColor = "#34d399";
        actionsDisconnected.style.display = "none";
        actionsConnected.style.display = "block";
        if (calIdEl) calIdEl.textContent = data.calendar_id || "...";
        if (tasksIdEl) tasksIdEl.textContent = data.tasks_list_id || "...";
      } else {
        badge.textContent = "Non connecté";
        badge.style.background = "rgba(239, 68, 68, 0.15)";
        badge.style.color = "#ef4444";
        badge.style.borderColor = "#ef4444";
        actionsDisconnected.style.display = "block";
        actionsConnected.style.display = "none";

        if (connectLink) {
          connectLink.href = `${API_BASE}/auth/google/login`;
        }
      }
    } catch (err) {
      console.error("Error fetching Google status:", err);
    }
  }

  const disconnectBtn = document.getElementById("google-disconnect-btn");
  if (disconnectBtn) {
    disconnectBtn.addEventListener("click", async () => {
      if (!confirm("Voulez-vous vraiment déconnecter votre compte Google ?\nVos quêtes ne seront plus synchronisées.")) return;
      try {
        const response = await fetch(`${API_BASE}/auth/google/disconnect`, {
          method: "POST",
          headers: {
            "X-User-ID": localStorage.getItem("user_id") || "1"
          }
        });
        if (response.ok) {
          showToast("Compte Google déconnecté avec succès.");
          fetchGoogleStatus();
        } else {
          showToast("Échec de la déconnexion.", true);
        }
      } catch (err) {
        showToast("Erreur lors de la déconnexion.", true);
      }
    });
  }

  function checkGoogleCallback() {
    const params = new URLSearchParams(window.location.search);
    if (params.has("google_success")) {
      showToast("Compte Google associé avec succès ! 🚀");
      params.delete("google_success");
      const cleanUrl = window.location.pathname + (params.toString() ? "?" + params.toString() : "") + window.location.hash;
      window.history.replaceState({}, document.title, cleanUrl);
    } else if (params.has("google_error")) {
      const err = params.get("google_error");
      showToast(`Erreur d'association Google : ${err}`, true);
      params.delete("google_error");
      const cleanUrl = window.location.pathname + (params.toString() ? "?" + params.toString() : "") + window.location.hash;
      window.history.replaceState({}, document.title, cleanUrl);
    }
  }

  fetchGoogleStatus();
  checkGoogleCallback();

});
