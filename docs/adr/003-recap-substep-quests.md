# Recap : les sous-étapes portent les quêtes d'objectifs

Date : 2026-10-04. Statut : accepté.

## Décision

Le Top 3 conserve jusqu'à trois objectifs prioritaires. Le Recap affiche jusqu'à
trois sous-étapes non terminées, réparties librement entre ces objectifs. Une
sous-étape partagée compte une seule fois.

Une quête de sous-étape est la sous-étape sélectionnée elle-même, sans copie dans
`habits`. Sa seule validation est `POST /substeps/{id}/complete`, depuis Objectifs
& Graphes. Cette action conserve la récompense d'Or existante et libère sa place
dans `users.pinned_substeps`. Aucun log quotidien, streak ou bonus supplémentaire
n'est créé. Le Recap ouvre le graphe sans valider.

Les colonnes et payloads existants `pinned_goals` / `pinned_substeps` suffisent ;
aucun changement de schéma. Le serveur applique la limite globale et filtre les
sous-étapes terminées, étrangères ou sorties du Top 3.

## Transition

L'épinglage d'un objectif et la création d'un objectif depuis une prime ne créent
plus de quête quotidienne. Au démarrage et à la sauvegarde des épingles, les
anciennes quêtes de rôle `goal` sont mises en pause via leur historique daté ;
leurs validations et données historiques sont conservées. Les anciennes API et
les tags restent compatibles, mais ces quêtes ne reprennent pas à l'épinglage.

Les compétences conservent leurs quêtes quotidiennes. Les primes conservent leur
validation finale et leur cycle de vie. Les Must restent le socle du Perfect Day.
