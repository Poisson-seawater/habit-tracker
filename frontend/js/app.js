document.addEventListener("DOMContentLoaded", () => {
  // Config
  const API_BASE = "/api/v1";

  // Override fetch to always include X-User-ID header if logged in
  const originalFetch = window.fetch;
  window.fetch = async function(url, options = {}) {
    const userId = localStorage.getItem('user_id');
    if (userId) {
      options.headers = options.headers || {};
      options.headers['X-User-ID'] = userId;
    }
    return originalFetch(url, options);
  };

  // Navigation Tabs
  const navTabs = document.querySelectorAll(".nav-tab");
  const tabContents = document.querySelectorAll(".tab-content");

  navTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const targetTab = tab.getAttribute("data-tab");
      
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
        fetchWeeklyPotentials();
      }
    });
  });

  // Profile and Dashboard Elements
  const charLevel = document.getElementById("char-level");
  const badgeStatus = document.getElementById("badge-status");
  const templateSelect = document.getElementById("template-select");
  const questsListContainer = document.getElementById("quests-list-container");
  const toastNotification = document.getElementById("toast-notification");
  
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

  // 12 RPG Stats helper mapping
  const STAT_LABELS = {
    "force": "Force 💪",
    "endurance": "Endurance 🏃‍♂️",
    "mobilite": "Mobilité 🧘‍♂️",
    "discipline": "Discipline ⚔️",
    "creativite": "Créativité 🎨",
    "connaissance": "Connaissance 📚",
    "sociabilite": "Sociabilité 🤝",
    "sante_mentale": "Santé Mentale 🧠",
    "finance": "Finance 💰",
    "organisation": "Organisation 📂",
    "spiritualite": "Spiritualité 🌌",
    "repos": "Repos 💤"
  };

  // Helper to format stat list for rewards description
  function formatPointRewards(rewards) {
    return Object.entries(rewards)
      .map(([stat, val]) => `+${val} ${STAT_LABELS[stat.toLowerCase()] || stat}`)
      .join(", ");
  }

  const substepStatsDropdowns = ["substep-stat-1", "substep-stat-2", "edit-substep-stat-1", "edit-substep-stat-2"];
  substepStatsDropdowns.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      Object.keys(STAT_LABELS).forEach(stat => {
        const option = document.createElement("option");
        option.value = stat;
        option.textContent = STAT_LABELS[stat];
        el.appendChild(option);
      });
    }
  });

  // ==============================================
  // FETCH PROFILE & DAILY DASHBOARD               //
  // ==============================================
  async function fetchProfile() {
    try {
      const response = await fetch(`${API_BASE}/profile`);
      if (!response.ok) throw new Error("Erreur profile API");
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

      // Update template dropdown selection
      if (data.active_template) {
        templateSelect.value = data.active_template;
      }
      
      // Update Daily Status Badge
      badgeStatus.textContent = data.scores.perfect_day_validated ? "🏆 Perfect Day !" : "🟥 Journée Incomplète";
      badgeStatus.className = "badge badge-status";
      if (!data.scores.perfect_day_validated) {
        badgeStatus.classList.add("failed");
      }

      // Update Character Sheet stats rows dynamically
      const statsContainer = document.getElementById("stats-container");
      if (statsContainer) {
        statsContainer.innerHTML = "";
        
        Object.keys(STAT_LABELS).forEach(stat => {
          const val = data.stats[stat] || 0;
          const target = data.thresholds[stat] || 0;
          const maxVal = Math.max(val, target, 10);
          const percent = Math.min((val / maxVal) * 100, 100);
          
          const statRow = document.createElement("div");
          statRow.className = `stat-row stat-${stat}`;
          
          let thresholdText = "";
          if (target > 0) {
            thresholdText = `<span style="font-size: 0.72rem; color: var(--text-muted);"> (Seuil: ${target})</span>`;
          }
          
          statRow.innerHTML = `
            <div class="stat-label-row">
              <span class="stat-name">${STAT_LABELS[stat]}${thresholdText}</span>
              <span class="stat-value">${val} pts</span>
            </div>
            <div class="stat-progress-track">
              <div class="stat-progress-bar" style="width: ${percent}%;"></div>
            </div>
          `;
          statsContainer.appendChild(statRow);
        });
      }

    } catch (error) {
      console.error(error);
      showToast("Erreur lors du chargement des statistiques", true);
    }
  }

  // ==============================================
  // ACTIVE QUESTS (HABITS CHECK-INS)             //
  // ==============================================
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

        const isCompleted = completedIds.includes(habit.id);
        const privateLock = habit.is_private ? " 🔒" : "";
        const rewards = formatPointRewards(habit.point_rewards);
        
        let buttonHTML = "";
        if (isCompleted) {
          buttonHTML = `<button class="quest-action-btn completed" disabled>Validé</button>`;
        } else {
          if (habit.type === "binary") {
            buttonHTML = `<button class="quest-action-btn done-action-btn" data-id="${habit.id}">Valider</button>`;
          } else {
            buttonHTML = `<button class="quest-action-btn log-action-btn" data-id="${habit.id}" data-unit="${habit.unit || ''}">Logger</button>`;
          }
        }

        questItem.innerHTML = `
          <div class="quest-details">
            <span class="quest-name">${habit.name}${privateLock}</span>
            <span class="quest-desc">${habit.description || 'Quête journalière'}</span>
            <span class="quest-reward-tag">Récompense : ${rewards}</span>
          </div>
          <div class="quest-action">
            ${buttonHTML}
          </div>
        `;
        questsListContainer.appendChild(questItem);
      });

      // Bind check-ins
      document.querySelectorAll(".done-action-btn").forEach(btn => {
        btn.addEventListener("click", async () => {
          const habitId = btn.getAttribute("data-id");
          await submitQuestLog(habitId, "done");
        });
      });

      document.querySelectorAll(".log-action-btn").forEach(btn => {
        btn.addEventListener("click", async () => {
          const habitId = btn.getAttribute("data-id");
          const unit = btn.getAttribute("data-unit");
          const val = prompt(`Combien de ${unit || 'points'} voulez-vous logger ?`);
          if (val === null) return;
          const amt = parseInt(val);
          if (isNaN(amt) || amt <= 0) {
            alert("Veuillez entrer une valeur positive valide.");
            return;
          }
          await submitQuestLog(habitId, "log", amt);
        });
      });

    } catch (error) {
      console.error(error);
      questsListContainer.innerHTML = `<p style="color: var(--accent-red); font-size: 0.9rem; text-align: center;">Erreur de chargement des quêtes.</p>`;
    }
  }

  async function submitQuestLog(habitId, logType, amount = null) {
    try {
      const response = await fetch(`${API_BASE}/logs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          habit_id: parseInt(habitId),
          log_type: logType,
          amount: amount
        })
      });

      if (!response.ok) throw new Error("Erreur de validation");
      showToast("Félicitations ! Quête quotidienne mise à jour ! ✨");
      refreshAll();
    } catch (error) {
      console.error(error);
      showToast("Erreur lors de l'enregistrement de l'habitude", true);
    }
  }

  // ==============================================
  // DAILY SCORES TEMPLATE OVERRIDES               //
  // ==============================================
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
      showToast(`Template réajusté : ${data.active_template.toUpperCase()} 🩹`);
      refreshAll();
    } catch (error) {
      console.error(error);
      showToast("Erreur lors du changement de template", true);
    }
  });

  // ==============================================
  // HISTORICAL Dot Calendar (30 Days)             //
  // ==============================================
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
        
        if (history.length > 0) {
            const firstDayOffset = history[0].weekday;
            for (let i = 0; i < firstDayOffset; i++) {
              const emptySlot = document.createElement("div");
              emptySlot.className = "calendar-day-empty";
              calendarContainer.appendChild(emptySlot);
            }
        }

        history.forEach(day => {
          const box = document.createElement("div");
          box.className = `calendar-day-box ${day.status}`;
          
          let statusText = day.status === "future" ? "À venir" : "Failed / Incomplet ❌";
          if (day.status === "perfect") statusText = "Perfect Day ! (+5 XP) 🏆";
          
          box.title = `${day.date} : ${statusText}`;
          box.textContent = day.label;
          calendarContainer.appendChild(box);
        });
      }
    } catch (error) {
      console.error(error);
    }
  }

  // ==============================================
  // BOUNTIES (TODOS / PRIMES)                     //
  // ==============================================
  async function fetchBounties() {
    try {
      const response = await fetch(`${API_BASE}/todos`);
      if (!response.ok) throw new Error("Erreur Todos API");
      const bounties = await response.json();

      const container = document.getElementById("bounties-list-container");
      if (!container) return;

      container.innerHTML = "";
      if (bounties.length === 0) {
        container.innerHTML = `<p style="color: var(--text-secondary); font-size: 0.85rem; text-align: center; padding: 1.5rem 0;">Aucune prime active. Déclarez vos exploits ! ⚔️</p>`;
        return;
      }

      bounties.forEach(b => {
        const item = document.createElement("div");
        item.className = "bounty-card";
        
        let rewardStatsText = "";
        if (b.stat_reward_1 && b.points_reward_1 > 0) {
          rewardStatsText += `(+${b.points_reward_1} ${STAT_LABELS[b.stat_reward_1.toLowerCase()] || b.stat_reward_1})`;
        }
        if (b.stat_reward_2 && b.points_reward_2 > 0) {
          rewardStatsText += ` (+${b.points_reward_2} ${STAT_LABELS[b.stat_reward_2.toLowerCase()] || b.stat_reward_2})`;
        }

        item.innerHTML = `
          <div class="bounty-info">
            <span class="bounty-title">${b.title}</span>
            <span class="bounty-xp-tag">🏆 +${b.xp_reward} XP ${rewardStatsText}</span>
          </div>
          <button class="substep-btn-check ${b.is_completed ? "completed" : ""}" data-id="${b.id}" ${b.is_completed ? "disabled" : ""}>
            ${b.is_completed ? "Réclamée" : "Réclamer"}
          </button>
        `;

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
        
        const stat1 = document.getElementById("new-bounty-stat-1").value || null;
        const pts1 = parseInt(document.getElementById("new-bounty-points-1").value) || 0;
        const stat2 = document.getElementById("new-bounty-stat-2").value || null;
        const pts2 = parseInt(document.getElementById("new-bounty-points-2").value) || 0;

        if (!title) {
          showToast("Veuillez donner un titre à la prime !", true);
          return;
        }

        try {
          const response = await fetch(`${API_BASE}/todos`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              title: title,
              xp_reward: xp,
              stat_reward_1: stat1,
              points_reward_1: pts1,
              stat_reward_2: stat2,
              points_reward_2: pts2
            })
          });

          if (!response.ok) throw new Error("Erreur de publication");
          showToast("Nouvelle prime publiée au tableau ! ⚔️");
          titleInput.value = "";
          xpInput.value = 20;
          document.getElementById("new-bounty-stat-1").value = "";
          document.getElementById("new-bounty-points-1").value = "5";
          document.getElementById("new-bounty-stat-2").value = "";
          document.getElementById("new-bounty-points-2").value = "0";
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
      const stats = substepData.stats || [];
      document.getElementById("edit-substep-stat-1").value = stats.length > 0 ? stats[0] : "";
      document.getElementById("edit-substep-stat-2").value = stats.length > 1 ? stats[1] : "";


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
  async function fetchGoals() {
    try {
      const response = await fetch(`${API_BASE}/goals`);
      if (!response.ok) throw new Error("Erreur fetch goals");
      const goals = await response.json();

      const selectorList = document.getElementById("goals-selector-list");
      if (!selectorList) return;

      selectorList.innerHTML = "";
      if (goals.length === 0) {
        selectorList.innerHTML = `<p style="color: var(--text-secondary); text-align: center; padding: 2rem 0; font-size: 0.85rem;">Aucun objectif principal. Créez-en un en cliquant sur + ! 🏆</p>`;
        renderGoalTree(null);
        return;
      }

      // Auto-select first goal if none or invalid activeGoalId
      const goalIds = goals.map(g => g.id);
      if (activeGoalId === null || !goalIds.includes(activeGoalId)) {
        activeGoalId = goals[0].id;
      }

      // Cache elements to update Goal/Substep creators dropdowns
      const substepGoalSelect = document.getElementById("substep-goal-select");
      const linkGoalSelect = document.getElementById("link-goal-select");
      const linkSubstepSelect = document.getElementById("link-substep-select");

      // Dynamic Dropdowns Sync
      if (substepGoalSelect) substepGoalSelect.innerHTML = "";
      if (linkGoalSelect) linkGoalSelect.innerHTML = "";
      if (linkSubstepSelect) linkSubstepSelect.innerHTML = "";

      const substepsMap = new Map(); // Keep track of unique substeps

      let activeGoal = null;

      goals.forEach(goal => {
        if (goal.id === activeGoalId) {
          activeGoal = goal;
        }

        // Dropdown additions
        if (substepGoalSelect) substepGoalSelect.innerHTML += `<option value="${goal.id}">${goal.title}</option>`;
        if (linkGoalSelect) linkGoalSelect.innerHTML += `<option value="${goal.id}">${goal.title}</option>`;

        // Render sidebar goal item
        const item = document.createElement("div");
        item.className = `goal-selector-item ${goal.id === activeGoalId ? 'active' : ''}`;
        
        // Calculate progress percentage
        const totalSteps = goal.substeps.length;
        const completedSteps = goal.substeps.filter(s => s.completed).length;
        const percent = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;

        item.innerHTML = `
          <div class="goal-selector-title">
            <span>${goal.title} ${goal.completed ? "🎉" : ""}</span>
            <span style="font-size: 0.75rem; color: var(--accent-cyan); font-weight: 700;">${percent}%</span>
          </div>
          <span class="goal-selector-meta">${totalSteps} sous-étape${totalSteps > 1 ? 's' : ''}</span>
          <div class="goal-selector-progress-track">
            <div class="goal-selector-progress-fill" style="width: ${percent}%;"></div>
          </div>
        `;

        item.addEventListener("click", () => {
          activeGoalId = goal.id;
          document.querySelectorAll(".goal-selector-item").forEach(el => el.classList.remove("active"));
          item.classList.add("active");
          renderGoalTree(goal);
        });

        selectorList.appendChild(item);

        goal.substeps.forEach(s => {
          substepsMap.set(s.id, s.title);
        });
      });

      // Populate unique substeps dropdown selectors
      substepsMap.forEach((title, id) => {
        const optionHTML = `<option value="${id}">${title}</option>`;
        if (linkSubstepSelect) linkSubstepSelect.innerHTML += optionHTML;
      });

      // Render Active Tree
      renderGoalTree(activeGoal);

    } catch (e) {
      console.error(e);
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

    // Header with actions
    let headerHTML = `
      <div class="skill-tree-header">
        <div>
          <span class="skill-tree-title">${goal.title} ${goal.completed ? "🎉" : ""}</span>
          <p style="font-size: 0.82rem; color: var(--text-muted); margin-top: 0.2rem;">${goal.description || 'Arbre de quêtes long terme.'} • ${percent}% complété</p>
        </div>
        <div class="skill-tree-actions">
          <button class="tree-icon-btn add-step" id="btn-add-substep" title="Nouvelle Sous-étape" style="font-size: 1.1rem; color: var(--accent-cyan);">➕</button>
          <button class="tree-icon-btn link" id="btn-link-substep" title="Liaisons & Verrous avancés" style="font-size: 1.1rem; color: var(--accent-purple);">🔗</button>
          <button class="tree-icon-btn edit" id="btn-edit-active-goal" title="Modifier l'objectif">✏️</button>
          <button class="tree-icon-btn delete" id="btn-delete-active-goal" title="Supprimer l'objectif">🗑️</button>
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

        let btnHTML = "";
        if (isCompleted) {
          btnHTML = `<span style="color: var(--accent-green); font-size: 0.75rem; font-weight: 700; margin-top: 0.4rem; display: flex; align-items: center; gap: 0.2rem;">✓ Complétée</span>`;
        } else {
          btnHTML = `<button class="tree-node-btn action-complete-substep" data-id="${s.id}">Valider</button>`;
        }

        const statsTags = s.stats.map(st => `<span class="substep-tag">${STAT_LABELS[st.toLowerCase()] || st}</span>`).join(" ");

        nodesHTML += `
          <div class="tree-node ${stateClass}" style="position: relative; padding-top: 1.6rem;">
            <div class="tree-node-actions" style="position: absolute; top: 8px; right: 8px; display: flex; gap: 0.4rem;">
              <span class="action-edit-substep-icon" data-id="${s.id}" style="cursor: pointer; font-size: 0.75rem; opacity: 0.6; hover: opacity: 1; transition: opacity 0.2s;" title="Modifier la sous-étape">✏️</span>
            </div>
            <span class="tree-node-title" style="margin-top: 0.2rem;"><span style="color: var(--text-muted); font-size: 0.75em; margin-right: 0.2em;">[Étape ${s.execution_order || 1}]</span> ${s.title}</span>
            ${s.description ? `<span class="tree-node-desc" style="font-size: 0.72rem; color: var(--text-muted); display: block; margin-top: 0.2rem; line-height: 1.2;">${s.description}</span>` : ""}
            <span class="tree-node-gold" style="margin-top: 0.3rem; display: block;">💰 +${s.gold_reward}g</span>
            <div class="tree-node-stats">${statsTags}</div>
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
    columnsHTML += `
      <div class="tree-column">
        <div class="tree-node ${goalIsCompleted ? 'completed-node' : 'unlocked-node'}" style="min-height: 120px;">
          <span class="substep-tag" style="background: rgba(234, 179, 8, 0.15); color: var(--accent-gold); font-size: 0.65rem;">OBJECTIF CENTRAL</span>
          <span class="tree-node-title" style="font-size: 1.1rem; color: var(--accent-green); margin-top: 0.3rem;">${goal.title}</span>
          <span class="tree-node-desc" style="font-size: 0.78rem;">${percent}% complété</span>
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
    document.getElementById("btn-edit-active-goal").addEventListener("click", () => openDrawer("edit", goal));
    document.getElementById("btn-delete-active-goal").addEventListener("click", () => deleteGoal(goal.id));

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

    try {
      let resp;
      if (editId) {
        resp = await fetch(`${API_BASE}/goals/${editId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title, description: desc })
        });
      } else {
        resp = await fetch(`${API_BASE}/goals`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title, description: desc })
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
    const gold = parseInt(document.getElementById("substep-gold-input").value) || 0;
    const order = parseInt(document.getElementById("substep-order-input").value) || 1;
    
    // Parse stats
    const stat1 = document.getElementById("substep-stat-1").value;
    const stat2 = document.getElementById("substep-stat-2").value;
    const stats = [stat1, stat2].filter(s => s !== "");

    try {
      const resp = await fetch(`${API_BASE}/goals/${goalId}/substeps`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: title,
          gold_reward: gold,
          stats_json: stats,
          execution_order: order
        })
      });
      if (!resp.ok) throw new Error();
      showToast("Sous-étape ajoutée et verrous forgés ! ⛓️");
      document.getElementById("create-substep-form").reset();
      closeDrawer();
      fetchGoals();
    } catch {
      showToast("Erreur lors de la création de la sous-étape", true);
    }
  });

  document.getElementById("edit-substep-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const subId = document.getElementById("edit-substep-id-input").value;
    const title = document.getElementById("edit-substep-title-input").value.trim();
    const desc = document.getElementById("edit-substep-desc-input").value.trim();
    const gold = parseInt(document.getElementById("edit-substep-gold-input").value) || 0;
    const order = parseInt(document.getElementById("edit-substep-order-input").value) || 1;
    
    // Parse stats
    const stat1 = document.getElementById("edit-substep-stat-1").value;
    const stat2 = document.getElementById("edit-substep-stat-2").value;
    const stats = [stat1, stat2].filter(s => s !== "");

    try {
      const resp = await fetch(`${API_BASE}/substeps/${subId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: title,
          description: desc,
          gold_reward: gold,
          stats_json: stats,
          execution_order: order
        })
      });
      if (!resp.ok) throw new Error();
      showToast("Sous-étape modifiée avec succès ! ✏️");
      closeDrawer();
      fetchGoals();
    } catch {
      showToast("Erreur lors de la modification de la sous-étape", true);
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
    const goalId = parseInt(document.getElementById("link-goal-select").value);

    try {
      const resp = await fetch(`${API_BASE}/substeps/link`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal_id: goalId, substep_id: subId })
      });
      if (!resp.ok) throw new Error();
      showToast("Sous-étape liée à l'arbre cible avec succès ! 🔗");
      closeDrawer();
      fetchGoals();
    } catch {
      showToast("Erreur lors du partage de la sous-étape", true);
    }
  });


  // ==============================================
  // SCREEN 3: SETTINGS & POTENTIALS               //
  // ==============================================
  const templateEditSelect = document.getElementById("template-edit-select");
  const editThresholdsForm = document.getElementById("edit-thresholds-form");
  const inputsContainer = document.getElementById("thresholds-inputs-container");

  templateEditSelect.addEventListener("change", loadSettingsThresholds);

  async function loadSettingsThresholds() {
    try {
      const response = await fetch(`${API_BASE}/templates`);
      if (!response.ok) throw new Error();
      const templates = await response.json();

      const activeTemplate = templateEditSelect.value;
      const thresholds = templates[activeTemplate] || {};

      inputsContainer.innerHTML = "";
      Object.keys(STAT_LABELS).forEach(stat => {
        const currentVal = thresholds[stat] || 0;
        inputsContainer.innerHTML += `
          <div class="form-group">
            <label>${STAT_LABELS[stat]}</label>
            <input type="number" name="${stat}" value="${currentVal}" min="0" required style="background: rgba(255,255,255,0.03); padding: 8px; border: 1px solid var(--border-glass); border-radius: 8px;">
          </div>
        `;
      });
    } catch {
      showToast("Erreur de récupération des templates", true);
    }
  }

  editThresholdsForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const activeTemplate = templateEditSelect.value;
    
    const thresholds = {};
    const inputs = inputsContainer.querySelectorAll("input");
    inputs.forEach(inp => {
      const val = parseInt(inp.value) || 0;
      if (val > 0) {
        thresholds[inp.name] = val;
      }
    });

    try {
      const response = await fetch(`${API_BASE}/templates`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          template_name: activeTemplate,
          thresholds_json: thresholds
        })
      });
      if (!response.ok) throw new Error();
      showToast("Seuils de Perfect Day mis à jour ! ⚙️");
      refreshAll();
    } catch {
      showToast("Erreur lors de l'enregistrement", true);
    }
  });

  async function fetchWeeklyPotentials() {
    try {
      const resp = await fetch(`${API_BASE}/quests/daily-stats-potentials`);
      if (!resp.ok) throw new Error();
      const potentials = await resp.json();

      const tbody = document.getElementById("potentials-table-body");
      if (!tbody) return;

      tbody.innerHTML = "";
      const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

      Object.keys(STAT_LABELS).forEach(stat => {
        let hasAnyPoints = false;
        let rowHtml = `<tr><td><strong>${STAT_LABELS[stat]}</strong></td>`;
        
        days.forEach(day => {
          const statsObj = potentials[day] || {};
          const val = statsObj[stat.toLowerCase()] || 0;
          if (val > 0) {
            hasAnyPoints = true;
            rowHtml += `<td style="color: var(--accent-green); font-weight: bold; text-align: center;">+${val}</td>`;
          } else {
            rowHtml += `<td style="color: var(--text-muted); text-align: center;">-</td>`;
          }
        });
        
        rowHtml += `</tr>`;
        
        if (hasAnyPoints) {
          tbody.innerHTML += rowHtml;
        }
      });
      
      if (tbody.innerHTML === "") {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 1rem;">Aucune stat planifiée cette semaine</td></tr>`;
      }
    } catch {
      console.error("Erreur de récupération des potentiels");
    }
  }

  // Refresh helper
  function refreshAll() {
    fetchProfile();
    fetchQuests();
    fetchHistory();
    fetchBounties();
  }

  // Multi-user Login & Initialization
  const currentUserId = localStorage.getItem('user_id');
  if (!currentUserId) {
    showLoginScreen();
  } else {
    initializeApp();
  }

  async function showLoginScreen() {
    const overlay = document.getElementById("login-overlay");
    const usersContainer = document.getElementById("login-users-container");
    if (overlay) overlay.style.display = "flex";
    
    try {
      const resp = await fetch(`${API_BASE}/users`);
      const users = await resp.json();
      if (usersContainer) {
        usersContainer.innerHTML = "";
        users.forEach(u => {
          const btn = document.createElement("button");
          btn.className = "login-user-btn";
          btn.innerHTML = `<span class="login-user-name">${u.username}</span>`;
          btn.onclick = () => {
            localStorage.setItem('user_id', u.id);
            if (overlay) overlay.style.display = "none";
            initializeApp();
          };
          usersContainer.appendChild(btn);
        });
      }
    } catch (e) {
      if (usersContainer) usersContainer.innerHTML = "<p style='color: var(--accent-red);'>Erreur de chargement des profils.</p>";
    }
  }

  function initializeApp() {
    refreshAll();
    setupBountiesEvents();
    // Auto-sync dashboard every 12 seconds
    setInterval(refreshAll, 12000);
  }

  // Logout Logic
  const switchProfileBtn = document.getElementById("switch-profile-btn");
  if (switchProfileBtn) {
    switchProfileBtn.addEventListener("click", () => {
      localStorage.removeItem('user_id');
      window.location.reload();
    });
  }
});
