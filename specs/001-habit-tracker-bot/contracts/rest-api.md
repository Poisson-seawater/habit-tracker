# REST API Endpoint Contracts: habit-tracker-bot

This document defines the REST API routes decoupling the data store from the local web dashboard interface.
All requests and responses use strict JSON format.

---

### 1. `GET /api/v1/profile`
Fetch current stats, level, active daily template, and daily threshold progress.

- **Request**: `GET /api/v1/profile`
- **Response**: `200 OK`
  ```json
  {
    "username": "Gabriel",
    "active_template": "Semaine",
    "scores": {
      "status": "Acceptable",
      "acceptable_day_validated": true,
      "perfect_day_validated": false
    },
    "stats": {
      "force": 12,
      "endurance": 8,
      "discipline": 6,
      "creativite": 5,
      "repos": 0
    },
    "thresholds": {
      "acceptable": {
        "discipline": 5,
        "force": 10
      },
      "perfect": {
        "discipline": 8,
        "force": 20
      }
    }
  }
  ```

---

### 2. `GET /api/v1/habits`
List all configured habits for the user.

- **Request**: `GET /api/v1/habits`
- **Response**: `200 OK`
  ```json
  [
    {
      "id": 1,
      "name": "routine_matin",
      "type": "binary",
      "is_private": false,
      "is_reportable": false,
      "is_mandatory": true,
      "point_rewards": {
        "discipline": 2,
        "organisation": 1
      },
      "daily_cap": null,
      "is_active": true
    },
    {
      "id": 2,
      "name": "lecture",
      "type": "quantitative",
      "unit": "min",
      "is_private": false,
      "is_reportable": false,
      "is_mandatory": false,
      "point_rewards": {
        "creativite": 5,
        "discipline": 2
      },
      "daily_cap": 5,
      "is_active": true
    }
  ]
  ```

---

### 3. `POST /api/v1/habits`
Create a new habit configuration.

- **Request**: `POST /api/v1/habits`
  ```json
  {
    "name": "ukulele",
    "type": "binary",
    "is_private": false,
    "is_reportable": false,
    "is_mandatory": false,
    "point_rewards": {
      "creativite": 5,
      "discipline": 2
    }
  }
  ```
- **Response**: `201 Created`
  ```json
  {
    "id": 3,
    "name": "ukulele",
    "status": "success"
  }
  ```

---

### 4. `GET /api/v1/streaks`
Retrieve all running and historical streaks.

- **Request**: `GET /api/v1/streaks`
- **Response**: `200 OK`
  ```json
  [
    {
      "streak_type": "Acceptable",
      "current_streak": 5,
      "max_streak": 22,
      "last_incremented": "2026-05-30"
    },
    {
      "streak_type": "Perfect",
      "current_streak": 0,
      "max_streak": 7,
      "last_incremented": "2026-05-28"
    }
  ]
  ```

---

### 5. `POST /api/v1/logs`
Submit a habit check-in directly from the dashboard.

- **Request**: `POST /api/v1/logs`
  ```json
  {
    "habit_id": 1,
    "log_type": "done",
    "amount": null,
    "reason": null
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "log_id": 412,
    "status": "logged",
    "affected_stats": {
      "discipline": 2,
      "organisation": 1
    }
  }
  ```
