---
name: habit-tracker-manage
description: Créer, modifier ou supprimer des structures dans le Habit Tracker distant avec aperçu et confirmation. Utiliser pour gérer habitudes (y compris archivage et montée de niveau), todos, no-todos, objectifs, sous-étapes, templates, épingles, récompenses, branches et nœuds de softskills, zones biologiques, et placements d'agenda.
---

# Habit Tracker Manage

Utiliser exclusivement le flux :

1. Si nécessaire, exécuter `habitctl.py configure --username Gabriel`.
2. Construire un objet JSON minimal.
3. Exécuter `habitctl.py plan OPERATION --data 'JSON'`.
4. Présenter exactement l'aperçu retourné et demander une confirmation explicite.
5. Après confirmation, exécuter `habitctl.py apply PLAN_ID`.
6. Si l'état distant a changé ou le plan a expiré, refaire le plan.
7. En cas de résultat `ambiguous`, exécuter `recover KEY`; ne jamais répéter `apply`.

Ne jamais inventer description, points, récompenses, stats, prérequis ou relations.
Utiliser les défauts techniques du CLI. Pour une nouvelle branche, générer des slugs
sans accents et laisser `description=""`, `prerequisites=[]`, `related=[]`,
`execution_order=1` si l'utilisateur ne précise rien. Ne pas envoyer `x` ou `y` :
le backend attribue automatiquement une position libre.

Exemple « branche Bon vivant avec karaoké, danse et ukulélé » :

```bash
python3 plugins/habit-tracker-control/scripts/habitctl.py plan softskill-branch-with-skills --data '{
  "name":"Bon vivant",
  "skills":["Karaoké","Danse","Ukulélé"]
}'
```

Les opérations disponibles sont listées par `habitctl.py plan --help`. Notamment :
`todo-update`, `todo-delete` (édition/suppression d'un bounty actif — champ `target`
= titre, plus `title`/`xp_reward`/`do_date`/`due_date` optionnels), `habit-archive`,
`habit-unarchive`, `habit-levelup` (= `POST /habits/{id}/versions`, champs
`description`/`source_description` optionnels), `biological-zone-create`,
`biological-zone-update`, `biological-zone-delete` (champ `target` = `zone_name`
pour update/delete), `agenda-placement-set` / `agenda-placement-clear` (champs
`habit`, `date` optionnel — défaut aujourd'hui — et pour `-set` :
`start_time`/`duration_minutes`/`allow_overlap`), `agenda-save-as-template` (champs
`date` optionnel, `template_name`), `notodo-delete` (champ `target` = titre).

Édition d'un no-todo (PUT) : toujours absente de l'API, reste indisponible.
