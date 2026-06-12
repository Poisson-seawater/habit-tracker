# Research and Decisions: Reward Shop (Boutique de Récompenses)

This document records the design decisions and technical choices made for the Reward Shop feature.

## 1. Database Modeling & Constraints Linking

- **Decision**: Store requirements directly in the `rewards` table using two nullable fields: `required_softskill_id` (VARCHAR(100), referencing the static softskill identifier) and `required_goal_id` (INTEGER, referencing `goals.id`).
- **Rationale**: Since a reward in this lightweight application will only have at most one softskill or one goal prerequisite, storing these directly in the row is the simplest, most performant, and easiest to query.
- **Alternatives Considered**: 
  - **Prerequisite Map/Link Tables**: Rejected because it adds database complexity and queries without providing any current benefit.
  - **JSON string constraint**: Storing requirements as a JSON string. Rejected because it makes database integrity checks (like foreign key cascading when a goal is deleted) impossible.

## 2. Gold Balance Safety & Transaction Integrity

- **Decision**: Perform the purchase operation within a single database transaction. We lock/read the User row, check that `user.gold >= reward.gold_cost`, verify requirements are met, deduct the gold, increment `reward.purchased_count`, and commit.
- **Rationale**: Ensures no gold double-spending can occur (e.g. via rapid API calls or bot spam).
- **Alternatives Considered**:
  - **Client-Side checks only**: Rejected as it allows bypass via direct REST calls or bot commands.

## 3. UI Tab Integration

- **Decision**: Add a new dedicated "Boutique" tab to the dashboard.
- **Rationale**: This fits perfectly into the existing tabbed navigation system in the HTML and `app.js` and provides a clean, premium dashboard layout to browse rewards.
- **Alternatives Considered**:
  - **Modal overlay on the main dashboard**: Rejected because a dedicated tab allows more room to present rewards, filters, and lock conditions elegantly.

## 4. Clean Cascade on Goal/Skill Deletion

- **Decision**: Set the foreign key constraint for `required_goal_id` to `ON DELETE SET NULL`. If a goal is deleted, any reward requiring it will automatically have its requirement cleared and become unlocked. For softskills, since they are defined in JSON, if a skill is deleted from the JSON, the service layer will automatically treat any reference to it as satisfied/cleared during the lock status evaluation.
- **Rationale**: Prevents orphaned requirement locks where a reward can never be purchased because its prerequisite no longer exists.
- **Alternatives Considered**:
  - **Cascade Delete the reward**: Rejected, as deleting a goal should not delete the reward itself, just remove the restriction.
