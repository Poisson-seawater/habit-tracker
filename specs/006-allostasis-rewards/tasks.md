# Tasks: Allostasis Rewards

**Input**: Design documents from `/specs/006-allostasis-rewards/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are requested for testing the capping rules and availability validations.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create specs/006-allostasis-rewards/ directory and verify plan file paths
- [x] T002 Ensure project database migrations directory backend/src/database/migrations/ exists

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Create database migration file backend/src/database/migrations/v7_allostasis_rewards.sql to add category and last_purchased_at columns
- [x] T004 Apply database migration using sqlite3 on data/habit_tracker.db
- [x] T005 Update Reward model in backend/src/database/models.py to define category and last_purchased_at columns
- [x] T006 Update Reward schemas and database seeding in backend/src/database/seed.py
- [x] T007 [P] Create initial test suite file backend/tests/test_allostasis_rewards.py with empty test skeletons

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Configuration des Items d'Allostasie (Priority: P1) 🎯 MVP

**Goal**: Configure up to 3 items per allostasis category with 0 gold cost via API and frontend.

**Independent Test**: Create an allostasis reward using the Web UI/form and verify that it enforces 0 gold cost and blocks creation of a 4th item.

### Tests for User Story 1

- [x] T008 [P] [US1] Add test_allostasis_limits_enforced in backend/tests/test_allostasis_rewards.py to assert creation fails when exceeding 3 items
- [x] T009 [P] [US1] Add test_allostasis_cost_zero in backend/tests/test_allostasis_rewards.py to assert allostasis items are always created with 0 gold cost

### Implementation for User Story 1

- [x] T010 [US1] Update RewardCreate and RewardUpdate Pydantic schemas in backend/src/api/routes.py to include category
- [x] T011 [US1] Update Reward CRUD endpoints in backend/src/api/routes.py to enforce 0 gold cost and max 3 items validation limit per category
- [x] T012 [US1] Add Category select field and cost-forcing logic to reward-form modal in frontend/index.html
- [x] T013 [US1] Update reward form submit payload logic in frontend/js/app.js to send category field

**Checkpoint**: User Story 1 is fully functional. The user can create up to 3 daily and 3 weekly zero-cost allostasis items in the database.

---

## Phase 4: User Story 2 - Validation/Rédemption des Items d'Allostasie (Priority: P1)

**Goal**: Redeem allostasis items in the shop (web & bot) without spending gold, resetting daily or weekly.

**Independent Test**: Click "Acheter" on a daily allostasis item. It becomes marked as checked off/redeemed, no gold is deducted, and a second purchase attempt is rejected.

### Tests for User Story 2

- [x] T014 [P] [US2] Add test_allostasis_purchase_free in backend/tests/test_allostasis_rewards.py to assert purchasing does not deduct gold
- [x] T015 [P] [US2] Add test_allostasis_purchase_availability in backend/tests/test_allostasis_rewards.py to assert daily items block second purchase on the same day and weekly items block second purchase in the same week

### Implementation for User Story 2

- [x] T016 [US2] Update purchase_reward endpoint in backend/src/api/routes.py to skip gold deduction and set last_purchased_at for allostasis items
- [x] T017 [US2] Implement availability check logic helper in backend/src/services/reward_service.py to check if a reward is already redeemed in the current period
- [x] T018 [US2] Organize frontend shop layout in frontend/index.html to have separate Allostasis and Standard Reward grids
- [x] T019 [US2] Update fetchRewards in frontend/js/app.js to split returned rewards by category and render them in their respective grids
- [x] T020 [US2] Add visual indicator and styling in frontend/css/style.css for checked off/completed allostasis items
- [x] T021 [US2] Update Telegram bot shop and purchase commands in backend/src/bot/listener.py to support free purchase and show status

**Checkpoint**: User Story 2 is complete. Allostasis items can be checked off in both dashboard and bot, resetting dynamically.

---

## Phase 5: User Story 3 - Intégration dans le Bilan Journalier (Daily Recap) (Priority: P1)

**Goal**: Show today's redeemed allostasis items in the Telegram daily recap.

**Independent Test**: Redeem an allostasis item, trigger the recap job, and verify it outputs in the message content.

### Tests for User Story 3

- [x] T022 [P] [US3] Add test_allostasis_daily_recap_inclusion in backend/tests/test_allostasis_rewards.py to assert recap message generator fetches today's redeemed allostasis items

### Implementation for User Story 3

- [x] T023 [US3] Implement helper function in backend/src/services/reward_service.py to fetch allostasis items purchased by a user on a specific date
- [x] T024 [US3] Modify publish_daily_recap in backend/src/bot/scheduler.py to fetch today's allostasis items and append them to the user recap block

**Checkpoint**: User Story 3 is complete. The Telegram group/user daily recap includes recovery details.

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T025 Update specs/006-allostasis-rewards/quickstart.md with validated sample data
- [x] T026 Update COMMANDS-INDEX.md with any changes to the bot command /shop or /buy (Hard rule)
- [x] T027 Code cleanup, formatting with black, and running full test suite
- [x] T028 Run quickstart.md validation to confirm success criteria

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion. Blocks all user stories.
- **User Stories (Phase 3+)**: All depend on Foundational phase completion.
  - Phase 3 (US1) -> Phase 4 (US2) -> Phase 5 (US3).
- **Polish (Final Phase)**: Depends on all user stories being complete.

---

## Parallel Example: User Story 1

```bash
# Launch both tests together:
pytest backend/tests/test_allostasis_rewards.py -k "test_allostasis_limits_enforced"
pytest backend/tests/test_allostasis_rewards.py -k "test_allostasis_cost_zero"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Setup and Foundational.
2. Complete US1.
3. Validate UI creation and 3-item limit.
