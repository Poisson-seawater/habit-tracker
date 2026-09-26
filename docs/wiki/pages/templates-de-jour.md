# Templates de jour

Selon les jours, tu peux en faire plus ou moins. Le template est le type de journée calculé automatiquement par ton planning. Il fixe les quêtes visibles et les budgets d'effort qui cadrent ton [Perfect Day](#/perfect-day).

## Les 3 templates

| Template | Clé(s) | Pour quoi |
|---|---|---|
| Rest | `rest` | Journée de repos, récupération, charge faible |
| Regular | `regular` | Journée normale et soutenable |
| Hustle | `hustle` | Journée intense, charge haute mais bornée |

## Planning automatique

Dans Réglages → Cycle des Journées, tu configures une semaine normale et une semaine moins intense, jour par jour. Le serveur déroule trois semaines normales puis une semaine moins intense depuis l'ancrage choisi. Une nouvelle programmation prend effet aujourd'hui ou à une date future; elle ne réécrit jamais les journées déjà calculées.

Le dashboard affiche le type actif sans menu de sélection. Si ton énergie chute, **Feel off today** applique `rest` uniquement à aujourd'hui et recalcule immédiatement les quêtes du jour, le Perfect Day, XP et streaks. **Revenir au planning prévu** retire cette dérogation. Les validations, skips, échecs et pénalités déjà enregistrés sont conservés.

Les anciennes commandes Telegram `/set-day` et `/template` ont été retirées.

Chaque template a ses propres budgets par catégorie d'effort (`musculaire`, `cerveau`, `emotionnel_social`, `creatif_divergent`), un objectif de focus et un objectif de repos minimum — les deux sont éditables directement dans l'onglet ⚙️ Perfect Days du dashboard, avec son propre sélecteur de template.

## Budgets d'effort

Les budgets des templates restent configurables dans Réglages. Un jour `hustle` autorise jusqu'à 4h par type d'effort (10h au total) ; un jour `rest` redescend à 1h par type (4h au total). Le Home montre les [quêtes du jour](#/agenda-timeline) en liste, sans grille horaire ni placement obligatoire.
