# Spécification Fonctionnelle — Multi-User & RPG Engine V2 ⚔️🧙‍♂️

Ce document spécifie les exigences fonctionnelles et techniques pour la **Phase 2 (V2)** du Habit RPG Accountability Tracker. 

---

## 🎯 Objectifs de la V2

1. **Multi-User Scaling** : Permettre à plusieurs aventuriers de rejoindre le bot Telegram simultanément et de consulter leurs dashboards personnels sécurisés.
2. **RPG Engine & XP** : Remplacer le système statique par un vrai gain d'XP dynamique avec formules de montée de niveau, et stockage persistant.
3. **Arbre de Compétences Interactif (Skill Tree)** : Débloquer les 4 compétences de l'arbre grâce à des points de talent gagnés à chaque montée de niveau.
4. **Système de Badges & Succès** : Débloquer des distinctions visuelles (ex : "Discipline d'Acier" pour un streak de 10 jours) affichées fièrement sur le profil.

---

## 👥 1. Multi-User Scaling

### Spécification de la Base de Données
- Le bot Telegram intercepte le `username` et le `chat_id` de chaque personne écrivant un message.
- Si le `username` n'existe pas en base de données, le bot crée automatiquement un nouvel `User` dans la table SQLite.
- Les tables `HabitLog`, `DailyScore` et `Streak` sont partitionnées par `user_id`.

### Dashboard Sécurisé
- L'URL `/` sert de portail de sélection ou d'authentification par code/identifiant Telegram.
- Une fois authentifié, l'utilisateur accède à sa feuille de personnage privée.

---

## 🧙‍♂️ 2. RPG Engine & XP Formula

### Formule d'XP
- Chaque point de statistique RPG (Force, Discipline, etc.) gagné lors de la complétion d'une quête accorde également de l'**XP**.
- **Formule de montée de niveau** :
  $$XP\_requis = \lfloor (Niveau)^{1.8} \times 100 \rfloor$$
- **Niveau 1** : 0 à 100 XP
- **Niveau 2** : 100 à 282 XP (Besoin de 182 XP supplémentaires)
- **Niveau 3** : 282 à 520 XP (Besoin de 238 XP supplémentaires)

### Progression en direct
- L'XP actuel et la barre de progression vers le prochain niveau sont renvoyés par `GET /profile` et dessinés avec des animations HSL dorées sous l'avatar.

---

## 🌲 3. Arbre de Compétences Interactif (Skill Tree)

À chaque montée de niveau, l'utilisateur gagne **1 Point de Talent**. 
Il peut cliquer sur les compétences de l'arbre du dashboard pour les débloquer :

1. **Focus Infini** 🛡️ (Requiert Niveau 2, Coûte 1 Point) : Accorde un bonus passif de +15% sur tous les gains de points de la statistique *Discipline*.
2. **Volonté d'Acier** 🔮 (Requiert Niveau 3, Coûte 1 Point) : Si l'utilisateur skip une habitude autorisée, la pénalité de streak est réduite de 50%.
3. **Savoir Ancestral** 📚 (Requiert Niveau 5, Coûte 2 Points) : Double les gains de points de *Connaissance* lors des lectures effectuées le week-end.
4. **Omniscience** 👑 (Requiert Niveau 8, Coûte 3 Points, requiert Focus Infini) : Double le cap journalier (`daily_cap`) de toutes les habitudes.

---

## 🎖️ 4. Système de Badges & Succès

Les badges sont débloqués automatiquement à minuit lors du calcul des scores ou en direct lors des logs :

- **Discipline d'Acier** 🛡️ : Avoir complété la quête `routine_matin` pendant 10 jours consécutifs.
- **Rat de Bibliothèque** 📖 : Avoir accumulé un total historique de 500 minutes de lecture.
- **Zen Master** 🧘‍♂️ : Avoir complété l'habitude `meditation` 15 fois dans le mois.
- **Survivant** 🩹 : Avoir validé une journée en template "Malade" ou "Récupération".

---

## 🧪 Scénarios d'Acceptation (UAT)

### Scénario 1 : Découverte & Création de Compte Bot
- **Étant donné** un nouvel utilisateur Telegram "@Jeanne" écrivant `/status` pour la première fois.
- **Quand** le listener intercepte le message.
- **Alors** Jeanne est enregistrée automatiquement comme aventurière de Niveau 1, et reçoit un message de bienvenue avec son profil vierge.

### Scénario 2 : Montée de Niveau & Attribution de XP
- **Étant donné** Gabriel ayant 95 XP de Niveau 1.
- **Quand** il logue une habitude rapportant 10 XP.
- **Alors** son total d'XP passe à 105, son niveau passe instantanément à **Level 2**, il reçoit une alerte animée sur le dashboard, et son compteur de points de talent passe à **1**.

### Scénario 3 : Achat d'une Compétence
- **Étant donné** Gabriel ayant 1 Point de Talent de niveau 2.
- **Quand** il clique sur "Focus Infini 🛡️" dans l'arbre de talents et valide.
- **Alors** le serveur API déduit son point de talent, enregistre la compétence débloquée, et les quêtes futures de Discipline appliquent le multiplicateur de +15% en base de données.

---

## 📅 5. Planification Hebdomadaire des Quêtes (Dailies Scheduling)

Pour s'assurer que les quêtes s'adaptent au rythme réel de l'utilisateur :
- Lors de la création d'une quête (via le dashboard ou le bot), l'utilisateur peut choisir d'activer la quête soit **"Tous les jours"**, soit pour des **"Jours spécifiques"** de la semaine.
- **Jours spécifiques** : L'utilisateur coche les jours souhaités (L, M, M, J, V, S, D).
- Le backend stocke cette planification dans le champ `scheduled_days` (représenté par des index de jours `0` à `6` séparés par des virgules).
- Si un jour donné n'est pas planifié pour une quête, celle-ci n'apparaît pas dans la liste des tâches actives du jour, n'affecte pas le calcul du score quotidien, et ne brise pas le streak de l'utilisateur.

---

## 📜 6. Le Tableau des Primes (Todos) & Le Grimoire du Jour Parfait

### Le Tableau des Primes (Todos)
- Les Todos sont des quêtes uniques (non récurrentes) destinées à accomplir des tâches ponctuelles importantes.
- **Zéro pénalité** : Les Todos n'ont pas de pénalité en cas d'inactivité, restant purement positifs et gratifiants.
- **Leveling & XP** : Compléter un Todo rapporte immédiatement de l'XP substantiel et des points pour une statistique RPG choisie, aidant directement l'utilisateur à monter de niveau.
- **Synergie Jour Parfait** : Les points de statistiques gagnés en complétant un Todo s'ajoutent aux statistiques accumulées de la journée. Ils comptent donc pour valider les seuils requis du jour !

### Le Grimoire du Jour Parfait (Active Templates Pathfinder)
Le **Grimoire du Jour Parfait** est un widget central qui affiche en clair les exigences du jour basées sur le template actif :
- **Adaptabilité** : Il traduit dynamiquement le template actuel (Semaine, Weekend, Récupération, Malade) en objectifs clairs (ex: *"Repos : 2 / 5 points requis pour une journée parfaite"*).
- **Visuel interactif** : Des indicateurs lumineux et des barres d'objectifs spécifiques guident l'aventurier tout au long de la journée.
- **Calendrier Synchrone** : Dès que les objectifs du Grimoire du jour sont validés (Acceptable ou Parfait), le statut de la journée est mis à jour et se répercute instantanément dans le **Calendrier de Progression 30 Jours** sous forme de sphère allumée (Vert/Or pour Parfait, Cyan pour Acceptable).

