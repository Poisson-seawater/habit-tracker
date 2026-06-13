---
name: habit-tracker-action
description: Exécuter immédiatement une action courante et bornée dans le Habit Tracker distant. Utiliser pour valider, logger ou skipper une habitude, compléter un todo ou une sous-étape, échouer un no-todo, compléter ou réinitialiser un softskill, acheter ou réclamer une récompense, ou changer le modèle du jour.
---

# Habit Tracker Action

Utiliser uniquement `plugins/habit-tracker-control/scripts/habitctl.py act`.

- Si le CLI n'est pas configuré, exécuter d'abord `habitctl.py configure --username Gabriel`.
- Résoudre les noms par le CLI; ne jamais fournir d'ID.
- Exécuter sans confirmation supplémentaire lorsque l'intention est explicite.
- Demander seulement la quantité d'une habitude quantitative ou la raison d'un skip si absente.
- En cas de résultat `ambiguous`, exécuter immédiatement `recover KEY`; ne jamais répéter l'action.
- Rapporter le résultat API sans l'embellir.

```bash
python3 plugins/habit-tracker-control/scripts/habitctl.py act habit-done --target "Routine matin"
python3 plugins/habit-tracker-control/scripts/habitctl.py act habit-log --target "Lecture" --amount 20
python3 plugins/habit-tracker-control/scripts/habitctl.py act reward-purchase --target "Film"
python3 plugins/habit-tracker-control/scripts/habitctl.py recover KEY
```

Actions : `habit-done`, `habit-log`, `habit-skip`, `todo-complete`,
`notodo-fail`, `substep-complete`, `softskill-complete`, `softskill-reset`,
`reward-purchase`, `template-set`.
