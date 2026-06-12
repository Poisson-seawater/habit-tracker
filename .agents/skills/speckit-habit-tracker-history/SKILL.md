---
name: "speckit-habit-tracker-history"
description: "Recalls the complete history of features implemented, database migrations, and development milestones in the Habit Tracker."
compatibility: "Habit Tracker project"
metadata:
  author: "Antigravity"
  purpose: "Activity logging and codebase history memory"
---

## Overview

This skill records the log of features added, major refactorings, database schema versions, and testing configurations in Gabriel's **Habit RPG Tracker** repository.

Agents **MUST** consult this history skill to understand what features have already been built, what migration files correspond to which tables, and the context of previous implementation iterations.

---

## 1. Project Implementation History & Milestones

### Milestone 1: Core RPG Engine & Bot Integration (Initial)
* **Goal**: Build the basic database, scheduled tasks, and Telegram Bot interactions.
* **Features**:
  * FastAPI endpoints supporting CRUD for habits, daily scores, templates, and todos.
  * Integration with Telegram Bot via `python-telegram-bot` to done/log/skip habits and check daily `/status`.
  * Multi-user configuration based on `X-User-ID` HTTP header for the frontend, and `chat_id` for Telegram Bot matching.
  * Local DB path at `backend/data/habit_tracker.db` and Production Pi DB path at `/data/habit_tracker.db`.

### Milestone 2: Goals, Substeps & Execution Order (Spec 002)
* **Goal**: Enable player tracking of long-term milestones divided into logical sequential substeps.
* **Features**:
  * `Goal`, `SubStep`, and `GoalSubStepLink` models created in `models.py`.
  * Completed substeps reward player gold, trigger passive stat increments, and auto-complete the parent Goal if all child substeps are marked completed.
  * horizontal columns in UI grouping substeps by `execution_order` with connections representing dependency sequences.
  * Large Slide-Out Drawer for creation, and centered scale-in modal popup for editing goals and substeps.

### Milestone 3: Softskill Progress Tree & Interactive Editor (Spec 003)
* **Goal**: Visualizing pure RPG character progress for self-improvement and internal work, separate from external goals, and adding interactive editing capabilities for both branches and skills.
* **Features**:
  * **Config Configuration & Safety** (`softskill_service.py`):
    * Static layout file `backend/src/data/softskills_tree.json` specifying coordinates, prerequisite trees, connection line colors, and descriptions.
    * Added configuration mutation functions with strict cycle detection (DFS-based) preventing circular dependencies when adding/updating prerequisites.
    * Automatic database cascade cleanup: deleting a skill wipes its associated progress records in the `user_softskill_progress` table. Deleting a branch removes all associated skills and their progress.
  * **FastAPI CRUD Routes** (`routes.py`):
    * `GET /api/v1/softskills` returns combined tree nodes and active user's level/completion progress.
    * `POST /api/v1/softskills/{softskill_id}/test` updates the custom success test text.
    * `POST /api/v1/softskills/{softskill_id}/complete` toggles completion status.
    * `POST /api/v1/softskills/branches` & `PUT /api/v1/softskills/branches/{key}` & `DELETE /api/v1/softskills/branches/{key}` for branch management.
    * `POST /api/v1/softskills/skills` & `PUT /api/v1/softskills/skills/{skill_id}` & `DELETE /api/v1/softskills/skills/{skill_id}` for skill management.
  * **Vanilla JS, CSS Grid & SVG UI** (`index.html`, `app.js`):
    * Re-architected softskills layout into a two-column viewport: a left-side branch selector and a right-side scrollable tree.
    * **Interactive Sidebar selector list**: Lists branches (color-coded dots) and sub-skills grouped together. Clic on a branch title highlights its skills (dimming the rest of the tree and SVG lines). Clic on a skill triggers a smooth scroll view alignment and a scale pulse highlight animation on the tree node.
    * **Detail Drawer Edit Modes**: Toggles sub-forms in the right-hand slide-out drawer, allowing full edit/creation of skills (with dependency checkboxes) and branch customization (keys, colors) without page reloads.
  * **PyTest Suite** (`test_softskills.py`):
    * Added comprehensive route tests using `mock_config_file` temporary fixtures to test config mutations in isolation without writing to the live database or original json layout.

