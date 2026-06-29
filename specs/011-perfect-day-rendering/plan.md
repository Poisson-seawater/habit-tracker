# Implementation Plan: Perfect Day Rendering (Vue Rendu)

**Branch**: `011-perfect-day-rendering` | **Date**: 2026-06-28 | **Spec**: [specs/011-perfect-day-rendering/spec.md](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/specs/011-perfect-day-rendering/spec.md)

**Input**: Feature specification from `/specs/011-perfect-day-rendering/spec.md`

## Summary

This feature adds a "Perfect Day Rendering" view to the dashboard that displays two independent visual components: (1) a horizontal 24h biological ideal day timeline at the top — a static, per-user reference showing energy zones based on the user's chronotype, and (2) a left-side daily activity recap panel listing all planned blocks for the active day-type template. A right-side effort budget gauge panel (from spec 010) completes the layout. The biological timeline is independent of day-type template switching and is configured from a new "Biological Day" section in the Settings tab. A new lightweight `BiologicalZone` entity stores the user's zone configuration.

## Technical Context

**Language/Version**: Python 3.12, JavaScript ES6

**Primary Dependencies**: FastAPI, SQLAlchemy 2.0, python-telegram-bot

**Storage**: SQLite (`/data/habit_tracker.db` in Docker, `backend/data/` in local)

**Testing**: pytest

**Target Platform**: Linux Server / Raspberry Pi 5

**Project Type**: web-service + Telegram bot

**Performance Goals**: Page render < 1s, zone CRUD < 50ms

**Constraints**: API memory footprint < 40MB, Bot memory footprint < 35MB

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Dual-Interface Design**: The biological zones and templates are stored in a single SQLite source-of-truth database, accessible by both dashboard and bot.
- [x] **Flexible Point-Based Accountability**: This feature does not modify the point/stat system. The effort budget gauge (spec 010) is displayed read-only; biological zones are a separate, independent system.
- [x] **Multi-User Foundation & Privacy**: BiologicalZone entity is scoped with `user_id`. All API endpoints resolve user via the `X-User-ID` header.
- [x] **Self-Hosted Pi & Docker**: No new dependencies or services. The new DB table is lightweight (< 10 rows per user). Migrations use the existing idempotent `_run_migrations()` pattern.
- [x] **Strict API Contract & Integration-Ready**: New REST endpoints follow existing `/api/v1` conventions with JSON request/response contracts.

---

## Project Structure

### Documentation (this feature)

```text
specs/011-perfect-day-rendering/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── contracts/
    └── api.md           # API request and response contracts
```

### Source Code

```text
backend/
├── src/
│   ├── api/
│   │   └── routes.py        # New biological_zones CRUD + rendering endpoint
│   ├── database/
│   │   ├── models.py         # New BiologicalZone model
│   │   └── seed.py           # Migration v18: biological_zones table + default zones
│   └── services/
│       └── score_service.py  # (read-only by this feature — budget gauge data source)
└── tests/
    └── test_biological_zones.py  # CRUD + validation tests

frontend/
├── index.html           # Perfect Day rendering view section + Settings bio config
├── css/style.css        # Bio timeline + rendering layout styles
└── js/app.js            # Bio zones fetch/render, rendering view assembly
```

**Structure Decision**: Web application layout using existing `backend/` and `frontend/` structure. No new directories needed.

---

## Proposed Changes

### Database Layer

#### [NEW] BiologicalZone model in [models.py](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/backend/src/database/models.py)
- Add `BiologicalZone` class with columns:
  - `id` (Integer, primary key)
  - `user_id` (Integer, FK → users.id, CASCADE)
  - `zone_name` (String, not null) — user-facing label
  - `zone_type` (String, not null) — one of: `deep_focus`, `physical_peak`, `creative`, `rest`, `social`, `sleep`
  - `start_time` (String, not null) — "HH:MM" format
  - `end_time` (String, not null) — "HH:MM" format
  - `color` (String, nullable) — optional override hex color
  - `display_order` (Integer, default 0) — for consistent rendering order
- Add `biological_zones` relationship on `User` model.

