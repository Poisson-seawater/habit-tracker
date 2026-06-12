# Research Notes: Allostasis Rewards

## Schema & Data Model Decisions

### Adding Columns to Rewards Table
- **Decision**: Add `category` (String, default `"regular"`) and `last_purchased_at` (DateTime, nullable) directly to the `rewards` table.
- **Rationale**: Reusing the existing `rewards` table is simpler and has less database/model overhead than creating a brand-new `allostasis_logs` or `allostasis_items` table. Since allostasis items are functionally similar to rewards (user-defined, descriptive, repeatable), categorizing them makes clean design sense.
- **Alternatives Considered**: 
  - Creating a separate `allostasis_rewards` table. Rejected because it would duplicate fields like `user_id`, `title`, and `description`, leading to redundant CRUD endpoints.

## Reset & Availability Design

### Reset Logic Calculations
- **Decision**: Validate availability dynamically during checks and purchase actions:
  - For `allostasis_daily`: Item is available if `last_purchased_at` is null or its calendar day is before the user's current local date.
  - For `allostasis_weekly`: Item is available if `last_purchased_at` is null or its ISO week start date is before the current week's Monday.
- **Rationale**: Avoiding a cron job to reset states reduces database writes and keeps the system lightweight. Dynamic checks based on the `last_purchased_at` timestamp are highly performant.

## Daily Recap Integration

### Querying Purchased Items
- **Decision**: In `publish_daily_recap()`, query the `rewards` table for allostasis items purchased on the current date, then format and group them in the Telegram message.
- **Rationale**: Keeps the logic centralized within the scheduler service and reuses the database session.
