# Habit RPG Tracker

Habit tracker auto-hébergé façon RPG + système de responsabilité, tournant sur un **Raspberry Pi 5**. Un bot Telegram et un dashboard web analytique partagent une même base **SQLite** locale et rapide.


## 🎯 Vision & Philosophie

### Pourquoi ce projet existe

Un habit tracker auto-hébergé, façon RPG, construit pour notre usage perso afin de se tenir mutuellement responsables de nos habitudes quotidiennes, avec un système de points, de stats, de streaks et de « journées parfaites ». Le pilotage se fait soit par le **bot Telegram**, les **skills LLM** ou le **dashboard web**.

L'idée de base : transformer la discipline quotidienne en jeu (XP, niveaux, or, quêtes) pour que tenir ses habitudes soit motivant plutôt que pénible.

### Définir le succès d'une quête

Une quête doit pouvoir expliquer ce qui compte comme un succès. Le titre seul ne
suffit pas toujours : une quête comme « tâche hustle », « admin » ou « avancer
projet » ne dit pas quoi faire concrètement, ni à quel moment la validation est
méritée.

Besoin produit à garder en tête : ajouter un mécanisme léger de mini-note ou de
post-it attaché à une quête, ou à son occurrence du jour. Cette note servirait à
préciser l'intention du jour, le résultat attendu, le seuil minimum acceptable ou
les critères de validation, sans transformer chaque quête en grosse fiche de
projet.

Exemples :
- « tâche hustle » -> « envoyer 3 messages de prospection ou finaliser 1
  follow-up client ».
- « sport » -> « 20 minutes minimum, même si l'intensité est faible ».
- « deep work » -> « 90 minutes sans distraction sur la landing page ».

### Public cible

- Amis et réseau proche.
- Usage **quotidien** : logger ses habitudes, voir son statut du jour, suivre ses streaks.
- Non développeurs.

### Ce que le projet N'EST PAS

- **Pas un SaaS.** 
- **Pas une plateforme générique.** Tout est personnalisé pour nos besoins.

### Non-goals explicites

- Pas de scaling horizontal, de microservices, de Kubernetes.
- Pas de mobile natif — le bot Telegram couvre les usages mobiles simples, et le
  dashboard web reste l'interface complète.
- Pas d'optimisation pour des milliers d'utilisateurs : on optimise pour la **RAM du Pi**, pas pour la charge.

### Améliorations livrées en juillet 2026

Le cadrage détaillé et son statut sont conservés dans [`specs/next-steps-multi-agent-brief.md`](specs/next-steps-multi-agent-brief.md). Il couvre le filtrage des quêtes par type de journée, les habitudes ratées et leur pénalité XP, la correction d'hier, les suggestions de créneaux biologiques, la durée d'authentification de 90 jours et le retrait du champ d'effort des sous-étapes.


## NEXT ACTIONS

### 1. Revoir Cloudflare Access : arrêter la reconnexion quotidienne

Constat : l'authentification interne du Habit Tracker est déjà pensée pour des
sessions et appareils approuvés de 90 jours (`AUTH_SESSION_DAYS` et
`AUTH_DEVICE_DAYS`), mais Cloudflare Access redemande encore un code tous les
jours sur les mêmes téléphone et ordinateur.

Objectif produit : sur un appareil et un navigateur déjà connus, Cloudflare doit
se souvenir de la session environ 3 mois. Le code ne devrait réapparaître qu'en
cas d'expiration 90 jours, nouveau navigateur/appareil, révocation, nettoyage des
cookies ou changement volontaire de politique de sécurité.

À cadrer :
- vérifier la durée de session côté Cloudflare Access pour l'application Habit
  Tracker, et la distinguer de la durée des cookies internes de l'app ;
- vérifier si une policy Cloudflare, un fournisseur d'identité, une option MFA ou
  un paramètre navigateur force une reconnexion quotidienne ;
- documenter le réglage cible : même téléphone/ordinateur reconnus pendant 90
  jours, sans affaiblir le bootstrap admin ni l'accès machine `HABIT_API_TOKEN`.

### 2. Penser un système habits / No-Todo / réflexes de remplacement

Besoin : le modèle actuel couvre déjà des quêtes positives et des No-Todo
négatifs, mais il manque un cadre explicite pour travailler les réflexes :
déclencheur -> besoin réel -> mauvais réflexe -> réflexe de remplacement ->
preuve minimale de réussite.

Idée à explorer :
- `Habit` : action positive à installer ou maintenir ;
- `No-Todo` : mauvais réflexe à éviter ou à déclarer quand il arrive ;
- `Réflexe de remplacement` : action courte liée à un déclencheur précis, pensée
  comme alternative au mauvais réflexe plutôt que comme simple tâche de plus.

Exemples de cadrage :
- café : clarifier le besoin réel avant de scorer. Est-ce pour se réveiller,
  retrouver du focus, prendre une pause, ou éviter de méditer/bouger ? Selon la
  réponse, le café peut être une stratégie contrôlée, un excès à limiter ou un
  signal vers une action de remplacement ;
