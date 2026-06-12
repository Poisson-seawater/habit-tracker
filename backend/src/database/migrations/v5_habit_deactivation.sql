-- Migration: Add deactivated_at and created_at to habits table
-- Target: SQLite DB (habit_tracker.db)
ALTER TABLE habits ADD COLUMN deactivated_at DATETIME;
ALTER TABLE habits ADD COLUMN created_at DATETIME;
UPDATE habits SET created_at = datetime('now') WHERE created_at IS NULL;
