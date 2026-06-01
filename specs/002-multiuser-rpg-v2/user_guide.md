# Guide de l'Aventurier - Habit Tracker RPG V2 (Progression Réelle) 🎮🎯

Bienvenue dans votre guide d'utilisation de l'Habit Tracker RPG V2. Ce document vous explique comment structurer vos objectifs de vie à long terme tout en maintenant une discipline quotidienne implacable grâce au concept des **Jours Parfaits**.

---

## 🔮 Le Concept : Vision Long Terme ➔ Focus Quotidien

Pour progresser réellement, le jeu se divise en deux aspects complémentaires :

1. **La Vision Long Terme (Graphe d'Objectifs)** :
   Vous définissez vos rêves et objectifs majeurs (ex: *Devenir millionnaire*, *Faire le tour du monde*). Vous les découpez en **sous-étapes** interconnectées (certaines se font en parallèle, d'autres sont bloquantes, d'autres sont partagées entre plusieurs objectifs). 
   Valider manuellement ces étapes vous fait gagner de l'**Or (Gold)** personnalisé !
   
2. **Le Focus Quotidien (Les Statistiques Éphémères)** :
   Chaque matin, vos statistiques de vie (Force, Discipline, Connaissance, etc.) retombent à **0**. La journée est une page blanche ! 
   Vos habitudes quotidiennes et vos Todos (Primes) du jour augmentent vos statistiques. L'objectif est de valider les seuils définis dans votre **Template de Perfect Day** pour remporter les **5 XP** précieux de la journée et monter de niveau permanent.

---

## 📖 Dictionnaire des Termes RPG

*   **Feuille de personnage (Character Sheet)** : Tableau de bord affichant vos statistiques personnelles réparties sur 12 dimensions (Force, Finance, Organisation, Connaissance, etc.). Ces barres de progression représentent votre investissement du jour et reviennent à 0 chaque matin.
*   **Or (Gold)** : La monnaie accumulée de manière permanente sur votre profil en accomplissant vos sous-étapes et objectifs.
*   **Niveau & XP exponentiels** : Votre indicateur global de régularité. Réaliser un Perfect Day vous octroie **5 XP**. Chaque niveau est deux fois plus dur que le précédent à atteindre ($N+1 = 2N$ XP requis).
*   **Quêtes Actives (Habitudes)** : Les actions régulières que vous devez faire selon les jours de la semaine (ex: sport le lundi et mercredi, lecture tous les jours). Elles augmentent vos statistiques quotidiennes.
*   **Tableau des Primes (Todos)** : Vos tâches uniques du jour. Les accomplir vous récompense en statistiques pour la journée ET en XP direct et personnalisé (jusqu'à 40 XP maximum par Todo).
*   **Grimoire du Jour Parfait** : Votre boussole de la journée. Il calcule en temps réel la différence entre vos scores actuels et les exigences de votre template actif pour vous indiquer quoi faire pour sécuriser votre journée.

---

## 🖥️ Exploration des 3 Écrans du Dashboard

### 1. Écran Principal (Main Screen) : Votre Quotidien
*   **À quoi sert-il ?** C'est l'écran par défaut que vous visitez plusieurs fois par jour.
*   **Ce qu'il affiche** :
    *   Votre profil de héros (Nom, Niveau, Jauge d'XP dorée, Solde d'Or permanent).
    *   La feuille de personnage éphémère (les 12 stats à 0 chaque matin, grimpant au fil de la journée).
    *   Vos Quêtes Actives (Habitudes) à valider aujourd'hui.
    *   Le Tableau des Primes (Todos) à cocher.
    *   Le widget du **Grimoire du Jour Parfait** montrant la progression de vos points actuels par rapport aux objectifs fixés.
    *   Le Calendrier des 30 derniers jours (les constellations de billes colorées résumant vos succès passés).
    *   Le bouton **"Terminer la Journée"** pour figer votre score final et déclarer si c'était une journée normale, de récupération ou de maladie.

### 2. Écran des Objectifs (Goal Screen) : Vos Rêves à Long Terme
*   **À quoi sert-il ?** Planifier vos grands projets de vie et suivre leur réalisation.
*   **Ce qu'il affiche** :
    *   Un **créateur graphique d'objectifs** où vous dessinez votre graphe de sous-étapes multiniveaux.
    *   L'indication claire des dépendances : les sous-étapes cadenassées (🔒) que vous ne pouvez pas cocher tant que leurs étapes bloquantes ne sont pas validées.
    *   La validation manuelle des jalons : cliquez sur une sous-étape résolue pour la valider. Si elle est partagée avec un autre objectif, elle se validera instantanément là-bas aussi !
    *   L'attribution de votre or personnalisé.

### 3. Paramètres des Perfect Days (Settings Screen) : Votre Stratégie
*   **À quoi sert-il ?** Paramétrer de manière ultra-réaliste les exigences de vos journées idéales.
*   **Ce qu'il affiche** :
    *   Un tableau sommant automatiquement la totalité des points de statistiques potentiels que vous pouvez obtenir chaque jour de la semaine en effectuant toutes vos habitudes actives.
    *   Les 4 formulaires pour configurer vos exigences de statistiques cibles pour les templates **Semaine (lundi-vendredi)**, **Weekend (samedi-dimanche)**, **Récupération** (journée tranquille), et **Malade** (repos total).
    *   L'éditeur de vos Quêtes Actives (Habitudes) récurrentes avec planification hebdomadaire.

---

## 🤖 Guide Rapide du Compagnon Telegram

Le bot Telegram est votre allié mobile ultra-rapide pour valider votre journée sans ouvrir le navigateur :

*   **Logguer une habitude** : Envoyez `/log <habit_key> <valeur>` (ex: `/log lecture 15` pour ajouter 15 minutes de lecture ou `/log sport 1` pour votre séance). Vos barres de statistiques du jour grimpent instantanément sur le tableau de bord web.
*   **Changer de template** : Envie d'une journée calme ? Envoyez `/template recup` ou `/template malade` pour ajuster instantanément vos seuils de Perfect Day.
*   **Voir son statut** : Envoyez `/status` pour voir vos points cumulés du jour et ce qu'il vous reste à faire pour décrocher le Perfect Day.
*   **Rapport de fin de journée** : À 23h59 (ou lors de la clotûre), le bot fige vos scores, calcule si vous avez atteint votre Perfect Day, attribue les **5 XP**, fait monter votre niveau si nécessaire, réinitialise la feuille de personnage à 0 pour le lendemain, et vous envoie un bilan final complet et inspirant dans votre chat !
