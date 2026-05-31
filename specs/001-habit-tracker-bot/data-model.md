# Database Schema & Data Model: habit-tracker-bot

This document defines the SQLite data model and schema relationships for the habit tracker.

```mermaid
erDiagram
    users ||--o{ habit_logs : logs
    users ||--o{ daily_scores : scores
    users ||--o{ streaks : tracking
    habits ||--o{ habit_logs : records

    habits {
        INTEGER id PK
        VARCHAR name
        TEXT description
        VARCHAR type "binary | quantitative"
        VARCHAR frequency "daily | weekly | custom"
        VARCHAR scheduled_days "e.g., '1,3,5' for Mon,Wed,Fri"
        VARCHAR reminder_time "HH:MM format, optional"
        BOOLEAN is_private
        BOOLEAN is_reportable
        BOOLEAN is_mandatory
        TEXT point_rewards "JSON mapping, e.g., {'discipline': 2, 'creativity': 5}"
        INTEGER daily_cap "optional point cap"
        BOOLEAN is_active
    }

    users {
        INTEGER id PK
        VARCHAR username
        VARCHAR chat_id "Telegram unique ID"
        DATETIME created_at
    }

    habit_logs {
        INTEGER id PK
        INTEGER user_id FK
        INTEGER habit_id FK
        DATETIME timestamp
        VARCHAR log_type "done | skip | log"
        INTEGER amount "optional quantitative value"
        VARCHAR unit "optional, e.g. min, km"
        TEXT reason "optional, for skips"
    }

    day_templates {
        INTEGER id PK
        VARCHAR name "e.g., Semaine, Weekend, Malade"
        TEXT acceptable_thresholds "JSON, e.g., {'discipline': 5, 'force': 10}"
        TEXT perfect_thresholds "JSON, e.g., {'discipline': 8, 'force': 20}"
    }

    daily_scores {
        INTEGER id PK
        INTEGER user_id FK
        DATE date
        VARCHAR status "Failed | Acceptable | Perfect"
        INTEGER active_template_id FK
        TEXT actual_stats "JSON mapping, e.g., {'discipline': 6, 'force': 12}"
    }

    streaks {
        INTEGER id PK
        INTEGER user_id FK
        VARCHAR streak_type "Acceptable | Perfect | habit:[habit_id]"
        INTEGER current_streak
        INTEGER max_streak
        DATE last_incremented
    }
```

## Schema Details & Constraints

### 1. `users` Table
- Stores participants. In V1 solo-mode, there is exactly one user row (e.g. username `Gabriel`), but the schema fully supports multi-user tracking (V2 ready).
- `chat_id`: Unique index to look up users by their incoming Telegram messaging ID.

### 2. `habits` Table
- `type`: Must be strictly `binary` (yes/no) or `quantitative` (measurable duration or quantity).
- `point_rewards`: Stores a JSON dictionary mapping the 12 general stats to specific awarded values (e.g., `{"creativity": 5, "discipline": 2}`).
- `scheduled_days`: Comma-separated integers `0` (Sunday) to `6` (Saturday) indicating when the habit is expected.

### 3. `habit_logs` Table
- `log_type`: Restricted to `done` (completed habit), `skip` (excused failure with reason), or `log` (quantitative logging).
- `amount` and `unit`: Required for quantitative logs (e.g., amount `30` and unit `min` for `/log lecture 30min`).
- Integrity: Cascade deletes on user or habit deletion.

### 4. `day_templates` Table
- Defaults:
  - ID 1: `Semaine` (default Mon-Fri)
  - ID 2: `Weekend` (default Sat-Sun)
  - ID 3: `Récupération` (manual switch)
  - ID 4: `Malade` (manual switch)
- `acceptable_thresholds` / `perfect_thresholds`: JSON mapping of stats needed to validate a day (e.g., `{"discipline": 5}`).

### 5. `daily_scores` Table
- Evaluated daily at 23:59 via database scheduler.
- Computes daily points across the 12 stats based on the logs for that date, applying daily caps.
- Compares computed totals against the `acceptable_thresholds` and `perfect_thresholds` of the currently active day template.

### 6. `streaks` Table
- `streak_type`: Can track the overall `Acceptable` streak, the `Perfect` streak, or individual habit streaks.
- `last_incremented`: Keeps track of date of last update to prevent double-increments on the same calendar day and manage streak breaking.
