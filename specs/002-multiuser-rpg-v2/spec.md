# Spécification Fonctionnelle — Multi-User & Progression Réelle (RPG V2) ⚔️🎯

Ce document spécifie les exigences fonctionnelles et techniques pour la **Phase 2 (V2)** réinventée du Habit RPG Accountability Tracker. L'objectif est de recentrer le système sur la progression réelle via des objectifs long terme et la discipline quotidienne, plutôt que sur des badges statiques.

---

## 🎯 Objectifs de la V2

1. **Progression par Objectifs & Graphe de Sous-étapes** : Remplacer l'arbre de talents statique par un système dynamique d'objectifs long terme découpés en sous-étapes interdépendantes (graphe orienté acyclique ou DAG).
2. **Économie de l'Or (Gold)** : Gagner de l'or personnalisé en accomplissant des sous-étapes et objectifs pour de futures récompenses.
3. **Statistiques Éphémères & Visualisation Quotidienne** : Les statistiques de la feuille de personnage retombent à 0 tous les matins pour refléter uniquement la discipline du jour.
4. **Calculateurs de "Perfect Day" Réalistes** : Visualiser la somme potentielle des statistiques par jour de la semaine pour paramétrer intelligemment les 4 templates de journées.
5. **Intégration Telegram Bot Enrichie** : Enregistrer les habitudes, changer de template et recevoir le bilan de fin de journée directement depuis le chat.

---

## 👥 1. Multi-User Scaling

### Spécification de la Base de Données
- Le bot Telegram intercepte le `username` et le `chat_id` de chaque personne écrivant un message.
- Si le `username` n'existe pas en base de données, le bot crée automatiquement un nouvel `User` dans la table SQLite.
- Les tables `HabitLog`, `DailyScore`, `Goal`, `SubStep`, et `Todo` sont partitionnées par `user_id`.

### Dashboard Sécurisé
- L'URL `/` sert de portail de sélection ou d'authentification par code/identifiant Telegram.
- Une fois authentifié, l'utilisateur accède à son tableau de bord privé (3 écrans).

---

## ⚔️ 2. Graphe d'Objectifs & Sous-étapes (Vision Long Terme)

Au lieu de badges ou compétences passives pré-calculés, l'utilisateur gère sa progression réelle :

