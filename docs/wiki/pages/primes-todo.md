# Primes (Todos)

Une prime, c'est une tâche pour aujourd'hui seulement. Quand tu la coches, elle te rapporte de l'XP direct.

Depuis le dashboard, « Créer un objectif lié » ajoute cette prime aux objectifs du moment et l'affiche automatiquement dans le bloc Objectifs du [Recap](#/recap-3-3-3), sans créer de quête quotidienne ni prendre une place de sous-étape. Si le Top 3 est plein, choisis l'objectif à remplacer. Le titre et les dates de l'objectif suivent ceux de la prime. Le bouton « + » du Recap ouvre la fiche de la prime.

La prime reste la seule validation finale : **Réclamer** au Tableau des Primes ou **Valider la to-do** dans le Recap termine la même prime et son objectif, donne les XP habituels une seule fois et libère la place du Top 3. Supprimer la prime supprime aussi son objectif et ses anciennes quêtes liées éventuelles. Une prime terminée reste enregistrée jusqu'au nettoyage du lendemain, qui supprime également l'objectif lié ; les XP déjà gagnés restent acquis.

## Différence avec les habitudes

Une [habitude](#/habitudes) est récurrente et compte pour le [Perfect Day](#/perfect-day). Une prime est **ponctuelle** (aujourd'hui seulement) et rapporte :

- de l'**XP direct** personnalisé (jusqu'à 40 XP par prime).

## Commandes

- `/liste todo` — voir les primes restantes du jour.
- `/add todo <titre>` — ajouter une prime.
- `/add todo <titre> do:<date> due:<date>` — ajouter une prime avec un jour de travail (`do`) et/ou une échéance (`due`). Formats acceptés : `today`, `tomorrow` (ou `aujourd'hui`, `demain`), `DD/MM`, `DD/MM/YYYY`, `YYYY-MM-DD`.

## Do date et due date

Une prime peut porter deux dates distinctes. La `do_date` (jour où tu comptes t'y mettre) part comme **événement** sur ton [Google Calendar](#/sync-google) ; la `due_date` (échéance) part comme **tâche Google** cochable. Si une `do_date` est fixée, le bot t'envoie un rappel Telegram à J-7, J-3 et J-1 avant l'échéance.

L'inverse existe aussi : des règles à ne pas enfreindre. C'est le concept [No-Todo](#/no-todo).
