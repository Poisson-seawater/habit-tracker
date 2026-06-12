# REST API Contract: Reward Shop (Boutique de Récompenses)

All endpoints require the `X-User-ID` header to isolate data per user.

## Base Path: `/api/v1/rewards`

### 1. Get Rewards List
*   **Method**: `GET`
*   **Path**: `/api/v1/rewards`
*   **Headers**:
    *   `X-User-ID`: `1` (required)
*   **Response**: `200 OK`
    *   **Body**:
        ```json
        [
          {
            "id": 1,
            "title": "Acheter un jeu vidéo",
            "description": "Se faire plaisir avec le nouveau Zelda",
            "gold_cost": 150,
            "required_softskill_id": "discipline_l1",
            "required_goal_id": 2,
            "is_one_time": true,
            "purchased_count": 0,
            "unlocked": true,
            "lock_reason": null
          },
          {
            "id": 2,
            "title": "Une soirée resto luxe",
            "description": "Manger avec des amis",
            "gold_cost": 300,
            "required_softskill_id": "sociabilite_l2",
            "required_goal_id": null,
            "is_one_time": false,
            "purchased_count": 2,
            "unlocked": false,
            "lock_reason": "Nécessite la softskill 'sociabilite_l2' complétée."
          }
        ]
        ```

### 2. Create Reward
*   **Method**: `POST`
*   **Path**: `/api/v1/rewards`
*   **Headers**:
    *   `X-User-ID`: `1` (required)
    *   `Content-Type`: `application/json`
*   **Request Body**:
    ```json
    {
      "title": "Acheter un jeu vidéo",
      "description": "Se faire plaisir avec le nouveau Zelda",
      "gold_cost": 150,
      "required_softskill_id": "discipline_l1",
      "required_goal_id": 2,
      "is_one_time": true
    }
    ```
*   **Response**: `201 Created`
    *   **Body**:
        ```json
        {
          "status": "success",
          "reward": {
            "id": 1,
            "title": "Acheter un jeu vidéo",
            "description": "Se faire plaisir avec le nouveau Zelda",
            "gold_cost": 150,
            "required_softskill_id": "discipline_l1",
            "required_goal_id": 2,
            "is_one_time": true,
            "purchased_count": 0
          }
        }
        ```

### 3. Update Reward
*   **Method**: `PUT`
*   **Path**: `/api/v1/rewards/{reward_id}`
*   **Headers**:
    *   `X-User-ID`: `1` (required)
    *   `Content-Type`: `application/json`
*   **Request Body**:
    ```json
    {
      "title": "Acheter un jeu vidéo (Édition Deluxe)",
      "description": "Se faire plaisir avec le nouveau Zelda deluxe",
      "gold_cost": 200,
      "required_softskill_id": null,
      "required_goal_id": null,
      "is_one_time": true
    }
    ```
*   **Response**: `200 OK`
    *   **Body**:
        ```json
        {
          "status": "success",
          "reward": {
            "id": 1,
            "title": "Acheter un jeu vidéo (Édition Deluxe)",
            "description": "Se faire plaisir avec le nouveau Zelda deluxe",
            "gold_cost": 200,
            "required_softskill_id": null,
            "required_goal_id": null,
            "is_one_time": true,
            "purchased_count": 0
          }
        }
        ```

### 4. Delete Reward
*   **Method**: `DELETE`
*   **Path**: `/api/v1/rewards/{reward_id}`
*   **Headers**:
    *   `X-User-ID`: `1` (required)
*   **Response**: `200 OK`
    *   **Body**:
        ```json
        {
          "status": "success",
          "message": "Reward deleted successfully"
        }
        ```

### 5. Purchase Reward
*   **Method**: `POST`
*   **Path**: `/api/v1/rewards/{reward_id}/purchase`
*   **Headers**:
    *   `X-User-ID`: `1` (required)
*   **Response**: `200 OK`
    *   **Body**:
        ```json
        {
          "status": "success",
          "gold_spent": 150,
          "new_gold": 450,
          "purchased_count": 1
        }
        ```
*   **Error Responses**:
    *   `400 Bad Request`: "Gold insuffisant" (If user.gold < reward.gold_cost)
    *   `400 Bad Request`: "Récompense unique déjà achetée" (If is_one_time is True and purchased_count > 0)
    *   `400 Bad Request`: "La récompense est verrouillée" (If requirements not met)
    *   `404 Not Found`: "Récompense introuvable" (If reward doesn't exist or belongs to another user)
