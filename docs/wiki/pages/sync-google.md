# Synchronisation Google Calendar & Tasks

Tu connais déjà les rappels d'agenda sur ton téléphone. Ici, le système pousse tes [primes](#/primes-todo) directement dans **ton propre** Google Agenda et Google Tasks, pour les retrouver dans ton app mobile habituelle sans ouvrir le bot ou le dashboard.

> [!note] Le fichier `google-calendar-integration-brainstorm.md` à la racine du projet reprend la même spécification : `do_date` crée l'événement Calendar, `due_date` crée la Google Task cochable.

## Le mapping des deux dates

Une [prime](#/primes-todo) porte deux dates optionnelles, `do_date` (jour où tu comptes t'y mettre) et `due_date` (échéance). Elles n'atterrissent pas au même endroit côté Google :

| Date de la prime | Destination Google | Pourquoi |
|---|---|---|
| `do_date` | **Événement** dans le calendrier dédié « Agenda des Quêtes » | c'est un jour de travail planifié, ça se bloque sur l'agenda |
| `due_date` | **Tâche Google** cochable, dans la liste « Habit RPG Tracker » | c'est une échéance, ça se coche comme une tâche |

Concrètement, l'événement Calendar porte le titre `⚔️ <titre de la prime>` et une couleur graphite fixe (`colorId` 8) — toutes les primes ont la même couleur, qu'importe leur nature. La tâche Google porte le titre `🏆 <titre de la prime>`.

> [!note] Les emojis et couleurs par type d'effort (💪 musculaire rouge, 🧠 cerveau bleu, ❤️ emotionnel_social orange, 🎨 creatif_divergent violet, 🌿 repos vert) ne s'appliquent **pas** aux primes : ils servent uniquement à l'export des quêtes de l'[agenda vertical](#/agenda-timeline), décrit plus bas.

## Cycle de vie de la synchro

Chaque écriture sur une prime déclenche une synchro en tâche de fond (le site ou le bot n'attendent pas la réponse de Google) :

- **Création** : si `do_date` est renseigné, un événement Calendar est créé et son id (`google_event_id`) stocké sur la prime. Si `due_date` est renseigné, une tâche Google est créée et son id (`google_task_id`) stocké de la même façon.
- **Modification** : si la date a changé, l'événement ou la tâche existante est mise à jour (`PATCH`). Si une date a été retirée, l'élément Google correspondant est supprimé et son id effacé. Si une date apparaît alors qu'elle était vide, l'élément est créé.
- **Complétion** : cocher la prime marque la tâche Google `completed`. L'événement Calendar, lui, reste en place — un jour de travail passé garde sa trace sur l'agenda.
- **Suppression** : la prime supprimée entraîne la suppression de l'événement **et** de la tâche associés.

## Export manuel des quêtes planifiées

En plus de la synchro automatique des primes, un bouton export pousse tes [quêtes](#/habitudes) déjà placées dans l'[agenda vertical](#/agenda-timeline) vers Google Calendar — pratique pour voir sa journée type sur son téléphone.

- `POST /api/v1/agenda/export-google` — exporte les quêtes placées sur une plage de dates (`start_date` à `end_date`).
- `POST /api/v1/agenda/{date}/export-google-quests` — exporte les quêtes placées d'un seul jour.

Chaque quête exportée reprend l'emoji et la couleur de son type d'effort. L'export est **idempotent** : chaque événement porte un tag interne (`origin=habit-tracker-quest`), et avant de réécrire un jour, les anciens événements du même jour portant ce tag sont supprimés — donc jamais de doublons en relançant l'export. Seules les quêtes placées partent vers Google ; les zones biologiques et les segments de template n'y figurent pas.

## Se connecter (OAuth2 sans navigateur sur le Pi)

Le Raspberry Pi qui héberge le projet n'a pas d'écran ni de navigateur. La connexion Google passe donc par un flux OAuth2 qui s'ouvre sur **ton** appareil, pas sur le Pi :

1. `GET /api/v1/auth/google/login` renvoie l'URL de consentement Google (scopes Calendar + Tasks) et redirige dessus.
2. Tu acceptes sur ton téléphone ou ton ordinateur.
3. Google redirige vers `GET /api/v1/auth/google/callback`, qui échange le code contre un `refresh_token`, crée au besoin le calendrier « Agenda des Quêtes » et la liste de tâches « Habit RPG Tracker », puis retourne sur le dashboard (onglet Réglages).

Le `refresh_token` est chiffré (XOR + base64, clé `GOOGLE_ENCRYPTION_KEY`) avant d'être stocké en base — voir [Règles & variables](#/regles-et-variables) pour les variables d'environnement Google.

`GET /api/v1/auth/google/status` indique si le compte est connecté ; `POST /api/v1/auth/google/disconnect` efface les tokens et identifiants stockés côté Habit Tracker (rien n'est supprimé côté Google).

## Rappels Telegram avant l'échéance

Une routine planifiée (voir [authentification](#/authentification) pour la distinction entre planification et pilotage machine) tourne chaque jour à 09:00 et regarde **toutes** les primes non complétées ayant une `do_date`. Si le jour planifié tombe dans 7, 3 ou 1 jour, le bot envoie un message de rappel dans le chat privé du joueur concerné, avec le titre de la prime et l'XP promise. Il n'y a pas de job individuel par prime : c'est une seule vérification quotidienne qui balaye toutes les primes actives.