- stress -> scroll : le No-Todo est le scroll réflexe, mais le système devrait
  proposer une alternative concrète comme 10 minutes de ménage, respiration,
  marche courte ou méditation ;
- ménage : ne pas le traiter seulement comme une corvée, mais parfois comme un
  réflexe de régulation du stress.

Prochaine étape de réflexion : concevoir une fiche légère par réflexe avec ces
champs possibles : déclencheur, besoin, mauvais réflexe, coût du mauvais réflexe,
réflexe de remplacement, durée minimale, preuve de réussite, règle de scoring,
et lien éventuel avec un No-Todo existant.

### 3. Débugger le système d'archives

Constat : le système d'archives est à considérer comme cassé tant qu'il n'est pas
revalidé bout en bout. Une quête archivée ne doit plus réapparaître dans
l'agenda, les quêtes à placer, les placements datés, les placements par défaut
des templates, ni les vues qui ne demandent pas explicitement les archives.

À investiguer :
- reproduire le bug depuis le dashboard avec une quête archivée qui reste visible
  ou qui revient dans le calendrier ;
- vérifier si le problème vient du backend, du frontend, de la banque de quêtes,
  du compactage des versions, ou de vieux placements encore présents en base ;
- confirmer le comportement attendu : archiver retire les références d'agenda,
  désarchiver ne restaure pas automatiquement les anciens placements.

### 4. Penser un système de simple compteur relié aux skills et objectifs

Besoin : certaines progressions ne sont pas de bonnes quêtes binaires. Il faut
parfois seulement compter des répétitions, des essais ou des unités utiles, sans
forcer une logique "fait/pas fait" trop lourde.

Exemples :
- nombre de reps de visualisation pour le social training ;
- nombre de bons pomodoros ;
- nombre de cold calls ;
- nombre d'expositions, de pratiques, de tentatives ou de répétitions liées à
  une compétence précise.

Image produit : une jar qui se remplit. Chaque unité ajoutée rend la progression
visible et concrète, même si aucune récompense majeure n'est déclenchée à chaque
fois. Le compteur peut servir à voir l'accumulation d'effort, motiver la
répétition et éviter que les petites reps disparaissent dans le système.

À cadrer :
- définir si le compteur est autonome, attaché à une quête, attaché à une
  softskill, ou attaché à un objectif ;
- permettre plusieurs types d'unités simples : reps, pomodoros, appels, essais,
  minutes, sessions ;
- prévoir des jalons lisibles, par exemple jar 25/100, série de 10 bons
  pomodoros, 50 cold calls, 30 visualisations ;
- relier les compteurs aux skills et objectifs définis pour que les reps
  nourrissent une progression plus grande au lieu d'être seulement des chiffres
  isolés.

### 5. Mettre en place la matrice d'Eisenhower

Besoin : aider à choisir quoi faire maintenant quand les quêtes, objectifs,
to-do et urgences se mélangent. Le système devrait distinguer clairement
l'important de l'urgent pour éviter que les tâches bruyantes prennent toute la
place dans l'agenda.

Idée produit : ajouter une vue 2x2 de type matrice d'Eisenhower :
- urgent + important : à faire en priorité, potentiellement visible dans
  l'agenda du jour ;
- important + non urgent : à planifier volontairement avant que ça devienne une
  urgence ;
- urgent + non important : à déléguer, réduire ou transformer en tâche courte ;
- non urgent + non important : à supprimer, archiver ou laisser hors focus.

À cadrer :
- décider si la matrice classe uniquement les to-do, ou aussi les quêtes,
  sous-étapes d'objectifs et réflexes de remplacement ;
- définir les champs nécessaires sans alourdir la création : importance, urgence,
  échéance, impact objectif/skill, énergie requise ;
- prévoir une interaction rapide depuis le dashboard pour déplacer un item entre
  les quadrants ;
- relier la matrice au Perfect Day : les items importants non urgents doivent
  pouvoir être planifiés dans les zones biologiques adaptées au lieu d'être
  oubliés.


## ROADMAP
- avec IA ou UX pour voir les quest archiver et les quest avec le meme nom
- a réfléchir, voir si je garde le systeme les 3 objectifs et competence créer une habitude OU je relie une quest a l'un des 3objectifs. et ses 3 objectifs deviennent une forme de tag ? pareil pour lier des to do a ses tags ET je peux mettre sa dans la matrix de einsenhower. exemple corps heal peut prendre tendon, natation, course et velo.
- Maybe / à réfléchir : version professionnelle de l'app pour partager des to-do provenant d'une compagnie. Ces to-do professionnels auraient aussi leur propre agenda spécifique, via la feature de quêtes, et leur propre Google Calendar spécifique. Exemples : quand un cx book un meeting, la to-do professionnelle reçoit automatiquement le meeting à la bonne heure ; quand j'assigne une tâche à un employé, l'employé reçoit automatiquement une to-do professionnelle avec une due date et une do date.



## 👥 Collaboration & développement

Projet perso. Avant de contribuer, lire :