### Milestone 4: Habit Streak Tracker & Interactive Calendar (Spec 004)
* **Goal**: Enable streak tracking with custom frequencies, soft deactivation/reactivation rules, and a detailed visual monthly calendar history.
* **Features**:
  * **Database columns**: Added `is_active`, `deactivated_at`, and `created_at` fields to the `Habit` model.
  * **Streak Logic & Rewards**: Continuity calculations ignore non-scheduled days, preserve streak on skips with reasons, reset only when scheduled days are missed, and award XP/Gold milestones at 30-day and 90-day marks.
  * **FastAPI Backend API**:
    * Soft-deactivation (DELETE) and reactivation (PUT) with 14-day freeze rules (re-activating after 14 days resets the streak to 0).
    * `GET /api/v1/habits/{habit_id}/calendar` resolving day states: `pre-creation`, `non-scheduled`, `completed`, `skipped`, and `missed`.
  * **Frontend Calendar UI**: Glassmorphism sliding detail drawer with previous/next month calendar grids, status-colored badges, and dynamic tooltips.
  * **PyTest Suite** (`test_habit_streaks.py`): Testing freeze rules, milestone rewards, and calendar resolution.

### Milestone 5: Reward Shop & Purchase Logic (Spec 005)
* **Goal**: Add a shop category allowing users to buy custom rewards with accumulated gold.
* **Features**:
  - `Reward` and `PurchaseLog` models created in `models.py`.
  - Check locks/requirements: rewards can be locked by unobtained softskills or uncompleted goals.
  - CRUD routes for rewards and `/rewards/{reward_id}/purchase` endpoint.
  - Interactive checkout modal in frontend.

### Milestone 6: Allostasis Rewards & Weekly Reset (Spec 006)
* **Goal**: Support specific Allostasis daily/weekly tasks that are free and reset at midnight / Monday morning.
* **Features**:
  - Added `allostasis_daily` and `allostasis_weekly` categories to rewards.
  - Reset logic in `scheduler.py` resetting availability.
  - Integration in Telegram Bot with `/shop` showing task status.

### Milestone 7: 3-3-3 Recap Dashboard Panel (Spec 007)
* **Goal**: Visually track the top 3 goals, top 3 softskills, and 3 active allostasis activities vertically on the main page.
* **Features**:
  - Added user fields `pinned_substeps` and `pinned_softskills` to store JSON arrays of pins.
  - Selection overlay drawer with checkboxes restricted to 3 choices max.
  - Navigation focusing: clicking a pinned item redirects to its respective tab and highlights the target node with a custom animation.
  - Inline Allostasis checklist validation directly on the dashboard.

---

## 2. Database Migration Log

Manual SQLite migrations are stored under `backend/src/database/migrations/`.

| Version | Migration File | Description |
|---|---|---|
| `v1` | (Base schema) | Initialization of `users`, `habits`, `habit_logs`, `daily_scores`, `perfect_day_templates`, `todos`, `no_todos`, `goals`, `substeps`, `goal_substep_links`. |
| `v2` | `v2_migration.sql` | Migration to handle database updates for v2 schemas. |
| `v3` | `v3_substep_order.sql` | Adds `execution_order` to the `substeps` table to layout goal milestones. |
| `v4` | `v4_softskills.sql` | Creates `user_softskill_progress` table tracking per-user completion and custom success criteria for softskills. |
| `v5` | `v5_habit_deactivation.sql` | Adds `is_active`, `deactivated_at`, and `created_at` columns to the `habits` table. |
| `v6` | `v6_rewards.sql` | Creates `rewards` and `purchase_logs` tables. |
| `v7` | `v7_allostasis_rewards.sql` | Modifies categories to support daily/weekly allostasis types. |
| `v8` | `v8_pinned_items.sql` | Adds `pinned_substeps` and `pinned_softskills` TEXT columns to `users`. |

---

## 3. Test Environments & Isolation Gotchas

### FastAPI Dependency Overrides
When testing routes, `app.dependency_overrides[get_db]` must be clean. 
* **DO NOT** register overrides at the global/module level of test files without cleaning up.
* **DO** use module-scoped pytest fixtures that clean up their overrides on teardown:
  ```python
  @pytest.fixture(scope="module")
  def setup_test_db():
      # Register overrides
      app.dependency_overrides[get_db] = override_db_func
      yield
      # Clean up overrides
      del app.dependency_overrides[get_db]
  ```

### Local vs. Docker Testing
* Local pytest uses local environment configs.
* Docker environment runs on port `5000` mapping path `./data` to `/data`.
* Rebuilding Docker containers is required after python backend edits: `docker compose up -d --build`.
