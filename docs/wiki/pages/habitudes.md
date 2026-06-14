# Habitudes (Quêtes)

Une habitude, c'est une action que tu répètes régulièrement, selon un planning. Chaque fois que tu la valides, elle nourrit tes [stats](#/stats-xp-niveau-or) du jour. Et sur la durée, c'est elle qui te fait avancer vers tes [objectifs](#/objectifs).

## Deux types

| Type | Validation | Commande |
|---|---|---|
| Binaire | faite / pas faite (une fois par jour) | `/done <habitude>` |
| Quantitative | une mesure (ex. 30min, 5km) | `/log <habitude> <valeur><unité>` |

## Planning

Une habitude n'est due que certains jours (tous les jours, ou par ex. lundi + mercredi). Elle n'apparaît dans les quêtes du jour que les jours prévus.

## Récompense

Chaque habitude attribue des points à une ou plusieurs [stats](#/stats-xp-niveau-or). Une habitude quantitative peut avoir un **plafond de points par jour** (daily cap). Les habitudes alimentent le [Perfect Day](#/perfect-day) mais ne donnent **pas** d'XP direct — contrairement aux [primes](#/primes-todo).

## Séparées des objectifs

Les habitudes et les [objectifs](#/objectifs) sont **séparés** : faire des habitudes ne valide pas tout seul une sous-étape d'objectif. Le lien est d'**intention** — la régularité construite par les habitudes rend les objectifs atteignables.

## Paliers d'ancrage (30J / 90J)

Pour récompenser la constance et vous motiver à installer des habitudes sur le long terme, le jeu intègre des paliers de continuité (streaks) :
- **Seuil des 30 jours (Adoption initiale) :** Atteindre un streak de 30 jours consécutifs sur une habitude déclenche une célébration visuelle et vous octroie **+100 XP** et **+50 Or**.
- **Seuil des 90 jours (Ancrage définitif) :** Atteindre un streak de 90 jours consécutifs déclenche une célébration majeure et vous octroie **+300 XP** et **+150 Or**.

*Note : Un `/skip` validé par le bot Telegram permet de suspendre temporairement une habitude pour un motif valable sans casser votre streak en cours.*
