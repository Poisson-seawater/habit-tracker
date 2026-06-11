# Implementation Plan: Softskill Progress Tree

**Branch**: `003-softskill-tree` | **Date**: 2026-06-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-softskill-tree/spec.md`

## Summary

The Softskill Progress Tree feature introduces a unified visual dashboard view styled like an RPG skill tree to display and track personal softskill progression.
The technical approach includes:
1. Defining the tree structure, colors, layout positions, and prerequisites in a static JSON configuration file on the backend.
2. Introducing new database models (`SoftskillProgress`) to persist user-specific progress, custom success tests, and completion status.
3. Exposing REST endpoints in the FastAPI backend under `/api/v1/softskills` to retrieve the tree structure, fetch current user progress, save a custom success test, and manually toggle skill completion.
4. Implementing an interactive SVG-based rendering canvas in the frontend using Vanilla JS ES6 within the existing multi-tab layout, styled with the dark theme and glassmorphism of the application.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI, SQLAlchemy 2.0, python-telegram-bot

**Storage**: SQLite (`backend/data/habit_tracker.db`)

**Testing**: pytest

**Target Platform**: Linux (Raspberry Pi 5 hosted via Docker Compose)

**Project Type**: web-service

**Performance Goals**: Page rendering and node graph initialization under 500ms

**Constraints**: API memory footprint < 40MB; Vanilla JS without build step or external frameworks; clean user isolation using `X-User-ID` header.

**Scale/Scope**: ~10-20 softskills grouped into 2-4 primary progression branches for 2 concurrent users.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Dual-Interface Design: Ensure both the Telegram/Discord bot and localhost dashboard access a single unified database.
- [x] Flexible Point-Based Accountability: Ensure habits award configurable stat points (capped daily) to validate daily streak thresholds.
- [x] Multi-User Foundation & Privacy: Ensure database schema supports user isolation and strict data-privacy gates for group recaps.
- [x] Self-Hosted Pi & Docker: Ensure lightweight, containerized Docker Compose setup optimized for persistent running on a Raspberry Pi 5.
- [x] Strict API Contract & Integration-Ready: Ensure backend exposes clean internal REST endpoints decoupling the database from bot and web UI.

## Project Structure

### Documentation (this feature)

```text
specs/003-softskill-tree/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
  src/
    api/
      routes.py        # Expose new /api/v1/softskills endpoints
    database/
      models.py        # Add UserSoftskillProgress model and database tables
      migrations/      # Write manual migration SQL script (e.g. v3_softskills.sql)
    bot/
      parser.py        # Add command parsing if needed (bot updates out of scope for MVP, but system is extensible)
      listener.py
    services/
      softskill_service.py  # Handle business logic for configuration loading and validation
frontend/
  index.html           # Add "Softskills" tab to navigation and container panel
  css/style.css        # Visual styles for the SVG skill tree and node states
  js/app.js            # Fetch and render the softskill SVG tree layout, handle modal detail viewer and updates
```

**Structure Decision**: Option 2 (Web application structure) is utilized as the backend uses FastAPI and the frontend uses Vanilla JS. We are adding files to the existing structure.

## Complexity Tracking

*No violations of the constitution were identified.*
