# Research: Perfect Day Redesign (Effort Budget Allocator)

This document outlines the technical research, architecture decisions, and design considerations for the Perfect Day redesign.

## Technical Scope & Constraints

- **Language/Version**: Python 3.12 (Backend), ES6 Javascript (Frontend)
- **Primary Dependencies**: FastAPI (Web API), SQLAlchemy 2.0 (ORM), python-telegram-bot (Telegram interface)
- **Storage**: SQLite (`/data/habit_tracker.db` in Docker, `backend/data/` in local)
- **Testing**: pytest
- **Target Platform**: Linux Server / Raspberry Pi 5
- **Performance Goals**: Budget calculation and validation < 50ms, page rendering < 100ms
- **Memory Constraint**: Bot service < 35MB, API service < 40MB RAM

---

## Key Architecture Decisions

### 1. Database Schema Updates
To support the effort budget model, we need to alter three existing entities:
- **`PerfectDayTemplate`**:
  - Add `focus_hours` (REAL, default 6.0)
  - Add `min_rest_hours` (REAL, default 8.0)
  - Add `ceilings_json` (TEXT/JSON, containing per-tag limits and total limit)
  - Keep `thresholds_json` as deprecated/nullable to avoid breaking existing DB files.
- **`Habit`** & **`SubStep`**:
  - Add `effort_type` (TEXT/String, nullable) - one of `musculaire`, `cerveau`, `emotionnel_social`, `creatif_divergent`, or `None`/`Null`.
  - Add `effort_duration` (REAL, default 1.0) - duration in hours.

### 2. Daily Validation & Warning Rules
Based on the spec and user clarifications:
- **Default Duration**: If a user creates a quest/sub-step with an effort type but leaves duration blank, the system automatically defaults it to `1.0` hour.
- **Ceiling Violations**:
  - `hustle` day: A warning is triggered if the planned effort duration for any single tag is **> 4.0 hours**.
  - `regular` day: A warning is triggered if the planned effort duration for any single tag is **> 2.0 hours**.
  - General: A warning is triggered if the sum of all planned effort durations exceeds the day-type's `total` ceiling.
- **Waking Day and Unplanned Time**:
  - We assume a fixed **16-hour waking day** for calculating unplanned time.
  - A `hustle` day requires $\ge 30\%$ unplanned time.
  - Formula: $\text{unplanned time} = 16.0 - \text{total planned effort hours}$.
  - A `hustle` day is marked **invalid** if $\text{unplanned time} < 4.8 \text{ hours}$ (which is $30\%$ of $16.0$ hours). This translates to: total planned effort hours cannot exceed **11.2 hours**.

### 3. API Contract Modifications
- `GET /templates`: Return the updated template settings with `focus_hours`, `min_rest_hours`, and `ceilings_json` for `rest`, `regular`, and `hustle`.
- `POST /templates`: Accept `focus_hours`, `min_rest_hours`, and `ceilings_json` for updates.
- `GET /habits` & `GET /todos` & `GET /substeps`: Include `effort_type` and `effort_duration`.
- `POST /habits` & `PUT /habits/{id}`: Accept `effort_type` and `effort_duration` in payloads.
- `POST /goals/{id}/substeps` & `PUT /substeps/{id}`: Accept `effort_type` and `effort_duration`.
- `POST /profile/template` & `GET /daily-score`: Adapt to calculate "Perfect" or "Failed" status based on the new logic instead of RPG stat points.

### 4. Frontend (UI) Changes
- **Settings tab**: Completely redesign the thresholds editor to show settings for `rest`, `regular`, and `hustle`. Provide inputs for focus target, minimum rest, and ceilings for each of the 4 effort types + total.
- **Dashboard tab**:
  - Add a **Daily Effort Budget Gauge** that lists the 4 tags, showing `planned_hours / ceiling` for each tag, and total planned effort.
  - If a ceiling is exceeded or a hustle day has less than 30% unplanned time, display warning banners/badges in red/orange.
  - Simplify the "Perfect Day Status" panel: instead of checking RPG stats, show the day-type status and list scheduled activities with their effort tags/durations.
- **Quest (Habit) and Sub-step Editor modals**: Add dropdown for `Effort Type` (Musculaire, Cerveau, Émotionnel/Social, Créatif/Divergent, Aucun) and a number field for `Durée d'effort` (default 1.0).

---

## Alternatives Considered & Rejected

### Alternative A: Storing Budgets in `thresholds_json` to avoid DB schema migrations
- **Why considered**: Avoids running `ALTER TABLE` statements on SQLite.
- **Why rejected**: A structured model with explicit columns (`focus_hours`, `min_rest_hours`, `ceilings_json`) is much cleaner, prevents JSON parsing errors in backend queries, and conforms to SQLAlchemy best practices. Since we already have a robust, tested `_run_migrations` function in `seed.py`, running migrations is straightforward.

### Alternative B: Dynamic waking hours per day-type template
- **Why considered**: Rest days might have longer sleep hours than hustle days.
- **Why rejected**: A fixed 16-hour waking day is simpler, predictable, and requires no extra configuration settings.
