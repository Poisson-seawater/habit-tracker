---
name: habit-tracker
description: Télécommande complète du Habit Tracker (Pi, http://192.168.0.199:5000) depuis un prompt — l'équivalent du bot Telegram. Crée en masse To-Do/Habitudes/No-To-Do ; logge des habitudes (done/log/skip) ; complète des primes ; marque un no-todo échoué ; change le template du jour ; liste, montre le statut du jour, l'historique, les objectifs ; gère objectifs & sous-étapes. Déclencher sur "ajoute des todo/habitudes/no-todo", "remplir la base habit-tracker", "insérer des primes/quêtes", "logger/valider une habit", "j'ai fait [habitude]", "statut du jour", "compléter un todo", "fail un no-todo", "change le template", "mes objectifs", ou /habit-tracker, /habit-bulk-add.
compatibility: "Habit Tracker MVP/V2"
metadata:
  purpose: "HTTP API remote control of habit-tracker"
---

# habit-tracker

Pilote **tout** le Habit Tracker via son **API HTTP** — comme le bot Telegram, mais depuis un prompt.
L'API valide (XP 0–40, nom d'habitude unique → 400, FK user, type binary/quantitative). **Ne devine
aucun champ ni aucun id** : `GET` d'abord, récap avant écriture, puis POST.

`B` = base URL (défaut `http://192.168.0.199:5000`, demander si injoignable).

## Setup (tout flux)

1. **Cible** — `curl -fsS "$B/health"` puis `curl -fsS "$B/api/v1/users"`. Montre la liste, fais
   **choisir le `user_id`** (jamais en dur, les ids changent). Tous les appels portent `?user_id=$U`.
2. **Résolution nom→id** (le pont central : l'API parle en `id`, l'humain en noms) — `GET` la liste
   concernée, match **insensible à la casse** : exact d'abord, sinon `contains`. Ambigu ou introuvable
   → demander, jamais deviner. (todos : ignorer ceux déjà complétés ; habits : `is_active` ; notodos :
   match flou.)

## Capacités (miroir du bot + au-delà)

| Intention | Appel(s) | Notes |
|-----------|----------|-------|
| **Statut du jour** | `GET /profile` (+ `GET /habits`, `GET /notodos`) | voir « Statut » plus bas |
| **Valider habit binaire** | résoudre → `POST /logs {habit_id,log_type:"done"}` | gère `already_logged` vs `logged` |
| **Logger habit quantitative** | résoudre → `POST /logs {habit_id,log_type:"log",amount}` | `amount` requis |
| **Skipper une habit** | résoudre → `POST /logs {habit_id,log_type:"skip",reason}` | streak préservé |
| **Compléter un todo (prime)** | résoudre → `POST /todos/{id}/complete` | renvoie xp / levels_gained / new_level |
| **Marquer un no-todo échoué** | résoudre (flou) → `POST /notodos/{id}/fail` | |
| **Changer le template du jour** | `POST /profile/template {template_name}` | `week|weekend|recup|malade` (+ alias `semaine/recovery/sick`) |
| **Lister** | `GET /todos` · `GET /habits` · `GET /notodos` | |
| **Objectifs** | `GET /goals` | titres + sous-étapes |
| **Historique du mois** | `GET /history` | calendrier perfect/failed/future |
| **Stats potentielles / jour** | `GET /quests/daily-stats-potentials` | |
| **Créer (unitaire ou en masse)** | `POST /todos` · `POST /habits` · `POST /notodos` (boucle) | voir « Création » |
| **Gérer objectifs & sous-étapes** | `POST/PUT/DELETE /goals` · `POST /goals/{id}/substeps` · `PUT/DELETE /substeps/{id}` · `POST /substeps/{id}/complete` (gold) · `POST /substeps/link` | |
| **Gérer la boutique & acheter** | `GET/POST/PUT/DELETE /rewards` · `POST /rewards/{id}/purchase` | |

## Endpoints (`?user_id=$U`, `-H 'Content-Type: application/json'` ; `/health` seul est hors `/api/v1`)

