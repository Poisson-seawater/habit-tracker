-- v11_habit_daily_target.sql
-- Ajoute la cible de répétitions/jour aux habitudes (affichage "X/N" dans le recap).
-- NULL = comportement actuel (1 validation/jour, pas d'affichage de cible).

ALTER TABLE habits ADD COLUMN daily_target INTEGER;
