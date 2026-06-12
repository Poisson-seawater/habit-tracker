# Quickstart: Habit Streak & Calendar

This guide provides steps to test the habit streak counter, milestone rewards, and calendar visualization feature.

## Backend Verification

### 1. Apply Database Migration
Ensure the database schema is updated to include the new columns:
```bash
# In SQLite CLI or your DB tool
sqlite3 backend/data/habit_tracker.db < backend/src/database/migrations/v5_habit_deactivation.sql
```

### 2. Run API Endpoints
You can verify the calendar API using curl:
```bash
# Get Gabriel's calendar logs for a habit (e.g. habit ID 1) in June 2026
curl -H "X-User-ID: 1" "http://localhost:5000/api/v1/habits/1/calendar?year=2026&month=6"
```

---

## Frontend Verification

### 1. Habit Detail Modal
1. Start the backend server:
   ```bash
   PYTHONPATH=backend python3 backend/src/main.py
   ```
2. Navigate to the localhost dashboard (`http://localhost:5000`).
3. Click on any habit name in the list.
4. A detail modal will slide open from the side/center displaying:
   - The habit description and stats rewards.
   - Streak counters showing the current streak 🔥 and all-time best streak 🏆.
   - The monthly calendar grid showing colored cells (green, orange, red, hashed gray) representing completion status.
   - A deactivation toggle/button.

### 2. Testing Streak Scenarios
- **Binary Logs**: Mark a daily habit done today and tomorrow. Observe the streak count incrementing to 2.
- **Skip Logs**: Mark a habit as skipped today. Observe the streak count freezing (retains current value) but the last-updated date shifting to today.
- **Non-Scheduled Days**: Check a custom habit (e.g. scheduled Mon/Wed/Fri). Observe that Tuesday is displayed as hachured/gray on the calendar and does not break the streak.
- **Milestone Reward**: When the streak reaches 30, check the user profile via `GET /api/v1/profile` or the dashboard to verify that +100 XP and +50 Gold have been awarded.
