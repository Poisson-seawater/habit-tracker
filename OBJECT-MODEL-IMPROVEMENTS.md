# Note: modele objet et ameliorations possibles

## 1. Probleme identifie

Le modele actuel fonctionne, mais plusieurs objets metier se recoupent et
creent de la duplication conceptuelle entre l'API, le frontend, le bot et la
base de donnees.

### Todo et SubStep sont proches

`Todo` et `SubStep` representent tous les deux une action ponctuelle que
l'utilisateur peut completer.

- `Todo` est une action libre, non rattachee a un objectif, avec recompense XP.
- `SubStep` est une action rattachee a un ou plusieurs objectifs, avec
  recompense en or.

La separation est comprehensible cote produit, mais elle cree deux chemins
techniques pour gerer une "chose concrete a faire": routes differentes, champs
similaires, logique de completion differente, affichages differents.

### NoTodo melange definition et historique

`notodos` definit une regle a ne pas transgresser, tandis que `notodo_logs`
stocke les transgressions datees. Le champ `failed_at` sur `notodos` fait aussi
office de trace de derniere transgression.

Ce double stockage peut rendre la source de verite ambigue:

- l'historique fiable devrait etre dans `notodo_logs`;
- `failed_at` devrait etre traite comme un cache/legacy ou renomme
  explicitement en `last_failed_at`.

### Softskills: definition JSON, progression SQL

Les branches et softskills sont definis dans `softskills_tree.json`, alors que
la progression utilisateur est stockee dans `user_softskill_progress`.

Ce choix est leger et adapte au Raspberry Pi, mais il a des limites:

- pas de foreign keys entre `rewards.required_softskill_id` et un vrai skill SQL;
- les branches/skills sont globaux plutot que naturellement scopes par user;
- les migrations, validations et recherches sont moins robustes que pour les
  tables SQL classiques.

### Le vocabulaire metier n'est pas encore assez canonique

Le systeme manipule plusieurs notions proches:

- habitude repetable;
- action ponctuelle libre;
- action ponctuelle rattachee a un objectif;
- regle negative;
- competence;
- objectif long terme.

Sans taxonomie officielle, chaque nouvelle feature risque de choisir son propre
objet, ce qui augmente la complexite et les doublons.

## 2. Ameliorations proposees

### Court terme: documenter la taxonomie canonique

Formaliser les definitions suivantes dans la documentation produit/technique:

- `Habit`: routine repetable, suivie par logs.
- `Todo`: action ponctuelle libre, completable une fois.
- `Goal`: objectif long terme.
- `SubStep`: action ponctuelle rattachee a un ou plusieurs objectifs.
- `NoTodo`: regle negative.
- `NoTodoLog`: transgression datee d'une regle negative.
- `Softskill`: competence dans un arbre de progression.
- `SoftskillBranch`: categorie visuelle et logique de softskills.

Cette clarification doit devenir la reference avant d'ajouter de nouvelles
routes, tables ou integrations.

### Court terme: ajouter une vue unifiee des actions

Creer une couche de service/API qui expose une liste unifiee des actions
ponctuelles, sans modifier la base de donnees dans un premier temps.

Exemple conceptuel:

```text
WorkItem
- source_type: "todo" | "substep"
- source_id
- title
- description
- completed
- completed_at
- do_date
- due_date
- reward_type: "xp" | "gold"
- reward_amount
- parent_goal_ids
```

Cette vue permettrait au frontend, au bot et a l'agenda de manipuler une seule
notion d'"action a faire", tout en conservant les tables actuelles.

### Court terme: clarifier NoTodo

Conserver `notodo_logs` comme source de verite pour les transgressions datees.
Traiter `notodos.failed_at` comme:

- soit un champ legacy a maintenir temporairement;
- soit un cache explicite renomme mentalement/documente comme `last_failed_at`.

Eviter d'ajouter de nouvelles features qui dependent uniquement de `failed_at`.

### Moyen terme: extraire la logique metier hors des routes

Une partie importante de la logique de completion vit encore dans
`backend/src/api/routes.py`. Les prochaines evolutions devraient deplacer la
logique metier vers des services dedies:

- completion de todos;
- completion de substeps;
- auto-completion des goals;
- calcul des recompenses;
- validation des actions focus/pinned.

Cela reduira le risque de divergence entre API, bot, frontend et futures
integrations.

### Moyen terme: stabiliser les softskills

Deux options sont possibles.

Option A: garder le JSON.

- Bon choix si l'arbre est global, petit et rarement modifie.
- Continuer a stocker seulement la progression en SQL.
- Ajouter plus de validations dans le service.

Option B: migrer branches et softskills en SQL.

- Meilleur choix si les skills deviennent user-scopes, dynamiques ou relies a
  beaucoup d'autres objets.
- Permet des foreign keys propres pour les rewards et les dependances.
- Plus couteux: migration, adaptation frontend, bot, tests et seed.

Recommandation actuelle: garder le JSON tant que le besoin multi-user avance
n'est pas prioritaire.

### Long terme: envisager une fusion Todo/SubStep

Si la duplication continue de grandir, introduire un modele commun d'action
ponctuelle pourrait simplifier le systeme.

Approche possible:

```text
tasks
- id
- user_id
- title
- description
- status
- completed_at
- do_date
- due_date
- reward_type
- reward_amount
- source_type

goal_task_links
- goal_id
- task_id
- execution_order
```

Dans ce modele:

- un Todo serait une task sans goal;
- un SubStep serait une task liee a un ou plusieurs goals;
- les affichages "bounty", "objectif" ou "agenda" seraient des vues metier.

Ce changement ne doit pas etre fait sans spec dediee, migration idempotente,
tests et audit des contrats API existants.

## Priorite recommandee

1. Documenter la taxonomie canonique.
2. Ajouter une vue/API unifiee des actions ponctuelles.
3. Clarifier `NoTodoLog` comme source de verite.
4. Extraire la logique de completion dans des services.
5. Reporter toute fusion SQL `Todo`/`SubStep` a une spec dediee.

Cette trajectoire ameliore la coherence du systeme sans casser les contrats API
actuels ni lancer une migration lourde prematuree.
