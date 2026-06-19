# Habit RPG Tracker

Habit tracker auto-hébergé façon RPG + système de responsabilité, tournant sur un **Raspberry Pi 5**. Un bot Telegram et un dashboard web analytique partagent une même base **SQLite** locale et rapide.

---

#### bug hunting

1. PULL MODIFICATION FAIT SUR ORDI
2. lancer toutes les prompts manquant
3. pull de la pie
4. test IA interaction direct sur le site web ! par modification http ???
5. rerun test de stockage pour optimisation du code !


objectif:
- [x] quand je lis un objectif ex avoir 500k en actif a objectif faire le tour du monde, je ne vois pas cet objectif s'afficher dans faire le tour du monde. comme cela ce fait dans softskill.
- [x] description apparais des que je batit la sous-etapes  ! pas uniquement dans edit.

softskill:
- [x] etre capable de delete un softskill
- [x] Compétences Liées (liaisons secondaires) c'est quoi  ?
- [x] quand je ✨ Forger une compétence, pouvoir ecrire la description ET son critere de validation aussi !
- [x] revoir les liens entre les skills
- [ ] revoir les couleurs quand c'est valider et non !

Add stat caché = life experience / personal lore -> option yes  /no sur des objectifs. 

message: 
- log vide permet de sélectionner to do ou habit puis de sélectionner habit de son choix

overall: 
- cleaner sur cellphone



aight so tu as fait de la merde ! je ne peux plus chagner l'étapes d;un sous objectifs ! aucun changement de place visuel ! ET apres avoir changer etape 1 pour 2, létape redevient 1 des que l'edit du sous-objecrifs est terminer



##### prompts list

**telegram**: 
A la fin de la journés, donc 21h30, le message de recap dois afficher les to do et les habit faite ! ainsi que les no-to-do de failure fait !

La commande /log me permet de selectionner une habitude ou une to do par bouton ! 1. donne le choix entre habitude ou bouton. 2. liste les habitudes/ boutons et je clique sur celui que je log. 

**objectifs**
dans les paramètre d'un sous-objectif, on peux cocher une case life lore. Quand un sous-objectifs life lore est réaliser. Alors il apparais dans les stats du jours. Le jour peux voir son life lore quand il clique sur son image de profil.

**skills**
OUTPUT: better ux. Les skills ont la meme logique par branche que les objectifs et refonte visuel.
Context: un sous-objectifs peuvent s'afficher dans plusieurs objectifs. Les skills aussi peuvent apparaitre dans plusieur branche.
Si skill fait, alors background change de couleur pour etre le meme que celui de la bordure (pas de verts).
La vue global, 

**not to-do**
je veux etre capable de delete un non to do


**esthetique**
Le rendu est propre sur ordi, mais tres moche des qu'on est sur telephone. Creer moi 2 maquettes: telephone et tablette afin quon verifie ensemble le visuel ! 



#### last prompt
double check database, code with 1 outputs in mind.
consume as little RAM as possible.

what can be optimize  ? database ? code librairie ? 

## 🎯 Vision & Philosophie

### Pourquoi ce projet existe

Un habit tracker auto-hébergé, façon RPG, construit pour notre usage perso afin de se tenir mutuellement responsables de nos habitudes quotidiennes, avec un système de points, de stats, de streaks et de « journées parfaites ». Le pilotage se fait soit par le **bot Telegram**, les **skills LLM** ou le **dashboard web**.

L'idée de base : transformer la discipline quotidienne en jeu (XP, niveaux, or, quêtes) pour que tenir ses habitudes soit motivant plutôt que pénible.

### Public cible

- Amis et réseau proche.
- Usage **quotidien** : logger ses habitudes, voir son statut du jour, suivre ses streaks.
- Non développeurs.

### Ce que le projet N'EST PAS

- **Pas un SaaS.** Aucune intention de vendre, d'héberger pour des tiers, ni de scaler.
- **Pas multi-tenant.** « Multi-utilisateur » = nous deux, sur une seule instance, une seule DB SQLite. Pas d'organisations, de rôles, de facturation.
- **Pas une app publique.** Tourne derrière notre réseau / tunnel. Pas de hardening niveau prod publique (CORS ouvert, auth par simple header `X-User-ID`).
- **Pas une plateforme générique.** Tout est personnalisé pour nos besoins.

### Non-goals explicites

- Pas d'inscription publique ni d'onboarding grand public.
- Pas de paiement, d'abonnement, de plan freemium.
- Pas de support multi-DB (Postgres, MySQL…) — SQLite suffit pour deux personnes.
- Pas de scaling horizontal, de microservices, de Kubernetes.
- Pas de mobile natif — le bot Telegram + la Mini App couvrent le besoin mobile.
- Pas d'i18n complète — FR/EN au fil de l'eau, sans framework de traduction.
- Pas d'optimisation pour des milliers d'utilisateurs : on optimise pour la **RAM du Pi**, pas pour la charge.

### Pistes futures (non engagées)

> Idées issues du cahier des charges initial, conservées ici en attendant d'être éventuellement cadrées dans `specs/`. Rien de tout ça n'est décidé.

- **V3 — intégrations externes** : calendrier employeur, app de todo externe, API professionnelles.
- **Fin d'objectif par cumul de succès** (ex. 180 succès ≈ 6 mois), statuts abandonné / terminé.
- **Planification quotidienne 3-3-3** : 3 objectifs majeurs, 3 tâches courtes, 3 tâches de maintenance.
- **Régulation de la charge cognitive** : limiter les projets et habitudes actifs simultanément.
- **Système de Punitions** : actions compensatoires constructives face à l'échec d'engagements.

---

## 👥 Collaboration & développement

Projet perso. Avant de contribuer, lire :

- 🎯 **[Vision & Philosophie](#-vision--philosophie)** — pourquoi ce projet existe, qui il vise, ce qu'il n'est pas (section ci-dessus).
- 🤖 **[CLAUDE.md](./CLAUDE.md)** — conventions et règles pour Claude Code / agents (symlink vers `AGENTS.md`).
- 🌿 **[CONTRIBUTING.md](./CONTRIBUTING.md)** — branches, PRs, format des commits.
- 🗺️ **[ROADMAP.md](./ROADMAP.md)** — ce qui reste à faire.

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

Mini App Telegram : exposer l'API en HTTPS, mettre l'URL publique `/mini-app/` dans
`TELEGRAM_WEB_APP_URL`, puis utiliser le menu d'aide (`/aide`) pour l'ouvrir.

---

## 🔑 Variables d'environnement

À mettre dans `.env` à la racine (copier depuis `.env.example`) :

| Variable | Exemple | Rôle |
|----------|---------|------|
| `TELEGRAM_BOT_TOKEN` | `123456:ABC-DEF...` | Token du bot (BotFather). |
| `TELEGRAM_GROUP_ID` | `-1003912636269` | ID du groupe Telegram autorisé. |
| `TELEGRAM_WEB_APP_URL` | `https://mon-domaine.example/mini-app/` | URL HTTPS publique de la Mini App. |
| `API_PORT` | `5000` | Port d'écoute de l'API / dashboard. |
| `ENV` | `development` | `development` en local, `production` sur le Pi. |
| `TIMEZONE` | `America/Toronto` | Fuseau pour les scores du jour et les rappels. |
| `DATABASE_URL` | `sqlite:////data/habit_tracker.db` | Chemin SQLite. À laisser vide en local : fallback auto vers `backend/data/`. |

> En local, tu peux ne renseigner que les variables Telegram : le reste a des valeurs par défaut.

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