### Structure en Graphe (DAG)
- **Objectifs (Goals)** : Buts majeurs à long terme (ex: *"Devenir millionnaire"*, *"Faire le tour du monde"*).
- **Sous-étapes (Sub-steps)** : Jalons intermédiaires nécessaires pour atteindre un objectif.
- **Multiniveau** : Une sous-étape peut elle-même posséder des sous-étapes enfants (ex: *Avoir de l'argent* ➔ sous-étape de *Avoir 500k* ➔ sous-étape de *Devenir millionnaire*).
- **Liaisons partagées** : Si une sous-étape est présente dans plusieurs objectifs (ex: *"Avoir une entrée d'argent stable"* lié à *Devenir millionnaire* et *Avoir des enfants*), **sa complétion est globale** (la cocher la valide instantanément partout).
- **Liaison aux Statistiques** : Chaque objectif et chaque sous-étape est lié à 1 ou plusieurs statistiques RPG (jusqu'à 12 maximum, ex: Force, Finance, Organisation, Connaissance) à des fins de catégorisation.

### Dépendances de Blocage (Option A - Strict)
- Une sous-étape peut déclarer une ou plusieurs autres sous-étapes comme "bloquantes" (dépendances requises).
- **Règle stricte** : Une sous-étape bloquée est affichée comme cadenassée dans l'interface et **ne peut pas être cochée/validée** par l'utilisateur tant que toutes ses étapes bloquantes ne sont pas validées.

### Validation Manuelle & Or (Gold)
- La validation des sous-étapes et objectifs est **exclusivement manuelle** par le user (pas de calcul automatique à partir des statistiques quotidiennes).
- Chaque sous-étape rapporte un montant d'**Or (Gold) personnalisé** défini par l'utilisateur lors de sa création. Cet or est accumulé de manière permanente sur le profil du joueur.

---

## 🧙‍♂️ 3. RPG Engine & Statistiques Éphémères

### Statistiques Éphémères (Daily Reset)
- Les statistiques quotidiennes accumulées via les habitudes et Todos **retombent strictement à 0 le lendemain matin** !
- Elles servent de tableau de bord d'efforts ("reps in") pour la journée en cours.
- Seul le calendrier de progression historique des 30 derniers jours conserve la trace de la qualité de la journée (Perfect Day, etc.). Le niveau global et l'XP de l'utilisateur sont également permanents.

### Formule d'XP Exponentielle
- **Perfect Day** : Réaliser un Perfect Day rapporte **5 XP** permanents.
- **Todos (Primes)** : Compléter un Todo rapporte des points de statistiques quotidiennes (max 2 statistiques différentes) et de l'**XP personnalisée** (définie à la création, max 40 XP par Todo).
- **Niveaux** : La progression vers le niveau suivant est exponentielle ($N+1 = 2N$). L'XP requise pour monter du niveau $L$ au niveau $L+1$ double à chaque niveau :
  $$XP_{requis}(L \rightarrow L+1) = 10 \times 2^{L-1}$$
  *(Niveau 1 ➔ 2 : 10 XP | Niveau 2 ➔ 3 : 20 XP | Niveau 3 ➔ 4 : 40 XP, etc.)*

---

## 📅 4. Le Grimoire du Jour Parfait (Active Templates & Paramétrages)

### Les 4 Templates de Journée
L'utilisateur définit ses objectifs en points de statistiques à atteindre pour valider un "Perfect Day" selon 4 templates :
1. **Semaine (Weekday)** : Calculé dynamiquement par défaut du lundi au vendredi.
2. **Weekend** : Calculé dynamiquement pour le samedi et le dimanche. Plus exigeant que la Semaine par défaut.
3. **Récupération (Recovery)** : Choisie manuellement par l'utilisateur en fin de journée (ex: targets de stats très basiques).
4. **Malade (Sick)** : Choisie manuellement en fin de journée (targets presque nulles).

### Paramétrage Intelligent des Templates
Dans l'écran de paramétrage :
- L'utilisateur voit toutes ses **Quêtes Actives (habitudes)** triées et regroupées par jour de la semaine.
- L'interface calcule dynamiquement la **somme totale des statistiques théoriques** réalisables chaque jour (ex: *Lundi : Force = 16pts, Mental = 3pts, etc.*).
- Grâce à cette somme, l'utilisateur peut paramétrer ses objectifs de Perfect Day (ex: fixer le seuil de Force à 16pts pour la semaine) de façon totalement réaliste et alignée.

---

## 🖥️ 5. Spécification des 3 Écrans de l'Interface

L'interface web se divise en 3 vues d'une clarté absolue :

### Écran 1 : Dashboard Principal (Main Screen)
- **Feuille de Personnage** : Niveau, jauge d'XP exponentielle dorée, solde d'Or (Gold) et les 12 barres de statistiques quotidiennes qui se réinitialisent tous les matins.
- **Quêtes Actives (Habitudes)** : Liste des quêtes à valider aujourd'hui.
- **Tableau des Primes (Todos)** : Liste des tâches ponctuelles avec récompenses en stats et XP personnalisés (max 40 XP).
- **Visualiseur du Grimoire** : Progression dynamique vers le Perfect Day du template actuel.
- **Calendrier de Progression** : Constellation des 30 derniers jours (Vert/Or pour Parfait, Rouge pour Manqué, etc.).
- **Bouton de Fin de Journée** : Permet de clore la journée et de sélectionner le template final (Récupération, Malade, ou laisser le calcul par défaut de la Semaine/Weekend).

### Écran 2 : Gestion des Objectifs (Goal Screen)
- **Créateur de Graphe** : Ajouter des objectifs majeurs et créer des sous-étapes multiniveaux avec :
  - Liens vers 1 ou plusieurs statistiques.
  - Dépendances de blocage (déclarer quelles sous-étapes bloquent cette étape).
  - Montant d'Or (Gold) personnalisé accordé à la complétion.
- **Visualisateur Graphique** : Rendu visuel clair de l'arbre et des connexions sous forme de nœuds (les nœuds bloqués affichent un cadenas 🔒).
- **Validation manuelle** : Cliquer pour cocher une étape accomplie et recevoir son Or. Les sous-étapes partagées se cochent automatiquement partout.

### Écran 3 : Paramètres des Perfect Days (Settings Screen)
- **Sommaire des Habitudes par Jour** : Tableau récapitulatif montrant la somme des points de statistiques potentiels par jour de la semaine en fonction des habitudes actives.
- **Configurateur de Templates** : Champs pour fixer les seuils statistiques exigés pour chacun des 4 templates (Semaine, Weekend, Récupération, Malade).
- **Gestionnaire d'Habitudes** : Ajouter, modifier ou supprimer des habitudes récurrentes et les jours de la semaine où elles sont programmées.

---

## 🤖 6. Commandes & Logique du Bot Telegram

Le bot Telegram est le compagnon quotidien fluide de l'utilisateur :

- `/log <habit_key> <valeur>` : Enregistre la complétion d'une habitude aujourd'hui (augmente les stats de la journée).
- `/template <nom>` : Permet de forcer manuellement le template de la journée courante (`recup` ou `malade`).
- `/status` : Affiche l'état actuel de la journée (les stats cumulées aujourd'hui par rapport aux exigences du template actif).
- **Bilan de fin de journée (Cron à 23h59 ou action manuelle)** : Le bot calcule si la journée est un "Perfect Day" selon le template final, attribue l'XP permanente (5 XP si parfait), réinitialise les stats de la feuille de personnage à 0 pour le lendemain, et envoie un récapitulatif détaillé et motivant du résultat dans le chat Telegram !
