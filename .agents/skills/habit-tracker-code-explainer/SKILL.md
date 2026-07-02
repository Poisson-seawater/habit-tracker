---
name: "habit-tracker-code-explainer"
description: "Explain the Habit Tracker codebase architecture, database models, API routes, Telegram bot features, and specific features like Life Lore and Daily Recap to users or other agents."
compatibility: "Habit Tracker MVP/V2"
metadata:
  purpose: "Codebase architecture and custom feature explanations"
---

# Habit Tracker Code Explainer

This skill provides a comprehensive architectural guide of the RPG Accountability Habit Tracker. Use this skill to explain how the code is structured, how the database schema works, how API routes interact with the bot and frontend, and how custom subsystems (like Life Lore or Allostasis) operate.

---

## 🏛️ General Architecture

The project is a lightweight, low-memory RPG Accountability system that runs on a Raspberry Pi. It is divided into three primary components sharing a single SQLite database:

1. **Backend API (FastAPI + SQLAlchemy 2.0)**:
   - Serves REST endpoints for the dashboard and automation clients.
   - Handled asynchronously with Uvicorn.
   - Mounted in Docker under a strict memory cap of **40 MB**.
2. **Telegram Bot (`python-telegram-bot`)**:
   - Runs as a listener daemon processing group chat commands and private messages.
   - Tracks streaks, scores, daily check-ins, boutique purchases, and softskills.
   - Mounted in Docker under a memory cap of **35 MB**.
3. **Frontend (Vanilla HTML/CSS/JS ES6)**:
   - Pure client-side application served statically by FastAPI.
   - No build tools, bundlers, or frameworks.
   - Communicates with the API using local credentials stored in `localStorage` under `X-User-ID`.

---

## 🗄️ Database Schema & Models (`backend/src/database/models.py`)

All tables partition data using the `user_id` foreign key pointing to the `users` table:

- **`users`**: Stores adventurer profile stats (username, chat_id, level, xp, gold, active_template, pinned items).
- **`habits`**: Habits definition (binary or quantitative, stats rewards, target per day).
- **`habit_logs`**: Logs check-ins (`done`, `log`, or `skip` with reason) of habits per day.
- **`todos`**: Simple tasks with custom XP and stats rewards, plus completion status.
- **`notodos`**: Rules/habits NOT to do. Violating them logs a failure with a timestamp.
- **`goals` & `substeps` & `goal_substep_links`**: 
  - `goals` represent long-term milestones.
  - `substeps` are individual tasks linked to goals.
  - Substeps can have stats rewards, a gold reward, and the `is_life_lore` boolean flag.
  - Complete goals automatically when all substeps are complete.
- **`rewards`**: Store items/activities (allostasis or basic) purchasable with user gold.
- **`daily_scores`**: Ephemeral scores calculated daily based on validated habits/tasks thresholds.
- **`streaks`**: Track perfect days, habits streak counts, freeze status, etc.

---

## 📖 Feature Spotlight: Life Lore Subsystem

The Life Lore system allows users to flag certain milestone subgoals as historical achievements. When completed, these items populate the daily character sheet stats and write to the adventurer's permanent grimoire history.

### 1. Database & Migrations
- The table `substeps` contains a column `is_life_lore` (Boolean, default False).
- Migration `v13_substep_life_lore.sql` handles adding the column to SQLite. It is run automatically on startup via `seed.py`.

### 2. Backend Flow (`backend/src/api/routes.py`)
- **Creation & Modification**: Substeps are created via `POST /api/v1/goals/{goal_id}/substeps` and updated via `PUT /api/v1/substeps/{substep_id}`. Both parse and store `is_life_lore`.
- **Today's Stats**: `GET /api/v1/profile` computes today's completed items. If a completed subgoal has `is_life_lore = True` and was completed today, it is appended to `life_lore_today`.
- **History Grimoire**: `GET /api/v1/profile/life-lore` queries all completed substeps of all time where `is_life_lore = True`, sorted chronologically by completion date.

### 3. Telegram Bot Notifications (`listener.py` & `scheduler.py`)
- **Status command (`/status`)**: When querying status, the bot fetches today's completed life lore items and lists them under an "Achievements" section.
- **Daily Recap (21:30)**: The scheduler calculates scores and formats a Markdown message containing today's completed life lore items for the daily recap in the guild Telegram group.

### 4. Frontend Integration (`index.html`, `style.css`, `app.js`)
- **Forms**: Creation and editing subgoal forms contain a checkbox: `📖 Marquer comme Life Lore`.
- **Dashboard Stats Panel**: A section `daily-life-lore-container` renders today's completed life lore items as golden-rimmed lists.
- **Grimoire Modal**: Clicking the user profile avatar (`.avatar-container`) triggers an async request to `/api/v1/profile/life-lore` and opens a scrollable, premium grimoire showing all-time achievements.

---

## 🛠️ Verification & Diagnostic Script

To verify that all components are connected correctly, you can run:

```bash
# Check FastAPI status
curl http://localhost:5000/health

# Run test suite
PYTHONPATH=backend .venv/bin/pytest backend/tests/test_life_lore.py
```
