# Research: Habit Streak Counter & Calendar

## Findings & System Analysis

### 1. Existing Streak Implementation
The codebase currently implements streaks in `backend/src/services/score_service.py` under the function `update_streaks`. 
It maintains:
- Perfect Day streak: `streak_type = "Perfect"`
- Individual habit streaks: `streak_type = "habit:[habit_id]"`

#### Existing Logic Bugs/Limitations:
1. **Non-daily schedules**: Currently, `update_streaks` checks if `h_streak.last_incremented == yesterday`. If a habit is scheduled Mon/Wed/Fri, `last_incremented` on Monday will not match `yesterday` (Tuesday) on Wednesday, causing the streak to reset to 1.
2. **Deactivation**: There is no tracking of when a habit is active/inactive relative to its streak preservation or the 14-day limit.
3. **Rewards**: Reaching 30-day and 90-day streaks does not currently award Gold or XP.
4. **Real-time incremental logic**: The system currently calculates streaks incrementally on each log entry (`create_log` calls `update_streaks`). If logs in the past are edited/deleted, the current streak count doesn't change, which is consistent with the clarified Option B.

### 2. Milestone Rewards Implementation
When a streak increases, we need to check if the new `current_streak` matches a milestone (30 or 90). If so:
- Award +100 XP and +50 Gold for the 30-day milestone.
- Award +300 XP and +150 Gold for the 90-day milestone.
- Add XP using `add_user_xp` from `score_service.py`, which handles leveling up.
- Add Gold directly to the user's `gold` attribute in the DB.
- Trigger/store the milestone validation so we don't award it multiple times if the user logs multiple entries on the same day (or if we have multiple logs on day 30, though the daily logging is already limited to once for binary habits, quantitative habits can have multiple logs). We must ensure the reward is only granted *once per milestone per streak progression*. Since streaks increment at most once per day, we can check if the milestone reward for this level (30 or 90) was already awarded for the current streak.

### 3. Calendar View Implementation
We need a monthly calendar representation for a habit.
- **Backend API Contract**: We need a new endpoint `/api/v1/habits/{habit_id}/calendar` which returns the log status for each day of a specified month/year.
- **JSON Structure**:
  ```json
  {
    "habit_id": 1,
    "year": 2026,
    "month": 6,
    "days": {
      "1": "completed",
      "2": "missed",
      "3": "skipped",
      "4": "non-scheduled",
      "5": "future",
      "6": "pre-creation"
    }
  }
  ```
- **Frontend Detail Panel**:
  When a habit list item is clicked in the dashboard, we will open a modal or panel displaying:
  - Habit description, type, frequency, point rewards.
  - Current streak and maximum streak.
  - A calendar component showing the days of the selected month with corresponding color codes:
    - Completed: Vibrant Green.
    - Missed: Muted Red/Gray.
    - Skipped: Orange/Yellow.
    - Non-scheduled: Dashed/grayed-out background.
    - Pre-creation / Future: Blank/neutral gray.
  - Month navigation (Left/Right buttons).

---

## Decisions

### Decision 1: Scheduled Day Continuity Calculation
- **Choice**: Instead of strictly comparing `last_incremented == yesterday`, the system will search backward for the *most recent scheduled day* prior to the log date. If the last log/increment matches that day (or a skip was logged on it), the streak continues. Otherwise, it resets.
- **Rationale**: Solves the non-daily habit streak bug correctly.

### Decision 2: 14-day Deactivation Cap
- **Choice**: Store the deactivation timestamp on the Habit model or calculate the deactivated duration dynamically from the logs. Since we want to know when a habit was deactivated, we can add a `deactivated_at` column (DateTime) to the `Habit` model. When `is_active` is set to False, we populate `deactivated_at`. On reactivation, if `now - deactivated_at > 14 days`, we reset the streak to 0.
- **Rationale**: Minimal schema changes and accurate time tracking.

### Decision 3: Single Reward Granting per Milestone
- **Choice**: We will check if `current_streak == 30` or `current_streak == 90` exactly at the moment of incrementing. Since the streak can only reach exactly 30 or 90 once per streak lifecycle, we can safely award the reward when `current_streak` equals the milestone value and the streak was incremented today.
- **Rationale**: Clean, event-driven reward trigger without needing a complex reward history table.
