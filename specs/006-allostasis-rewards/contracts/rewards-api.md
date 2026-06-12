# API Contract: Rewards & Allostasis

Endpoints for managing and purchasing rewards, extended to support Allostasis categories.

## 1. Get Rewards List
Retrieve all configured rewards for the user, including their current lock status, availability, and category details.

- **Method**: `GET`
- **Path**: `/api/v1/rewards`
- **Headers**:
  - `X-User-ID`: `1` (User ID string)
- **Response** (`200 OK`):
  ```json
  [
    {
      "id": 1,
      "title": "25 min TV Show",
      "description": "Watch an episode of your favorite show",
      "gold_cost": 0,
      "category": "allostasis_daily",
      "is_one_time": false,
      "purchased_count": 5,
      "last_purchased_at": "2026-06-12T14:20:00Z",
      "unlocked": true,
      "lock_reason": null,
      "is_available": false
    },
    {
      "id": 2,
      "title": "Acheter un jeu",
      "description": "Acheter un nouveau jeu vidéo",
      "gold_cost": 150,
      "category": "regular",
      "is_one_time": true,
      "purchased_count": 0,
      "last_purchased_at": null,
      "unlocked": false,
      "lock_reason": "Nécessite le softskill 'Discipline'",
      "is_available": false
    }
  ]
  ```

---

## 2. Create Reward
Create a new reward item. Enforces limits and category restrictions.

- **Method**: `POST`
- **Path**: `/api/v1/rewards`
- **Headers**:
  - `X-User-ID`: `1`
  - `Content-Type`: `application/json`
- **Request Body**:
  ```json
  {
    "title": "Prendre une bière le soir",
    "description": "Moment de détente le week-end",
    "gold_cost": 0,
    "category": "allostasis_weekly",
    "is_one_time": false,
    "required_softskill_id": null,
    "required_goal_id": null
  }
  ```
- **Response** (`201 Created`):
  ```json
  {
    "id": 3,
    "title": "Prendre une bière le soir",
    "description": "Moment de détente le week-end",
    "gold_cost": 0,
    "category": "allostasis_weekly",
    "is_one_time": false,
    "required_softskill_id": null,
    "required_goal_id": null,
    "purchased_count": 0,
    "last_purchased_at": null
  }
  ```
- **Errors**:
  - `400 Bad Request` (Category limit exceeded or non-zero cost specified for allostasis):
    ```json
    {
      "detail": "Limite de 3 items pour la catégorie allostasis_weekly atteinte."
    }
    ```

---

## 3. Purchase / Redeem Reward
Purchase a standard reward or check off an allostasis item.

- **Method**: `POST`
- **Path**: `/api/v1/rewards/{reward_id}/purchase`
- **Headers**:
  - `X-User-ID`: `1`
- **Response** (`200 OK`):
  ```json
  {
    "reward_id": 3,
    "purchased_count": 1,
    "gold_spent": 0,
    "last_purchased_at": "2026-06-12T17:29:47Z"
  }
  ```
- **Errors**:
  - `400 Bad Request` (Allostasis item already redeemed today or this week):
    ```json
    {
      "detail": "Cet item d'allostasie a déjà été validé pour cette période."
    }
    ```
