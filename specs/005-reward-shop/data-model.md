# Data Model: Reward Shop (Boutique de Récompenses)

This document specifies the database schema and model mappings for the rewards table.

## Entity: Reward

Represents a reward purchasable with gold in a user's shop.

### SQLite Schema (`rewards`)

```sql
CREATE TABLE IF NOT EXISTS rewards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    gold_cost INTEGER NOT NULL DEFAULT 0,
    required_softskill_id VARCHAR(100),
    required_goal_id INTEGER,
    is_one_time BOOLEAN DEFAULT 0,
    purchased_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(required_goal_id) REFERENCES goals(id) ON DELETE SET NULL
);
```

### Attributes

| Field Name | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | Primary Key, Auto-increment | Unique identifier. |
| `user_id` | Integer | Foreign Key -> `users.id` (Cascade) | The user who owns this reward. |
| `title` | String | Not Null | Title of the reward. |
| `description` | Text | Nullable | Detail/description of the reward. |
| `gold_cost` | Integer | Not Null, Default 0, >= 0 | Cost in gold to buy. |
| `required_softskill_id` | String(100) | Nullable | ID of the softskill required to unlock (from JSON tree). |
| `required_goal_id` | Integer | Nullable, FK -> `goals.id` (Set Null) | ID of the goal required to unlock. |
| `is_one_time` | Boolean | Default False (0) | If True, can only be purchased once. |
| `purchased_count` | Integer | Default 0, >= 0 | Number of times this user purchased this reward. |
| `created_at` | DateTime | Default CURRENT_TIMESTAMP | Date and time of creation. |

### Relationships

- **User**: One-to-Many. An user has many rewards. A reward belongs to one user.
- **Goal**: Many-to-One. A reward optionally references a goal requirement. If the goal is deleted, the reference is set to null (unlocked).
- **Softskill**: Loose relationship. References a `softskill_id` defined in `softskills_tree.json`. Checked dynamically.

### Validation Rules

1. `gold_cost` must be greater than or equal to 0.
2. `title` must be a non-empty string.
3. `is_one_time` boolean.
4. If a purchase is made:
   - User's `gold` balance must be >= reward's `gold_cost`.
   - If `is_one_time` is True, `purchased_count` must be 0 before purchase.
   - If `required_softskill_id` is set, `UserSoftskillProgress` for that user and skill ID must have `completed=True`.
   - If `required_goal_id` is set, the referenced `Goal` must have `completed=True`.
