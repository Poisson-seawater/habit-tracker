# Tasks: Perfect Day Rendering (Vue Rendu)

**Input**: Design documents from `/specs/011-perfect-day-rendering/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/api.md ✅

**Tests**: Included — spec references automated tests for CRUD and overlap validation.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: No new project setup needed — extending existing codebase. This phase covers the database schema addition and migration.

- [x] T001 Add BiologicalZone model to `backend/src/database/models.py` with columns: id, user_id (FK), zone_name, zone_type, start_time, end_time, color, display_order and add `biological_zones` relationship on User model
- [x] T002 Add migration v18 to `_run_migrations()` in `backend/src/database/seed.py`: create `biological_zones` table if not exists, seed default zones (Sleep 23:00–07:00, Deep Focus 08:00–12:00, Rest 12:00–13:00, Physical Peak 14:00–17:00, Creative 20:00–22:00) for all existing users when table is empty

---

## Phase 2: Foundational (API Layer)

**Purpose**: CRUD endpoints for biological zones — required before any frontend work can begin.

**⚠️ CRITICAL**: Frontend rendering depends on these endpoints being available.

- [x] T003 Add Pydantic schemas `BiologicalZoneCreate` and `BiologicalZoneUpdate` to `backend/src/api/routes.py` with fields: zone_name, zone_type (validated enum), start_time, end_time, color (optional), display_order (optional)
- [x] T004 Implement overlap detection helper function in `backend/src/api/routes.py`: given a user_id, start_time, end_time, and optional exclude_zone_id, check for overlapping zones accounting for midnight wrapping (split overnight zones into two virtual segments)
- [x] T005 Implement `GET /biological-zones` endpoint in `backend/src/api/routes.py`: list all zones for user ordered by start_time, return JSON array per contracts/api.md
- [x] T006 Implement `POST /biological-zones` endpoint (status 201) in `backend/src/api/routes.py`: create zone with overlap validation, return created zone or 422 error
- [x] T007 Implement `PUT /biological-zones/{zone_id}` endpoint in `backend/src/api/routes.py`: update zone with overlap validation, return 404 if not found, 422 on overlap
- [x] T008 Implement `DELETE /biological-zones/{zone_id}` endpoint in `backend/src/api/routes.py`: delete zone, return 404 if not found

### Tests

- [x] T009 Create `backend/tests/test_biological_zones.py` with tests for: CRUD operations, overlap detection rejects overlapping zones, overnight zones (23:00–07:00) accepted without false overlap, default seeding creates expected zones, invalid zone_type rejected

**Checkpoint**: API is functional — all CRUD operations work. Run: `PYTHONPATH=backend .venv/bin/pytest backend/tests/test_biological_zones.py -v`

---

## Phase 3: User Story 1 — Biological Ideal Day Timeline (Priority: P1) 🎯 MVP

**Goal**: Display a read-only horizontal 24h biological timeline at the top of the Perfect Day view, fetched from the API.

**Independent Test**: Navigate to Perfect Day view → see colored biological zone blocks at top. Switch templates → timeline does not change.

### Implementation for User Story 1

- [x] T010 [US1] Add biological timeline CSS styles to `frontend/css/style.css`: zone-type color variables (deep_focus=#8b5cf6, physical_peak=#06b6d4, creative=#eab308, sleep=#475569, rest=#22c55e, social=#f97316), timeline bar layout (~60px height full-width), zone block styling with labels, gap rendering as transparent/neutral space, tooltip on hover
- [x] T011 [US1] Add `fetchBiologicalZones()` function in `frontend/js/app.js`: GET `/api/v1/biological-zones`, cache result in memory (does not change per template switch)
- [x] T012 [US1] Add `renderBioTimeline(zones)` function in `frontend/js/app.js`: render 24h horizontal bar with color-coded blocks per zone, handle overnight wrapping (split visually into two segments), render gaps as neutral empty space, show zone name + type emoji inside blocks, add tooltip on hover with zone details
- [x] T013 [US1] Add the rendering view HTML structure to `frontend/index.html`: top section for bio timeline inside the Perfect Day tab area, wire it to load on tab activation via `fetchBiologicalZones()` → `renderBioTimeline()`

**Checkpoint**: Bio timeline visible at top of Perfect Day view with default zones. Template switching does NOT affect it.

---

## Phase 4: User Story 2 — Daily Activity Recap Panel (Priority: P1)

**Goal**: Display a left-side scrollable panel listing planned blocks for the active day-type template.

**Independent Test**: Navigate to Perfect Day rendering → see chronological activity list on the left. Switch template → list updates with different blocks.

### Implementation for User Story 2

- [x] T014 [P] [US2] Add daily recap panel CSS styles to `frontend/css/style.css`: rendering view grid layout (top full-width, bottom left 60% + right 40%), scrollable left panel with max-height, activity item cards with time badge, title, effort tag badge, category badge, empty state styling
- [x] T015 [US2] Add `renderDailyRecap(templateName)` function in `frontend/js/app.js`: fetch templates via existing `GET /templates`, extract `agenda_json` for the active template, render each block as a card with time range badge (cyan), title, effort tag, and category badge, show empty state message if no blocks, make list independently scrollable
- [x] T016 [US2] Integrate the rendering view layout in `frontend/index.html`: add the left panel container inside the Perfect Day rendering section, wire template switching to re-render the left panel while keeping the bio timeline untouched
- [x] T017 [US2] Wire template tab switching in `frontend/js/app.js`: when user switches day-type (rest/regular/hustle), call `renderDailyRecap()` with the new template but do NOT re-fetch or re-render the bio timeline

**Checkpoint**: Full rendering view shows bio timeline (top) + activity recap (left). Template switching updates recap only.

---

## Phase 5: User Story 3 — Effort Budget Gauge Panel (Priority: P2)

**Goal**: Display a right-side panel showing the effort budget gauge with per-tag breakdowns and ceiling warnings.

**Independent Test**: Navigate to Perfect Day rendering → see budget gauge on right with totals and warnings. Switch template → gauge updates.

### Implementation for User Story 3

- [x] T018 [P] [US3] Add budget gauge CSS styles to `frontend/css/style.css`: right panel layout, gauge bar styling per effort tag (musculaire, cerveau, emotionnel_social, creatif_divergent), overflow warning indicators (red glow/border), total hours display, tag-color coding
- [x] T019 [US3] Add `renderBudgetGauge(templateName)` function in `frontend/js/app.js`: compute per-tag effort totals from the active template's agenda blocks (sum effort_duration grouped by effort_type), compare against the template's ceilings_json, render visual bars with actual/ceiling ratios, highlight overflows with warning style, show total planned vs ceiling
- [x] T020 [US3] Add the right panel HTML container to `frontend/index.html` inside the rendering view grid, wire to `renderBudgetGauge()` on tab activation and template switch

**Checkpoint**: 3-zone rendering view complete — bio timeline (top), recap (left), budget gauge (right). All update correctly on template switch.

---

## Phase 6: Settings UI — Biological Day Configuration

**Goal**: Allow users to add/edit/delete biological zones from the Settings tab.

**Independent Test**: Go to Settings → "Journée Biologique" section → add a zone → see it appear on the Perfect Day rendering view timeline.

### Implementation for Settings

- [x] T021 [P] Add biological zone settings CSS styles to `frontend/css/style.css`: zone list item styling, add/edit form, zone-type color indicator, delete button, overlap error alert
- [x] T022 Add `renderBioZoneSettings(zones)` function in `frontend/js/app.js`: render current zones as a list with edit/delete buttons, show zone type emoji + color indicator per item, add "Add Zone" form with: name (text input), type (select with 6 options), start/end time pickers, display overlap error feedback from API 422 responses
- [x] T023 Add bio zone CRUD handlers in `frontend/js/app.js`: `addBioZone(formData)` POST to `/api/v1/biological-zones`, `updateBioZone(id, formData)` PUT, `deleteBioZone(id)` DELETE, on success refresh the settings list AND the rendering view bio timeline
- [x] T024 Add the "Journée Biologique" section HTML to the Settings area in `frontend/index.html`, wire to load on settings tab activation

**Checkpoint**: Full CRUD of biological zones from Settings. Changes immediately reflected on the rendering view.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final quality pass across all components.

- [x] T025 [P] Responsive layout testing and fixes in `frontend/css/style.css`: verify rendering view at 768px and 1920px viewports, collapse to single column on narrow screens
- [x] T026 [P] Add French-language empty states and labels across all new UI sections in `frontend/js/app.js` and `frontend/index.html`
- [x] T027 Run quickstart.md validation: execute all manual verification steps from `specs/011-perfect-day-rendering/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (model + migration must exist)
- **US1 (Phase 3)**: Depends on Phase 2 (needs GET endpoint)
- **US2 (Phase 4)**: Depends on Phase 2 (uses existing GET /templates) — can run in parallel with US1
- **US3 (Phase 5)**: Depends on Phase 2 — can run in parallel with US1 and US2
- **Settings (Phase 6)**: Depends on Phase 2 (needs all CRUD endpoints) — can run in parallel with US1/US2/US3
- **Polish (Phase 7)**: Depends on all previous phases

