# Feature Specification: Affichage des liaisons d'objectifs

**Feature Branch**: `008-goal-dependency-display`

**Created**: 2026-06-15

**Status**: Draft

**Input**: User description: "quand je fait un lien avec un objectif ex 'avoir 500k en actif' de 'devenir millionnnaire' a objectif ex 'faire le tour du monde', je ne vois pas cet objectif s'afficher dans faire le tour du monde. comme cela ce fait dans softskill."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Affichage des liaisons d'objectifs dans le graphe (Priority: P1)

En tant qu'utilisateur, lorsque je visualise l'arbre d'un objectif (ex: "Faire le tour du monde") et qu'une de ses étapes (ex: "Avoir 500k en actif") est partagée/liée avec un autre objectif (ex: "Devenir millionnaire"), je veux voir cet autre objectif affiché sous forme de badge interactif sur la carte de l'étape pour comprendre les dépendances croisées de mes projets.

**Why this priority**: C'est le coeur du besoin utilisateur permettant d'avoir la visibilité sur la provenance et les impacts transversaux des étapes partagées.

**Independent Test**: Créer un objectif A, y ajouter une étape, lier cette étape à un objectif B. Naviguer sur l'arbre de l'objectif B et vérifier que le badge de l'objectif A apparaît bien sur la carte de l'étape.

**Acceptance Scenarios**:

1. **Given** un utilisateur connecté ayant l'objectif "Devenir millionnaire" avec l'étape "Avoir 500k en actif", liée également à l'objectif "Faire le tour du monde",
   **When** l'utilisateur affiche l'arbre "Faire le tour du monde",
   **Then** l'étape "Avoir 500k en actif" affiche une section de liaison contenant le badge interactif "🔗 Devenir Millionnaire".
2. **Given** une étape liée uniquement à son objectif principal,
   **When** l'utilisateur affiche son arbre d'objectifs,
   **Then** l'étape ne montre aucune section de liaison ni badge superflu.

---

### User Story 2 - Navigation rapide par clic sur badge (Priority: P2)

En tant qu'utilisateur, je veux pouvoir cliquer sur le badge d'un objectif lié sur une carte d'étape pour basculer instantanément sur l'arbre de cet objectif cible sans devoir le chercher dans le menu latéral.

**Why this priority**: Améliore considérablement l'expérience utilisateur et l'exploration de la carte d'objectifs liés, de la même manière que la navigation entre compétences liées sur l'arbre de softskills.

**Independent Test**: Cliquer sur le badge "Devenir Millionnaire" présent sur l'étape "Avoir 500k en actif" depuis l'arbre de "Faire le tour du monde" et vérifier que le graphe affiché change pour celui de "Devenir Millionnaire".

**Acceptance Scenarios**:

1. **Given** l'arbre d'objectifs "Faire le tour du monde" affiché avec l'étape "Avoir 500k en actif" liée à "Devenir Millionnaire",
   **When** l'utilisateur clique sur le badge "Devenir Millionnaire" sur la carte de l'étape,
   **Then** l'affichage bascule immédiatement sur l'arbre de "Devenir Millionnaire" et l'élément correspondant dans la liste latérale devient actif.

---

### User Story 3 - Affichage des liaisons dans le tiroir d'édition (Priority: P3)

En tant qu'utilisateur, lorsque j'édite une étape dans le panneau/tiroir latéral, je veux voir la liste des objectifs auxquels elle est actuellement liée pour avoir le contexte complet avant de la modifier ou de la supprimer.

**Why this priority**: Complète la visibilité du contexte au moment de la gestion (édition/suppression) de l'étape.

**Independent Test**: Ouvrir le formulaire d'édition d'une étape partagée et vérifier que la liste de tous ses objectifs parents/liés est affichée.

**Acceptance Scenarios**:

1. **Given** une étape partagée entre "Devenir Millionnaire" et "Faire le tour du monde",
   **When** l'utilisateur ouvre le tiroir d'édition de cette étape,
   **Then** une section "Objectifs associés" liste les deux objectifs.

---

### Edge Cases

- **Objectif cible supprimé** : Si un objectif associé est supprimé, le lien dans `goal_substep_links` doit être supprimé en cascade (géré par la contrainte de clé étrangère SQLite) et le badge ne doit plus s'afficher.
- **Grand nombre de liaisons** : Si une étape est liée à 5 objectifs ou plus, les badges doivent s'enrouler sur plusieurs lignes proprement sans déformer la carte ou la colonne.
- **Caractères spéciaux** : Les titres d'objectifs contenant des emoji ou des apostrophes doivent s'afficher et se lier correctement.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Le endpoint API `GET /api/v1/goals` doit retourner pour chaque sous-étape la liste des autres objectifs auxquels elle est liée sous la forme d'un tableau d'objets `linked_goals` (chaque objet contenant `id` et `title`).
- **FR-002**: L'interface de rendu des objectifs (`renderGoalTree`) doit afficher sous le titre/desc de chaque étape les badges correspondants à ses `linked_goals`.
- **FR-003**: Chaque badge d'objectif lié doit afficher une icône de lien `🔗` suivie du titre de l'objectif, avec un style premium (couleur d'accentuation violette ou similaire, fond semi-transparent et effet hover).
- **FR-004**: Cliquer sur un badge d'objectif lié doit déclencher le changement d'arbre actif en mettant à jour `activeGoalId`, en appliquant la classe active dans la barre latérale, et en appelant `renderGoalTree` pour le nouvel objectif.
- **FR-005**: Le tiroir d'édition d'une sous-étape (`openDrawer` en mode `edit-substep`) doit lister de manière informative les objectifs auxquels la sous-étape est rattachée.

### Key Entities

- **Goal** : Un objectif majeur à long terme (ex: "Devenir Millionnaire"). Possède un id, un titre, une description, un état complété.
- **SubStep** : Une sous-étape / étape intermédiaire d'un ou plusieurs objectifs (ex: "Avoir 500k en actif"). Possède des points d'XP/Gold et un ordre d'exécution.
- **GoalSubStepLink** : Table de liaison gérant la relation plusieurs-à-plusieurs entre les objectifs et les sous-étapes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** : Lorsqu'un lien est créé entre une étape et un nouvel objectif, le badge de liaison doit s'afficher en temps réel sur les arbres respectifs après la confirmation.
- **SC-002** : Le changement d'arbre au clic sur un badge doit s'effectuer en moins de 100 ms côté client, de manière fluide et sans rechargement de page.

## Assumptions

- L'utilisateur utilise le dashboard existant servi en statique.
- Les liaisons multi-objectifs sont déjà persistées correctement via `GoalSubStepLink` dans la base SQLite.
- Les droits d'accès sont isolés par `user_id` (déjà géré par le header `X-User-ID`).
