# Templates de jour

Selon les jours, tu peux en faire plus ou moins. Le template est le type de journée calculé automatiquement par ton planning. Il fixe un agenda type et des budgets d'effort pour cadrer ton [Perfect Day](#/perfect-day).

## Les 3 templates

| Template | Clé(s) | Pour quoi |
|---|---|---|
| Rest | `rest` | Journée de repos, récupération, charge faible |
| Regular | `regular` | Journée normale et soutenable |
| Hustle | `hustle` | Journée intense, charge haute mais bornée |

## Planning automatique

Dans Réglages → Cycle des Journées, tu configures une semaine normale et une semaine moins intense, jour par jour. Le serveur déroule trois semaines normales puis une semaine moins intense depuis l'ancrage choisi. Une nouvelle programmation prend effet aujourd'hui ou à une date future; elle ne réécrit jamais les journées déjà calculées.

Le dashboard affiche le type actif sans menu de sélection. Si ton énergie chute, **Feel off today** applique `rest` uniquement à aujourd'hui et recalcule immédiatement agenda, Perfect Day, XP et streaks. **Revenir au planning prévu** retire cette dérogation. Les validations, skips, échecs et pénalités déjà enregistrés sont conservés.

Les anciennes commandes Telegram `/set-day` et `/template` ont été retirées.

Chaque template a ses propres budgets par catégorie d'effort (`musculaire`, `cerveau`, `emotionnel_social`, `creatif_divergent`), un objectif de focus et un objectif de repos minimum — les deux sont éditables directement dans l'onglet ⚙️ Perfect Days du dashboard, avec son propre sélecteur de template.

## Budgets et agenda vertical

Les budgets ne sont pas de simples plafonds abstraits : ils cadrent ce que tu peux placer dans l'[agenda vertical](#/agenda-timeline). Un jour `hustle` autorise jusqu'à 4h par type d'effort (10h au total) ; un jour `rest` redescend à 1h par type (4h au total), pour garder une journée de récupération réellement légère. Une fois ta journée type planifiée, un bouton export la pousse vers [Google Calendar](#/sync-google).
