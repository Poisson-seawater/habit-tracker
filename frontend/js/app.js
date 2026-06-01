document.addEventListener("DOMContentLoaded", () => {
  // Config
  const API_BASE = "/api/v1";

  // Elements
  const charLevel = document.getElementById("char-level");
  const badgeStatus = document.getElementById("badge-status");
  const templateSelect = document.getElementById("template-select");
  const streakAccVal = document.getElementById("streak-acc-val");
  const streakPerfVal = document.getElementById("streak-perf-val");
  const questsListContainer = document.getElementById("quests-list-container");
  const toastNotification = document.getElementById("toast-notification");

  // Modal elements
  const openAddModalBtn = document.getElementById("open-add-modal-btn");
  const addQuestModal = document.getElementById("add-quest-modal");
  const closeModalBtn = document.getElementById("close-modal-btn");
  const addQuestForm = document.getElementById("add-quest-form");
  const newQuestType = document.getElementById("new-quest-type");
  const unitGroup = document.getElementById("unit-group");

  // Show a glowing toast alert
  function showToast(message, isError = false) {
    toastNotification.textContent = message;
    toastNotification.style.display = "block";
    toastNotification.style.border = isError ? "1px solid var(--accent-red)" : "1px solid var(--accent-cyan)";
    toastNotification.style.boxShadow = isError ? "0 8px 24px rgba(239, 68, 68, 0.4)" : "0 8px 24px var(--accent-cyan-glow)";
    
    setTimeout(() => {
      toastNotification.style.display = "none";
    }, 4000);
  }

  // Helper to format stat list for rewards description
  function formatPointRewards(rewards) {
    return Object.entries(rewards)
      .map(([stat, val]) => `+${val} ${stat.charAt(0).toUpperCase() + stat.slice(1)}`)
      .join(", ");
  }

  // 1. Fetch Profile and Update Stats Sheets
  async function fetchProfile() {
    try {
      const response = await fetch(`${API_BASE}/profile`);
      if (!response.ok) throw new Error("Erreur profile API");
      const data = await response.json();

      // Determine level: Level = Math.floor(Total Stats Points / 15) + 1
      let totalPoints = 0;
      Object.entries(data.stats).forEach(([stat, val]) => {
        totalPoints += val;
      });
      const level = Math.floor(totalPoints / 15) + 1;
      charLevel.textContent = `LV. ${level}`;

      // Update template dropdown selection (prevent triggering change event during sync)
      if (data.active_template) {
        templateSelect.value = data.active_template;
      }
      
      // Update Daily Status Badge
      badgeStatus.textContent = `Statut : ${data.scores.status}`;
      badgeStatus.className = "badge badge-status";
      if (data.scores.status === "Failed" || data.scores.status === "Ratée") {
        badgeStatus.classList.add("failed");
      }

      // Update 12 Progress Bars
      const stats = data.stats;
      const thresholds = data.thresholds;

      Object.entries(stats).forEach(([stat, val]) => {
        const bar = document.getElementById(`stat-bar-${stat}`);
        const textVal = document.getElementById(`stat-val-${stat}`);
        
        if (bar && textVal) {
          // Determine scale max: max of current val, acceptable, perfect, or default to 10
          const accT = thresholds.acceptable ? (thresholds.acceptable[stat] || 0) : 0;
          const perfT = thresholds.perfect ? (thresholds.perfect[stat] || 0) : 0;
          const maxVal = Math.max(val, accT, perfT, 10);
          
          const percent = Math.min((val / maxVal) * 100, 100);
          bar.style.width = `${percent}%`;

          // Format value display
          let thresholdInfo = "";
          if (accT > 0 || perfT > 0) {
            thresholdInfo = ` (Acc: ${accT} / Perf: ${perfT})`;
          }
          textVal.textContent = `${val} pts${thresholdInfo}`;
        }
      });

    } catch (error) {
      console.error(error);
      showToast("Erreur lors du chargement des statistiques", true);
    }
  }

  // 2. Fetch Streaks
  async function fetchStreaks() {
    try {
      const response = await fetch(`${API_BASE}/streaks`);
      if (!response.ok) throw new Error("Erreur streaks API");
      const streaks = await response.json();

      const accS = streaks.find(s => s.streak_type === "Acceptable");
      const perfS = streaks.find(s => s.streak_type === "Perfect");

      streakAccVal.textContent = accS ? accS.current_streak : 0;
      streakPerfVal.textContent = perfS ? perfS.current_streak : 0;
    } catch (error) {
      console.error(error);
    }
  }

  // 3. Fetch Habits & Active Quests
  async function fetchQuests() {
    try {
      const habitsResponse = await fetch(`${API_BASE}/habits`);
      if (!habitsResponse.ok) throw new Error("Erreur habits API");
      const habits = await habitsResponse.json();

      const profileResponse = await fetch(`${API_BASE}/profile`);
      if (!profileResponse.ok) throw new Error("Erreur profile API");
      const profileData = await profileResponse.json();
      
      const completedIds = profileData.completed_habit_ids || [];

      questsListContainer.innerHTML = "";

      if (habits.length === 0) {
        questsListContainer.innerHTML = `<p style="color: var(--text-muted); font-size: 0.9rem; text-align: center;">Aucune habitude active configurée.</p>`;
        return;
      }

      habits.forEach(habit => {
        const questItem = document.createElement("div");
        questItem.className = "quest-item";
        questItem.id = `quest-item-${habit.id}`;

        const isCompleted = completedIds.includes(habit.id);
        const privateLock = habit.is_private ? " 🔒" : "";
        const rewards = formatPointRewards(habit.point_rewards);
        
        let buttonHTML = "";
        if (isCompleted) {
          buttonHTML = `<button class="quest-action-btn completed" disabled id="quest-btn-${habit.id}">Validé</button>`;
        } else {
          if (habit.type === "binary") {
            buttonHTML = `<button class="quest-action-btn" id="quest-btn-${habit.id}" data-id="${habit.id}">Valider</button>`;
          } else {
            buttonHTML = `<button class="quest-action-btn" id="quest-btn-${habit.id}" data-id="${habit.id}" data-type="quant" data-unit="${habit.unit || ''}">Logger</button>`;
          }
        }

        questItem.innerHTML = `
          <div class="quest-details">
            <span class="quest-name" id="quest-name-${habit.id}">${habit.name}${privateLock}</span>
            <span class="quest-desc" id="quest-desc-${habit.id}">${habit.description || 'Quête journalière'}</span>
            <span class="quest-reward-tag" id="quest-rewards-${habit.id}">Récompense : ${rewards}</span>
          </div>
          <div class="quest-action">
            ${buttonHTML}
          </div>
        `;

        questsListContainer.appendChild(questItem);
      });

      // Bind click handlers to buttons
      document.querySelectorAll(".quest-action-btn:not(.completed)").forEach(btn => {
        btn.addEventListener("click", async (e) => {
          const habitId = parseInt(e.target.getAttribute("data-id"));
          const isQuant = e.target.getAttribute("data-type") === "quant";
          const unit = e.target.getAttribute("data-unit");

          let amount = null;
          let logType = "done";

          if (isQuant) {
            const promptVal = prompt(`Combien de ${unit} voulez-vous logger ?`);
            if (promptVal === null) return;
            
            amount = parseInt(promptVal);
            if (isNaN(amount) || amount <= 0) {
              alert("Veuillez saisir un entier positif.");
              return;
            }
            logType = "log";
          }

          try {
            const response = await fetch(`${API_BASE}/logs`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                habit_id: habitId,
                log_type: logType,
                amount: amount
              })
            });

            if (!response.ok) throw new Error("Erreur de log");
            showToast("Félicitations ! Quête accomplie ! ✨");
            refreshAll();

          } catch (error) {
            console.error(error);
            showToast("Erreur lors de la validation", true);
          }
        });
      });

    } catch (error) {
      console.error(error);
      questsListContainer.innerHTML = `<p style="color: var(--accent-red); font-size: 0.9rem; text-align: center;">Erreur de chargement des quêtes.</p>`;
    }
  }

  // 4. Change day score template on dropdown toggle
  templateSelect.addEventListener("change", async () => {
    const selectedTemplate = templateSelect.value;
    try {
      const response = await fetch(`${API_BASE}/profile/template`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ template_name: selectedTemplate })
      });

      if (!response.ok) throw new Error("Erreur template change");
      const data = await response.json();

      showToast(`Template mis à jour : ${data.active_template} 🩹`);
      refreshAll();

    } catch (error) {
      console.error(error);
      showToast("Erreur de mise à jour du template", true);
    }
  });

  // 5. Quest Creation Modal Events
  openAddModalBtn.addEventListener("click", () => {
    addQuestModal.classList.add("active");
  });

  closeModalBtn.addEventListener("click", () => {
    addQuestModal.classList.remove("active");
  });

  // Close modal if user clicks outside of it
  window.addEventListener("click", (e) => {
    if (e.target === addQuestModal) {
      addQuestModal.classList.remove("active");
    }
  });

  // Show/Hide unit field based on type selected
  newQuestType.addEventListener("change", () => {
    if (newQuestType.value === "quantitative") {
      unitGroup.style.display = "flex";
    } else {
      unitGroup.style.display = "none";
    }
  });

  // Handle habit form submit
  addQuestForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const name = document.getElementById("new-quest-name").value.trim();
    const desc = document.getElementById("new-quest-desc").value.trim();
    const type = newQuestType.value;
    const unit = document.getElementById("new-quest-unit").value.trim() || null;
    const stat = document.getElementById("new-quest-stat").value;
    const points = parseInt(document.getElementById("new-quest-points").value);
    const cap = parseInt(document.getElementById("new-quest-cap").value) || null;
    const isPrivate = document.getElementById("new-quest-private").checked;

    // Package point rewards
    const pointRewards = { [stat]: points };

    try {
      const response = await fetch(`${API_BASE}/habits`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name,
          type: type,
          description: desc,
          point_rewards: pointRewards,
          daily_cap: cap,
          unit: unit,
          is_private: isPrivate
        })
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Erreur de création de quête");
      }

      showToast(`Quête "${name}" ajoutée au Grimoire ! 📜`);
      
      // Close and Reset Form
      addQuestModal.classList.remove("active");
      addQuestForm.reset();
      unitGroup.style.display = "none";

      refreshAll();

    } catch (error) {
      console.error(error);
      showToast(error.message || "Erreur de création", true);
    }
  });

  // 6. Fetch and render Progression Calendar
  async function fetchHistory() {
    try {
      const response = await fetch(`${API_BASE}/history`);
      if (!response.ok) throw new Error("Erreur history API");
      const history = await response.json();

      const calendarContainer = document.getElementById("calendar-grid-container");
      if (calendarContainer) {
        calendarContainer.innerHTML = "";
        history.forEach(day => {
          const dot = document.createElement("div");
          dot.className = `calendar-day-dot ${day.status}`;
          
          // Translate DB status to readable tooltip
          let statusText = "Incomplet / Échec ❌";
          if (day.status === "perfect") statusText = "Journée Parfaite ! ⭐";
          else if (day.status === "acceptable") statusText = "Journée Acceptable 👍";
          
          dot.title = `${day.label} : ${statusText}`;
          calendarContainer.appendChild(dot);
        });
      }
    } catch (error) {
      console.error(error);
    }
  }

  function refreshAll() {
    fetchProfile();
    fetchStreaks();
    fetchQuests();
    fetchHistory();
  }

  // Initial Load
  refreshAll();

  // Auto-Sync
  setInterval(refreshAll, 10000);
});
