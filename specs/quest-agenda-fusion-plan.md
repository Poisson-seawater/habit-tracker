# Plan: Quest Agenda Fusion

**Generated**: 2026-06-30
**Estimated Complexity**: High

## Overview

Build a manual daily agenda that fuses the day timeline with RPG quests.

The agenda does not mention or use biological zones. Biological rhythm remains an independent reference view. The agenda's job is to show today's eligible quests, let the user place them manually on a 15-minute grid, and calculate planned effort totals against the active day-type budget (`rest`, `regular`, `hustle`).

The feature should preserve the existing Habit Tracker architecture:

- Existing `Habit` remains the durable quest bank.
- Existing quest frequency fields (`frequency`, `scheduled_days`) determine which recurring quests are eligible today.
- Existing `PerfectDayTemplate` remains the day-type budget source.
- Existing `pinned_goals` and `pinned_softskills` are the source for the 3 goals and 3 skills focus.
- Generated focus quests are durable quests tied to a goal or softskill source. Removing a goal/skill focus hides its generated quest from the agenda, but does not archive or delete the quest.
- Generated focus quests must preserve their filled details over time: duration, effort type, placement history, streak/log records, and any quest-step/checklist data attached later.

Key product rule: archive is explicit only. A Sunday admin quest that is not visible Monday to Saturday is not archived; it is simply not eligible on those dates.

## Prerequisites

- Keep the Telegram command index rule in mind, but this plan does not require adding or modifying bot commands.
- Keep SQLite migrations idempotent in `backend/src/database/seed.py`.
- Respect the existing `X-User-ID` API contract.
- Avoid heavy frontend dependencies; drag and drop should use native browser APIs or lightweight local code.
- Preserve Raspberry Pi memory constraints.

## Core Decisions

- **No automatic ordering**: the system never decides the hour for the user.
- **Manual placement**: the user drags quests into time slots snapped to 15-minute increments.
- **Budget includes visible quests**: the effort gauge sums today's visible/eligible quests, whether placed or still unplaced. Quests missing effort metadata are shown as incomplete and excluded from effort totals until filled.
- **Disposition is explicit**: editing today's agenda only affects that date. A separate action, "Sauver comme disposition hustle/regular/rest", updates the saved day-type disposition.
- **Archive is explicit**: only user-archived quests are archived. Schedule-based absence and focus removal are not archive states.
- **Generated focus quests are durable**: goal and softskill quests keep their steps, effort settings, placement history, logs, and streaks when focus is removed and later re-added.

## Data Model Direction

### Existing Entities To Reuse

- `Habit`: durable quest identity, recurrence, effort type, effort duration, streak/log source.
- `HabitLog`: completion and quantitative tracking.
- `PerfectDayTemplate`: day-type budgets and existing `agenda_json`.
- `User.pinned_goals`: selected Top 3 goals.
- `User.pinned_softskills`: selected Top 3 skills.
- `Goal` and `SubStep`: existing objective graph.
- Softskill tree from `backend/src/services/softskill_service.py`: source of skill names and IDs.

### Proposed Model Additions

#### Habit Fields

Add fields to `Habit` to distinguish manual quests from generated focus quests and explicit archive state:

- `source_type`: nullable string, one of `manual`, `goal`, `softskill`.
- `source_ref`: nullable string, goal ID or softskill ID as text.
- `auto_managed`: boolean, default `false`.
- `archived_at`: nullable datetime. Explicit archive only.
- `agenda_duration_minutes`: nullable integer. Defaults from `effort_duration * 60` when missing.

Notes:

- Do not use `is_active=False` for temporary agenda absence.
- Keep old `is_active` behavior working for existing delete/deactivation flows during migration.
- Generated focus quests should use a unique `(user_id, source_type, source_ref)` rule at the application level, or a DB unique constraint if feasible with SQLite migration safety.
- If "quest steps" become a first-class requirement beyond existing goal substeps and softskill validation criteria, add a dedicated `QuestStep` table keyed to `Habit.id` instead of storing step checklists inside placement rows.

#### DailyAgendaPlacement

Create a new table for per-date manual placements:

- `id`
- `user_id`
- `date`
- `habit_id`
- `start_time`: `HH:MM`, nullable for unplaced if rows are pre-created; otherwise no row means unplaced.
- `duration_minutes`
- `status`: `planned`, `done`, `skipped`; default `planned`.
- `actual_minutes`: nullable integer.
- `created_at`, `updated_at`

