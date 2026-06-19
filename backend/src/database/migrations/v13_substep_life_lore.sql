-- v13_substep_life_lore.sql
-- Ajoute la colonne is_life_lore aux sous-objectifs (SubStep) pour identifier les éléments d'histoire de vie.

ALTER TABLE substeps ADD COLUMN is_life_lore BOOLEAN DEFAULT 0;
