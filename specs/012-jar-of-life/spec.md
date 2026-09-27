# Jar of Life — cadrage du premier test

Statut : **implémenté**. La capacité se lit en blocs, pas en heures.

## But

Au début de la semaine, protéger jusqu'à trois priorités importantes avant de
laisser les obligations et petites tâches occuper l'attention disponible. Une
semaine reste valide avec des blocs libres : repos et imprévu ont une place.

## Unité et vue

- Semaine du lundi au dimanche, avec matin, après-midi et soir pour chaque jour.
- L'utilisateur marque les blocs qu'il peut réellement piloter. Les autres ne
  comptent pas dans sa capacité; l'application ne suppose pas que les 21 blocs
  sont libres.
- Un bloc disponible est libre ou réservé à un focus dominant : gros caillou,
  galet ou sable. Le libellé peut être libre ou venir d'une action existante.
- La synthèse montre les blocs disponibles, ceux réservés et la marge restante,
  sans transformer la marge en objectif à remplir.

## Parcours minimal

1. Ouvrir la semaine et indiquer ses blocs disponibles.
2. Nommer jusqu'à trois gros cailloux pour cette semaine. Une priorité peut être
   libre (par exemple « voir un ami ») ou liée à une quête ou une To-do. Elle
   peut occuper plusieurs blocs.
3. Réserver au moins un bloc disponible pour chaque gros caillou choisi. Une
   priorité sans bloc reste visible comme décision incomplète, sans sanction.
4. Voir les quêtes prévues et les To-dos dont `do_date` tombe cette semaine.
   L'utilisateur choisit explicitement de les placer, de les classer comme
   galets/sable, ou de les laisser de côté. Leur présence n'occupe aucun bloc
   automatiquement.
5. Modifier ou retirer une réservation sans modifier la quête ou la To-do liée.

## Règles du premier test

- Le classement ne vient ni des XP, ni des tags, ni du Top 3 des objectifs.
- Les sous-étapes restent des jalons; elles ne deviennent pas des actions du
  bocal. Les épingles du Recap restent indépendantes.
- Un bloc représente une intention dominante, pas une durée exacte ni une
  promesse de compléter toutes les actions de ce moment.
- Le bocal n'attribue ni XP, ni pénalité, ni validation, et ne déplace aucune
  quête dans le Home ou dans Google Calendar.
- Aucun placement horaire fin, glisser-déposer obligatoire, ou report automatique
  d'une semaine à l'autre dans ce premier test.

## Critère de réussite

Après une semaine réelle, l'utilisateur peut dire si cette vue l'a amené à
réserver un moment pour un gros caillou et à reporter, réduire ou refuser du
sable. Si la grille devient surtout une nouvelle liste à remplir, le principe
doit être revu avant d'ajouter des fonctions.

## Persistance

Le plan hebdomadaire est retrouvé sur plusieurs appareils grâce à la table
`jar_weeks`, liée à l'utilisateur et au lundi de la semaine. La migration v36
est idempotente. Les routes `GET` et `PUT /api/v1/jar-of-life/{week_start}`
lisent les suggestions et enregistrent les choix explicites. L'accord pour la
modification du schéma a été donné dans la conversation avant le changement.
