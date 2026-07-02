---
name: habit-tracker-query
description: Consulter le Habit Tracker distant avec des réponses françaises concises. Utiliser pour les questions sur le statut du jour, profil, objectifs, sous-étapes, habitudes, calendrier, agenda du jour, zones biologiques, todos, no-todos, softskills, boutique, allostasie, historique, modèles ou statistiques potentielles.
---

# Habit Tracker Query

Utiliser uniquement `plugins/habit-tracker-control/scripts/habitctl.py`.

1. Si le CLI n'est pas configuré, exécuter `configure --username Gabriel`.
2. Exécuter `doctor` si la cible n'a pas encore été vérifiée dans cette conversation.
3. Exécuter `query RESOURCE`; ajouter `--name "..."` pour un détail.
4. Ne jamais appeler directement `curl`, SQLite ou les routes API.
5. Répondre en français, brièvement, puis proposer au plus un détail pertinent.

```bash
python3 plugins/habit-tracker-control/scripts/habitctl.py query goals
python3 plugins/habit-tracker-control/scripts/habitctl.py query goals --name "Tour du monde"
python3 plugins/habit-tracker-control/scripts/habitctl.py query status
python3 plugins/habit-tracker-control/scripts/habitctl.py query softskills
python3 plugins/habit-tracker-control/scripts/habitctl.py query agenda
python3 plugins/habit-tracker-control/scripts/habitctl.py query agenda --date 2026-07-04
python3 plugins/habit-tracker-control/scripts/habitctl.py query biological-zones
```

Ressources : `status`, `profile`, `goals`, `habits`, `habit-calendar`, `todos`,
`notodos`, `softskills`, `rewards`, `history`, `templates`, `potentials`, `agenda`
(accepte `--date YYYY-MM-DD`, défaut aujourd'hui), `biological-zones`.
