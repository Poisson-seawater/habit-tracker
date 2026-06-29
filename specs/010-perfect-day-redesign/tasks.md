# Tasks: Perfect Day Redesign (Effort Budget Allocator)

**Input**: Design documents from `/specs/010-perfect-day-redesign/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md

**Tests**: Tests are generated for each story to ensure TDD and coverage of calculations.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Initialize test suite for Perfect Day in backend/tests/test_perfect_day.py
- [x] T002 Configure style utility classes for effort badges in frontend/css/style.css

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Setup database migrations for perfect day redesign in backend/src/database/seed.py
- [x] T004 Update database models for templates, habits, and substeps in backend/src/database/models.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Configure Day-Type Budgets (Priority: P1) 🎯 MVP

**Goal**: Configure the effort budgets for the 3 day-types (rest, regular, hustle) in settings, defining focus hours, ceilings, and minimum rest.

**Independent Test**: Load settings tab, select perfect day templates editor, edit values, save, refresh page, and verify values are correctly stored and retrieved.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T005 [P] [US1] Create unit tests for template GET/POST routes in backend/tests/test_perfect_day.py

### Implementation for User Story 1

- [x] T006 [US1] Implement template REST API routes and Pydantic schemas in backend/src/api/routes.py
- [x] T007 [P] [US1] Redesign template settings editor layout in frontend/index.html
- [x] T008 [US1] Implement settings template load and save handlers in frontend/js/app.js

**Checkpoint**: At this point, Day-Type budget templates are fully functional and editable.

---

## Phase 4: User Story 2 - Tag Quests and Sub-steps with Effort Types (Priority: P1)

**Goal**: Assign an effort type tag and duration to habits (quests) and sub-steps, defaulting duration to 1.0 hour.

**Independent Test**: Create a quest and sub-step without specifying duration and check that it saves with 1.0. Update they contain correct effort tags.

### Tests for User Story 2

- [x] T009 [P] [US2] Create unit tests for habits and substeps effort fields CRUD in backend/tests/test_perfect_day.py

### Implementation for User Story 2

- [x] T010 [US2] Implement effort tags and duration fields in backend/src/api/routes.py
- [x] T011 [P] [US2] Add effort fields to habit creation/edit forms in frontend/index.html
- [x] T012 [P] [US2] Add effort fields to substep creation/edit forms in frontend/index.html
- [x] T013 [US2] Update habit and substep UI serialization and rendering in frontend/js/app.js

**Checkpoint**: Quests and sub-steps can now be categorized with effort types and durations.

---

## Phase 5: User Story 3 - Daily Budget Gauge and Validation (Priority: P1)

**Goal**: Show daily budget gauge, summing effort duration by tag and checking thresholds, with warnings for exceeded ceilings or invalid hustle days (<30% unplanned).

**Independent Test**: Load dashboard, schedule habits, verify category gauge filling, trigger category ceiling limit warning, and trigger hustle day invalid day warning.

### Tests for User Story 3

- [x] T014 [P] [US3] Create unit tests for score and validation calculations in backend/tests/test_perfect_day.py

### Implementation for User Story 3

- [x] T015 [US3] Refactor daily score calculation and validation logic in backend/src/services/score_service.py
- [x] T016 [P] [US3] Add daily budget gauge visual container to dashboard in frontend/index.html
- [x] T017 [US3] Implement dynamic budget gauge fetching, aggregation, and warning display in frontend/js/app.js
- [x] T018 [P] [US3] Style the budget progress bars, tags, and warnings in frontend/css/style.css

**Checkpoint**: All budget validations and gauges are functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T019 Clean up and remove deprecated RPG stats logic from backend/src/services/score_service.py (RPG stats ignored/treated as out-of-scope for this phase)
- [x] T020 Run quickstart.md validation to verify end-to-end functionality in specs/010-perfect-day-redesign/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Depends on US1 (for day budgets) and US2 (for task costs)

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch tests and templates setup
Task: "Create unit tests for template GET/POST routes in backend/tests/test_perfect_day.py"
Task: "Redesign template settings editor layout in frontend/index.html"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories
