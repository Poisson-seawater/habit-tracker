-- Migration v3: Add substep details for ordered graph rendering

ALTER TABLE substeps ADD COLUMN description TEXT;
ALTER TABLE substeps ADD COLUMN execution_order INTEGER DEFAULT 1;
