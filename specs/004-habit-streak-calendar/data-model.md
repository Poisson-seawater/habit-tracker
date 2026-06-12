# Data Model: Habit Streak Counter & Calendar

## Schema Modifications

### Table: `habits`
We need to extend the `habits` table with two new columns:
1. `deactivated_at`: Stores the timestamp when the habit was last deactivated. Used for validating the 14-day freeze limit.
2. `created_at`: Stores the timestamp when the habit was created. Used to determine if calendar days are before the habit existed (which display as neutral/pre-creation days instead of missed).

```sql
-- migration file: backend/src/database/migrations/v5_habit_deactivation.sql
ALTER TABLE habits ADD COLUMN deactivated_at DATETIME;
ALTER TABLE habits ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP;
```

#### Updated Entity Model Mapping:
```python
# backend/src/database/models.py
class Habit(Base):
    # ... existing columns ...
    deactivated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)
```

---

## Validation & State Transitions

### 1. Habit Activation State Changes
- **Transition to Inactive (Deactivation)**:
  - Trigger: Delete API request (`DELETE /api/v1/habits/{id}`) or edit API request updating `is_active=False`.
  - Action: Update `is_active = False` and set `deactivated_at = datetime.datetime.now()`.
- **Transition to Active (Reactivation)**:
  - Trigger: Edit API request (`PUT /api/v1/habits/{id}`) updating `is_active=True`.
  - Action: 
    1. Check if `deactivated_at` is set.
    2. Calculate `now() - deactivated_at`.
    3. If duration > 14 days, locate the habit's corresponding `Streak` record (`streak_type = f"habit:{habit.id}"`) and reset `current_streak = 0`.
    4. Set `is_active = True` and reset `deactivated_at = None`.

### 2. Streak Continuity Calculation (Non-Daily Frequency)
To evaluate the streak properly:
- Find the habit's scheduled days.
- When incrementing the streak, instead of checking if `last_incremented == yesterday`:
  1. Retrieve the list of scheduled dates in chronological order before the current date.
  2. Find the *most recent* scheduled date before the log date.
  3. If `last_incremented` matches this most recent scheduled date, the streak continues.
  4. If `last_incremented` is older than this date, the streak resets to 1 (since the user missed a scheduled day).
  5. If the log type is `skip`, the streak's `last_incremented` moves to the current day but the count does not increment.