- 🎯 **[Vision & Philosophie](#-vision--philosophie)** — pourquoi ce projet existe, qui il vise, ce qu'il n'est pas (section ci-dessus).
- 🤖 **[CLAUDE.md](./CLAUDE.md)** — conventions et règles pour Claude Code / agents (symlink vers `AGENTS.md`).
- 🌿 **[CONTRIBUTING.md](./CONTRIBUTING.md)** — branches, PRs, format des commits.
 
On travaille par branches `feat/...` → PR vers `dev` → PR vers `main`, 1 review minimum.

---

## 🛠️ Stack (résumé)

- **Backend** : FastAPI + SQLAlchemy 2.0 + Uvicorn, `python-telegram-bot`, APScheduler, PyTest.
- **Frontend** : Vanilla HTML5 / CSS3 / JS ES6, sans framework ni build, servi en statique.
- **Données & déploiement** : SQLite unique ; Docker Compose (`api` + `bot`) sur Pi 5, limites RAM 40 / 35 Mo.

Détails et choix d'architecture → [CLAUDE.md](./CLAUDE.md) et [`specs/001-habit-tracker-bot/plan.md`](./specs/001-habit-tracker-bot/plan.md).

Télécommande IA sans MCP :
[fonctionnement du plugin](./docs/notes/habit-tracker-control-plugin.md),
[migration SQLite v9](./docs/notes/database-v9-remote-operations.md) et
[décision d'architecture](./docs/adr/002-plugin-habit-tracker-control.md).

- Plugin (recommandé) : [`plugins/habit-tracker-control/`](./plugins/habit-tracker-control/)
  — CLI `scripts/habitctl.py` + skills `query`/`action`/`manage`.
- Skill globale (ancienne, hors dépôt) : `~/.claude/skills/habit-tracker/SKILL.md`
  — parle à l'API en `curl` direct, sans passer par le CLI du plugin.

---

## 🚀 Setup local (≤ 5 commandes)

```bash
git clone <url-du-repo> habit-tracker
cd habit-tracker
cp .env.example .env          # puis remplir les valeurs Telegram
uv venv && source .venv/bin/activate && uv pip install -r backend/requirements.txt
PYTHONPATH=backend python3 backend/src/main.py   # dashboard → http://localhost:5000
```

Le serveur initialise les tables, lance les seeders de démarrage, monte le frontend statique
et sert le dashboard sur [http://localhost:5000](http://localhost:5000).

Le bot Telegram (optionnel en local) se lance à part :

```bash
PYTHONPATH=backend python3 backend/src/bot/listener.py
```

Les tests :

```bash
PYTHONPATH=backend .venv/bin/pytest backend/tests
```

---

## 🔑 Variables d'environnement

À mettre dans `.env` à la racine (copier depuis `.env.example`) :

| Variable | Exemple | Rôle |
|----------|---------|------|
| `TELEGRAM_BOT_TOKEN` | `123456:ABC-DEF...` | Token du bot (BotFather). |
| `TELEGRAM_GROUP_ID` | `-1003912636269` | ID du groupe Telegram autorisé. |
| `API_PORT` | `5000` | Port d'écoute de l'API / dashboard. |
| `ENV` | `development` | `development` en local, `production` sur le Pi. |
| `TIMEZONE` | `America/Toronto` | Fuseau pour les scores du jour et les rappels. |
| `DATABASE_URL` | `sqlite:////data/habit_tracker.db` | Chemin SQLite. À laisser vide en local : fallback auto vers `backend/data/`. |
| `AUTH_BOOTSTRAP_CODE` | `long-code-secret` | Code temporaire requis pour créer le premier mot de passe admin et approuver le premier appareil. |
| `HABIT_API_TOKEN` | `long-api-token` | Token machine pour le plugin `habit-tracker-control` et les appels API non navigateur. |
| `AUTH_SESSION_DAYS` | `90` | Durée des sessions web en jours. |
| `AUTH_DEVICE_DAYS` | `90` | Durée d'approbation d'un navigateur/appareil en jours. |
| `AUTH_COOKIE_SECURE` | `false` | Mettre `true` uniquement si le dashboard est servi en HTTPS. |

> En local, tu peux ne renseigner que les variables Telegram si tu veux garder le
> mode legacy non authentifié. Sur la Pi, définis `AUTH_BOOTSTRAP_CODE` et
> `HABIT_API_TOKEN` avant de déployer.

---

## 🐳 Docker (production Pi 5)

```bash
docker compose up -d --build      # build + run en arrière-plan
docker compose ps
```

Mettre à jour un déploiement existant sur le Pi :

```bash
git pull --ff-only
docker compose up -d --build
docker compose ps
```

Pour remplacer les données du Pi par le snapshot SQLite committé, restaurer **après** le pull
et **avant** de redémarrer la stack :

```bash
docker compose down
python3 ops/db/habit_tracker_db_admin.py restore-snapshot
docker compose up -d --build
docker compose ps
```

La commande de restore crée d'abord une sauvegarde horodatée sous `data/backups/` avant de
remplacer `data/habit_tracker.db`.

---

## 📦 Sauvegardes automatiques

Rotation SQLite quotidienne via `backend/src/database/backup.py` : copies horodatées sous
`/data/backups/`, avec purge automatique pour ne garder que les **5 dernières** (préserve le
stockage du Pi).
