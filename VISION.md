# Vision — Habit RPG Tracker

## Pourquoi ce projet existe

Un habit tracker auto-hébergé, façon RPG, qui tourne **en local** sur un Raspberry Pi 5.
On l'a construit pour notre usage perso : se tenir mutuellement responsables (entre frères)
sur nos habitudes quotidiennes, avec un système de points, de stats, de streaks et de
« journées parfaites ». Le pilotage se fait soit par le **bot Telegram**, soit par le
**dashboard web**.

L'idée de base : transformer la discipline quotidienne en jeu (XP, niveaux, or, quêtes)
pour que tenir ses habitudes soit motivant plutôt que pénible.

## Public cible

Nous deux. Point.

- Deux utilisateurs (deux frères), chacun avec son profil, ses habitudes, ses scores.
- Usage **quotidien** : logger ses habitudes, voir son statut du jour, suivre ses streaks.
- On connaît le code, on déploie nous-mêmes, on accepte un setup technique.

## Ce que le projet N'EST PAS

- **Pas un SaaS.** Aucune intention de vendre, d'héberger pour des tiers, ni de scaler.
- **Pas multi-tenant.** « Multi-utilisateur » = nous deux, sur une seule instance, une
  seule DB SQLite. Pas d'organisations, de rôles, de facturation.
- **Pas une app publique.** Tourne derrière notre réseau / tunnel. Pas de hardening
  niveau prod publique (CORS ouvert, auth par simple header `X-User-ID`).
- **Pas une plateforme générique.** Les mécaniques (12 stats, templates de journée,
  no-todos, quêtes) sont taillées pour nos besoins, pas pour être configurables par
  n'importe qui.

## Stack technique actuelle

- **Backend** : FastAPI (Python), SQLAlchemy 2.0 (ORM), Uvicorn, python-telegram-bot,
  APScheduler (rappels / tâches planifiées), PyTest.
- **Frontend** : Vanilla HTML5 / CSS3 / JS ES6 (pas de framework, pas de build).
  Servi en statique par le backend. Palette sombre HSL + glassmorphism.
- **Base de données** : SQLite unique, montée sur `/data/habit_tracker.db` (Docker) ou
  `backend/data/` (local).
- **Déploiement** : Docker Compose (services `api` + `bot`) sur Raspberry Pi 5, avec
  limites mémoire strictes (`api` 40 Mo, `bot` 35 Mo).
- **Spec-driven** : GitHub Spec Kit (`.specify/`, `specs/`) pour cadrer les features.

## Non-goals explicites

- Pas d'inscription publique ni d'onboarding grand public.
- Pas de paiement, d'abonnement, de plan freemium.
- Pas de support multi-DB (Postgres, MySQL…) — SQLite suffit pour deux personnes.
- Pas de scaling horizontal, de microservices, de Kubernetes.
- Pas de mobile natif — le bot Telegram + la Mini App couvrent le besoin mobile.
- Pas d'i18n complète — FR/EN au fil de l'eau, sans framework de traduction.
- Pas d'optimisation pour des milliers d'utilisateurs : on optimise pour la **RAM du Pi**,
  pas pour la charge.

## Pistes futures (non engagées)

> Idées issues du cahier des charges initial, conservées ici en attendant d'être
> éventuellement cadrées dans `specs/`. Rien de tout ça n'est décidé.

**V3 — intégrations externes**

- Connexion à un calendrier externe (ex. calendrier employeur → tâches → rappel bot → recap).
- Connexion à une app de todo externe.
- API externe + intégrations avec des outils professionnels.
- Synchronisation avec des systèmes tiers.

**À réconcilier avec le graphe d'objectifs V2** (cf. [`specs/002-multiuser-rpg-v2/spec.md`](./specs/002-multiuser-rpg-v2/spec.md))

- Fin d'objectif par cumul de succès (ex. 180 succès ≈ 6 mois), en plus du streak complet.
- Statuts de fin d'objectif : abandonné / terminé avec déblocage du suivant / terminé sans suite.
