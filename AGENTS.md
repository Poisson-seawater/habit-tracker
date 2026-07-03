<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
[specs/011-perfect-day-rendering/plan.md](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/specs/011-perfect-day-rendering/plan.md)

**NEXT STEP FOR AGENT SESSIONS:**
The final specifications for the Google Calendar & Tasks API Integration have been defined in [google-calendar-integration-brainstorm.md](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/google-calendar-integration-brainstorm.md).

**CRITICAL RULE FOR COMMANDS:**
Whenever you add, modify, or delete any Telegram Bot commands in the code, you MUST update the `COMMANDS-INDEX.md` document at the root of the project to ensure the command index is always accurate and up-to-date.
<!-- SPECKIT END -->

# Guide projet — Habit RPG Tracker

> Ce fichier guide les agents (Claude Code, Codex…). `CLAUDE.md` est un **symlink** vers ce fichier.
> Contexte produit & Vision → [README.md](./README.md). Workflow de contribution → [CONTRIBUTING.md](./CONTRIBUTING.md).

## Stack

- **Backend** : FastAPI + SQLAlchemy 2.0 + Uvicorn, Python 3.12. Bot Telegram via
  `python-telegram-bot[ext]`, tâches planifiées via APScheduler. Tests PyTest.
- **Frontend** : Vanilla HTML/CSS/JS ES6, **sans framework ni build**. Servi en statique
  par FastAPI.
- **DB** : SQLite unique (`/data/habit_tracker.db` en Docker, `backend/data/` en local).
- **Déploiement** : Docker Compose (`api` + `bot`) sur Raspberry Pi 5, limites RAM 40/35 Mo.

## Structure des dossiers

```
backend/
  src/
    main.py            # point d'entrée FastAPI (lifespan = init_db au démarrage)
    config.py          # lecture des variables d'env (+ fallback DATABASE_URL)
    api/
      routes.py        # toutes les routes REST sous /api/v1 (APIRouter)
      static_config.py # montage des fichiers statiques frontend
    bot/
      listener.py      # daemon Telegram (entrée du service bot)
      parser.py        # parsing des messages / commandes
      scheduler.py     # rappels APScheduler
    database/
      models.py        # modèles SQLAlchemy (= schéma DB)
      session.py       # engine + get_db()
      seed.py          # init_db() idempotent + seeders
      backup.py        # rotation des snapshots SQLite
      migrations/      # v9_remote_operations.sql : référence SQL à appliquer à la main
                       #   (le schéma vivant est créé par create_all + _run_migrations())
    services/
      score_service.py # logique métier (scores, stats, XP, streaks)
  tests/               # pytest (test_*.py)
frontend/
  index.html           # dashboard
  js/app.js            # toute la logique front (fetch /api/v1, navigation à onglets)
  css/style.css        # styles (palette HSL sombre, glassmorphism)
docs/
  adr/                 # décisions d'architecture (Architecture Decision Records)
  wiki/                # site de doc d'onboarding généré
specs/                 # specs Spec Kit
ops/db/                # admin DB côté hôte (snapshots, restore)
```

## Conventions de nommage (observées)

**Python (backend)**
- Classes (modèles, schémas) : `PascalCase` singulier (`Habit`, `HabitLog`, `Todo`).
- Tables : `snake_case` pluriel (`habits`, `habit_logs`, `daily_scores`).
- Fonctions / variables : `snake_case` (`calculate_daily_score`, `get_db`).
- Schémas Pydantic de requête : suffixe explicite (`HabitCreate`, `LogCreate`, `TemplateSave`).
- Formatage : **black**, ligne max 88 (`backend/pyproject.toml`).

**API (routes)**
- Préfixe global `/api/v1` (monté dans `main.py`).
- Ressources au pluriel, lowercase : `/habits`, `/todos`, `/notodos`, `/goals`,
  `/substeps`, `/templates`.
- Sous-actions en POST sur la ressource : `/todos/{todo_id}/complete`,
  `/notodos/{notodo_id}/fail`, `/substeps/{substep_id}/complete`.
- CRUD via verbes HTTP : `GET` (liste/détail), `POST` (création, `status_code=201`),
  `PUT` (édition), `DELETE` (suppression).
- Identité utilisateur passée via le header **`X-User-ID`** (pas de session ni JWT).

