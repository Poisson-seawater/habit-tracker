# ADR 001 — Stack initiale

- **Statut** : Accepté
- **Date** : 2026-05-31
- **Décideurs** : Les deux frères

> Cet ADR documente *a posteriori* les choix techniques déjà en place. Les raisons sont
> déduites du code existant et des contraintes connues (Pi, usage à deux).

## Contexte

On veut un habit tracker perso, façon RPG, qui :

- tourne **en local** sur un Raspberry Pi 5 (RAM très limitée),
- se pilote depuis le **téléphone** (Telegram) **et** depuis un **dashboard web**,
- reste **simple à maintenir à deux**, sans infra lourde.

## Décision

### Backend : FastAPI (Python)

- Async natif, léger, rapide à écrire. Idéal pour exposer une petite API REST `/api/v1`
  et servir le frontend statique depuis le même process.
- L'écosystème Python colle avec `python-telegram-bot` : le bot et l'API partagent les
  mêmes modèles SQLAlchemy et la même DB.

### ORM : SQLAlchemy 2.0

- Modèles déclaratifs clairs (`backend/src/database/models.py`), relations explicites,
  migrations gérées en SQL à la main (`backend/src/database/migrations/`).

### Base de données : SQLite

- Un seul fichier, zéro serveur à faire tourner → parfait pour la RAM du Pi.
- Deux utilisateurs, faible concurrence : SQLite suffit largement.
- Facile à sauvegarder (snapshot SQL, rotation de backups) et à déplacer.

### Frontend : Vanilla HTML/CSS/JS (pas de framework)

- Pas de build, pas de `node_modules` à déployer sur le Pi, empreinte mémoire minimale.
- L'UI reste simple (dashboard + Mini App Telegram) : un framework serait surdimensionné.
- Servi directement en statique par FastAPI.

### Bot : python-telegram-bot + APScheduler

- Telegram = interface mobile gratuite, déjà installée, notifications incluses.
- APScheduler gère les rappels et tâches planifiées sans cron externe.

### Déploiement : Docker Compose sur Raspberry Pi 5

- Deux services (`api`, `bot`) isolés, avec limites mémoire (40 Mo / 35 Mo) pour ne pas
  saturer le Pi.
- `git pull` + `docker compose up -d --build` = déploiement en une commande.

## Alternatives envisagées

- **Postgres au lieu de SQLite** : écarté — overkill pour deux users, consomme de la RAM
  qu'on n'a pas sur le Pi.
- **React / Vue pour le front** : écarté — build et taille inutiles pour une UI simple,
  alourdit le déploiement sur le Pi.
- **App mobile native** : écartée — le bot Telegram + Mini App couvrent le mobile sans
  coût de dev ni store.

## Conséquences

- **+** Empreinte mémoire minimale, déploiement simple, une seule source de données.
- **+** Le bot et l'API partagent modèles et DB → pas de duplication de logique.
- **−** SQLite limite la concurrence (acceptable à deux).
- **−** Front vanilla : pas de composants réutilisables, `app.js` grossit (~1500 lignes)
  → à surveiller, refacto si ça devient ingérable.
- **−** CORS ouvert + auth par header `X-User-ID` : OK en réseau privé, **à ne pas
  exposer publiquement** tel quel.
