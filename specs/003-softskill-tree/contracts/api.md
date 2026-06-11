# API Contracts: Softskill Progress Tree

All API endpoints are prefixed with `/api/v1` and require the `X-User-ID` header.

## 1. Get Softskill Tree & Progress
Retrieves the static tree layout combined with the current user's progress.

- **URL**: `/softskills`
- **Method**: `GET`
- **Headers**:
  - `X-User-ID`: `[user_id]` (Required)
- **Response**: `200 OK`
  - **Body**:
    ```json
    {
      "branches": {
        "communication": {
          "color": "#e74c3c",
          "pale_color": "#fadbd8"
        }
      },
      "skills": [
        {
          "id": "ecoute",
          "name": "Écoute Active",
          "description": "Capacité à écouter attentivement sans interrompre.",
          "branch": "communication",
          "prerequisites": [],
          "related": ["vente"],
          "x": 200,
          "y": 100,
          "progress": {
            "success_criteria_test": "Talk to 10 strangers without feeling burned out",
            "current_level": 50,
            "completed": false,
            "updated_at": "2026-06-11T12:00:00"
          }
        }
      ]
    }
    ```

---

## 2. Update Success Criteria Test
Saves or edits the user's custom test sentence for a skill.

- **URL**: `/softskills/{softskill_id}/test`
- **Method**: `POST`
- **Headers**:
  - `X-User-ID`: `[user_id]` (Required)
  - `Content-Type`: `application/json`
- **Request Body**:
  ```json
  {
    "success_criteria_test": "Talk to 10 strangers without feeling burned out"
  }
  ```
- **Response**: `200 OK`
  - **Body**:
    ```json
    {
      "status": "success",
      "message": "Success criteria test updated",
      "data": {
        "softskill_id": "ecoute",
        "success_criteria_test": "Talk to 10 strangers without feeling burned out"
      }
    }
    ```

---

## 3. Toggle Softskill Completion
Manually updates progress or completes a softskill.

- **URL**: `/softskills/{softskill_id}/complete`
- **Method**: `POST`
- **Headers**:
  - `X-User-ID`: `[user_id]` (Required)
  - `Content-Type`: `application/json`
- **Request Body**:
  ```json
  {
    "completed": true
  }
  ```
- **Response**:
  - **Success (`200 OK`)**:
    ```json
    {
      "status": "success",
      "message": "Softskill marked as completed",
      "data": {
        "softskill_id": "ecoute",
        "completed": true,
        "current_level": 100
      }
    }
    ```
  - **Failure (`400 Bad Request`)** - Prerequisites not met:
    ```json
    {
      "status": "error",
      "message": "Cannot unlock 'vente': Prerequisite 'ecoute' is not completed."
    }
    ```
