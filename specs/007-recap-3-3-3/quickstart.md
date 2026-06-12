# Quickstart: 3-3-3 Recap Dashboard Panel

## Running the Migration
Apply the manual SQLite migration script:
```bash
sqlite3 backend/data/habit_tracker.db < backend/src/database/migrations/v8_pinned_items.sql
```

## Running the Backend API
Start the FastAPI server in development mode:
```bash
PYTHONPATH=backend python3 backend/src/main.py
```

## Running the Bot Daemon (optional)
Start the Telegram Bot listener daemon:
```bash
PYTHONPATH=backend python3 backend/src/bot/listener.py
```

## Running Tests
Execute the unit tests to verify database changes and API endpoints:
```bash
PYTHONPATH=backend .venv/bin/pytest backend/tests/test_profile_pins.py
```
