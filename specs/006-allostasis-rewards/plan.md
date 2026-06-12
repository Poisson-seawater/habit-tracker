# Implementation Plan: Allostasis Rewards

**Branch**: `006-allostasis-rewards` | **Date**: 2026-06-12 | **Spec**: [spec.md](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/specs/006-allostasis-rewards/spec.md)

**Input**: Feature specification from `/specs/006-allostasis-rewards/spec.md`

## Summary

Add daily and weekly "Allostasis" rewards to the shop. Allostasis rewards are special, repeatable items with zero gold cost (capped at 3 items per category: daily/weekly). When redeemed, they are logged/tracked via `last_purchased_at` and shown in the daily group recap. This involves SQLite schema updates, FastAPI REST API modifications, Telegram bot shop integration, and an interactive, beautifully structured allostasis section on the Web Dashboard.

## Technical Context

**Language/Version**: Python 3.12 (Backend), ES6 JavaScript (Frontend, No Build/No Framework)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.0, python-telegram-bot[ext]

**Storage**: SQLite (`data/habit_tracker.db` in local, `/data/habit_tracker.db` in Docker)

**Testing**: pytest

**Target Platform**: Raspberry Pi 5 (ARM64) via Docker Compose

**Project Type**: Web Service / Chat Bot

**Performance Goals**: API response time < 50ms, Shop load time < 200ms

**Constraints**: API memory limit 40MB, Bot listener memory limit 35MB. Keep frontend vanilla JS/CSS lightweight.

## Constitution Check

- [x] Dual-Interface Design: Both the Telegram bot and localhost dashboard access a single unified SQLite database. Users can redeem allostasis items via either the Telegram bot or the dashboard.
- [x] Flexible Point-Based Accountability: Allostasis rewards are zero-cost items that represent healthy daily/weekly recovery activities, integrating with daily recap reporting.
- [x] Multi-User Foundation & Privacy: All rewards filter and isolate data by the `user_id` context.
- [x] Self-Hosted Pi & Docker: Lightweight SQLite migrations and minor memory overhead keep the Raspberry Pi constraints satisfied.
- [x] Strict API Contract & Integration-Ready: Updates current reward API endpoints to support categorizing and purchasing allostasis items.

## Project Structure

### Documentation (this feature)

```text
specs/006-allostasis-rewards/
├── spec.md              # Feature specification
├── checklists/
│   └── requirements.md  # Spec quality validation checklist
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── contracts/
    └── rewards-api.md   # Phase 1 output
```

### Source Code

```text
backend/
├── src/
│   ├── database/
│   │   ├── models.py        # Modify: add category and last_purchased_at to Reward model
│   │   └── migrations/
│   │       └── v7_allostasis_rewards.sql  # [NEW] migration file
│   │   └── seed.py          # Modify: update seed data if needed
│   ├── api/
│   │   └── routes.py        # Modify: update Reward schemas, validation, creation caps, and purchase logic
│   ├── bot/
│   │   ├── listener.py      # Modify: add bot command support or shop view formatting
│   │   └── scheduler.py     # Modify: inject today's allostasis purchases into publish_daily_recap()
│   └── services/
│       └── reward_service.py # Modify: add validation logic for purchase availability and capping rules
frontend/
├── index.html               # Modify: add Allostasis categories and category dropdown to create/edit form
├── css/style.css            # Modify: add styling for Allostasis section, buttons, and custom badges
└── js/app.js                # Modify: update fetchRewards, form submission, and purchase triggers
```

**Structure Decision**: Web application option, since the codebase consists of FastAPI backend and vanilla HTML/CSS/JS frontend.
