# Templates de jour

Selon les jours, tu peux en faire plus ou moins. Le template, c'est le « type de journée » que tu choisis. Il fixe les seuils de stats à atteindre pour décrocher un [Perfect Day](#/perfect-day).

## Les 4 templates

| Template | Clé(s) | Pour quoi |
|---|---|---|
| Semaine | `semaine` | Lundi → vendredi, exigences pleines |
| Weekend | `weekend` | Samedi → dimanche |
| Récupération | `recovery` (alias `recup`) | Journée calme, seuils réduits |
| Malade | `sick` (alias `malade`) | Repos total, seuils minimaux |

## Bascule

`/set-day <template>` (alias `/template`) change le type de journée et réajuste **instantanément** les seuils. Le bon template évite de « rater » une journée off : un jour malade ne se juge pas avec les exigences d'un jour de semaine.

Chaque template a ses propres seuils par [stat](#/stats-xp-niveau-or), configurables dans l'écran Paramètres du site.
