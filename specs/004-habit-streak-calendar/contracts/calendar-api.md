# API Contract: Habit Calendar & Detail

## 1. Get Habit Calendar Logs
Retrieve completion logs, scheduling details, and streak counts for a specific habit in a given month.

* **URL**: `/api/v1/habits/{habit_id}/calendar`
* **Method**: `GET`
* **Headers**:
  * `X-User-ID`: `integer` (User ID, e.g., `1` for Gabriel)
* **Query Parameters**:
  * `year`: `integer` (optional, defaults to current year)
  * `month`: `integer` (optional, 1-12, defaults to current month)

### Response (Success 200 OK)
```json
{
  "habit_id": 1,
  "habit_name": "routine_matin",
  "year": 2026,
  "month": 6,
  "current_streak": 14,
  "max_streak": 30,
  "deactivated_at": null,
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

### Possible Day States:
* `completed`: The habit was successfully logged as `done` or `log` on that day.
* `missed`: The habit was scheduled but neither completed nor skipped (and the day has passed).
* `skipped`: The habit was explicitly marked as skipped (preserves streak).
* `non-scheduled`: The day is not in the habit's scheduled days.
* `future`: The day is in the future.
* `pre-creation`: The day is before the habit was created.

---

## 2. Update Habit Activation State
Reactivate or deactivate a habit. If deactivating, sets `deactivated_at`. If reactivating, checks if `deactivated_at` was >14 days ago and resets streak to 0 if so.

* **URL**: `/api/v1/habits/{habit_id}`
* **Method**: `PUT`
* **Headers**:
  * `X-User-ID`: `integer`
* **Payload (JSON)**:
  * Supports all fields in the existing `HabitUpdate` schema, plus `is_active` (boolean, optional).

### Request Payload Example:
```json
{
  "is_active": true
}
```

### Response (Success 200 OK)
```json
{
  "status": "updated",
  "habit_id": 1,
  "is_active": true,
  "streak_reset": false
}
```