### User Story Dependencies

- **US1 (Bio Timeline)**: Independent — only needs GET /biological-zones
- **US2 (Daily Recap)**: Independent — only needs GET /templates (existing)
- **US3 (Budget Gauge)**: Independent — reads from existing template data
- **Settings (Bio Config)**: Independent — full CRUD on /biological-zones

### Within Each Phase

- Models before migrations (T001 → T002)
- Overlap helper before CRUD endpoints (T004 → T005/T006/T007/T008)
- CSS can run in parallel with JS (marked [P])
- HTML wiring depends on JS functions being implemented

### Parallel Opportunities

```
Phase 2: T005, T006, T007, T008 are sequential (same file)
         T003, T004 can precede them
         T009 (tests) can be written after T005-T008

After Phase 2 completes:
  US1 (T010-T013) ←→ US2 (T014-T017) ←→ US3 (T018-T020) ←→ Settings (T021-T024)
  All four can run in parallel if different developers
```

---

## Parallel Example: After Phase 2

```
# All four story phases can start simultaneously:
Developer A: US1 — Bio timeline (T010 → T011 → T012 → T013)
Developer B: US2 — Daily recap (T014 → T015 → T016 → T017)
Developer C: US3 — Budget gauge (T018 → T019 → T020)
Developer D: Settings — Bio config (T021 → T022 → T023 → T024)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational API (T003–T009)
3. Complete Phase 3: US1 Bio Timeline (T010–T013)
4. **STOP and VALIDATE**: Bio timeline renders at top with default zones
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → API ready ✓
2. Add US1 (Bio Timeline) → visual anchor at top ✓ **(MVP)**
3. Add US2 (Daily Recap) → left panel with blocks ✓
4. Add US3 (Budget Gauge) → right panel with effort data ✓
5. Add Settings (Bio Config) → full CRUD from Settings ✓
6. Polish → responsive + labels ✓

---

## Notes

- All routes go in `backend/src/api/routes.py` (project convention — single routes file)
- All frontend JS in `frontend/js/app.js` (single file convention)
- Bio zones are independent of effort tags (confirmed in spec clarification)
- No bot commands are added/modified — COMMANDS-INDEX.md does NOT need updating
- Overnight zone rendering: split visually into two segments at midnight boundary
