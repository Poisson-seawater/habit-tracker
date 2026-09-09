---
name: "speckit-habit-tracker-memory"
description: "Recalls design decisions, codebase architecture, and implementation details for Gabriel's Habit Tracker project."
metadata:
  author: "Antigravity"
  purpose: "Knowledge recall and codebase memory"
  compatibility: "Habit Tracker current project"
---

## Overview

This skill contains the comprehensive developer memory, architectural patterns, database schemas, and UX design decisions for Gabriel's self-hosted, RPG-style **Habit Tracker**. 

Whenever you need to make changes, modify features, or debug the habit tracker, you **MUST** read this skill file first to align with established patterns.

---

## 1. Project Architecture

The application is split into a robust, fast backend API service and an interactive, glassmorphic frontend application.

```mermaid
graph TD
    User([Gabriel]) <--> Frontend[Vanilla CSS / JS / HTML]
    Frontend <--> |FastAPI HTTP Endpoints| Backend[Python FastAPI Service]
    Backend <--> |SQLAlchemy ORM| DB[(SQLite Database)]
```

### Key Files
- **Backend Directory**: `/backend`
  - [models.py](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/backend/src/database/models.py): Declares database tables and SQLAlchemy schemas.
  - [routes.py](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/backend/src/api/routes.py): Handles REST API endpoints and Pydantic validation schemas.
  - [seed.py](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/backend/src/database/seed.py): Seeds database structures on startup.
- **Frontend Directory**: `/frontend`
  - [index.html](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/frontend/index.html): Houses layouts, glassmorphic styles, and DOM node structures.
  - [app.js](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/frontend/js/app.js): Handles state, routing, visual DAG skill-tree column renders, and network fetches.
  - [style.css](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/frontend/css/style.css): Main stylesheet with primary HSL colors and dashboard widgets.

---

## Current Truth Notes

- The old daily RPG stat/threshold system has been removed from the live schema.
  Do not describe current habits, todos, substeps, or Perfect Day validation as
  awarding daily character-sheet stats.
- Current day types are `rest`, `regular`, and `hustle`; older names such as
  `week`, `weekend`, `recup`, and `malade` are historical aliases/context only.
- Day types are server-authoritative. A fixed four-week cycle contains three
  normal weeks and one less-intense week, with a configurable seven-day map for
  each week type. Defaults are Monday-Friday `regular`, Saturday `hustle`, and
  Sunday `rest`; the less-intense week changes Saturday to `regular`.
- Cycle policies may take effect today or in the future. Keep at most one pending
  future policy, preserve past policies, and resolve historical days from their
  `DailyScore` snapshot when one exists.
- `Feel off today` is the only manual day-type exception. It creates a reversible
  dated `rest` override for today, then fully recalculates the score, Perfect Day,
  effort budgets, agenda filtering, streak transitions, and the existing +/-5 XP
  transition without deleting habit logs or failures.
- Do not restore the dashboard day selector, Telegram `/set-day` or `/template`,
  API `/api/v1/profile/template`, or habitctl `template-set`. Remote control uses
  protocol v3 actions `feel-off` and `day-plan-restore`.
- The dashboard uses cookie sessions and approved devices. `X-User-ID` remains
  important compatibility for local development, tests, bot/automation, and the
  habit-tracker-control plugin.
- For spec status, check `specs/ETAT_DES_SPECS.md` before relying on old `tasks.md`
  checkboxes.

---

## 2. Database Models & Schema

The core relational structure is defined using SQLAlchemy. The relationships allow a structured progression of substeps under goals, grouped by their execution order.

### 1. `Goal`
Represents high-level player objectives.
- `id` (Integer, Primary Key)
- `title` (String, Required)
- `description` (Text, Optional)
- `completed` (Boolean, default: `False`)

### 2. `SubStep`
Represents tasks or stages necessary to accomplish a goal.
- `id` (Integer, Primary Key)
- `title` (String, Required)
- `description` (Text, Optional)
- `gold_reward` (Integer, default: `150`)
- `execution_order` (Integer, default: `1`)
- `completed` (Boolean, default: `False`)
- `effort_type` / `effort_minutes` style fields for current Perfect Day budget
  accounting where present in the live model.
- `is_life_lore` (Boolean) marks permanent achievement entries.



