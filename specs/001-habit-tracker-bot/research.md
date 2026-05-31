# Research & Technical Decisions: habit-tracker-bot

This document details the architectural decisions and technology evaluations made during the design phase of the self-hosted habit tracker.

## 1. Storage Choice (Database)

- **Decision**: **SQLite** (via Python `sqlite3` and `SQLAlchemy`).
- **Rationale**: 
  - Zero baseline memory overhead (runs in-process within the FastAPI container).
  - Simple local file backup: the entire database is a single `habit_tracker.db` file that can be copied or backed up with standard cron scripts.
  - Excellent read/write speed for a single-user system.
- **Alternatives Considered**: 
  - *PostgreSQL*: Rejected because it requires a dedicated container running a persistent DBMS daemon, consuming a baseline of 100MB to 150MB of RAM, violating the 2GB Pi 5 lightweight footprint goal.

## 2. Programming Language & Frameworks

- **Decision**: **Python 3.11** with **FastAPI** (REST API backend) and **python-telegram-bot** (Bot Listener daemon).
- **Rationale**:
  - *FastAPI + Uvicorn* uses minimal RAM (<25MB baseline) while delivering high-throughput async processing and automatic OpenAPI docs.
  - *python-telegram-bot* provides an extremely stable, async-native wrapper for the Telegram Bot API with robust polling handlers.
  - Dual-process separation: The API server and the Bot daemon run as separate lightweight containers sharing the same database volume, ensuring high reliability and separation of concerns.
- **Alternatives Considered**:
  - *Node.js (Express / Telegraf)*: Comparable, but Python is favored for its native SQLite integration and simpler rapid-prototyping scripting on local Linux platforms.
  - *Rust*: Highly lightweight but rejected due to high compilation times and slower development speed for a V1 prototype.

## 3. Frontend Web Dashboard Stack

- **Decision**: **Vanilla HTML5 / CSS3 / ES6+ JavaScript** served as static files by FastAPI.
- **Rationale**:
  - Zero server-side runtime overhead: Frontend files are served statically from memory or disk by the backend, completely eliminating a Node/React server container (saving ~50-80MB RAM).
  - Fully complies with our *Vanilla-First* and *Premium Aesthetics* design language (clean HSL Hues, CSS grid layout, smooth visual animations, and glassmorphism styling).
- **Alternatives Considered**:
  - *Next.js / React*: Rejected because it introduces massive compile-time and runtime memory overheads, which are entirely unnecessary for a local analytical dashboard.

## 4. Containerization & Deployment

- **Decision**: **Docker Compose** with 2 lightweight services sharing a volume.
  - Service `api`: Runs the FastAPI server on port 5000, mounting `./data` volume (holds the SQLite database) and serving the web dashboard files.
  - Service `bot`: Runs the Telegram bot daemon in async polling mode, sharing the same `./data` database volume.
- **Rationale**: Ensures both components run persistently with automatic `restart: always` policies, isolated environments, and easy configuration using a local `.env` secrets file.