**JavaScript (frontend)**
- Fonctions : `camelCase` (`fetchGoals`, `loadSettingsThresholds`).
- Indentation 2 espaces, guillemets doubles.
- Un seul `app.js`, tout dans un `DOMContentLoaded`. `API_BASE = "/api/v1"`.
- `fetch` est wrappé pour injecter `X-User-ID` depuis `localStorage`.

**Commits / branches** → [CONTRIBUTING.md](./CONTRIBUTING.md)
(`type(scope): description`, branches `feat/...` → `dev` → `main`).

## Journal et décisions

- **Commandes Docker / DB / reset / migration / déploiement** : toujours préciser la cible
  avant de donner ou lancer la commande : instance locale, Raspberry Pi / serveur de prod,
  ou autre environnement. Si la cible est ambiguë, demander confirmation. Ne pas donner de
  placeholder non remplacé dans une commande à copier-coller.
- **log.md** : documenter les décisions opérationnelles, les échecs et les pistes écartées.
  Priorité aux décisions rejetées ou aux tentatives qui n'ont pas fonctionné, car les
  décisions retenues sont généralement déjà visibles dans les commits, PR et GitHub Actions.

## Patterns à respecter

- **Nouvelle route** : l'ajouter dans `backend/src/api/routes.py`, avec son schéma
  Pydantic en haut du fichier, sous le préfixe `/api/v1`, en suivant les conventions
  ci-dessus. Récupérer l'utilisateur via le header `X-User-ID`.
- **Nouveau champ DB** : modifier `models.py` **et** ajouter un `ALTER` idempotent dans
  `_run_migrations()` de `database/seed.py` (vérifier la colonne via `inspect()` avant de
  l'ajouter). C'est le seul mécanisme exécuté au démarrage — `create_all()` ne modifie pas
  les tables existantes, et les `.sql` ne sont **pas** lus automatiquement. Pas d'Alembic.
- **Logique métier** (scoring, stats, XP, streaks) : dans `services/`, jamais dans les routes.
- **Front** : étendre `app.js` en réutilisant le wrapper `fetch` et le système d'onglets
  existant. Pas de framework, pas de build step.
- **Commande bot ajoutée / modifiée** : mettre à jour `COMMANDS-INDEX.md` (règle dure).
- **Empreinte mémoire** : on tourne sur un Pi à 40/35 Mo par service. Éviter les grosses
  libs et de tout garder en mémoire.

## Télécommande IA

Le plugin local `habit-tracker-control` permet à un agent de consulter et modifier
l'instance distante sans MCP. Avant de modifier ce mécanisme, lire :

- [docs/notes/habit-tracker-control-plugin.md](./docs/notes/habit-tracker-control-plugin.md)
- [docs/notes/database-v9-remote-operations.md](./docs/notes/database-v9-remote-operations.md)
- [docs/adr/002-plugin-habit-tracker-control.md](./docs/adr/002-plugin-habit-tracker-control.md)

## Ne PAS modifier sans discussion

- **Le schéma DB** (`backend/src/database/models.py`) : le bot, l'API, le front et des
  skills externes en dépendent. Tout changement = migration + accord.
- **Les contrats d'API** (`/api/v1/*` et les schémas Pydantic) : le front, le bot et la
  skill `habit-tracker` (télécommande HTTP) consomment ces endpoints. Ne pas renommer /
  changer les payloads sans prévenir.
- **Les limites mémoire** de `docker-compose.yml` (40/35 Mo) : contrainte matérielle du Pi.
- **`docker-compose.yml`** : marqué `skip-worktree` (réglages par-machine). Ne pas le
  dé-skip ni committer de valeurs locales.
- **Le header d'auth `X-User-ID`** : changer le mécanisme d'auth casse front + bot + skills.

## Commandes utiles

```bash
# Setup (uv)
uv venv && source .venv/bin/activate && uv pip install -r backend/requirements.txt

# Lancer le dashboard / API  → http://localhost:5000
PYTHONPATH=backend python3 backend/src/main.py

# Lancer le bot Telegram
PYTHONPATH=backend python3 backend/src/bot/listener.py

# Tests
PYTHONPATH=backend .venv/bin/pytest backend/tests

# Formatage (configuré, pas encore appliqué partout)
black backend/

# Docker (prod Pi)
docker compose up -d --build
docker compose ps
```
