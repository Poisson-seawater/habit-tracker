# Implementation Plan: Reward Shop (Boutique de Récompenses)

**Branch**: `005-reward-shop` | **Date**: 2026-06-12 | **Spec**: [spec.md](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/specs/005-reward-shop/spec.md)

**Input**: Feature specification from `/specs/005-reward-shop/spec.md`

## Summary

This feature adds a Reward Shop (Boutique) where users can create custom rewards, assign gold costs, and purchase them using accumulated gold. Rewards can optionally be locked behind completed softskills or long-term goals. Interaction is dual-interface, supported via both the localhost web dashboard (new "Boutique" tab) and Telegram Bot commands (`/shop` and `/buy <reward_id>`).

## Technical Context

**Language/Version**: Python 3.12 (backend), Vanilla JS ES6 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.0, python-telegram-bot[ext]

**Storage**: SQLite (`backend/data/habit_tracker.db` in local, `/data/habit_tracker.db` in Docker)

**Testing**: PyTest (`backend/tests/test_rewards.py`)

**Target Platform**: Linux / Raspberry Pi 5 (ARM64) via Docker Compose

**Project Type**: Web application (FastAPI backend + Vanilla HTML/CSS/JS frontend + Telegram bot)

**Performance Goals**:
- Page load & rewards listing: <300ms
- Purchase execution api response: <100ms
- Telegram bot response: <1.5s

**Constraints**:
- Strict Pi memory limits (40MB limit for API/bot services)
- Multi-user isolation by `user_id`
- Maintain SQLite database integrity

**Scale/Scope**: Private instance for 2 users, single database.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Dual-Interface Design: Both the Telegram bot commands (`/shop`, `/buy`) and dashboard frontend (Boutique tab) access the same unified SQLite database.
- [x] Flexible Point-Based Accountability: Rewards are purchased with gold, which is accumulated through point-based daily scoring, todos, and substeps.
- [x] Multi-User Foundation & Privacy: Rewards are isolated per `user_id`. One user cannot view, edit, or purchase another user's rewards.
- [x] Self-Hosted Pi & Docker: Lightweight services keeping CPU/RAM usage low to fit within the 40MB limits.
- [x] Strict API Contract & Integration-Ready: Clean REST API endpoints under `/api/v1/rewards` return structured JSON and manage integrity locks.

## Project Structure

### Documentation (this feature)

```text
specs/005-reward-shop/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── rewards-api.md   # Phase 1 output: REST API contracts
└── tasks.md             # Phase 2 output (generated later)
```

### Source Code

```text
backend/
├── src/
│   ├── database/
│   │   ├── models.py                   # MODIFY: Add Reward table schema
│   │   └── migrations/
│   │       └── v6_rewards.sql          # NEW: SQL migration to create rewards table
│   ├── api/
│   │   └── routes.py                   # MODIFY: Add Reward schemas and REST routes
│   ├── bot/
│   │   ├── parser.py                   # MODIFY: Add /shop and /buy commands parsing
│   │   └── listener.py                 # MODIFY: Handle /shop and /buy command routing
│   └── services/
│       └── reward_service.py           # NEW: Gold checks, requirements checks, purchase transactions
└── tests/
    └── test_rewards.py                 # NEW: Unit tests for rewards CRUD & purchases

frontend/
├── index.html                          # MODIFY: Add "Boutique" tab link and section
├── css/style.css                       # MODIFY: Add custom boutique responsive card styling
└── js/app.js                           # MODIFY: Add boutique tab navigation, fetch, create/delete, purchase logic

COMMANDS-INDEX.md                       # MODIFY: Index new /shop and /buy commands
```

**Structure Decision**: Web application option matching the current project layout. All backend code sits in `backend/` and frontend in `frontend/`.

## Complexity Tracking

*No constitution violations detected. The feature aligns with all core principles.*
