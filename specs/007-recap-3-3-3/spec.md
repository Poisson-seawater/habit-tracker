# Feature Specification: 3-3-3 Recap Dashboard Panel

**Feature Branch**: `007-recap-3-3-3`

**Created**: 2026-06-12

**Status**: Draft

**Input**: User description: "en tant qu'user jai beaucoup de tache, skills a travailler et objectifs. Je ne veux pas me perdre dans la perfection et me rapeler c'est quoi les main main ! Donc dans la colonne de droite - main page - juste en haut de la feuille de personnage, jaimerai un 3 -3 -3 recap. premier 3 c'est les 3 mains goals, donc trois sous-étapes d'un objectif. Si je clique sur l'un des sous etapes, cela mamene a la page des objectifs dans sa categorie (et de la je la valide). ou bien le crayon pour changer de sous categorie. Meme chose pour le deuxieme 3, qui sont 3 sous-skills selectionner. le troicieme 3 c'est les 3 activités d'allostasie du jour (je peux les valider ici) et une fleche pour switch et voir les 3 allostasie de la semaine."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Affichage du 3-3-3 Recap (Priority: P1)

En tant qu'utilisateur, je veux voir un panneau récapitulatif "3-3-3" au-dessus de ma feuille de personnage sur la page principale pour garder mes priorités (3 objectifs majeurs, 3 compétences clés, 3 activités d'allostasie) sous les yeux à tout moment.

**Why this priority**: C'est le cœur de la demande. Le panneau doit regrouper de façon premium et condensée les 3 catégories clés de mon développement quotidien.

**Independent Test**: L'utilisateur accède au tableau de bord et voit un panneau de style glassmorphism intitulé "Recap 3-3-3" contenant trois listes de 3 items chacune : objectifs (sous-étapes), compétences, et activités d'allostasie.

**Acceptance Scenarios**:

1. **Given** un utilisateur connecté ayant configuré ses sélections, **When** il charge la page d'accueil, **Then** le panneau "Recap 3-3-3" s'affiche au-dessus de sa feuille de personnage.
2. **Given** un nouvel utilisateur sans aucun item épinglé ou configuré, **When** il charge la page d'accueil, **Then** le panneau s'affiche avec des indicateurs vides ou des invitations à épingler des items.

---

### User Story 2 - Sélection et Navigation des Objectifs Majeurs (Priority: P1)

En tant qu'utilisateur, je veux pouvoir choisir jusqu'à 3 sous-étapes d'objectifs actives à épingler comme "Objectifs Majeurs", et cliquer sur l'une d'elles pour être redirigé vers l'onglet Objectifs afin de la consulter ou la valider.

**Why this priority**: Permet une priorisation directe des sous-étapes et assure une navigation rapide pour éviter de se perdre dans l'interface.

**Independent Test**: L'utilisateur clique sur le crayon d'édition à côté des objectifs majeurs, coche jusqu'à 3 sous-étapes d'objectifs dans la liste des sous-étapes en cours, et valide. Le panneau affiche les sous-étapes sélectionnées. Il clique sur une sous-étape et l'application bascule automatiquement sur l'onglet "Objectifs" en affichant l'arbre de l'objectif correspondant et en mettant en surbrillance la sous-étape.

**Acceptance Scenarios**:

1. **Given** le panneau de recap affiché, **When** l'utilisateur clique sur le crayon d'édition de la section des objectifs, **Then** un modal s'ouvre, listant toutes les sous-étapes d'objectifs en cours de réalisation (non complétées).
2. **Given** la liste des sous-étapes dans le modal, **When** l'utilisateur en sélectionne 3 et enregistre, **Then** les 3 sous-étapes s'affichent dans la section "Objectifs Majeurs".
3. **Given** 3 sous-étapes épinglées, **When** l'utilisateur clique sur l'une d'elles, **Then** l'onglet change pour "Objectifs", l'objectif parent est sélectionné dans la liste latérale, l'arbre de quêtes est rendu, et la sous-étape ciblée est mise en valeur.

