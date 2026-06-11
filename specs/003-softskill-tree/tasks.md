# Tasks: Softskill Progress Tree

**Input**: Design documents from `/specs/003-softskill-tree/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md

**Tests**: Unit tests are included to verify route behavior, database constraints, and business logic.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Exact file paths are included in descriptions.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic config files

- [x] T001 Create static layout config file in backend/src/data/softskills_tree.json
- [x] T002 Create database migration file in backend/src/database/migrations/v3_softskills.sql

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Apply database migration to backend/data/habit_tracker.db
- [x] T004 Implement UserSoftskillProgress model in backend/src/database/models.py
- [x] T005 Create softskill service in backend/src/services/softskill_service.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Viewing the Softskill Tree (Priority: P1) 🎯 MVP

**Goal**: Render all softskills, branches, colors, layout coordinates, and prerequisites visually on a single page.

**Independent Test**: Navigate to the "Softskills" tab on the dashboard, and the SVG tree renders correctly matching the static JSON configuration.

### Implementation for User Story 1

- [x] T006 [US1] Create API endpoint /api/v1/softskills in backend/src/api/routes.py
- [x] T007 [P] [US1] Create unit tests in backend/tests/test_softskills.py
- [x] T008 [US1] Update frontend/index.html to add Softskills navigation tab
- [x] T009 [P] [US1] Add styling rules in frontend/css/style.css
- [x] T010 [US1] Implement SVG tree rendering logic in frontend/js/app.js

**Checkpoint**: At this point, User Story 1 is fully functional and testable independently.

---

## Phase 4: User Story 2 - Viewing Skill Details (Priority: P2)

**Goal**: Click a softskill node to display its details, description, prerequisites, and custom success test in a modal/panel.

**Independent Test**: Click a skill node, and the details panel displays correct information.

### Implementation for User Story 2

- [x] T011 [US2] Add details panel HTML markup in frontend/index.html
- [x] T012 [P] [US2] Add details panel styling in frontend/css/style.css
- [x] T013 [US2] Bind click events and details rendering in frontend/js/app.js

**Checkpoint**: At this point, User Stories 1 AND 2 work together.

---

## Phase 5: User Story 3 - Updating Softskill Progress (Priority: P3)

**Goal**: Allow the user to write/edit their custom success test sentence and manually toggle completion status.

**Independent Test**: Edit the success test sentence and mark the skill complete; database is updated, and the node's visual style updates to unlocked.

### Implementation for User Story 3

- [x] T014 [US3] Create API endpoint /api/v1/softskills/{softskill_id}/test in backend/src/api/routes.py
- [x] T015 [US3] Create API endpoint /api/v1/softskills/{softskill_id}/complete in backend/src/api/routes.py
- [x] T016 [P] [US3] Create unit tests for progress updates in backend/tests/test_softskills.py
- [x] T017 [US3] Add edit input and complete button to modal HTML in frontend/index.html
- [x] T018 [US3] Implement API integration and UI state refresh in frontend/js/app.js

**Checkpoint**: All user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Cleanup, validation, and documentation updates.

- [x] T019 Run quickstart.md validation
- [x] T020 [P] Create documentation in docs/wiki/softskills.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories.
- **User Stories (Phase 3+)**: All depend on Foundational phase completion.
  - User stories can then proceed in parallel or sequentially (P1 → P2 → P3).
- **Polish (Final Phase)**: Depends on all user stories being complete.

### Parallel Opportunities

- Setup tasks T001 and T002 can run in parallel.
- Test tasks and styles marked [P] can run in parallel with their backend implementation counterparts.
- Different user stories can be worked on in parallel once Phase 2 completes.

---

## Parallel Example: User Story 1

```bash
# Style tasks and API unit tests can be worked on in parallel
Task: "Add styling rules in frontend/css/style.css"
Task: "Create unit tests in backend/tests/test_softskills.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational.
3. Complete Phase 3: User Story 1.
4. **STOP and VALIDATE**: Test User Story 1 independently in the browser.
