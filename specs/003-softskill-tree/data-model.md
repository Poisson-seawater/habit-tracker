# Data Model: Softskill Progress Tree

This document describes the data structure and validation rules for the Softskill Progress Tree feature.

## 1. Database Model: `UserSoftskillProgress`

Stores user progress and custom success criteria for each softskill.

| Field Name | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | Integer | Primary Key, Auto-increment | Unique identifier for the progress log. |
| `user_id` | Integer | ForeignKey(`users.id`), Not Null | The user to whom this progress belongs. |
| `softskill_id` | String | Not Null, Unique with `user_id` | The string ID of the skill matching the JSON config. |
| `success_criteria_test` | Text | Nullable | User's custom test sentence for completing this skill. |
| `current_level` | Integer | Default: 0 | Current progress level of the skill (e.g. 0 to 100%). |
| `completed` | Boolean | Default: False | True if the user manually marked the success test as completed. |
| `updated_at` | DateTime | Default: CURRENT_TIMESTAMP | Timestamp of the last update. |

### Database Relations
- `User` (1) ─── (N) `UserSoftskillProgress`

---

## 2. Validation & Business Rules

1. **Prerequisite Check**:
   - A softskill CANNOT be marked as `completed` if any of its prerequisites (defined in `softskills_tree.json`) are not marked as `completed` for the user.
2. **Cyclic Dependency Gate**:
   - On server startup, the backend service MUST parse `softskills_tree.json` and validate that there are no loops in prerequisites (e.g., A -> B -> A). If a loop is found, the server must log a critical warning or raise an error.
3. **User Isolation**:
   - All CRUD actions on `UserSoftskillProgress` MUST query by the current user ID retrieved from the `X-User-ID` header.