### 3. `SubStepGoalLink`
Maps many-to-many linkages so steps can belong to multiple goal trees.
- `goal_id` (Integer, Foreign Key)
- `substep_id` (Integer, Foreign Key)

### 4. `Habit`
Represents character habits and scheduled check-ins.
- `id` (Integer, Primary Key)
- `user_id` (Integer, Foreign Key)
- `name` (String, Required)
- `type` (String, "binary" or "quantitative")
- `frequency` (String, default: "daily")
- `scheduled_days` (String, default: "0,1,2,3,4,5,6")
- `is_active` (Boolean, default: `True`)
- `deactivated_at` (DateTime, Optional)
- `created_at` (DateTime, default: `datetime.now`)

### 5. `User`
Represents character profile and pinned goals/softskills.
- `id` (Integer, Primary Key)
- `username` (String)
- `level` (Integer, default: `1`)
- `xp` (Integer, default: `0`)
- `gold` (Integer, default: `0`)
- `pinned_substeps` (TEXT, serialized JSON list of integers)
- `pinned_softskills` (TEXT, serialized JSON list of strings)
- Google OAuth/status fields and auth/session/device fields exist in the live
  model; inspect `models.py` before changing authentication or sync behavior.

### 6. `BiologicalZone`
Represents user-configurable biological capacity windows for Perfect Day rendering.
- `user_id` scopes each zone to a player.
- `zone_name`, `zone_type`, `start_time`, `end_time`, `color`, and
  `display_order` drive the timeline UI.

### 7. `DailyAgendaPlacement`
Stores per-date quest placements for the vertical agenda/timeline.

### 8. `DayCyclePolicy` and `DayTypeOverride`
- `DayCyclePolicy` stores `anchor_date`, `effective_from`, `normal_week_json`, and
  `chill_week_json`. The anchor is normalized to Monday and selects the position
  in the repeating four-week cycle.
- `DayTypeOverride` stores a unique `(user_id, date)` exception. The implemented
  source is `feel_off`, with `day_type=rest`.
- Automatic migration v33 in `database/seed.py` adds the two JSON schedules,
  backfills their defaults, and creates `day_type_overrides` idempotently.
- Resolution belongs in `services/day_cycle_service.py`; consumers such as score
  and agenda services must not implement competing day-type logic.

---

## 3. Backend Endpoints

### Profile & Pins
- `GET /api/v1/profile` — Retrieves active player statistics and pinned lists.
- `PUT /api/v1/profile/pins` — Saves user's pinned sub-step and softskill IDs (max 3 per category).

### Automatic Day Planning
- `GET /api/v1/profile/cycle` — Returns the active policy and optional pending
  policy, both weekly maps, current cycle week, and planned type.
- `PUT /api/v1/profile/cycle` — Programs complete normal/less-intense weekday
  maps with `anchor_date` and a today-or-future `effective_from`.
- `POST /api/v1/profile/feel-off` — Turns today into an exceptional Rest Day.
- `DELETE /api/v1/profile/feel-off` — Removes today's exception and restores the
  scheduled type.
- `GET /api/v1/profile` exposes `active_template`, `scheduled_template`,
  `day_type_source`, and `feel_off_active` for the dashboard status control.

### Goals
- `GET /api/v1/goals` — Retrieves all goals with resolved substeps and completeness percentages.
- `POST /api/v1/goals` — Creates a new goal.
- `PUT /api/v1/goals/{id}` — Updates a goal's title and description.
- `DELETE /api/v1/goals/{id}` — Cascade deletes a goal and its associated linkages.

### Substeps
- `POST /api/v1/goals/{goal_id}/substeps` — Creates a substep within a goal.
- `PUT /api/v1/substeps/{substep_id}` — Updates title, description, gold reward, effort metadata where applicable, and execution order.
- `DELETE /api/v1/substeps/{substep_id}` — Deletes a substep.
- `POST /api/v1/substeps/{substep_id}/complete` — Marks substep as complete, rewards the player gold, records Life Lore when applicable, and flags the parent goal as complete if all substeps are satisfied.

