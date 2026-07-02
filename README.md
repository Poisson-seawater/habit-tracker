# Habit RPG Tracker

Habit tracker auto-hébergé façon RPG + système de responsabilité, tournant sur un **Raspberry Pi 5**. Un bot Telegram et un dashboard web analytique partagent une même base **SQLite** locale et rapide.


## 🎯 Vision & Philosophie

### Pourquoi ce projet existe

Un habit tracker auto-hébergé, façon RPG, construit pour notre usage perso afin de se tenir mutuellement responsables de nos habitudes quotidiennes, avec un système de points, de stats, de streaks et de « journées parfaites ». Le pilotage se fait soit par le **bot Telegram**, les **skills LLM** ou le **dashboard web**.

L'idée de base : transformer la discipline quotidienne en jeu (XP, niveaux, or, quêtes) pour que tenir ses habitudes soit motivant plutôt que pénible.

### Public cible

- Amis et réseau proche.
- Usage **quotidien** : logger ses habitudes, voir son statut du jour, suivre ses streaks.
- Non développeurs.

### Ce que le projet N'EST PAS

- **Pas un SaaS.** 
- **Pas une plateforme générique.** Tout est personnalisé pour nos besoins.

### Non-goals explicites

- Pas de scaling horizontal, de microservices, de Kubernetes.
- Pas de mobile natif — le bot Telegram + la Mini App couvrent le besoin mobile.
- Pas d'optimisation pour des milliers d'utilisateurs : on optimise pour la **RAM du Pi**, pas pour la charge.

### Pistes futures (non engagées)

> idées conservées ici en attendant d'être cadrées dans `specs/`. 

MODIFICATION total
- L'integration Google agenda (spec fait)
- **Système de Punitions** : actions compensatoires constructives face à l'échec d'engagements
- **Accès à distance sécurisé** : Configurer la Raspberry Pi (par exemple via Tailscale, Cloudflare Tunnels ou un reverse proxy sécurisé) afin de pouvoir accéder au site web et à l'API de n'importe où dans le monde.

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
| `AUTH_BOOTSTRAP_CODE` | `long-code-secret` | Code temporaire requis pour créer le premier mot de passe admin et approuver le premier appareil. |
| `HABIT_API_TOKEN` | `long-api-token` | Token machine pour le plugin `habit-tracker-control` et les appels API non navigateur. |
| `AUTH_SESSION_DAYS` | `30` | Durée des sessions web en jours. |
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
