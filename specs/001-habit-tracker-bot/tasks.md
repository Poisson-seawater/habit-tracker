# Tasks: habit-tracker-bot

**Input**: Design documents from `/specs/001-habit-tracker-bot/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Includes specific unit and integration testing tasks to ensure robust performance, scheduled recaps, and strict command-unit parsing.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- All descriptions specify exact file paths.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, Docker Compose environments, and base folder structures.

- [ ] T001 Create project directories (backend/src/api, backend/src/bot, backend/src/database, frontend/src/css, frontend/src/js) per implementation plan
- [ ] T002 Configure Python 3.11 requirements (FastAPI, python-telegram-bot, SQLAlchemy, pytest, httpx) in backend/requirements.txt
- [ ] T003 [P] Configure code style, formatting, and test tools (black, flake8, pytest) in backend/pyproject.toml
- [ ] T004 Setup containerization environments with low memory caps (FastAPI API uvicorn and Bot listener daemon) in docker-compose.yml, backend/Dockerfile.api, and backend/Dockerfile.bot

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: SQLite database connections, models, and startup configuration layers.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T005 Setup environment configurations loader (`.env` parsing for Telegram Tokens, Group IDs, and Ports) in backend/src/config.py
- [ ] T006 Setup SQLite engine session manager in backend/src/database/session.py
- [ ] T007 [P] Create SQLAlchemy core entities definitions (User, Habit, HabitLog, DayTemplate, DailyScore, Streak) in backend/src/database/models.py
- [ ] T008 Implement startup seeding scripts for default V1 user (Gabriel), default 12 RPG stats, and default templates (Semaine, Weekend, Récupération, Malade) in backend/src/database/seed.py
- [ ] T009 Create unified FastAPI backend server configuration and uvicorn bootstrap in backend/src/main.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Daily Habit Logging & Accountability Bot (Priority: P1) 🎯 MVP

**Goal**: Establish Telegram Bot group chat command parses (`/done`, `/log`, `/skip`, `/status`, `/set-day`), compute dynamic point cap distributions, update SQLite logs, and broadcast daily RPG-style summaries while masking private habits.

**Independent Test**: Send test group messages to the Telegram Bot mockup, verify database entries, and confirm the generated 23:59 markdown recap formats correctly.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T010 [P] [US1] Create unit tests for parsing bot command grammars and unit suffixes in backend/tests/test_bot_parser.py
- [ ] T011 [P] [US1] Create integration tests for daily stat sums, points limits, and streak validations in backend/tests/test_daily_score.py

### Implementation for User Story 1

- [ ] T012 [P] [US1] Implement bot commands parser for strict validation (verifying unit metadata and numeric inputs) in backend/src/bot/parser.py
- [ ] T013 [US1] Implement daily stats and points processor (handling capped stat rewards, streaks, and Acceptable/Perfect day checks) in backend/src/services/score_service.py
- [ ] T014 [US1] Implement Telegram bot polling listener and action handler bindings in backend/src/bot/listener.py
- [ ] T015 [US1] Implement scheduled daily RPG recap publisher (running at 23:59, aggregating private habits, and broadcasting results) in backend/src/bot/scheduler.py

**Checkpoint**: User Story 1 is fully functional and testable independently.

---

## Phase 4: User Story 2 - Localhost Analytical Character Dashboard (Priority: P2)

**Goal**: Build a visual, premium localhost character sheet analytical dashboard showing stats progression, streak calendars, and goals progress using HSL color tokens and glassmorphism.

**Independent Test**: Load the localhost web page, check that it loads stats cleanly from the REST endpoints, and verify responsive styling on mobile formats.

### Tests for User Story 2

- [ ] T016 [P] [US2] Create endpoint integration contract tests for profile and logs querying in backend/tests/test_api_endpoints.py

### Implementation for User Story 2

- [ ] T017 [P] [US2] Implement REST API endpoints (GET /profile, GET /habits, GET /streaks, POST /logs) in backend/src/api/routes.py
- [ ] T018 [US2] Configure FastAPI static directory assets serving in backend/src/api/static_config.py
- [ ] T019 [P] [US2] Implement responsive styling (curated HSL dark palette, grids, glassmorphism UI) in frontend/src/css/style.css
- [ ] T020 [P] [US2] Build visual HTML structures (RPG stats sheet bars, quête sections, streaks heatmap, and profile cards) in frontend/src/index.html
- [ ] T021 [US2] Implement ES6 fetch client logic to retrieve JSON stats and dynamically update progress widgets in frontend/src/js/app.js

**Checkpoint**: User Stories 1 AND 2 work independently.

---

## Phase 5: User Story 3 - Habit & Template Configuration API (Priority: P3)

**Goal**: Allow creating, editing, and deleting habits, and overriding active templates dynamically via Bot commands and REST API configurations.

**Independent Test**: Submit new custom habits and templates, verifying that the scheduler adjusts point evaluation limits dynamically.

### Tests for User Story 3

- [ ] T022 [P] [US3] Create tests for habit configurations modifications and template swaps validation in backend/tests/test_config_features.py

### Implementation for User Story 3

- [ ] T023 [P] [US3] Implement day-template dynamic swapping service in backend/src/services/template_service.py
- [ ] T024 [US3] Add POST endpoints for habits registration in backend/src/api/routes.py
- [ ] T025 [US3] Add Telegram command routers for `/create-habit`, `/edit-habit`, and `/delete-habit` in backend/src/bot/listener.py

**Checkpoint**: All user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Database backups, documentation validation, and general system verification.

- [ ] T026 [P] Implement SQLite file automatic cron backup rotations in backend/src/database/backup.py
- [ ] T027 Run quickstart.md simulation locally to validate Pi 5 ARM64 low memory compose setups
- [ ] T028 [P] Document environment configuration keys in README.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories.
- **User Stories (Phases 3-5)**: Depend on Foundational phase completion. 
- **Polish (Phase 6)**: Depends on completion of all desired user stories.

### User Story Dependencies

- **User Story 1 (P1)**: The core Telegram Bot accountability logging. MVP scope - must complete first.
- **User Story 2 (P2)**: Independent visualization layer. Can be developed in parallel with US1 once Phase 2 (Foundation) is complete.
- **User Story 3 (P3)**: Configurations layer. Can be developed once the base bot features (US1) and REST endpoints (US2) are functional.

### Parallel Opportunities

- **Phase 1 [P] tasks** (T003) can run in parallel.
- **Phase 2 [P] models** (T007) can be generated in parallel.
- **US1 [P] tests** (T010, T011) can run in parallel.
- **US2 [P] routes, static configurations, and HTML structures** (T016, T017, T019, T020) can run in parallel.
- Once Foundation completes, Developer A (implementing US1 bot logging) and Developer B (implementing US2 visual frontend) can work simultaneously.

---

## Parallel Example: User Story 2

```bash
# Developer A builds endpoint endpoints:
Task: "Implement REST API endpoints (GET /profile, GET /habits, GET /streaks, POST /logs) in backend/src/api/routes.py"

# Developer B builds web assets in parallel:
Task: "Implement responsive styling (curated HSL dark palette, grids, glassmorphism UI) in frontend/src/css/style.css"
Task: "Build visual HTML structures (RPG stats sheet bars, quête sections, streaks heatmap, and profile cards) in frontend/src/index.html"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (CRITICAL - database schemas and defaults seeding).
3. Complete Phase 3: User Story 1 (Telegram bot async command logging).
4. **STOP and VALIDATE**: Verify check-ins are logged and recaps broadcast.

### Incremental Delivery

1. Complete Setup + Foundational -> SQLite database ready.
2. Add User Story 1 (Bot Core) -> Deploy/Demo MVP!
3. Add User Story 2 (Dashboard Visuals) -> Render RPG sheet stats.
4. Add User Story 3 (Customization commands) -> Expand configurations.
