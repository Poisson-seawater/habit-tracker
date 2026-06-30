# Habitudes (Quêtes)

Une habitude, c'est une action que tu répètes régulièrement, selon un planning. Chaque fois que tu la valides, elle traite une partie de ton [Perfect Day](#/perfect-day). Et sur la durée, c'est elle qui te fait avancer vers tes [objectifs](#/objectifs).

## Deux types

| Type | Validation | Commande |
|---|---|---|
| Binaire | faite / pas faite (une fois par jour) | `/done <habitude>` |
| Quantitative | une mesure (ex. 30min, 5km) | `/log <habitude> <valeur><unité>` |

## Planning

Une habitude n'est due que certains jours (tous les jours, ou par ex. lundi + mercredi). Elle n'apparaît dans les quêtes du jour que les jours prévus.

## Effort et Perfect Day

Les habitudes alimentent le [Perfect Day](#/perfect-day) par leur statut : validée, loggée, skippée ou restante. Une habitude quantitative peut avoir un **plafond de log par jour** (daily cap) et une unité. Certaines habitudes portent aussi un type et une durée d'effort (`musculaire`, `cerveau`, `emotionnel_social`, `creatif_divergent`) pour les budgets de journée. Elles ne donnent **pas** d'XP direct — contrairement aux [primes](#/primes-todo).

## Séparées des objectifs

Les habitudes et les [objectifs](#/objectifs) sont **séparés** : faire des habitudes ne valide pas tout seul une sous-étape d'objectif. Le lien est d'**intention** — la régularité construite par les habitudes rend les objectifs atteignables.

## Paliers d'ancrage (30J / 90J)

Pour récompenser la constance et vous motiver à installer des habitudes sur le long terme, le jeu intègre des paliers de continuité (streaks) :
- **Seuil des 30 jours (Adoption initiale) :** Atteindre un streak de 30 jours consécutifs sur une habitude déclenche une célébration visuelle et vous octroie **+100 XP** et **+50 Or**.
- **Seuil des 90 jours (Ancrage définitif) :** Atteindre un streak de 90 jours consécutifs déclenche une célébration majeure et vous octroie **+300 XP** et **+150 Or**.

### Comment fonctionne le streak d'une habitude ?

Le streak (votre série de succès consécutifs) est géré selon les règles suivantes :

* **Progression (+1) :** Chaque fois que vous validez l'habitude (`/done` ou `/log`) un jour où elle est planifiée, votre streak augmente de 1.
* **Gel (Pause) :** Si vous ne pouvez pas faire l'habitude un jour où elle est due, vous pouvez utiliser la commande `/skip <habitude> raison: <texte>`. Votre streak est mis en pause (il ne retombe pas à 0, mais n'augmente pas non plus).
* **Réinitialisation (0) :** Si l'habitude est planifiée aujourd'hui et que vous ne la faites pas (et ne la skippez pas avec `/skip`), **votre streak retombe immédiatement à 0**.
* **Jours non-planifiés :** Les jours où l'habitude n'est pas planifiée (par exemple, les jours de repos prévus dans son planning) n'ont aucun impact : le streak ne progresse pas et ne se brise pas.
