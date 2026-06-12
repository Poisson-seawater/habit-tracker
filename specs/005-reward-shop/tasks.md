# Tasks: Reward Shop (Boutique de Récompenses)

**Input**: Design documents from `/specs/005-reward-shop/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/rewards-api.md

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Basic initialization of the new migration file and setup for unit tests.

- [ ] T001 [P] Create SQL migration file in `backend/src/database/migrations/v6_rewards.sql`
- [ ] T002 [P] Create empty tests file in `backend/tests/test_rewards.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database models and schema structure

- [ ] T003 Modify database models in `backend/src/database/models.py` to define the `Reward` entity and User relationships
- [ ] T004 Run and verify database migrations with `backend/src/database/migrations/v6_rewards.sql`

---

## Phase 3: User Story 1 - Gestion des Récompenses (Priority: P1)

**Goal**: Implement CRUD operations for rewards via REST API endpoints and web interface forms.

**Independent Test**: Create, list, edit, and delete rewards via `/api/v1/rewards` and verify dashboard Boutique rendering.

### Implementation for User Story 1

- [ ] T005 [P] [US1] Define Pydantic request/response schemas for rewards in `backend/src/api/routes.py`
- [ ] T006 [US1] Implement CRUD endpoints (`GET`, `POST`, `PUT`, `DELETE` under `/api/v1/rewards`) in `backend/src/api/routes.py`
- [ ] T007 [P] [US1] Add a "Boutique" tab button and section container in `frontend/index.html`
- [ ] T008 [US1] Implement the Boutique tab navigation, fetch, rendering, and creation/deletion UI functions in `frontend/js/app.js`
- [ ] T009 [US1] Style the rewards list grid, forms, buttons, and responsive inputs in `frontend/css/style.css`

---

## Phase 4: User Story 2 - Achat de Récompenses (Priority: P1)

**Goal**: Implement purchasing logic with gold deduction and transaction safety.

**Independent Test**: Buy an unlocked reward, verify user gold balance decreases, purchase count increases, and errors are handled for insufficient funds.

### Implementation for User Story 2

- [ ] T010 [US2] Create reward service logic in `backend/src/services/reward_service.py` to handle ACID-compliant purchase transactions
- [ ] T011 [US2] Implement `/api/v1/rewards/{reward_id}/purchase` endpoint in `backend/src/api/routes.py` calling the purchase service
- [ ] T012 [US2] Implement buy button event handler and state updates in `frontend/js/app.js`

---

## Phase 5: User Story 3 - Récompenses Verrouillées (Priority: P2)

**Goal**: Implement locks based on softskills and goals completion.

**Independent Test**: Link a reward to a softskill or goal, verify it displays as locked when not met, and automatically unlocks when requirements are completed.

### Implementation for User Story 3

- [ ] T013 [US3] Implement validation functions checking softskill or goal completion in `backend/src/services/reward_service.py`
- [ ] T014 [US3] Merge lock states dynamically inside the GET rewards route in `backend/src/api/routes.py`
- [ ] T015 [US3] Implement dynamic dropdown selections for softskills and goals in the creation form in `frontend/js/app.js`
- [ ] T016 [US3] Add lock/unlock visual indicators and style overlays in `frontend/css/style.css`

---

## Phase 6: User Story 4 - Bot Telegram Commandes (Priority: P3)

**Goal**: Access and buy rewards directly through Telegram Bot commands `/shop` and `/buy`.

**Independent Test**: Use `/shop` to view rewards and `/buy <id>` to purchase, verifying gold updates and validations in the chat.

### Implementation for User Story 4

- [ ] T017 [P] [US4] Add command definitions and parsing logic for `/shop` and `/buy` in `backend/src/bot/parser.py`
- [ ] T018 [US4] Add command handler implementations for `/shop` and `/buy` in `backend/src/bot/listener.py`
- [ ] T019 [US4] Update `COMMANDS-INDEX.md` at the root of the project with details of `/shop` and `/buy`

---

## Phase 7: Polish & Validation

**Purpose**: Test verification and UI refinements.

- [ ] T020 [P] Implement comprehensive unit tests in `backend/tests/test_rewards.py`
- [ ] T021 Execute pytest verification suite for rewards
- [ ] T022 Refine card micro-animations and styling polish in `frontend/css/style.css`
- [ ] T023 Run quickstart manual validation steps

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Phase 1 completion.
- **User Stories (Phases 3-6)**: Depend on Foundational phase completion.
- **Polish (Phase 7)**: Depends on all user stories being implemented.

### Parallel Opportunities

- Phase 1 setup tasks T001 and T002 can run in parallel.
- Frontend styling (T009) can be worked on in parallel with backend endpoints (T006).
- Parsing changes (T017) can be added in parallel with listener implementation.
