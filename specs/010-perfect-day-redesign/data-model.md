# Data Model: Perfect Day Redesign (Effort Budget Allocator)

This document specifies the database schemas, column definitions, and validation rules.

## Modified Entities

### 1. `perfect_day_templates` Table

Stores budget configurations for the three day-types: `rest`, `regular`, and `hustle`.

| Column Name | SQLite Type | SQLAlchemy Type | Constraints / Defaults | Description |
|---|---|---|---|---|
| `id` | INTEGER | Integer | Primary Key | Unique template ID |
| `user_id` | INTEGER | Integer | ForeignKey(users.id), NOT NULL | Owner of the template |
| `template_name` | TEXT | String | NOT NULL | One of: `rest`, `regular`, `hustle` |
| `focus_hours` | REAL | Float | NOT NULL, Default: 6.0 | Target focus duration in hours |
| `min_rest_hours` | REAL | Float | NOT NULL, Default: 8.0 | Minimum rest duration in hours |
| `ceilings_json` | TEXT | JSON | Nullable | JSON dictionary of limits: e.g., `{"musculaire": 2.0, "cerveau": 2.0, "emotionnel_social": 2.0, "creatif_divergent": 2.0, "total": 10.0}` |
| `thresholds_json`| TEXT | JSON | Nullable | Deprecated RPG stats json (retained for backward compatibility) |

---

### 2. `habits` Table (Quests)

Modified to store the associated effort type and duration.

| Column Name | SQLite Type | SQLAlchemy Type | Constraints / Defaults | Description |
|---|---|---|---|---|
| `effort_type` | TEXT | String | Nullable | One of: `musculaire`, `cerveau`, `emotionnel_social`, `creatif_divergent` or `NULL` |
| `effort_duration` | REAL | Float | NOT NULL, Default: 1.0 | Duration in hours (e.g., 0.5, 2.0) |

---

### 3. `substeps` Table (Sub-steps)

Modified to store the associated effort type and duration.

| Column Name | SQLite Type | SQLAlchemy Type | Constraints / Defaults | Description |
|---|---|---|---|---|
| `effort_type` | TEXT | String | Nullable | One of: `musculaire`, `cerveau`, `emotionnel_social`, `creatif_divergent` or `NULL` |
| `effort_duration` | REAL | Float | NOT NULL, Default: 1.0 | Duration in hours (e.g., 0.5, 2.0) |

---

## Validation & Business Logic

### Effort Tag Ceiling Checks
When a user evaluates a day or previews the daily budget gauge on the dashboard:
1. **Planned Activities**:
   - Get all active habits scheduled for `date` (based on day of week).
   - Get all sub-steps scheduled/todo for `date`.
2. **Calculate Sums**:
   - Sum the `effort_duration` grouped by `effort_type`.
   - Sum total planned hours: $H_{\text{total}} = \sum \text{effort\_duration}$ for all planned items with any effort type.
3. **Template Comparison**:
   - Fetch active day-type template for the user (defaulting to `regular` if none selected).
   - Check ceilings:
     - For each `effort_type` $T$, if $\sum \text{duration}(T) > \text{ceiling}(T)$, trigger a ceiling warning.
     - Default ceilings:
       - `regular`: max 2 hours per type.
       - `hustle`: max 4 hours per type.
       - `rest`: max 1 hour per type.
     - If $H_{\text{total}} > \text{total\_ceiling}$ (default 10h), trigger total warning.
4. **Hustle Day Validation**:
   - If the active template is `hustle`:
     - $\text{unplanned time} = 16.0 - H_{\text{total}}$.
     - If $\text{unplanned time} < 4.8 \text{ hours}$ (which is 30% of 16h waking day), mark the day as **Failed/Invalid** and display a warning.
