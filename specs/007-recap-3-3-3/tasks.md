# Tasks: 3-3-3 Recap Dashboard Panel

**Input**: Design documents from `/specs/007-recap-3-3-3/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Backend unit tests requested and planned.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Database migration scripts setup.

- [ ] T001 Create SQLite migration file `backend/src/database/migrations/v8_pinned_items.sql`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core model updates and backend REST API development.

**⚠️ CRITICAL**: Must complete before frontend integration can begin.

- [ ] T002 Update `User` model with `pinned_substeps` and `pinned_softskills` columns in `backend/src/database/models.py`
- [ ] T003 Create `PUT /profile/pins` route and update `GET /profile` response in `backend/src/api/routes.py`
- [ ] T004 Create API unit tests in `backend/tests/test_profile_pins.py`

---

## Phase 3: User Story 1 - Affichage du 3-3-3 Recap (Priority: P1) 🎯 MVP

**Goal**: Render the structural 3-3-3 recap card layout above the character sheet.

**Independent Test**: The card skeleton displays correctly on load above the stats panel.

- [ ] T005 [US1] Wrap stats panel and add `#recap-3-3-3-panel` card skeleton in `frontend/index.html`
- [ ] T006 [P] [US1] Add responsive style definitions for the recap card in `frontend/css/style.css`
- [ ] T007 [US1] Implement core logic to fetch and display the card sections in `frontend/js/app.js`

---

## Phase 4: User Story 2 - Sélection et Navigation des Objectifs Majeurs (Priority: P1)

**Goal**: Select up to 3 sub-steps to pin, and click a pinned step to navigate and focus the node.

**Independent Test**: Pinned sub-steps show on recap, click redirects and flashes the sub-step node.

- [ ] T008 [US2] Add layout structure for selection drawer `#recap-pin-drawer` in `frontend/index.html`
- [ ] T009 [US2] Implement sub-step selection listing, 3-checkbox limits, and save API integration in `frontend/js/app.js`
- [ ] T010 [US2] Implement tab redirection and goal/sub-step node scroll and focus in `frontend/js/app.js`

---

## Phase 5: User Story 3 - Sélection et Navigation des Compétences Clés (Priority: P1)

**Goal**: Pin up to 3 softskills, click to redirect and focus the skill node in the tree.

**Independent Test**: Pinned softskills show on recap, click redirects and highlights the node.

- [ ] T011 [US3] Add softskills list container in the selection drawer in `frontend/index.html`
- [ ] T012 [US3] Implement softskill selection listing, checkbox validation, and save integration in `frontend/js/app.js`
- [ ] T013 [US3] Implement tab redirection and softskill node highlight in `frontend/js/app.js`

---

## Phase 6: User Story 4 - Suivi et Validation Directe de l'Allostasie (Priority: P1)

**Goal**: Display daily or weekly allostasis items, switch views, and claim them directly.

**Independent Test**: Switching updates displayed items, claiming them updates character stats immediately.

- [ ] T014 [US4] Add daily/weekly toggle buttons and claim button actions to the HTML in `frontend/index.html`
- [ ] T015 [US4] Implement swap, list loading, and purchase handler in `frontend/js/app.js`

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Quality verification and final deployment sanity checks.

- [ ] T016 Verify responsive rendering and styling behavior on both mobile and desktop viewports
- [ ] T017 Verify all unit tests pass with `PYTHONPATH=backend pytest backend/tests`
- [ ] T018 Update command documentation if any CLI or commands change