Recommended behavior: do not create placement rows for every eligible unplaced quest. Build unplaced quests dynamically from eligibility rules, then merge in placement rows for the date.

#### Template Agenda JSON V2

Evolve `PerfectDayTemplate.agenda_json` from a free block list into a versioned structure:

```json
{
  "schema_version": 2,
  "segments": [
    {"id": "sleep-1", "kind": "sleep", "start": "00:00", "end": "07:30"},
    {"id": "admin-1", "kind": "admin", "start": "13:00", "end": "15:00"},
    {"id": "intense-1", "kind": "intense", "start": "08:00", "end": "12:00"},
    {"id": "rest-1", "kind": "rest", "start": "20:00", "end": "22:00"}
  ],
  "default_placements": [
    {"habit_id": 12, "start": "08:30", "duration_minutes": 30}
  ]
}
```

The frontend/backend should normalize old list-shaped `agenda_json` values so existing data does not break.

## Sprint 1: Domain Semantics And Backend Foundations

**Goal**: Separate quest bank, archive state, schedule eligibility, generated focus quests, and agenda placements.

**Demo/Validation**:

- A recurring Sunday quest appears on Sunday and not Monday without being archived.
- A softskill-generated quest disappears when the softskill is removed from focus, then reappears with the same habit ID/settings when re-selected.
- Existing habit endpoints still work.

### Task 1.1: Add Quest Source And Archive Fields

- **Location**: `backend/src/database/models.py`, `backend/src/database/seed.py`
- **Description**: Add `source_type`, `source_ref`, `auto_managed`, `archived_at`, and `agenda_duration_minutes` to `Habit`. Add idempotent migration checks in `_run_migrations()`.
- **Dependencies**: None
- **Acceptance Criteria**:
  - Existing DBs gain columns safely on startup.
  - Existing habits default to manual, non-archived behavior.
  - `is_active` remains backwards compatible.
- **Validation**:
  - Add/extend schema tests in `backend/tests/test_perfect_day.py` or a new `backend/tests/test_agenda_quests.py`.

### Task 1.2: Add DailyAgendaPlacement Model

- **Location**: `backend/src/database/models.py`, `backend/src/database/seed.py`
- **Description**: Add a placement table keyed by user/date/habit. Include duration, status, and actual minutes.
- **Dependencies**: Task 1.1
- **Acceptance Criteria**:
  - Multiple users can place the same habit independently.
  - Same user/date/habit has at most one active placement.
  - Times store as `HH:MM` and are validated in service/API layer.
- **Validation**:
  - Unit test table creation and uniqueness behavior.

### Task 1.3: Create Agenda Service

- **Location**: `backend/src/services/agenda_service.py`
- **Description**: Centralize agenda logic outside routes.
- **Dependencies**: Tasks 1.1, 1.2
- **Acceptance Criteria**:
  - `is_habit_eligible_on_date(habit, date)` supports `daily`, `weekly`, `monthly`, and `specific_days`.
  - Explicit archive excludes a quest.
  - Focus-generated quests require their source to still be pinned and their quest schedule to include the date.
  - Sunday admin quest is non-archived but absent Monday-Saturday.
- **Validation**:
  - Unit tests for daily/specific day/weekly/monthly eligibility.

### Task 1.4: Synchronize Generated Goal And Skill Quests

- **Location**: `backend/src/services/agenda_service.py`, `backend/src/api/routes.py`
- **Description**: When profile pins change, ensure durable generated `Habit` records exist for pinned goals and pinned softskills. Do not delete/archive them when pins are removed.
- **Dependencies**: Task 1.3
- **Acceptance Criteria**:
  - Pinning softskill `python` creates or reuses one auto-managed quest.
  - Unpinning `python` removes it from agenda eligibility but preserves the `Habit`.
  - Re-pinning `python` reuses the same quest with previous effort/duration/streak/logs.
  - Generated quests are clearly incomplete until the user fills duration/effort/details.
- **Validation**:
  - Tests around `PUT /api/v1/profile/pins`.

## Sprint 2: Agenda API

**Goal**: Provide a single API surface for the frontend agenda: visible quests, placements, template disposition, and effort totals.

**Demo/Validation**:

