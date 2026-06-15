-- v12: Add per-goal execution_order to GoalSubStepLink
-- This allows a substep to have different ordering in each objective it belongs to.

ALTER TABLE goal_substep_links ADD COLUMN execution_order INTEGER DEFAULT 1;

-- Migrate existing values: copy execution_order from substeps table into each link
UPDATE goal_substep_links
SET execution_order = (
    SELECT execution_order FROM substeps WHERE substeps.id = goal_substep_links.substep_id
);
