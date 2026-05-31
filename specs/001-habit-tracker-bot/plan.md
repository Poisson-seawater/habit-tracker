# Implementation Plan: habit-tracker-bot

**Branch**: `001-habit-tracker-bot` | **Date**: 2026-05-31 | **Spec**: [specs/001-habit-tracker-bot/spec.md](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/specs/001-habit-tracker-bot/spec.md)

**Input**: Feature specification from `/specs/001-habit-tracker-bot/spec.md`

## Summary

The habit tracker is designed as a self-hosted, lightweight RPG-accountability ecosystem running on a 2GB Raspberry Pi 5 under Docker Compose. Daily operations (binarized habit checking, quantitative logging, templates switching, and status checks) are handled via a strict Telegram Bot chat interface to ensure zero friction. Visual analysis, quête progress, and RPG character sheet progress are displayed on a localhost web dashboard. The backend is a modular Python FastAPI server that decouples the data layer (SQLite database) from both the Telegram bot listener and the visual dashboard assets.

## Technical Context

**Language/Version**: Python 3.11 (Native async uvicorn stack)

**Primary Dependencies**: FastAPI (backend REST API), python-telegram-bot (async bot daemon), SQLAlchemy (database ORM)

**Storage**: SQLite (stored in shared local file `/data/habit_tracker.db` mounted via Docker volumes)

**Testing**: pytest (for unit and integration endpoints testing)

**Target Platform**: Linux ARM64 (Raspberry Pi 5 hosted in Docker containers)

**Project Type**: Web Service + Background Bot Daemon

**Performance Goals**: API response time < 100ms, Bot message parsing time < 100ms

**Constraints**: Stack memory footprint strictly limited to < 75MB baseline to run reliably on the 2GB Pi 5

**Scale/Scope**: Solo V1 user with isolated fields ready to scale for multi-user in V2

## Constitution Check

*GATE: Passed successfully before Phase 0 research. Re-checked after Phase 1 design.*

- [x] Dual-Interface Design: The SQLite database serves as the single source of truth for both the bot listener and the FastAPI dashboard backend.
- [x] Flexible Point-Based Accountability: Habits award points to 12 customizable stats, computed at 23:59 and compared against dynamic template thresholds.
- [x] Multi-User Foundation & Privacy: Database schema isolates users via `user_id` relations, and group recap generation masks private habit text labels.
- [x] Self-Hosted Pi & Docker: Containerized service configurations with memory-cap limits (<40M and <35M) for efficient 24/7 Pi 5 hosting.
- [x] Strict API Contract & Integration-Ready: Decoupled REST routes isolate the SQLite storage layer from external interaction daemons.

## Project Structure

### Documentation (this feature)

```text
specs/001-habit-tracker-bot/
├── plan.md              # This file
├── research.md          # Technology choices and memory optimization details
├── data-model.md        # SQLite database schema and Mermaid ERD
├── quickstart.md        # Step-by-step launch manual
└── contracts/           # API and Bot command interfaces
    ├── bot-commands.md  # Telegram commands parsing rules
    └── rest-api.md      # REST endpoints JSON contracts
```

### Source Code

```text
backend/
├── src/
│   ├── api/             # FastAPI routers, app bootstrap, CORS configs
│   ├── bot/             # Telegram bot listener code and handler modules
│   ├── database/        # SQLite migrations, models, CRUD queries
│   └── main.py          # Entrypoint script
├── Dockerfile.api       # FastAPI container build script
├── Dockerfile.bot       # Telegram bot container build script
└── tests/               # Unit, integration, and mock contract tests

frontend/
├── src/
│   ├── index.html       # Visual RPG character sheet layout
│   ├── css/             # Custom responsive styling and dark templates
│   └── js/              # Vanilla ES6 fetch client and visual components
```

**Structure Decision**: Option 2: Web application. The layout separates backend containers (`backend/` API and Bot listener) from the static web asset files (`frontend/`), ensuring modular container builds and optimal local resource isolation.

## Complexity Tracking

*(No constitution check violations; architecture strictly adheres to lightweight design constraints).*
