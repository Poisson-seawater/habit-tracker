# Data Model: 3-3-3 Recap Dashboard Panel

## Model Changes

### User model (`backend/src/database/models.py`)
- New columns:
  - `pinned_substeps` : `JSON` / `TEXT` representation of a list of integers (e.g. `[1, 3, 5]`) storing pinned sub-step IDs.
  - `pinned_softskills` : `JSON` / `TEXT` representation of a list of strings (e.g. `["ecoute", "focus"]`) storing pinned softskill keys.

## API Contracts

### Update Pinned Items
- **Endpoint**: `PUT /api/v1/profile/pins`
- **Request Headers**: `X-User-ID` (optional, falls back to Gabriel = 1)
- **Request Body**:
  ```json
  {
    "pinned_substeps": [1, 2, 3],
    "pinned_softskills": ["focus", "lecture", "sommeil"]
  }
  ```
- **Response**:
  ```json
  {
    "status": "success",
    "message": "Pins updated successfully"
  }
  ```

### Fetch Profile
- **Endpoint**: `GET /api/v1/profile`
- **Response Extension**:
  ```json
  {
    "username": "Gabriel",
    "active_template": "week",
    "xp": 120,
    "level": 3,
    "gold": 500,
    "stats": {},
    "thresholds": {},
    "completed_habit_ids": [],
    "scores": {},
    "pinned_substeps": [1, 2, 3],
    "pinned_softskills": ["focus", "lecture", "sommeil"]
  }
  ```
