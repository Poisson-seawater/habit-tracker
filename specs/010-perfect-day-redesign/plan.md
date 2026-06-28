# Implementation Plan: Perfect Day Redesign (Effort Budget Allocator)

**Branch**: `010-perfect-day-redesign` | **Date**: 2026-06-28 | **Spec**: [specs/010-perfect-day-redesign/spec.md](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/specs/010-perfect-day-redesign/spec.md)

**Input**: Feature specification from `/specs/010-perfect-day-redesign/spec.md`

## Summary

This feature refactors the "Perfect Day" system from an RPG stat-based validation calendar to a sustainable effort budget allocator. It replaces the old four template types with three day-types (`rest`, `regular`, and `hustle`), configures focus target/rest/ceilings for each type, introduces effort tags (`musculaire`, `cerveau`, `emotionnel_social`, `creatif_divergent`) and durations for habits/quests and sub-steps, and updates the dashboard with a dynamic budget gauge featuring overflow and validation alerts.

## Technical Context

**Language/Version**: Python 3.12, Javascript ES6

**Primary Dependencies**: FastAPI, SQLAlchemy 2.0, python-telegram-bot

**Storage**: SQLite (`/data/habit_tracker.db` in Docker, `backend/data/` in local)

**Testing**: pytest

**Target Platform**: Linux Server / Raspberry Pi 5

**Project Type**: web-service + Telegram bot

**Performance Goals**: Daily validation and budget aggregation < 50ms, UI rendering < 100ms

**Constraints**: API memory footprint < 40MB, Bot memory footprint < 35MB

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Dual-Interface Design**: Both Telegram bot and localhost dashboard read/write from a single source of truth database.
- [ ] **Flexible Point-Based Accountability**: RPG stats and thresholds for Perfect Day are abandoned in favor of effort budgets. *(Violated - see Complexity Tracking)*
- [x] **Multi-User Foundation & Privacy**: Templates and habits are associated with `user_id` resolved via the `X-User-ID` header.
- [x] **Self-Hosted Pi & Docker**: Migrations are executed dynamically at start-up via `_run_migrations` to keep SQLite database updated without heavy tools.
- [x] **Strict API Contract & Integration-Ready**: Expose updated REST API endpoints for templates, habits, and sub-steps with clear JSON contracts.

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle II: Flexible Point-Based Accountability | User testing showed RPG stats did not work well for the user, who wanted an effort/energy-based budget allocator instead. | Keeping the RPG stats was rejected because the user explicitly wants them removed and replaced by the 4 effort types and time-based budgets. |

---

## Project Structure

### Documentation (this feature)

```text
specs/010-perfect-day-redesign/
├── plan.md              # This file
├── research.md          # Research and architectural decisions
├── data-model.md        # Database schema modifications
├── quickstart.md        # Testing and manual verification guide
└── contracts/
    └── api.md           # API request and response contracts
```

### Source Code

```text
backend/
├── src/
│   ├── api/
│   │   └── routes.py    # FastAPI routes and schemas
│   ├── bot/
│   │   └── listener.py  # Bot commands
│   ├── database/
│   │   ├── models.py    # SQLAlchemy models
│   │   └── seed.py      # Database migrations and default templates
│   └── services/
│       └── score_service.py # Scoring, validation, and energy budget calculations
└── tests/
    └── test_perfect_day.py  # Unit tests for the budget allocator
frontend/
├── index.html           # Settings UI changes & Daily gauge panel
├── css/style.css        # Gauge visual styles and colors
└── js/app.js            # Frontend logic, fetch and render gauges
```

**Structure Decision**: Web application layout containing `backend/` and `frontend/` as structured above.

---

## Proposed Changes

### Database Layer

#### [MODIFY] [models.py](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/backend/src/database/models.py)
- Modify `PerfectDayTemplate`:
  - Add `focus_hours = Column(Float, default=6.0, nullable=False)`
  - Add `ceilings_json = Column(JSON, nullable=True)`
  - Add `min_rest_hours = Column(Float, default=8.0, nullable=False)`
  - Keep `thresholds_json` as deprecated/nullable.
- Modify `Habit` and `SubStep`:
  - Add `effort_type = Column(String, nullable=True)`
  - Add `effort_duration = Column(Float, default=1.0, nullable=False)`

#### [MODIFY] [seed.py](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/backend/src/database/seed.py)
- Update default template seeding to seed the 3 new day-types (`rest`, `regular`, `hustle`) with default budgets.
- Add migration steps inside `_run_migrations()` to dynamically add `focus_hours`, `ceilings_json`, `min_rest_hours`, `effort_type`, and `effort_duration` to the corresponding SQLite tables if they do not exist.

### Logic Layer

#### [MODIFY] [score_service.py](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/backend/src/services/score_service.py)
- Refactor `calculate_daily_score` to query the active day-type template.
- Calculate planned effort duration per category and total daily planned hours.
- Perform validation checks:
  - Exceeding single category ceilings.
  - Exceeding total day-type ceiling.
  - Hustle day minimum unplanned time check ($\ge 30\%$ of a 16h waking day).
- Update the `DailyScore` model or status response to return the details of the budget allocation (actual vs budgeted hours per tag, warnings, validation status).

### API Layer

#### [MODIFY] [routes.py](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/backend/src/api/routes.py)
- Update `TemplateSave` Pydantic schema to accept new budget parameters.
- Update GET/POST `/templates` routes to handle the updated fields.
- Update CRUD routes for habits and substeps to handle `effort_type` and `effort_duration`.

### Frontend Layer

#### [MODIFY] [index.html](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/frontend/index.html)
- Redesign the Perfect Day template settings section.
- Add fields for `effort_type` and `effort_duration` to habit creation and substep creation forms.
- Add a daily budget gauge section to the dashboard.

#### [MODIFY] [app.js](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/frontend/js/app.js)
- Fetch and render template budget settings in the settings tab.
- Fetch daily scheduled quest and substep details, compute actual vs budget values, and render the visual progress gauges.
- Display warning alerts if any ceilings are exceeded or if a hustle day fails the 30% unplanned time validation.

---

## Verification Plan

### Automated Tests
- Create `backend/tests/test_perfect_day.py` verifying:
  - Database schema migrations and defaults.
  - Category ceiling warnings.
  - Hustle day unplanned time calculation and invalidation.
- Command to run: `PYTHONPATH=backend pytest backend/tests/test_perfect_day.py`

### Manual Verification
- Verify Settings tab can successfully update day-type thresholds.
- Verify creation of quests with optional effort durations (ensuring a 1.0 hour default).
- Verify visual warnings on the dashboard when limits are exceeded.
- Verify visual invalidation of hustle days when planned hours exceed 11.2 hours.