### Habits & Streaks
- `GET /api/v1/habits` — Retrieves all habits.
- `POST /api/v1/habits` — Creates a new habit.
- `PUT /api/v1/habits/{id}` — Updates a habit (handles deactivation/reactivation state and streak freeze resets).
- `DELETE /api/v1/habits/{id}` — Soft-deactivates a habit and sets `deactivated_at`.
- `GET /api/v1/habits/{id}/calendar` — Retrieves monthly streak data and status calendar grid.

### Perfect Day, Agenda & Google
- `GET/POST /api/v1/templates` — Current `rest`, `regular`, and `hustle`
  effort-budget templates.
- `GET /api/v1/agenda` plus placement/save-as-template routes — Current vertical
  daily agenda source.
- `GET/POST/PUT/DELETE /api/v1/biological-zones` — Biological timeline CRUD.
- `GET /api/v1/auth/google/status`, OAuth login/callback/disconnect, and agenda
  export routes — Google Calendar & Tasks integration is implemented.

---

## 4. Frontend & Layout Conventions

### 3-3-3 Recap Dashboard Panel
- **Vertical Stack**: Placed on the main page above the character sheet, displaying sections vertically (`display: flex; flex-direction: column;`).
- **Focus Node Animation**: Clicking a pinned item focuses on its node (redirecting to the respective tab and animating with `pulse-highlight` keyframes).
- **Selection Constraints**: Selection checkboxes in `#recap-pin-drawer` are limited to 3 items max.

### Slide-Out Drawer vs Centered Modal Popup
1. **Creation View**: Clicking `⚔️ Forger & Gérer` slides a large panel out from the right (`right: 0`) showing all form sections.
2. **Editing View**: Clicking the `✏️` button on a Goal or Substep centers the panel as a beautiful centered popup modal.
   - Class: `.creators-drawer.modal-popup`
   - Transition: Satisfying spring-scale animation using `transform: translate(-50%, -50%) scale(1);` with `cubic-bezier(0.34, 1.56, 0.64, 1)`.

### Responsiveness Rules
- The drawer uses responsive constraints: `width: 100%; max-width: 420px; right: -100%;` to slide cleanly on mobile viewports.
- The modal popup uses responsive sizing: `width: 95% !important; max-width: 550px !important;` to render wide and spacious on desktop, while scaling down cleanly to fit mobile portrait layouts without horizontal clipping.
- Padding inside popup: `1.5rem 1.2rem` to maximize input spaces.

### Skill Tree Rendering (execution_order)
The visual representation of goals and substeps in `app.js` groups items horizontally by `execution_order`. 
- Columns are generated dynamically based on unique `execution_order` values.
- Within a column, substeps are stacked vertically.
- The parent Goal node is displayed as the final step in its own dedicated column to visually symbolize the culmination of the journey.

### Dynamic Card Visibility
In `app.js`, `openDrawer(mode, ...)` handles toggling specific form cards to prevent UI clutter:
- **`mode === "add-goal"`**: Displays only `#edit-goal-section` to create a new goal.
- **`mode === "add-substep"`**: Displays only `#create-substep-section` to quickly add a new substep.
- **`mode === "links"`**: Displays only `#links-blockers-section` to handle advanced goal linkages.
- **`mode === "edit"`**: Displays only `#edit-goal-section` populated with existing goal data.
- **`mode === "edit-substep"`**: Displays only `#edit-substep-section` populated with existing substep data.

### Habit Detail Drawer & Calendar
- **Interactive Habit View**: Clicking on a habit card slides out the `#habit-detail-drawer` containing badges for current and max streak plus a monthly interactive calendar grid (`#habit-detail-calendar-grid`). Stat reward badges were removed with the RPG stat system.
- **Calendar Color Codes**: Days are visually distinct based on state classes (`completed`, `skipped`, `missed`, `non-scheduled`, `pre-creation`). Tooltips are rendered dynamically on hover to show the detailed state name.
- **Deactivation/Reactivation Toggle**: A button inside the drawer allows users to soft-delete (deactivate) or reactivate habits, applying confirmation alerts and calling the soft-delete/update API routes.

---

## 5. Development & Testing Commands

To verify backend schema changes, API endpoints, or database structures:
- Run Pytest from the backend directory using the project's virtualenv:
  ```bash
  PYTHONPATH=backend .venv/bin/pytest backend/tests
  ```
- All endpoints, daily scores, and user isolation schemas should remain 100% green.
