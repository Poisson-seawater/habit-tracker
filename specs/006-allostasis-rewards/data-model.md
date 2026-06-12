# Data Model & Validation: Allostasis Rewards

## Entities

### Reward (Modified)

| Field | Type | Description | Constraints |
|---|---|---|---|
| `id` | Integer (PK) | Unique identifier | Auto-increment |
| `user_id` | Integer (FK) | Owner of the reward | References `users.id` |
| `title` | String(255) | Name of the reward/activity | Not Null |
| `description` | Text | Explanation of the item | Nullable |
| `gold_cost` | Integer | Cost in gold | >= 0 (Forced to 0 if allostasis) |
| `category` | String(50) | Category type | One of: `regular`, `allostasis_daily`, `allostasis_weekly` (Default: `regular`) |
| `last_purchased_at`| DateTime | Timestamp of last purchase | Nullable |

## Validation Rules

### Capping Limit
- A user can have at most **3** items of category `allostasis_daily` where the reward is active (created/not deleted).
- A user can have at most **3** items of category `allostasis_weekly` where the reward is active.
- Attempting to create or update an item to exceed these limits must return a `400 Bad Request` or raise an API validation error.

### Cost Enforcement
- Any reward with category `allostasis_daily` or `allostasis_weekly` must have `gold_cost` set/validated to `0`.

## State Transitions & Reset Logic

### Redeeming/Purchasing
- When an allostasis reward is purchased/checked off:
  - Gold is **not** deducted.
  - `purchased_count` is incremented by 1.
  - `last_purchased_at` is set to the current UTC timestamp (e.g. `datetime.utcnow()`).

### Availability State
- **Available**:
  - For `allostasis_daily`: `last_purchased_at` is `null` OR the day of `last_purchased_at` is strictly before the current local day of the user.
  - For `allostasis_weekly`: `last_purchased_at` is `null` OR the Monday of the week of `last_purchased_at` is strictly before the Monday of the current local week.
- **Redeemed / Unavailable**:
  - Otherwise, the item shows as already checked off / redeemed and cannot be purchased again until the reset period is crossed.