- `GET /api/v1/agenda?date=YYYY-MM-DD` returns all visible quests split into placed and unplaced lists.
- Budget totals match the active day-type ceilings.
- Placement update snaps/validates 15-minute slots.

### Task 2.1: Add Agenda Response Contract

- **Location**: `backend/src/api/routes.py`
- **Description**: Add schemas for agenda quest items, placements, budget summary, and template segments.
- **Dependencies**: Sprint 1
- **Acceptance Criteria**:
  - Response includes `date`, `day_type`, `segments`, `placed_quests`, `unplaced_quests`, `effort_totals`, `ceilings`, and `warnings`.
  - Response has no biological terminology.
  - Incomplete generated quests include a clear `needs_configuration` flag.
- **Validation**:
  - FastAPI TestClient contract test.

### Task 2.2: Implement GET Agenda Endpoint

- **Location**: `backend/src/api/routes.py`, `backend/src/services/agenda_service.py`
- **Description**: Add `GET /api/v1/agenda?date=YYYY-MM-DD`.
- **Dependencies**: Task 2.1
- **Acceptance Criteria**:
  - Combines eligible habits with placements for the date.
  - Unplaced quests are returned when no placement exists.
  - Effort totals sum visible configured quests.
  - Existing `PerfectDayTemplate` ceilings are reused.
- **Validation**:
  - Tests for empty agenda, Sunday-only quest, generated focus quest, archived quest, and budget overflow.

### Task 2.3: Implement Placement Mutation

- **Location**: `backend/src/api/routes.py`, `backend/src/services/agenda_service.py`
- **Description**: Add `PUT /api/v1/agenda/{date}/quests/{habit_id}/placement` and `DELETE /api/v1/agenda/{date}/quests/{habit_id}/placement`.
- **Dependencies**: Task 2.2
- **Acceptance Criteria**:
  - Start time must be on a 15-minute boundary.
  - Duration must be positive and should default from quest settings.
  - Placement rejects overlaps unless the request explicitly allows overlap.
  - Delete placement returns the quest to unplaced for that date.
- **Validation**:
  - Tests for valid placement, snapping validation, overlap rejection, and unplacing.

### Task 2.4: Implement Save As Day-Type Disposition

- **Location**: `backend/src/api/routes.py`, `backend/src/services/agenda_service.py`
- **Description**: Add `POST /api/v1/agenda/{date}/save-as-template` with `{ "template_name": "hustle" }`.
- **Dependencies**: Task 2.3
- **Acceptance Criteria**:
  - Today's segment layout and selected template-safe placements are saved to the matching `PerfectDayTemplate.agenda_json`.
  - Regular date edits do not modify the template until this endpoint is called.
  - Default behavior excludes one-off/date-only placements from the template.
- **Validation**:
  - Test that Monday hustle edits do not affect future hustle until saved.
  - Test that saving updates future hustle agenda defaults.

## Sprint 3: Frontend Agenda Surface

**Goal**: Replace the static block recap with a manual quest agenda: unplaced list, 15-minute timeline, drag/drop, and effort budget.

**Demo/Validation**:

- User sees today's unplaced quests and placed quests in one agenda.
- Dragging a quest to 07:45 places it there.
- Moving it to 15:00 updates only that date.
- Budget gauges update immediately.

### Task 3.1: Refactor Agenda Layout UI

- **Location**: `frontend/index.html`, `frontend/css/style.css`
- **Description**: Convert "Chronologie de la Journée Type" into an operational agenda card.
- **Dependencies**: Sprint 2 API
- **Acceptance Criteria**:
  - Agenda area has no biology copy or labels.
  - Shows day-type selector, save-as-disposition action, 15-minute grid/timeline, unplaced quest list, and effort summary.
  - Day moments are limited to `sleep`, `rest`, `admin`, `intense`.
  - UI remains dense and operational, not a landing-page style.
- **Validation**:
  - Manual desktop check at common viewport widths.

### Task 3.2: Add Agenda Data Loader

- **Location**: `frontend/js/app.js`
- **Description**: Fetch `GET /api/v1/agenda`, render placed/unplaced quests, and keep current template/profile fetches compatible.
- **Dependencies**: Task 3.1
- **Acceptance Criteria**:
  - Agenda refreshes after profile pin changes, day-type changes, quest edits, placement edits, and validation/logging.
  - Missing metadata is surfaced inline on generated focus quests.
  - Existing quest list can remain during transition, but agenda uses the new source.