---

### User Story 3 - Sélection et Navigation des Compétences Clés (Priority: P1)

En tant qu'utilisateur, je veux pouvoir choisir jusqu'à 3 compétences (softskills) actives à épingler dans le récapitulatif, et cliquer sur l'une d'elles pour être redirigé vers l'arbre des compétences afin de voir son état.

**Why this priority**: Permet de focaliser l'attention sur 3 softskills prioritaires à travailler parmi toutes celles disponibles dans l'arbre.

**Independent Test**: L'utilisateur clique sur le crayon d'édition à côté des compétences clés, sélectionne jusqu'à 3 compétences non complétées dans le modal et enregistre. Les compétences s'affichent dans le récapitulatif. En cliquant sur l'une d'elles, l'application bascule sur l'onglet "Softskills" et centre/met en valeur cette compétence.

**Acceptance Scenarios**:

1. **Given** le panneau de recap affiché, **When** l'utilisateur clique sur le crayon de la section compétences, **Then** un modal s'ouvre avec la liste de toutes les compétences non complétées.
2. **Given** le modal ouvert, **When** l'utilisateur sélectionne 3 compétences et valide, **Then** ces compétences apparaissent dans le panneau de recap.
3. **Given** 3 compétences épinglées, **When** l'utilisateur clique sur l'une d'elles, **Then** l'onglet change pour "Softskills" et le nœud correspondant est mis en surbrillance dans l'arbre graphique.

---

### User Story 4 - Suivi et Validation Directe de l'Allostasie (Priority: P1)

En tant qu'utilisateur, je veux voir mes 3 activités d'allostasie daily et pouvoir les valider directement dans le panneau de recap, avec la possibilité de basculer pour voir et valider mes 3 activités d'allostasie weekly.

**Why this priority**: Offre un raccourci de validation indispensable pour la récupération sans forcer l'utilisateur à naviguer jusqu'à la boutique de récompenses.

**Independent Test**: L'utilisateur voit ses activités d'allostasie quotidienne dans le récapitulatif. Il clique sur le bouton de validation d'une activité non complétée. L'état passe immédiatement à "Validé" sans quitter la page principale et sans coût en or. Il clique sur la flèche de basculement : le panneau affiche désormais les activités d'allostasie hebdomadaire, qu'il peut également valider.

**Acceptance Scenarios**:

1. **Given** les activités d'allostasie daily affichées, **When** l'utilisateur clique sur le bouton de validation d'une activité, **Then** l'activité est validée (réclamée), son état visuel passe en complété, et les statistiques/scores de la journée sont mis à jour sans frais d'Or.
2. **Given** le panneau d'allostasie en mode Daily, **When** l'utilisateur clique sur l'icône de flèche de basculement, **Then** le widget affiche la liste des 3 activités d'allostasie hebdomadaire.
3. **Given** le panneau d'allostasie en mode Weekly, **When** l'utilisateur clique sur la flèche, **Then** le widget revient à la liste des activités d'allostasie quotidienne.

---

## Edge Cases

