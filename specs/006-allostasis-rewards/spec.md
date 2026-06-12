# Feature Specification: Allostasis Rewards (Boutique d'Allostasie)

**Feature Branch**: `006-allostasis-rewards`

**Created**: 2026-06-12

**Status**: Draft

**Input**: User description: "dans la boutique. Je veux 2 catégories spéciales: allostasie daily et allostasie weekly. Chacune des 2 catégorie on max 3 items ! Ses items se font call dans le recap de la journée. Ex: allostasie dayli - 25 tv show et allostasie weekly - prendre un biere le soir. Spécification: aucun coût, se repete tout les jour ou toute les semaines !"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configuration des Items d'Allostasie (Priority: P1)

En tant qu'utilisateur, je veux pouvoir configurer jusqu'à 3 items d'Allostasie Daily et 3 items d'Allostasie Weekly dans ma boutique de récompenses sans coût en or (0 Gold) pour définir mes activités de récupération de la journée ou de la semaine.

**Why this priority**: C'est la base de la configuration. L'utilisateur doit pouvoir définir ses propres activités de bien-être limitées en nombre pour éviter la surcharge cognitive.

**Independent Test**: L'utilisateur ouvre le formulaire de création de récompense, sélectionne la catégorie "Allostasie Daily" ou "Allostasie Weekly", entre le titre et la description, constate que le coût est forcé à 0 Gold et enregistre. L'item s'affiche dans la section d'Allostasie dédiée. Si l'utilisateur tente d'en créer un 4ème, le système rejette l'enregistrement.

**Acceptance Scenarios**:

1. **Given** un utilisateur connecté, **When** il crée une récompense avec le titre "25 min TV Show" et la catégorie "Allostasie Daily", **Then** l'item est créé avec un coût forcé de 0 Gold et s'affiche sous la section "Allostasie Daily" de la boutique.
2. **Given** un utilisateur ayant déjà 3 items d'Allostasie Daily, **When** il tente de créer un 4ème item dans cette même catégorie, **Then** le système retourne une erreur et refuse la création.
3. **Given** un item d'Allostasie existant, **When** l'utilisateur le modifie pour changer son titre, **Then** la mise à jour est enregistrée avec succès.

---

### User Story 2 - Validation/Rédemption des Items d'Allostasie (Priority: P1)

En tant qu'utilisateur, je veux pouvoir cocher/réclamer mes items d'Allostasie dans la boutique (web ou bot Telegram) au cours de la journée ou de la semaine sans dépenser d'Or.

**Why this priority**: Permet à l'utilisateur de valider concrètement qu'il a pris ce moment pour lui (ex: regarder sa série ou boire une bière), sans pénalité financière dans le RPG.

**Independent Test**: L'utilisateur clique sur le bouton "Réclamer / Valider" d'un item d'Allostasie disponible dans la boutique. L'état de l'item passe en "Réclamé", et le bouton d'action se désactive jusqu'au prochain reset (lendemain pour daily, début de semaine suivante pour weekly).

**Acceptance Scenarios**:

1. **Given** un item d'Allostasie Daily "25 min TV Show" non encore réclamé aujourd'hui, **When** l'utilisateur le valide, **Then** l'item est marqué comme complété pour aujourd'hui et son solde d'Or reste inchangé.
2. **Given** un item d'Allostasie Daily déjà réclamé aujourd'hui, **When** l'utilisateur tente de le réclamer à nouveau, **Then** l'opération est bloquée.
3. **Given** un item d'Allostasie Weekly "Prendre une bière le soir" réclamé ce jour, **When** le lendemain arrive, **Then** l'item reste marqué comme complété pour la semaine en cours et n'est pas réinitialisé avant le début de la semaine suivante (lundi matin).

---

### User Story 3 - Intégration dans le Bilan Journalier (Daily Recap) (Priority: P1)

En tant qu'utilisateur, je veux que mes items d'Allostasie réclamés durant la journée apparaissent clairement dans le bilan du soir de la guilde pour que je puisse suivre mes moments de décompression.

**Why this priority**: C'est la boucle de feedback essentielle mentionnée par l'utilisateur. Le bilan journalier compile le travail accompli (quêtes, primes) mais doit aussi valoriser la récupération équilibrée (allostasie).

**Independent Test**: Le script de bilan quotidien tourne à 21h30, collecte les items d'Allostasie réclamés aujourd'hui par l'utilisateur, et les affiche dans le rapport envoyé sur Telegram et sur le tableau de bord.

**Acceptance Scenarios**:

1. **Given** que l'utilisateur a validé "25 min TV Show" (Daily) et "Prendre une bière le soir" (Weekly) aujourd'hui, **When** le bilan quotidien est généré à 21h30, **Then** le message Telegram inclut une ligne : `🧠 Allostasie : 25 min TV Show ✅, Prendre une bière le soir ✅`.
2. **Given** que l'utilisateur n'a réclamé aucun item d'Allostasie aujourd'hui, **When** le bilan quotidien est généré, **Then** la section Allostasie n'affiche rien ou indique "Aucune".

