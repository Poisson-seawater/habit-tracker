<!--
SYNC IMPACT REPORT
==================
- Version change: v1.0.0 → v2.0.0
- List of modified principles:
  * I. Client-Side Local-First Architecture → I. Dual-Interface Design (Bot-First + Dashboard)
  * II. Premium Aesthetics & Modern Design → II. Flexible Point-Based Accountability
  * III. Standard Tech Stack Discipline (Vanilla-First) → III. Multi-User Foundation & Privacy Gates
  * IV. Robust State & Local Persistence → IV. Self-Hosted Raspberry Pi & Docker Architecture
  * V. Web Standards, SEO & Accessibility (a11y) → V. Strict API Contract & Integration-Ready
- Added sections: None
- Removed sections: None
- Templates requiring updates:
  * .specify/templates/plan-template.md (✅ updated)
  * .specify/templates/spec-template.md (✅ updated - no changes needed)
  * .specify/templates/tasks-template.md (✅ updated - no changes needed)
- Follow-up TODOs: None
-->

# habit-tracker Constitution

## Core Principles

### I. Dual-Interface Design (Bot-First + Dashboard)
Daily operations (logging habits, skips, viewing day status) MUST happen via the Telegram/Discord
bot in a group to minimize user friction. The localhost web dashboard acts as a visual, interactive
analytical character sheet. Both interfaces MUST read/write from a single source of truth database.

### II. Flexible Point-Based Accountability
Daily validation is evaluated via points and customizable stat thresholds (Acceptable Day and
Perfect Day) rather than rigid checkboxes. Habits reward points to customizable stats (capped
daily), letting the user validate their streak via diverse, flexible combinations of actions.

### III. Multi-User Foundation & Privacy Gates
The database schema and API structure MUST support user isolation (with a `users` table in V1) to
make V2 multi-user expansion seamless. Strict privacy gates must separate private habits and reasons
from being broadcast in the public chat group recaps.

### IV. Self-Hosted Raspberry Pi & Docker Architecture
The system must be fully self-hostable, containerized with Docker Compose, and optimized to run
reliably 24/7 on a Raspberry Pi 5. Structured persistence (SQLite/PostgreSQL) and simple database
backups are essential to protect the long-term history of habit data.

### V. Strict API Contract & Integration-Ready
A robust internal REST API must decouple the data layer from both the bot daemon and the web
dashboard. This ensures a clean separation of concerns and guarantees the system is ready to integrate
with external calendar/todo tools (V3) and skill-tree RPG mechanics (V2).

## Technical Constraints & Stack

- **Platform**: Raspberry Pi 5 (ARM64) hosted via Docker Compose.
- **Database**: PostgreSQL or SQLite for local structured persistence.
- **Backend API**: Modern, lightweight REST API (e.g. Python FastAPI or Node.js Express).
- **Frontend Dashboard**: Localhost web dashboard combining character sheet styling with analytical tools.
- **Chat Bot**: Telegram Bot API (or Discord Bot API) running as a group-listening bot daemon.

## Development Quality Gates

- **Integration Contracts**: Every API route and bot command must have structured error handling and return deterministic JSON responses.
- **State Isolation**: Database migrations must be managed systematically to protect local data history.
- **Performance & Uptime**: The bot listener and cron-scheduler must run as persistent daemon containers with automatic recovery.

## Governance

- This constitution governs the design of the habit-tracker RPG/Accountability system.
- Any changes to core principles, stat systems, or interfaces require updating this constitution with a version bump.
- Refer to [cahier-des-charges](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/cahier-des-charges) for full product and feature details.

**Version**: 2.0.0 | **Ratified**: 2026-05-31 | **Last Amended**: 2026-05-31
