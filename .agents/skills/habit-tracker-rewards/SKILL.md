---
name: "habit-tracker-rewards"
description: "Gère la boutique de récompenses (Boutique de Récompenses) de Gabriel's Habit Tracker: création, édition, suppression, vérification des verrous (softskills et objectifs) et exécution d'achats via l'API REST ou par script DB."
compatibility: "Habit Tracker MVP/V2/V3"
metadata:
  purpose: "Administering and interacting with the reward shop system"
---

# Habit Tracker Rewards

This skill covers direct operations on the Reward Shop (Boutique de Récompenses) of Gabriel's Habit Tracker. It provides instructions on how to manage, inspect, or buy rewards via either the REST API or direct database manipulations.

## 🗄️ Database Schema (`rewards`)

The SQLite table `rewards` stores all rewards configured per user.

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER | Primary Key (Autoincrement) |
| `user_id` | INTEGER | Foreign Key to `users.id` (not null) |
| `title` | VARCHAR(100) | Title of the reward (not null) |
| `description` | TEXT | Description/Details (optional) |
| `gold_cost` | INTEGER | Price in Gold (must be >= 0) |
| `category` | VARCHAR(50) | Type of reward (`regular`, `allostasis_daily`, `allostasis_weekly`) (default 'regular') |
| `required_softskill_id` | VARCHAR(100) | Optional softskill ID prerequisite |
| `required_goal_id` | INTEGER | Optional goal ID prerequisite (`goals.id`) |
| `is_one_time` | BOOLEAN | If True, can only be purchased once (default False) |
| `purchased_count` | INTEGER | Total successful purchases (default 0) |
| `last_purchased_at` | DATETIME | Timestamp of the last purchase or allostasis redemption (nullable) |
| `created_at` | TIMESTAMP | Creation date/time |

### Prerequisites & Cascades
- If a goal is deleted, the database sets `required_goal_id` to `NULL` (via `ON DELETE SET NULL`), unlocking the reward.
- If a user is deleted, all their rewards are deleted (via `ON DELETE CASCADE`).

---

## 📡 REST API Contract

All paths require the `X-User-ID` header containing the user's database ID (e.g. `1` for Gabriel).

### 1. List Rewards
- **Endpoint**: `GET /api/v1/rewards`
- **Output**: JSON list of rewards. In addition to the database columns, each item contains:
  - `unlocked`: `True` if all prerequisites are completed, `False` otherwise.
  - `lock_reason`: A string explanation if locked, or `null` if unlocked.

### 2. Create Reward
- **Endpoint**: `POST /api/v1/rewards`
- **Payload**:
  ```json
  {
    "title": "Acheter un livre",
    "description": "Un livre technique ou de fiction",
    "gold_cost": 50,
    "required_softskill_id": "lecture",
    "required_goal_id": 2,
    "is_one_time": false
  }
  ```
- **Response**: `201 Created` with `{"status": "success", "reward": {...}}`.

### 3. Update Reward
- **Endpoint**: `PUT /api/v1/rewards/{reward_id}`
- **Payload**: Full reward schema matching the creation payload.
- **Response**: `200 OK` with updated reward details.

### 4. Delete Reward
- **Endpoint**: `DELETE /api/v1/rewards/{reward_id}`
- **Response**: `200 OK` with `{"status": "success"}`.

### 5. Purchase Reward
- **Endpoint**: `POST /api/v1/rewards/{reward_id}/purchase`
- **Behavior**: Atomically verifies:
  1. If user balance `gold` >= `gold_cost` of the reward.
  2. If the reward is unlocked (prerequisites met).
  3. If the reward is a one-time reward and has not been purchased yet.
  Deducts `gold_cost` from user, increments `purchased_count`, and commits the transaction.
- **Response**:
  ```json
  {
    "status": "success",
    "gold_spent": 50,
    "new_gold": 120,
    "purchased_count": 1
  }
  ```

---

## 🤖 Bot Telegram Commands

Users can interact with the shop via Telegram using these commands:

- `/shop` : List all rewards grouped by section (Allostasie Daily, Allostasie Weekly, Récompenses Classiques) with prices, lock badges, and allostasis status (`[✓ Validé]` or `[🔄 A valider]`).
- `/shop dispos` : Filter list to only show available (unlocked & unowned/unredeemed) rewards.
- `/shop verrouillees` : Filter list to only show locked rewards.
- `/buy [nom_recompense]` : Attempts to buy/redeem the reward matching the name. For allostasis items, this is free and sets the completion badge.

---

## 💡 Common Operations Guidelines

### direct Database Insert (python script)
```python
from src.database.session import SessionLocal
from src.database.models import Reward

db = SessionLocal()
try:
    new_reward = Reward(
        user_id=1,
        title="Regarder un film",
        description="Une soirée cinéma de détente",
        gold_cost=40,
        required_softskill_id=None,
        required_goal_id=None,
        is_one_time=False
    )
    db.add(new_reward)
    db.commit()
finally:
    db.close()
```

### Direct Purchase Script
To bypass API validation or run offline maintenance, use the service transaction:
```python
from src.database.session import SessionLocal
from src.services.reward_service import purchase_reward

db = SessionLocal()
try:
    res = purchase_reward(db, user_id=1, reward_id=3)
    print(f"Purchase OK! New gold balance: {res['new_gold']}")
except Exception as e:
    print(f"Purchase failed: {e}")
finally:
    db.close()
```
