# Boutique de Récompenses & Allostasie

La Boutique de Récompenses est le lieu où tu dépenses ton [Or](#/stats-xp-niveau-or) durement accumulé pour t'accorder de vraies récompenses, tout en intégrant des activités de récupération saine grâce aux catégories d'Allostasie.

## 1. Récompenses Classiques

Les récompenses classiques te permettent de lier tes efforts à des plaisirs concrets (ex : s'acheter un jeu vidéo, s'offrir un resto). Elles possèdent un coût en Or et peuvent être verrouillées par des prérequis :

- **Coût en Or** : Soustrait directement de ta cagnotte d'Or globale lors de l'achat.
- **Prérequis Softskill** : La récompense reste verrouillée tant que le [softskill](#/softskills) associé dans ton arbre de compétences n'est pas validé.
- **Prérequis Objectif** : La récompense reste verrouillée tant que l'[objectif](#/objectifs) long terme choisi n'est pas complété.
- **Achat unique (One-Time)** : Si coché, l'item ne peut être acheté qu'une seule fois dans la vie du compte. Sinon, il peut être acheté de manière répétée.

## 2. Catégories d'Allostasie (Récupération)

L'Allostasie désigne la capacité d'un organisme à maintenir sa stabilité par le changement. Dans le Habit Tracker, elle représente tes activités de décompression et de bien-être (ex : regarder un épisode de série, boire une bière entre amis).

Ces récompenses ont des règles très spécifiques :

| Règle / Propriété | Allostasie Daily (Quotidienne) | Allostasie Weekly (Hebdomadaire) |
|---|---|---|
| **Coût en Or** | Gratuit (Forcé à 0 Or) | Gratuit (Forcé à 0 Or) |
| **Nombre maximum d'items** | Maximum 3 par utilisateur | Maximum 3 par utilisateur |
| **Fréquence de reset** | Chaque jour à minuit (heure locale) | Chaque lundi à minuit (heure locale) |
| **Bilan journalier** | Affiché dans le recap Telegram du soir | Affiché dans le recap Telegram du soir (le jour de validation) |

Ces activités sont aussi accessibles directement depuis le panneau [Recap 3-3-3](#/recap-3-3-3) sur la page d'accueil — tu peux les valider sans naviguer jusqu'à la boutique.

## 3. Commandes Telegram du Bot

Tu peux afficher la boutique et réclamer tes récompenses directement depuis Telegram :

- `/shop` : Affiche toutes les récompenses. Les catégories d'Allostasie y sont listées en premier avec des indicateurs d'état :
  - `[✓ Validé]` : Déjà réclamé pour la période en cours.
  - `[🔄 A valider]` : Disponible à la validation.
- `/shop dispos` : Filtre la boutique pour n'afficher que les items disponibles à l'achat ou à la rédemption.
- `/shop verrouillees` : Affiche uniquement les items verrouillés par des prérequis de softskills ou d'objectifs non atteints.
- `/buy [nom]` : Permet d'acheter ou réclamer un item par son titre (ou une portion unique du titre).
