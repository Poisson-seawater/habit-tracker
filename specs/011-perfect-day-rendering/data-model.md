# Data Model: Perfect Day Rendering

**Feature**: 011-perfect-day-rendering | **Date**: 2026-06-28

## New Entity: BiologicalZone

**Table name**: `biological_zones`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PK, auto-increment | Unique identifier |
| `user_id` | INTEGER | FK → users.id, ON DELETE CASCADE, NOT NULL | Owner of the zone |
| `zone_name` | VARCHAR | NOT NULL | User-facing label (e.g., "Focus Profond Matin") |
| `zone_type` | VARCHAR | NOT NULL | Category enum: `deep_focus`, `physical_peak`, `creative`, `rest`, `social`, `sleep` |
| `start_time` | VARCHAR | NOT NULL | "HH:MM" format (e.g., "08:00") |
| `end_time` | VARCHAR | NOT NULL | "HH:MM" format (e.g., "12:00") |
| `color` | VARCHAR | NULLABLE | Optional hex color override (e.g., "#8b5cf6") |
| `display_order` | INTEGER | DEFAULT 0 | Rendering order (lower = first) |

### Validation Rules

- `zone_type` must be one of: `deep_focus`, `physical_peak`, `creative`, `rest`, `social`, `sleep`.
- `start_time` and `end_time` must be valid "HH:MM" strings (00:00–23:59).
- No two zones for the same `user_id` may overlap in time (accounting for midnight wrapping).
- `start_time` may be greater than `end_time` for overnight zones (e.g., Sleep 23:00–07:00).

### Relationships

- `BiologicalZone.user_id` → `User.id` (many-to-one)
- `User.biological_zones` (one-to-many, cascade delete)

### Indexes

- Primary key on `id`
- Index on `user_id` for filtering

## Modified Entity: User

Add relationship only (no new columns):

```
biological_zones = relationship("BiologicalZone", back_populates="user", cascade="all, delete-orphan")
```

## Existing Entities (Read-Only by this feature)

### PerfectDayTemplate

Used to populate the left recap panel via `agenda_json` field. No modifications needed.

### Habit / SubStep

`effort_type` and `effort_duration` fields are read by the budget gauge panel. No modifications needed.

## Migration Strategy

Migration v18 in `_run_migrations()`:
1. Check if `biological_zones` table exists via `inspector.get_table_names()`.
2. If not, create it using `CREATE TABLE IF NOT EXISTS` with all columns.
3. Seed default biological zones for all existing users if table is empty.