- **Sous-étape ou compétence complétée ailleurs** : Si une sous-étape ou une compétence épinglée est marquée comme complétée depuis sa page dédiée, elle doit automatiquement apparaître comme complétée dans le recap ou être désépinglée lors du prochain chargement pour laisser place à d'autres choix.
- **Moins de 3 items configurés/disponibles** : Si l'utilisateur n'a créé que 1 ou 2 items d'allostasie dans la boutique, ou s'il y a moins de 3 sous-étapes en cours de réalisation, le système doit afficher uniquement les items disponibles sans planter, et proposer un emplacement vide ou un raccourci de configuration.
- **Changement de template journalier** : Le panneau d'allostasie doit toujours refléter l'état de validation de la journée en cours, y compris si l'utilisateur change de template (ex: "week" à "recup").

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Le système MUST permettre d'enregistrer les préférences d'épinglage de l'utilisateur pour le recap 3-3-3 (jusqu'à 3 identifiants de sous-étapes d'objectifs et jusqu'à 3 clés de softskills).
- **FR-002**: Le modèle `User` ou un endpoint de profil dédié MUST stocker ces sélections d'épinglage dans la base de données pour assurer leur persistance.
- **FR-003**: L'API MUST exposer un endpoint (ex: `PUT /api/v1/profile/pins`) pour sauvegarder les listes d'identifiants de sous-étapes et de softskills épinglées.
- **FR-004**: L'API `GET /api/v1/profile` MUST inclure les listes d'items épinglés afin que le frontend puisse les restituer au chargement.
- **FR-005**: Le widget 3-3-3 recap MUST être inséré dans la colonne de gauche (Dashboard Tab) juste au-dessus de la feuille de personnage (`stats-panel`).
- **FR-006**: Le frontend MUST proposer une interaction (bouton crayon) ouvrant un modal de sélection pour les sous-étapes d'objectifs et un modal de sélection pour les softskills.
- **FR-007**: Les sélections d'allostasie dans le recap MUST charger directement les récompenses de catégorie `allostasis_daily` (pour le mode quotidien) ou `allostasis_weekly` (pour le mode hebdomadaire) configurées par l'utilisateur dans la boutique de récompenses.
- **FR-008**: Le bouton de validation des activités d'allostasie dans le recap MUST appeler l'API de rédemption existante (`POST /api/v1/rewards/{reward_id}/purchase`) et mettre à jour immédiatement les scores et statistiques globaux de la page sans recharger.
- **FR-009**: Le clic sur une sous-étape d'objectif dans le recap MUST rediriger vers l'onglet "Objectifs", charger l'arbre de l'objectif correspondant et faire défiler l'écran vers le nœud ciblé tout en le mettant en surbrillance temporaire.
- **FR-010**: Le clic sur une compétence dans le recap MUST rediriger vers l'onglet "Softskills" et centrer ou mettre en valeur le nœud hexagonal de la compétence ciblée.

### Key Entities

- **User (Aventurier)** : Entité centrale, étendue avec les attributs de préférences d'épinglage (ex: `pinned_substeps` sous forme de liste d'identifiants d'étapes et `pinned_softskills` sous forme de liste de clés de softskills).
- **SubStep (Sous-étape)** : Étape d'un objectif à long terme. Possède un identifiant unique, un statut de complétion, et un lien vers son objectif parent.
- **Softskill (Compétence)** : Nœud de l'arbre des compétences personnelles. Possède un identifiant de chaîne unique et un statut de complétion.
- **Reward (Récompense d'Allostasie)** : Item de récupération gratuit de catégorie `allostasis_daily` ou `allostasis_weekly`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: La sélection des items épinglés est enregistrée en base de données et persiste lors du rechargement de la page (100% de persistance).
- **SC-002**: Le passage d'un onglet à un autre et le ciblage/mise en valeur d'une étape ou compétence après clic dans le recap s'effectue en moins de 150ms.
- **SC-003**: Le temps de réponse lors de la validation d'une activité d'allostasie depuis le recap est inférieur à 100ms et rafraîchit les statistiques de la journée en temps réel.
- **SC-004**: L'interface s'adapte de manière responsive aux écrans étroits en empilant le récapitulatif au-dessus de la feuille de personnage sans briser le style général.

## Assumptions

- Les sous-étapes et les compétences épinglées appartiennent à l'utilisateur connecté identifié par le header `X-User-ID`.
- Les activités d'allostasie affichées sont celles qui ont déjà été créées et activées dans la boutique de récompenses.
- Si un item épinglé est supprimé de la base de données, le backend l'ignore ou filtre automatiquement la sélection pour éviter tout blocage.
