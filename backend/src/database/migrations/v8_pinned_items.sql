-- v8_pinned_items.sql
-- Add pinned_substeps and pinned_softskills columns to users table

ALTER TABLE users ADD COLUMN pinned_substeps TEXT DEFAULT '[]';
ALTER TABLE users ADD COLUMN pinned_softskills TEXT DEFAULT '[]';