---

## Edge Cases

- **Changement de catégorie d'une récompense existante** : Si l'utilisateur change une récompense standard en Allostasie, son coût en or doit être réinitialisé à 0 et la limite des 3 items doit être validée.
- **Fuseau horaire pour le reset daily/weekly** : Le reset journalier doit s'effectuer selon le fuseau horaire de l'utilisateur (défini dans la config, par exemple Europe/Paris ou America/New_York) à minuit pour le daily, et le lundi à minuit pour le weekly.
- **Suppression d'un item réclamé aujourd'hui** : Si un item d'Allostasie réclamé aujourd'hui est supprimé, il doit soit disparaître du recap, soit être ignoré sans causer d'erreur de base de données.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Le système MUST ajouter un champ `category` au modèle `Reward` (valeurs possibles : `regular`, `allostasis_daily`, `allostasis_weekly`). Par défaut, les récompenses existantes sont de catégorie `regular`.
- **FR-002**: Le système MUST ajouter un champ `last_purchased_at` (DateTime) au modèle `Reward` pour suivre la date de dernière rédemption/achat.
- **FR-003**: Le système MUST forcer le coût en or (`gold_cost`) à 0 pour toute récompense appartenant à `allostasis_daily` ou `allostasis_weekly`.
- **FR-004**: Lors de la création ou de la mise à jour d'une récompense, le système MUST vérifier que le nombre d'items actifs de catégorie `allostasis_daily` ne dépasse pas 3 par utilisateur, et de même pour `allostasis_weekly`.
- **FR-005**: Le système MUST déterminer si un item d'Allostasie est achetable/réclamable :
  - Un item `allostasis_daily` n'est plus réclamable si sa valeur de `last_purchased_at` correspond à la date locale d'aujourd'hui.
  - Un item `allostasis_weekly` n'est plus réclamable si sa valeur de `last_purchased_at` se situe dans la semaine en cours (du lundi 00h00 au dimanche 23h59 de la semaine en cours).
- **FR-006**: L'achat d'une récompense d'Allostasie MUST être gratuit (0 gold déduit) et mettre à jour le champ `last_purchased_at` à la date/heure actuelle.
- **FR-007**: Le bilan journalier (généré à 21h30 dans `publish_daily_recap`) MUST inclure la liste des titres des items d'Allostasie réclamés aujourd'hui (c'est-à-dire ceux dont `last_purchased_at` est égal à la date d'aujourd'hui).
- **FR-008**: L'interface Web de la boutique MUST être réorganisée pour présenter :
  - Une section distincte et premium pour les "Régulateurs d'Allostasie" avec les items Daily et Weekly (maximum 6 cartes au total).
  - Un bouton de validation/réclamation avec des états visuels clairs (disponible vs complété/déjà réclamé).
  - Une section "Récompenses Standards" pour les autres récompenses payantes.
- **FR-009**: Le formulaire de gestion des récompenses MUST inclure un sélecteur de catégorie. Si une catégorie d'Allostasie est choisie, le champ de saisie du coût en or doit être désactivé ou masqué et forcé à 0.
- **FR-010**: Le bot Telegram MUST supporter la réclamation des items d'Allostasie via la commande `/buy <id>` existante et afficher leur statut (réclamé ou disponible) dans la commande `/shop`.

### Key Entities *(include if feature involves data)*

- **Reward (Récompense)**: Modèle existant étendu :
  - `category` (String, non nul, par défaut "regular") : Type de la récompense (`regular`, `allostasis_daily`, `allostasis_weekly`).
  - `last_purchased_at` (DateTime, optionnel) : Date et heure du dernier achat ou de la dernière réclamation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: L'utilisateur ne peut jamais enregistrer plus de 3 items actifs dans chaque catégorie d'Allostasie (100% de validation d'intégrité).
- **SC-002**: L'affichage des sections d'Allostasie dans la boutique charge en moins de 100ms.
- **SC-003**: Le message de bilan journalier envoyé sur Telegram à 21h30 affiche correctement les items d'Allostasie validés aujourd'hui sans ralentir l'exécution du planificateur.
- **SC-004**: La réinitialisation journalière et hebdomadaire de la réclamation d'un item d'Allostasie fonctionne de manière prévisible selon le fuseau horaire configuré.

## Assumptions

- Les items d'Allostasie sont gérés par utilisateur (chaque aventurier a ses propres items d'Allostasie configurés).
- Le reset hebdomadaire se base sur le calendrier ISO (la semaine commence le lundi).
- Le fuseau horaire de l'application est configuré via la variable d'environnement `TIMEZONE` (par exemple Europe/Paris).