- **Validation**:
  - Manual check with daily, Sunday-only, skill-generated, and goal-generated quests.

### Task 3.3: Implement Native Drag And Drop

- **Location**: `frontend/js/app.js`, `frontend/css/style.css`
- **Description**: Add drag/drop from unplaced list to timeline, and move existing blocks along the grid.
- **Dependencies**: Task 3.2
- **Acceptance Criteria**:
  - Drops snap to 15-minute increments.
  - Quest duration controls visual width.
  - Dragging within same day updates placement via API.
  - Removing placement returns quest to unplaced list.
  - Overlap is clearly blocked or warned.
- **Validation**:
  - Manual drag/drop tests for 07:45, 08:00, 15:00.

### Task 3.4: Render Budget From Agenda State

- **Location**: `frontend/js/app.js`, `frontend/css/style.css`
- **Description**: Update effort summary to use agenda response totals rather than recomputing from old `agenda_json` blocks.
- **Dependencies**: Task 3.2
- **Acceptance Criteria**:
  - Displays totals for `musculaire`, `cerveau`, `emotionnel_social`, `creatif_divergent`.
  - Compares against active day-type ceilings.
  - Warnings display when any ceiling is exceeded.
  - Unplaced configured quests still count toward totals.
- **Validation**:
  - Create visible quests exceeding regular `cerveau` budget and verify warning.

### Task 3.5: Add Save As Disposition UI

- **Location**: `frontend/index.html`, `frontend/js/app.js`, `frontend/css/style.css`
- **Description**: Add explicit action to persist current day layout as `rest`, `regular`, or `hustle`.
- **Dependencies**: Task 3.3
- **Acceptance Criteria**:
  - Moving quests today does not change the template by default.
  - Clicking "Sauver comme disposition hustle" persists the reusable layout.
  - User gets clear success/error feedback.
- **Validation**:
  - Place a quest on Monday hustle, switch/reload Tuesday hustle before and after save.

## Sprint 4: Quest Configuration And Archive UX

**Goal**: Make generated quests fillable, preserve durable settings, and expose explicit archive behavior.

**Demo/Validation**:

- Generated `Python` quest appears incomplete, can be filled, then keeps its settings across focus remove/re-add.
- Archive hides a quest because the user explicitly archived it.

### Task 4.1: Extend Quest Editor For Agenda Fields

- **Location**: `frontend/index.html`, `frontend/js/app.js`, `backend/src/api/routes.py`
- **Description**: Add/edit `agenda_duration_minutes`, source metadata display, generated-quest details, and explicit archive controls.
- **Dependencies**: Sprint 1 model fields
- **Acceptance Criteria**:
  - User can set a 30-minute default duration.
  - Effort type/duration remains editable.
  - Generated quests show their source, e.g. `Skill: Python` or `Objectif: Business`.
  - Source metadata cannot accidentally be changed from the editor.
  - Generated quest details are preserved when the related goal/skill is removed from focus and later selected again.
- **Validation**:
  - Edit generated Python quest, remove/re-add skill, verify settings persist.
  - If quest steps are added in this sprint, verify steps persist across remove/re-add as well.

### Task 4.2: Implement Explicit Archive/Unarchive

- **Location**: `backend/src/api/routes.py`, `frontend/js/app.js`
- **Description**: Add explicit archive flow without reusing temporary schedule absence.
- **Dependencies**: Task 4.1
- **Acceptance Criteria**:
  - Archived quests are excluded from agenda eligibility.
  - Archived quests preserve logs and streak records.
  - Unarchive makes them eligible again if recurrence/focus rules allow it.
  - Existing delete/deactivation behavior remains compatible.
- **Validation**:
  - Test archive/unarchive for manual and generated quest.

### Task 4.3: Add Quest Bank View Or Filter

- **Location**: `frontend/index.html`, `frontend/js/app.js`
- **Description**: Provide a way to find durable quests that are not visible today, including archived quests if toggled.
- **Dependencies**: Task 4.2
- **Acceptance Criteria**:
  - User can distinguish not scheduled today from archived.
  - Sunday admin quest is visible in bank Monday as not scheduled, not archived.
  - Archive section only contains explicitly archived quests.
