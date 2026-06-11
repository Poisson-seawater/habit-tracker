# Quickstart: Softskill Progress Tree

This guide covers how to set up, run, and test the Softskill Progress Tree locally.

## 1. Setup Configuration File
Ensure the static configuration file `backend/src/data/softskills_tree.json` is created with a default set of branches and skills. You can use the default configuration provided in `specs/003-softskill-tree/research.md`.

## 2. Apply Database Migration
Run the manual database migration script to add the new `user_softskill_progress` table.
```bash
sqlite3 backend/data/habit_tracker.db < backend/src/database/migrations/v3_softskills.sql
```

## 3. Launch the Backend & Frontend
Start the local FastAPI development server:
```bash
PYTHONPATH=backend python3 backend/src/main.py
```
Open `http://localhost:5000` in your browser. The "Softskills" tab will render the interactive SVG skill tree.

## 4. Run Automated Tests
Verify backend correctness by running pytest:
```bash
PYTHONPATH=backend .venv/bin/pytest backend/tests
```
Specifically, tests should target route validation, prerequisite completion checks, and json schema loading.