#### [MODIFY] [seed.py](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/backend/src/database/seed.py)
- Add migration v18 in `_run_migrations()`: create `biological_zones` table if it doesn't exist (using `inspector.get_table_names()` check).
- Seed default biological zones for existing users when table is empty:
  - 😴 Sleep: 23:00–07:00
  - 🧠 Deep Focus: 08:00–12:00
  - 🧘 Rest: 12:00–13:00
  - 💪 Physical Peak: 14:00–17:00
  - 🎨 Creative: 20:00–22:00

### API Layer

#### [MODIFY] [routes.py](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/backend/src/api/routes.py)
- Add Pydantic schemas: `BiologicalZoneCreate`, `BiologicalZoneUpdate`.
- Add CRUD endpoints under `/api/v1/biological-zones`:
  - `GET /biological-zones` — list all zones for the user, ordered by `start_time`.
  - `POST /biological-zones` (201) — create a new zone with overlap validation.
  - `PUT /biological-zones/{zone_id}` — update a zone with overlap validation.
  - `DELETE /biological-zones/{zone_id}` — delete a zone.
- Overlap validation: Before insert/update, check that no existing zone for the same user overlaps the new start_time/end_time range (excluding the zone being updated). Return 422 with error details if overlap detected.
- Overnight handling: A zone spanning midnight (e.g., 23:00–07:00) is stored as-is; overlap detection treats `end_time < start_time` as wrapping across midnight.

### Frontend Layer

#### [MODIFY] [index.html](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/frontend/index.html)
- Add a "Perfect Day Rendering" section/tab to the dashboard with the 3-zone layout:
  - **Top**: Biological ideal day timeline (24h horizontal bar).
  - **Left**: Daily activity recap panel (scrollable block list from active template's `agenda_json`).
  - **Right**: Effort budget gauge panel (reads from existing budget endpoint).
- Add a "Biological Day" configuration section in the Settings tab with:
  - List of current biological zones with edit/delete buttons.
  - Form to add a new zone (name, type dropdown, start/end time pickers).

#### [MODIFY] [style.css](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/frontend/css/style.css)
- Add styles for the biological timeline bar with zone-type color coding:
  - `deep_focus` → purple (#8b5cf6)
  - `physical_peak` → cyan (#06b6d4)
  - `creative` → gold (#eab308)
  - `sleep` → slate (#475569)
  - `rest` → green (#22c55e)
  - `social` → warm orange (#f97316)
- Add rendering view layout styles (3-zone grid: top full-width, bottom left+right).
- Add Settings bio zone list and form styles.

#### [MODIFY] [app.js](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/frontend/js/app.js)
- Add `fetchBiologicalZones()` — GET `/api/v1/biological-zones`.
- Add `renderBioTimeline(zones)` — renders the 24h horizontal bar with color-coded blocks and gap handling.
- Add `renderDailyRecap(template)` — renders the left panel with blocks from the active template's `agenda_json`.
- Add `renderBudgetGauge()` — renders the right panel (reuses existing budget data from spec 010).
- Add bio zone CRUD functions for the Settings tab (add/edit/delete with overlap validation feedback).
- Wire the rendering view to load bio zones (independent) + template blocks (template-dependent) on Perfect Day tab activation.

### Tests

#### [NEW] [test_biological_zones.py](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/backend/tests/test_biological_zones.py)
- Test CRUD operations for biological zones.
- Test overlap detection rejects overlapping zones.
- Test overnight zones (23:00–07:00) are accepted and don't falsely overlap.
- Test default seeding creates expected zones.

---

## Verification Plan

### Automated Tests
- Run: `PYTHONPATH=backend .venv/bin/pytest backend/tests/test_biological_zones.py -v`
- Verify CRUD, overlap detection, overnight handling, and default seeding.

### Manual Verification
- Load the dashboard, navigate to Perfect Day rendering view.
- Verify biological timeline renders default zones at top.
- Verify left panel shows blocks from the active template.
- Switch templates (rest/regular/hustle) → left panel updates, bio timeline stays.
- Go to Settings → add/edit/delete biological zones.
- Verify overlap rejection with user-friendly error.
- Verify gaps render as neutral space on the timeline.
- Test at 768px and 1920px viewport widths.

---

## Complexity Tracking

No constitution violations. No complexity tracking entries needed.
