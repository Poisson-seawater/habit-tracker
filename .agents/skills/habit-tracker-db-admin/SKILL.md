---
name: "habit-tracker-db-admin"
description: "Modify Gabriel's Habit Tracker SQLite data safely: add or validate habits, goals, todos, no-todos, logs, templates, and user records without corrupting the shared bot/dashboard database."
compatibility: "Habit Tracker MVP/V2"
metadata:
  purpose: "Safe database operations for LLM agents"
---

# Habit Tracker DB Admin

Use this skill whenever a task asks to modify Habit Tracker data directly or indirectly: users, habits, habit logs, goals, substeps, todos, no-todos, daily scores, streaks, templates, or DB snapshots.

## Core Rules

- Read `backend/src/database/models.py` before changing DB data. The SQLAlchemy models are the source of truth.
- Never edit `data/habit_tracker.db` with ad hoc shell SQL unless the user explicitly asks for a one-off emergency fix.
- Prefer a small Python script using `sqlite3` or the project SQLAlchemy models, run from the repo root.
- Always create a DB backup before mutating data. Use `python3 ops/db/habit_tracker_db_admin.py inspect` first, then backup through the same maintenance script or copy to `data/backups/`.
- Keep `data/` ignored by Git. To move DB state through GitHub, export `ops/db/habit_tracker_snapshot.sql` with `python3 ops/db/habit_tracker_db_admin.py export-snapshot`.
- After changes, verify no orphan rows and run focused tests.

## User Resolution

- Bot and dashboard data are partitioned by `users.id`.
- Use `chat_id` as the durable Telegram identity when available.
- Do not rename an existing DB user just because Telegram sends a different `username`; the displayed RPG profile name may intentionally differ from Telegram.
- For Gabriel production data, the canonical profile should be username `Gabriel`.

## Common Operations

### Add a Habit

- Insert into `habits` with the target `user_id`.
- Required fields: `name`, `type`, `point_rewards`.
- Valid `type`: `binary` or `quantitative`.
- For quantitative habits, set `unit`; for binary habits, leave `unit` null.
- Use unique habit names per user. Check `(user_id, name)` before insert.
- If adding through API behavior, mirror `HabitCreate` in `backend/src/api/routes.py`.

### Validate or Log a Habit

- Binary completion: insert `habit_logs` with `log_type="done"`.
- Quantitative completion: insert `habit_logs` with `log_type="log"`, `amount`, and `unit`.
- Skip: insert `habit_logs` with `log_type="skip"` and `reason`.
- After inserting a log, recalculate today with `calculate_daily_score(db, user_id, date)` and `update_streaks(db, user_id, date)` from `backend/src/services/score_service.py`.
- Do not log inactive habits.

### Add or Complete a Todo

- Insert into `todos` with `title`, optional stat rewards, and `xp_reward` between 0 and 40.
- To complete, set `is_completed=True` and `completed_at` to current UTC time.
- Then award XP through existing service behavior where possible and recalculate daily score/streaks.

### Add or Fail a No-Todo

- Insert into `notodos` with `user_id` and `title`.
- To mark a failure, set `failed_at` to current UTC time.
- No-todo failures are displayed in `/status`; they are not habit logs.

### Add Goals and Substeps

- Insert long-term objectives into `goals`.
- Insert steps into `substeps`, including `gold_reward`, optional `stats_json`, and `execution_order`.
- Link them through `goal_substep_links`.
- To complete a substep, prefer the API/service route behavior: set `completed=True`, set `completed_at`, add `gold_reward` to the user, and mark parent goals complete only when all linked substeps are complete.

### Templates and Daily Scores

- Templates live in `perfect_day_templates` as JSON thresholds per user and template key.
- Valid template keys are `week`, `weekend`, `recup`, and `malade`.
- Daily score rows are derived data. Prefer recalculation over manual edits unless fixing a known bad row.

## Snapshot Workflow

From the repo root:

```bash
python3 ops/db/habit_tracker_db_admin.py inspect
python3 ops/db/habit_tracker_db_admin.py export-snapshot
```

On the Raspberry Pi after `git pull`:

```bash
docker compose down
python3 ops/db/habit_tracker_db_admin.py restore-snapshot
docker compose up -d --build
docker compose ps
```

If anything looks wrong, restore the backup created under `data/backups/`.