- **Validation**:
  - Manual check with Sunday-only quest and archived manual quest.

## Sprint 5: Integration Cleanup And Regression Coverage

**Goal**: Stabilize the feature, avoid duplicate budget logic, and keep old surfaces working.

**Demo/Validation**:

- Full dashboard loads.
- Agenda, quest list, 3-3-3 recap, and Perfect Day budgets remain coherent.
- Tests pass.

### Task 5.1: Consolidate Effort Calculation

- **Location**: `backend/src/services/agenda_service.py`, `frontend/js/app.js`
- **Description**: Move authoritative effort totals to backend agenda response. Remove or reduce duplicated frontend budget calculations where possible.
- **Dependencies**: Sprint 3
- **Acceptance Criteria**:
  - UI and API agree on effort totals.
  - Day-type budget defaults remain unchanged.
- **Validation**:
  - Backend test and manual dashboard comparison.

### Task 5.2: Update Existing Tests

- **Location**: `backend/tests/test_perfect_day.py`, `backend/tests/test_profile_pins.py`, `backend/tests/test_habit_streaks.py`, new `backend/tests/test_agenda_quests.py`
- **Description**: Add regression coverage for generated quests, schedule eligibility, explicit archive, placements, and save-as-template.
- **Dependencies**: Sprints 1-4
- **Acceptance Criteria**:
  - Existing tests updated for new fields.
  - New tests cover the product rules from this plan.
- **Validation**:
  - `PYTHONPATH=backend .venv/bin/pytest backend/tests/test_agenda_quests.py backend/tests/test_profile_pins.py backend/tests/test_perfect_day.py`

### Task 5.3: Manual UI Verification

- **Location**: Browser, `frontend/index.html`, `frontend/js/app.js`
- **Description**: Verify the end-to-end dashboard flow.
- **Dependencies**: Sprint 4
- **Acceptance Criteria**:
  - Select skill Python -> generated quest appears if active today.
  - Remove Python -> generated quest disappears from agenda but stays in quest bank.
  - Re-select Python -> same quest returns with previous settings.
  - Sunday admin quest appears Sunday only.
  - Drag/drop works at 15-minute increments.
  - Budget warnings match day type.
  - Biological timeline remains independent and not referenced inside agenda.
- **Validation**:
  - Run local server and test in browser.

## Testing Strategy

- Backend unit/API tests first, because agenda eligibility and generated quest preservation are the highest-risk business rules.
- Frontend manual validation is acceptable initially because the project currently has no frontend test runner.
- Add targeted tests for:
  - focus quest creation/reuse
  - focus quest absence after unpin
  - schedule absence vs archive
  - day-type-specific saved dispositions
  - 15-minute placement validation
  - effort totals and ceiling warnings

## Potential Risks & Gotchas

- **`is_active` currently means soft delete/deactivation**: do not overload it for "not visible today". This is the biggest semantic risk.
- **Existing `agenda_json` shape is list-based**: changing it directly will break current renderers unless a normalizer supports both old and new shapes.
- **Generated quest uniqueness**: softskills use string IDs while goals use integer IDs. Store `source_ref` consistently as string.
- **Pinned goals vs pinned substeps**: current 3-3-3 UI displays pinned substeps. This feature wants the 3 objectives themselves to create quests, so the implementation must be explicit about whether generated goal quests come from `pinned_goals` or `pinned_substeps`. Recommended: generated objective quests come from `pinned_goals`; pinned substeps can remain a recap/detail feature.
- **Quest steps are not currently a Habit model concept**: if "étapes" means a per-quest checklist, it needs a small `QuestStep` model or a deliberate reuse of existing `SubStep`. Do not bury that data in `agenda_json`.
- **Budget counting unplaced quests**: this is intentional. The agenda shows workload even before every quest has an hour.
- **Special weekday quests**: default plan keeps them unplaced unless the user places them on that date. Saving as a day-type disposition should avoid accidentally baking one-off/date-specific items into every future day-type layout.

## Rollback Plan

- New agenda endpoints can be introduced without removing existing `/templates` and `/habits` behavior.
- If frontend rollout fails, hide the new agenda UI and keep the existing quest list and old `agenda_json` recap.
- DB changes are additive. Existing data remains readable.
- Generated focus quests can be disabled by skipping synchronization in `/profile/pins`; durable generated habits remain in the bank and can be manually archived if needed.
