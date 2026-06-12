# Feature Specification: Reward Shop (Boutique de Récompenses)

**Feature Branch**: `005-reward-shop`

**Created**: 2026-06-12

**Status**: Draft

**Input**: User description: "rajoute une boutique. Dans la boutique, on créer des récompenses et chaque recompense est achetable en or. Certaine récompenses sont débloquable uniquement quand certain skill ou objectifs on ete accomplis !"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gestion des Récompenses (Priority: P1)

En tant qu'utilisateur, je veux pouvoir créer, afficher, modifier et supprimer des récompenses dans ma boutique afin de définir mes propres motivations (ex: "Regarder un épisode de série", "Acheter un jeu vidéo").

**Why this priority**: C'est la base de la boutique. Sans possibilité de créer de récompenses, la boutique est vide et inutilisable.

**Independent Test**: L'utilisateur navigue vers l'onglet "Boutique", clique sur "Ajouter une récompense", remplit le formulaire (nom, description, coût en or, type d'achat) et la voit apparaître dans sa boutique.

**Acceptance Scenarios**:

1. **Given** un utilisateur connecté, **When** il crée une récompense avec le titre "Cheat Meal", une description, et un coût de 100 Or, **Then** la récompense est ajoutée avec succès et s'affiche dans la boutique.
2. **Given** une récompense existante dans la boutique, **When** l'utilisateur modifie son coût en or de 100 à 150 Or, **Then** la modification est enregistrée et immédiatement visible.
3. **Given** une récompense existante, **When** l'utilisateur la supprime, **Then** elle disparaît définitivement de sa boutique.

---

### User Story 2 - Achat de Récompenses (Priority: P1)

En tant qu'utilisateur, je veux dépenser mon Or accumulé pour acheter des récompenses débloquées, ce qui déduira le coût de mon solde d'Or et comptabilisera l'achat.

**Why this priority**: C'est la boucle de rétroaction principale du système RPG. L'Or gagné via les objectifs ou habitudes doit pouvoir être dépensé pour avoir une utilité réelle.

**Independent Test**: L'utilisateur clique sur "Acheter" sur une récompense disponible. Son solde d'or diminue de la valeur de la récompense, et le compteur d'achats de celle-ci augmente.

**Acceptance Scenarios**:

1. **Given** un utilisateur ayant 150 Or et une récompense "Café Premium" coûtant 50 Or, **When** il achète cette récompense, **Then** son solde passe à 100 Or, et le nombre d'achats de la récompense passe à 1.
2. **Given** un utilisateur ayant 30 Or et une récompense "Cinéma" coûtant 100 Or, **When** il tente d'acheter la récompense, **Then** l'achat est refusé et un message indique que l'Or est insuffisant.
3. **Given** une récompense à achat unique (one-time) déjà achetée par l'utilisateur, **When** elle est affichée dans la boutique, **Then** l'option d'achat est désactivée et marquée comme "Déjà possédée / Achetée".

---

### User Story 3 - Récompenses Verrouillées (Skills & Objectifs) (Priority: P2)

En tant qu'utilisateur, je veux pouvoir lier une récompense à un softskill spécifique (arbre de compétences) ou à un objectif long terme, afin que la récompense reste verrouillée tant que ce prérequis n'est pas complété.

**Why this priority**: Cela lie la gratification (boutique) aux efforts de développement personnel à long terme, renforçant la discipline et l'aspect ludique (RPG).

**Independent Test**: L'utilisateur consulte la boutique et voit des récompenses verrouillées (cadenassées) avec l'indication du prérequis manquant. Une fois le prérequis validé, la récompense devient achetable.

**Acceptance Scenarios**:

1. **Given** une récompense "Nouveau Livre" exigeant que le softskill "Lecture" soit complété, **When** le softskill "Lecture" n'est pas encore complété par l'utilisateur, **Then** la récompense est affichée avec un cadenas et le bouton d'achat est bloqué.
2. **Given** la même récompense "Nouveau Livre" verrouillée par le softskill "Lecture", **When** l'utilisateur complète le softskill "Lecture" dans son arbre de compétences, **Then** la récompense dans la boutique se déverrouille automatiquement et devient achetable.
3. **Given** une récompense "Voyage" exigeant la complétion de l'objectif majeur "Économiser 5000 Or", **When** l'objectif n'est pas complété, **Then** la récompense reste bloquée. Dès que l'objectif est validé, elle se débloque.

---

### User Story 4 - Interaction via le Bot Telegram (Priority: P3)

En tant qu'utilisateur, je veux pouvoir lister la boutique et acheter mes récompenses directement via le Bot Telegram.

**Why this priority**: Permet un accès rapide en mobilité sans ouvrir le tableau de bord web, conformément à l'approche Telegram-first du projet.

**Independent Test**: L'utilisateur envoie une commande au bot pour lister les récompenses, puis une autre pour effectuer un achat, et reçoit une confirmation.

**Acceptance Scenarios**:

1. **When** l'utilisateur envoie `/shop` au bot, **Then** le bot retourne la liste de ses récompenses configurées avec leur ID, leur coût en or, et leur statut (disponible, verrouillé, ou déjà acheté pour les achats uniques).
2. **Given** une récompense disponible avec l'ID 3 coûtant 40 Or, **When** l'utilisateur envoie `/buy 3` au bot, **Then** le bot effectue l'achat, déduit 40 Or du solde de l'utilisateur, et envoie un message de confirmation chaleureux avec le nouveau solde d'or.
3. **Given** une récompense verrouillée avec l'ID 5, **When** l'utilisateur envoie `/buy 5`, **Then** le bot refuse l'achat et explique le prérequis manquant.

---

### Edge Cases

- **Modification de prix après achat** : Que se passe-t-il si le prix d'une récompense est modifié ? Les achats passés restent inchangés et ne font l'objet d'aucun ajustement rétroactif de solde.
- **Suppression de prérequis** : Que se passe-t-il si un softskill ou un objectif lié à une récompense est supprimé de l'application ? La récompense doit automatiquement perdre cette condition de verrouillage et devenir accessible sans restriction.
- **Solde d'or négatif** : Le système doit garantir par des validations strictes au niveau de la base de données et de l'API qu'aucune opération ne peut amener le solde d'or d'un utilisateur en dessous de 0.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Le système MUST permettre à l'utilisateur de gérer ses récompenses (création, lecture, modification, suppression).
- **FR-002**: Chaque récompense MUST posséder un titre (obligatoire), une description (optionnelle), un coût en Or (obligatoire, entier positif), et un type d'achat (unique ou répétable).
- **FR-003**: Le système MUST permettre de lier une récompense à un prérequis optionnel de softskill (identifiant de softskill) ou d'objectif (identifiant d'objectif).
- **FR-004**: Le système MUST calculer dynamiquement le statut de verrouillage de chaque récompense pour l'utilisateur en vérifiant la complétion du softskill ou de l'objectif lié.
- **FR-005**: Le système MUST déduire le coût en Or du solde de l'utilisateur lors de l'achat d'une récompense et incrémenter son compteur d'achats.
- **FR-006**: Le système MUST empêcher l'achat d'une récompense si le solde d'Or de l'utilisateur est inférieur à son coût, ou si la récompense est verrouillée, ou si c'est une récompense unique déjà achetée.
- **FR-007**: Le système MUST exposer une interface web (onglet "Boutique") pour gérer et acheter les récompenses avec un rendu visuel premium (cartes de récompenses, badges de statut, cadenas interactifs, animations d'achat).
- **FR-008**: Le bot Telegram MUST supporter la commande `/shop` pour lister les récompenses de l'utilisateur.
- **FR-009**: Le bot Telegram MUST supporter la commande `/buy <reward_id>` pour acheter directement une récompense.
- **FR-010**: En cas de suppression d'un objectif ou d'un softskill, toutes les récompenses qui y faisaient référence MUST être nettoyées de leur prérequis (mise à NULL du lien) pour éviter tout verrouillage orphelin.

### Key Entities *(include if feature involves data)*

- **Reward (Récompense)**: Représente un élément achetable dans la boutique d'un utilisateur.
  - Attributs : `id` (identifiant unique), `user_id` (lien vers l'utilisateur propriétaire), `title` (titre), `description` (détails), `gold_cost` (coût en or, >= 0), `required_softskill_id` (identifiant optionnel du softskill prérequis), `required_goal_id` (identifiant optionnel de l'objectif prérequis), `is_one_time` (booleen, achat unique), `purchased_count` (nombre de fois acheté), `created_at` (date de création).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: La page de la boutique charge et liste toutes les récompenses en moins de 300ms sur le Raspberry Pi.
- **SC-002**: Un achat de récompense est traité (validation des règles, déduction de l'or, mise à jour des compteurs et retour d'API) en moins de 100ms.
- **SC-003**: La commande de bot `/shop` répond avec la liste des récompenses en moins de 1.5 seconde.
- **SC-004**: Aucun scénario d'achat simultané ou d'action rapide dans l'interface ne peut corrompre la base de données ou induire un solde d'or négatif (100% de validation d'intégrité).

## Assumptions

- Le solde d'or actuel des utilisateurs est stocké dans la colonne `gold` de la table `users`.
- Les softskills sont chargés dynamiquement depuis `softskills_tree.json` et les progrès associés sont dans `user_softskill_progress`.
- Les objectifs sont stockés dans la table `goals`.
- L'authentification utilise le header `X-User-ID` identique au reste de l'application.
