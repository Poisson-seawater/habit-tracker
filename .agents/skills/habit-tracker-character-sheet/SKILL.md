---
name: "habit-tracker-character-sheet"
description: "Explain that the old ephemeral Character Sheet and 6 daily RPG stats were removed from Habit Tracker."
compatibility: "Habit Tracker current"
metadata:
  purpose: "Document the removed stats system and current Perfect Day calculation"
---

# Habit Tracker - Character Sheet Removed

The old **Feuille de Personnage Éphémère** system is no longer an active feature.

Removed concepts:

- Daily RPG stats: `forme_physique`, `sante`, `social`, `finance`, `apprendre`, `discipline`
- Habit stat rewards via `habits.point_rewards`
- Todo stat rewards via `todos.stat_reward_1`, `todos.points_reward_1`, `todos.stat_reward_2`, `todos.points_reward_2`
- Substep stat tags via `substeps.stats_json`
- Template stat thresholds via `perfect_day_templates.thresholds_json`
- Daily stat history via `daily_scores.actual_stats`
- The weekly stat potential endpoint `/api/v1/quests/daily-stats-potentials`

## Current Perfect Day Model

A Perfect Day is now based on scheduled habit accountability:

1. Load active habits planned for the date.
2. Each planned habit must be completed/logged or skipped with a reason.
3. If every planned habit is handled, the daily score is `"Perfect"`; otherwise it is `"Failed"`.
4. The active template (`rest`, `regular`, `hustle`) still provides the day context, agenda, and effort budgets.

Todos still grant direct XP. Substeps still grant Gold. Effort categories are still active:

- `musculaire`
- `cerveau`
- `emotionnel_social`
- `creatif_divergent`

## Bot/API Notes

- `/status` reports Perfect Day status, streak, gold, level/XP, completed/skipped/remaining habits, failed No-Todos, and Life Lore. It does not show stats.
- `/set-day` / `/template` switches between `rest`, `regular`, and `hustle` and recalculates the day.
- `/add_habit` creates a habit without stat rewards.
