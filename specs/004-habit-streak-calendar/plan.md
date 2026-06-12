# Implementation Plan: Habit Streak Counter & Calendar

**Branch**: `004-habit-streak-calendar` | **Date**: 2026-06-12 | **Spec**: [spec.md](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/specs/004-habit-streak-calendar/spec.md)

## Summary
Implement a visual calendar and streak counter per habit on the Habit RPG Tracker. This involves extending the `habits` schema with deactivation and creation timestamps, rewriting the streak update service to accurately track streaks for non-daily frequencies, and creating a new detail modal/panel on the web dashboard featuring a monthly completion grid, streak progress badges, milestone rewards (+100 XP/+50 Gold at 30 days, +300 XP/+150 Gold at 90 days), and habit deactivation controls.

## Technical Context

**Language/Version**: Python 3.12 (Backend), ES6 JavaScript (Frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.0, Uvicorn, python-telegram-bot

**Storage**: SQLite (`backend/data/habit_tracker.db`)

**Testing**: pytest

**Target Platform**: Linux / self-hosted Docker on Raspberry Pi 5

**Project Type**: Web Service / Chat Bot

**Performance Goals**: Page & Calendar load < 1s, API response time < 100ms.

**Constraints**: Memory limits: 40MB API, 35MB Bot. Keep JS and CSS light, utilizing native DOM APIs.

## Constitution Check

- [x] **Dual-Interface Design**: Both the Telegram/Discord bot and localhost dashboard access a single unified SQLite database.
- [x] **Flexible Point-Based Accountability**: Individual habit streaks and calendars supplement the daily point-based accountability without altering daily score evaluation.
- [x] **Multi-User Foundation & Privacy**: Every query and transaction filters by the header `X-User-ID` to ensure data isolation.
- [x] **Self-Hosted Pi & Docker**: Single-file SQLite storage and light backend dependencies ensure the 40MB/35MB constraints are respected.
- [x] **Strict API Contract & Integration-Ready**: Exposes a new `/api/v1/habits/{habit_id}/calendar` REST contract returning structured completion records.

---

## Project Structure

### Documentation (this feature)
```text
specs/004-habit-streak-calendar/
├── plan.md              # This file
├── research.md          # Phase 0 output (Findings and design decisions)
├── data-model.md        # Phase 1 output (Schema modifications and state logic)
├── quickstart.md        # Phase 1 output (Test guidelines)
└── contracts/
    └── calendar-api.md  # Phase 1 output (API contract definitions)
```

### Source Code
```text
backend/
├── src/
│   ├── database/
│   │   ├── models.py        # Modify: add created_at, deactivated_at to Habit model
│   │   └── migrations/
│   │       └── v5_habit_deactivation.sql  # [NEW] migration file
│   │   └── seed.py          # Modify: update seeders to populate new columns
│   ├── api/
│   │   └── routes.py        # Modify: add calendar route, allow editing is_active / deactivated_at
│   └── services/
│       └── score_service.py # Modify: fix streak update logic for custom frequencies & milestones
frontend/
├── index.html               # Modify: add habit detail modal & calendar grid elements
├── js/app.js                # Modify: add detail modal rendering & month traversal logic
└── css/style.css            # Modify: add calendar grid layout and status colors
```

**Structure Decision**: Web application layout containing FastAPI backend and vanilla HTML/CSS/JS frontend.

---

## Proposed Changes

### Database Layer

#### [MODIFY] [models.py](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/backend/src/database/models.py)
- Add `deactivated_at = Column(DateTime, nullable=True)` and `created_at = Column(DateTime, default=datetime.datetime.now)` to the `Habit` model.

#### [NEW] [v5_habit_deactivation.sql](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/backend/src/database/migrations/v5_habit_deactivation.sql)
- Migration script to add `deactivated_at` and `created_at` fields to the `habits` table in the SQLite database.

#### [MODIFY] [seed.py](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/backend/src/database/seed.py)
- Update default seeded habits with default values for `created_at` and `deactivated_at`.

---

### Backend Logic & API

#### [MODIFY] [score_service.py](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/backend/src/services/score_service.py)
- Rewrite `update_streaks` logic for individual habits:
  - Find the most recent scheduled day before today.
  - If `last_incremented` matches that day, increment the streak.
  - If `last_incremented` is earlier, reset the streak to 1.
  - If log type is `skip`, update `last_incremented` to today without incrementing the count.
  - Check milestones: if `current_streak == 30`, add 100 XP (using `add_user_xp`) and 50 Gold to the user profile. If `current_streak == 90`, add 300 XP and 150 Gold. Ensure this is only rewarded once per day when the streak progresses.

#### [MODIFY] [routes.py](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/backend/src/api/routes.py)
- Add `is_active` to `HabitUpdate` payload schema.
- Update `PUT /api/v1/habits/{habit_id}` to:
  - Track if `is_active` transitions from `true` to `false` -> set `deactivated_at = datetime.datetime.now()`.
  - Track if `is_active` transitions from `false` to `true` -> if `deactivated_at` > 14 days ago, reset the streak count to 0 in the `streaks` table. Set `deactivated_at = None`.
- Add `GET /api/v1/habits/{habit_id}/calendar` endpoint:
  - Accepts `year` and `month` parameters.
  - Fetches habit, its creation date, its logs, and returns the status of each day of the month: `completed`, `missed`, `skipped`, `non-scheduled`, `future`, `pre-creation`.

---

### Frontend Dashboard

#### [MODIFY] [index.html](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/frontend/index.html)
- Add a sidebar drawer or modal container `habit-detail-modal` with elements for:
  - Habit title, description, reward stats.
  - Current streak and max streak badges.
  - Month/year navigation buttons and calendar title.
  - Calendar grid wrapper (`.calendar-grid`).
  - Active/Deactivate toggle/button.

#### [MODIFY] [style.css](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/frontend/css/style.css)
- Add calendar grid container styles (7 columns layout).
- Style individual day states:
  - Completed: Vibrant Green.
  - Missed: Muted Red/Gray.
  - Skipped: Orange/Yellow.
  - Non-scheduled: Dashed/grayed hachured style.
  - Neutral / Pre-creation / Future: Muted dark gray.
- Style streak badges (fire icon for current streak, crown icon for max streak).

#### [MODIFY] [app.js](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/frontend/js/app.js)
- Attach click event listeners to `.quest-details` in `fetchQuests`.
- Implement `openHabitDetailModal(habit, year, month)`:
  - Fetch calendar data from `/api/v1/habits/{id}/calendar?year={year}&month={month}`.
  - Render calendar grid with proper days and empty offset slots based on the month's first weekday.
  - Bind previous/next month buttons to reload.
  - Bind toggle active/inactive button to hit the update endpoint and refresh.

---

## Verification Plan

### Automated Tests
- Run backend unit tests: `PYTHONPATH=backend pytest backend/tests`
- Create a test file `backend/tests/test_habit_streaks.py` to assert:
  - Streak incrementing on consecutive scheduled days.
  - Streak freezing on skips.
  - Streak resetting after a missed scheduled day.
  - Milestone XP/Gold rewards.
  - Deactivation freeze duration (under 14 days vs over 14 days reactivation behavior).

### Manual Verification
1. Launch the server and check the dashboard on `http://localhost:5000`.
2. Click on a habit to open the detail panel and verify visual excellence.
3. Test month-by-month navigation.
4. Add logs and skips to see the calendar update in real-time.
5. Deactivate a habit, check that it disappears from the active list, check reactivation through settings (or show deactivated list), and check if the streak freezes/resets properly.