| Méthode | Chemin | Corps JSON |
|---------|--------|-----------|
| GET | `/health`, `/api/v1/users`, `/api/v1/profile`, `/api/v1/history`, `/api/v1/quests/daily-stats-potentials`, `/api/v1/templates` | — |
| GET | `/api/v1/habits`, `/api/v1/todos`, `/api/v1/notodos`, `/api/v1/goals`, `/api/v1/rewards` | — |
| POST | `/api/v1/logs` | `{habit_id, log_type:"done"|"log"|"skip", amount?, reason?}` |
| POST | `/api/v1/habits` | `{name, type, description?, frequency?, scheduled_days?, reminder_time?, is_private?, is_reportable?, is_mandatory?, point_rewards, daily_cap?, unit?}` |
| POST | `/api/v1/todos` | `{title, stat_reward_1?, points_reward_1?, stat_reward_2?, points_reward_2?, xp_reward?}` |
| POST | `/api/v1/todos/{id}/complete` | — |
| POST | `/api/v1/notodos` | `{title}` |
| POST | `/api/v1/notodos/{id}/fail` | — |
| POST | `/api/v1/profile/template` | `{template_name}` |
| POST | `/api/v1/templates` | `{template_name, thresholds_json:{stat:int}}` |
| POST/PUT/DELETE | `/api/v1/goals` · `/api/v1/goals/{id}` | `{title, description?}` |
| POST | `/api/v1/goals/{id}/substeps` · PUT `/api/v1/substeps/{id}` | `{title, description?, gold_reward?, stats_json?, execution_order?}` |
| POST | `/api/v1/substeps/{id}/complete` · DELETE `/api/v1/substeps/{id}` | — |
| POST | `/api/v1/substeps/link` | `{goal_id, substep_id}` |
| POST/PUT/DELETE | `/api/v1/rewards` · `/api/v1/rewards/{id}` | `{title, description?, gold_cost, category?, required_softskill_id?, required_goal_id?, is_one_time}` |
| POST | `/api/v1/rewards/{id}/purchase` | — |

```bash
# Créer une prime
curl -fsS -X POST "$B/api/v1/todos?user_id=$U" -H 'Content-Type: application/json' \
  -d '{"title":"⚔️ Séance jambes","stat_reward_1":"force","points_reward_1":16,"xp_reward":20}'
# Valider une habit binaire (après avoir résolu son habit_id via GET /habits)
curl -fsS -X POST "$B/api/v1/logs?user_id=$U" -H 'Content-Type: application/json' \
  -d '{"habit_id":12,"log_type":"done"}'
```

## Statut du jour

`GET /profile` renvoie : `username`, `active_template`, `completed_habit_ids`, `scores{status,
perfect_day_validated}`, `stats` (12 valeurs), `thresholds`, `xp`, `level`, `gold`. Reconstruis le
statut :
- **Quêtes restantes** = habits `is_active` planifiées aujourd'hui non dans `completed_habit_ids`.
  *Jour planifié* : `scheduled_days` est un CSV où **0=Dim … 6=Sam** ; l'index d'aujourd'hui = numéro
  du jour avec Dimanche=0.
- **No-todos échoués** = `GET /notodos` → items `failed_today:true`.
- *(Le streak Perfect et les raisons des skips ne sont pas exposés par l'API — les omettre.)*

## Règles de remplissage

- **12 stats** (clés exactes, sans accent) : `force endurance mobilite discipline creativite connaissance
  sociabilite sante_mentale finance organisation spiritualite repos`.
- **To-Do** : `title` requis ; `xp_reward` entier **0–40** (défaut 10, proposer selon difficulté) ;
  `points_reward_*` entier ≥ 0 lié à une stat valide ; 2ᵉ stat optionnelle.
- **Habitude** : `name` requis (**unique par user** → doublon = 400) ; `type` = `binary` |
  `quantitative` ; `point_rewards` = objet `{stat: int}` non vide ; `frequency` = `daily|weekly|custom` ;
  `scheduled_days` = CSV `0..6` (**0=Dim … 6=Sam**, défaut `0,1,2,3,4,5,6`) ; `reminder_time` = `HH:MM` ;
  quantitative → `unit` (`min`,`km`,`pages`…) et `daily_cap` (entier > 0) ; `is_mandatory`/`is_private`
  défaut `false`, `is_reportable` défaut `true`.
- **No-To-Do** / **Goal** : `title` requis. **SubStep** : `title` requis, `gold_reward` défaut 50.

## Règles d'or

- `GET` d'abord (users, listes) — **jamais d'id ni d'user en dur**.
- **Récap avant toute écriture**, confirmation explicite.
- Un appel par élément (boucle bash pour le bulk). **Rapporter tout 4xx** (ex. habitude en double).
- **Re-`GET` après écriture** pour vérifier. Écriture minimaliste.
