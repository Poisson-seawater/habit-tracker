document.addEventListener("DOMContentLoaded", () => {
  // Config
  const API_BASE = "/api/v1";

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

  // ==============================================
  // FETCH PROFILE & DAILY DASHBOARD               //
  // ==============================================
  async function fetchProfile() {
    try {
      const response = await fetch(`${API_BASE}/profile`);
      if (!response.ok) throw new Error("Erreur profile API");
      const data = await response.json();

      // Update RPG Level & XP Bar dynamically
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
        history.forEach(day => {
          const dot = document.createElement("div");
          dot.className = `calendar-day-dot ${day.status}`;
          
          let statusText = "Failed / Incomplet ❌";
          if (day.status === "perfect") statusText = "Perfect Day ! (+5 XP) 🏆";
          
          dot.title = `${day.label} : ${statusText}`;
          calendarContainer.appendChild(dot);
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
  async function fetchGoals() {
    try {
      const response = await fetch(`${API_BASE}/goals`);
      if (!response.ok) throw new Error("Erreur fetch goals");
      const goals = await response.json();

      const listContainer = document.getElementById("goals-list-container");
      if (!listContainer) return;

      listContainer.innerHTML = "";
      if (goals.length === 0) {
        listContainer.innerHTML = `<p style="color: var(--text-secondary); text-align: center; padding: 2rem 0;">Aucun objectif principal forgié. Créez-en un à droite ! 🏆</p>`;
        return;
      }

      // Cache elements to update Goal/Substep creators dropdowns
      const substepGoalSelect = document.getElementById("substep-goal-select");
      const linkGoalSelect = document.getElementById("link-goal-select");
      const blockerSelect = document.getElementById("substep-blocker-select");
      const linkSubstepSelect = document.getElementById("link-substep-select");
      const targetSelect = document.getElementById("block-target-select");
      const sourceSelect = document.getElementById("block-source-select");

      // Dynamic Dropdowns Sync
      if (substepGoalSelect) substepGoalSelect.innerHTML = "";
      if (linkGoalSelect) linkGoalSelect.innerHTML = "";
      if (blockerSelect) blockerSelect.innerHTML = `<option value="">-- Aucune (déverrouillé d'office) --</option>`;
      if (linkSubstepSelect) linkSubstepSelect.innerHTML = "";
      if (targetSelect) targetSelect.innerHTML = "";
      if (sourceSelect) sourceSelect.innerHTML = "";

      const substepsMap = new Map(); // Keep track of unique substeps

      goals.forEach(goal => {
        // Dropdown additions
        if (substepGoalSelect) substepGoalSelect.innerHTML += `<option value="${goal.id}">${goal.title}</option>`;
        if (linkGoalSelect) linkGoalSelect.innerHTML += `<option value="${goal.id}">${goal.title}</option>`;

        const card = document.createElement("div");
        card.className = "glass-card goal-card";

        // Calculate progress percentage
        const totalSteps = goal.substeps.length;
        const completedSteps = goal.substeps.filter(s => s.completed).length;
        const percent = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;

        let substepsHTML = "";
        if (totalSteps === 0) {
          substepsHTML = `<p style="font-size: 0.8rem; color: var(--text-muted); text-align: center; padding: 10px;">Aucune sous-étape. Liez des étapes pour commencer !</p>`;
        } else {
          goal.substeps.forEach(s => {
            substepsMap.set(s.id, s.title);
            
            const isCompleted = s.completed;
            const isBlocked = s.is_blocked;
            const lockIcon = isBlocked ? "🔒 " : "";
            
            let btnHTML = "";
            if (isCompleted) {
              btnHTML = `<button class="substep-btn-check completed" disabled>Validée</button>`;
            } else if (isBlocked) {
              btnHTML = `<button class="substep-btn-check" disabled style="background: rgba(255,255,255,0.05); color: var(--text-muted); cursor: not-allowed; box-shadow: none;">Bloquée</button>`;
            } else {
              btnHTML = `<button class="substep-btn-check action-complete-substep" data-id="${s.id}">Valider (+${s.gold_reward}g)</button>`;
            }

            const statsTags = s.stats.map(st => `<span class="substep-tag">${STAT_LABELS[st.toLowerCase()] || st}</span>`).join(" ");

            substepsHTML += `
              <div class="substep-node ${isCompleted ? 'completed-step' : ''} ${isBlocked ? 'blocked-step' : ''}">
                <div class="substep-left">
                  <span>${lockIcon}<strong>${s.title}</strong></span>
                  ${statsTags}
                </div>
                <div>
                  ${btnHTML}
                </div>
              </div>
            `;
          });
        }

        card.innerHTML = `
          <div class="goal-header-row">
            <span class="goal-title">${goal.title} ${goal.completed ? "🎉" : ""}</span>
            <span class="substep-tag" style="background: rgba(6, 182, 212, 0.15); color: var(--accent-cyan);">${percent}% complété</span>
          </div>
          <div class="goal-description">${goal.description || 'Arbre de quêtes long terme.'}</div>
          <div class="goal-progress-bar-container">
            <div class="goal-progress-bar-fill" style="width: ${percent}%;"></div>
          </div>
          <div class="substeps-tree">
            ${substepsHTML}
          </div>
        `;
        listContainer.appendChild(card);
      });

      // Populate unique substeps dropdown selectors
      substepsMap.forEach((title, id) => {
        const optionHTML = `<option value="${id}">${title}</option>`;
        if (blockerSelect) blockerSelect.innerHTML += optionHTML;
        if (linkSubstepSelect) linkSubstepSelect.innerHTML += optionHTML;
        if (targetSelect) targetSelect.innerHTML += optionHTML;
        if (sourceSelect) sourceSelect.innerHTML += optionHTML;
      });

      // Bind Complete button handlers
      document.querySelectorAll(".action-complete-substep").forEach(btn => {
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

    } catch (e) {
      console.error(e);
    }
  }

  // Bind Screen 2 Form Submissions
  document.getElementById("create-goal-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = document.getElementById("goal-title-input").value.trim();
    const desc = document.getElementById("goal-desc-input").value.trim();

    try {
      const resp = await fetch(`${API_BASE}/goals`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, description: desc })
      });
      if (!resp.ok) throw new Error();
      showToast("Arbre d'Objectif principal forgé avec succès ! 🏆");
      document.getElementById("create-goal-form").reset();
      fetchGoals();
    } catch {
      showToast("Erreur lors de la création de l'objectif", true);
    }
  });

  document.getElementById("create-substep-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const goalId = document.getElementById("substep-goal-select").value;
    const title = document.getElementById("substep-title-input").value.trim();
    const gold = parseInt(document.getElementById("substep-gold-input").value) || 0;
    
    // Parse stats
    const statsInput = document.getElementById("substep-stats-input").value;
    const stats = statsInput.split(",").map(s => s.trim().toLowerCase()).filter(s => s in STAT_LABELS);
    
    const blockerId = document.getElementById("substep-blocker-select").value;
    const blockers = blockerId ? [parseInt(blockerId)] : [];

    try {
      const resp = await fetch(`${API_BASE}/goals/${goalId}/substeps`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: title,
          gold_reward: gold,
          stats_json: stats,
          blocked_by_ids: blockers
        })
      });
      if (!resp.ok) throw new Error();
      showToast("Sous-étape ajoutée et verrous forgés ! ⛓️");
      document.getElementById("create-substep-form").reset();
      fetchGoals();
    } catch {
      showToast("Erreur lors de la création de la sous-étape", true);
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
      fetchGoals();
    } catch {
      showToast("Erreur lors du partage de la sous-étape", true);
    }
  });

  document.getElementById("add-blocker-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const targetId = parseInt(document.getElementById("block-target-select").value);
    const sourceId = parseInt(document.getElementById("block-source-select").value);

    try {
      const resp = await fetch(`${API_BASE}/substeps/${targetId}/dependency`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ blocked_by_id: sourceId })
      });
      if (!resp.ok) throw new Error();
      showToast("Verrou de blocage DAG forgé ! 🔒");
      fetchGoals();
    } catch {
      showToast("Erreur lors de la création du blocage", true);
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
      // Loop over 7 days in order
      const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
      const frDays = ["Lundi ⚔️", "Mardi ⚔️", "Mercredi ⚔️", "Jeudi ⚔️", "Vendredi ⚔️", "Samedi 💤", "Dimanche 💤"];

      days.forEach((day, idx) => {
        const statsObj = potentials[day] || {};
        const statsStr = Object.entries(statsObj)
          .filter(([_, val]) => val > 0)
          .map(([stat, val]) => `${STAT_LABELS[stat.toLowerCase()] || stat}: +${val}`)
          .join(", ");

        tbody.innerHTML += `
          <tr>
            <td><strong>${frDays[idx]}</strong></td>
            <td>${statsStr || '<span style="color: var(--text-muted);">Aucune stat planifiée</span>'}</td>
          </tr>
        `;
      });
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

  // Initial loads
  refreshAll();
  setupBountiesEvents();

  // Auto-sync dashboard every 12 seconds
  setInterval(refreshAll, 12000);
});
