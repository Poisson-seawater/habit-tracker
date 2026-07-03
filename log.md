# Journal des changements

> Une entrée par session / push, anti-chronologique. Rédigé par `/doc-sync` avant push.
> Format : date, résumé `type(scope): description`, ce qui a changé, docs touchés.

## 2026-07-02 — feat(google): inversion du mapping do/due (event vs task cochable)

- **Décision produit** : inverser le mapping Google. Avant : `due_date`→événement agenda, `do_date`→Google Task. Après : **`do_date`→événement** (⚔️, jour de travail bloqué dans l'agenda) et **`due_date`→Google Task** (🏆, cochable, cochée à la complétion). Raison : le jour où on bosse mérite un créneau agenda ; l'échéance est ce qu'on « termine ». Le mapping initial du brainstorm (`google-calendar-integration-brainstorm.md` §1) est donc **remplacé** — doc à mettre à jour si on la garde comme référence.
- **Colonnes renommées** (feature Google jamais déployée en prod, donc rename direct sans migration de rename) : `todos.google_due_event_id/google_do_task_id` → `google_event_id/google_task_id` (noms neutres, corrects après l'inversion). Migration v23 (`seed.py`) crée directement les nouveaux noms. Sur le Pi : aucune manip manuelle, v23 créera les bonnes colonnes au 1ᵉʳ déploiement. En local dev : 2 colonnes mortes `google_due_*/google_do_*` subsistent (inoffensives).
- Backend : `models.py`, `seed.py` (v23), `google_sync_service.py` (helpers renommés `create_calendar_event`/`create_task`/… + wiring inversé + emoji/textes), `routes.py` (route delete).
- **Rappel visibilité** (piste écartée comme « bug ») : un todo sans `do_date` **ni** `due_date` ne crée **rien** côté Google — comportement voulu, pas un bug. La confusion venait de 2 quêtes sans date.
- Vérif : test bout-en-bout en direct contre les vraies API Google (do_date→événement au bon jour, due_date→task cochable `needsAction`), résidus orphelins nettoyés, conteneur `api` rebuild sain. Non commité.
- Docs : log.md ✔ · google-calendar-integration-brainstorm.md ✔ (mapping §1 réaligné) · docs/wiki ✔ · COMMANDS-INDEX.md — (aucune commande bot touchée)

## 2026-07-02 — ops(prod): health check Pi post-incident + nettoyage

- Health check prod (Pi `192.168.0.199`) : hôte sain (uptime 38j, disque 6%, RAM ok), conteneurs `api`+`bot` Up `restarts=0`, API 200 sur tous les endpoints, 20 tables présentes (dont `auth_devices`/`auth_sessions`), données OK.
- Incident DB vidée du matin **confirmé résolu** : recovery manuelle (`restore-snapshot` + migrations). Burst de ~1100 erreurs `no such table: auth_sessions/auth_devices` entre le restart et l'application des migrations (snapshot restauré antérieur aux tables auth) → **stoppé depuis 15:40 UTC**, plus aucune erreur live.
- Nettoyage : fichier résiduel `habit_tracker.EMPTY-20260702.db` (0 octet, root) supprimé. Logs conteneurs cleared.
- Tests connexion Cloudflare effectués.
- **Cause racine du wipe (DB → 0 octet à 15:44) non identifiée** — `journalctl` non lisible (sudo). Piste ouverte.

## 2026-07-02 — fix(auth): tentative infructueuse sur l'erreur profil

- Tentative de résolution de l'erreur front `Erreur lors du chargement du profil` sur la Raspberry Pi, c'est-à-dire le serveur de prod.
- PR #6 puis PR #7 réalisées, puis décision de redémarrer avec une base de données réinitialisée.
- Résultat : rien n'a corrigé durablement le problème.

## 2026-06-14 — feat(habits): cible de répétitions/jour (daily_target) — affichage X/N

- Nouvelle option **Cible/jour** (`daily_target`) sur une habitude : quand elle est définie (> 1), chaque validation compte et rapporte son XP (pas de pénalité à 1 fois, `n+1` = XP en plus, dépassement `3/2` permis), et le recap Telegram + la tuile du dashboard affichent `X/N`. `daily_cap` reste respecté. Les habitudes sans cible sont inchangées.
- Backend : colonne `daily_target` (`models.py`) + migration `v11_habit_daily_target.sql` ; `score_service.py` (binaire à cible → XP par validation, cap appliqué) ; `routes.py` (`HabitCreate`/`HabitUpdate`, `create_habit`, `get_habits` expose `daily_target` + `today_count`, `/logs` ne bloque plus le 2ᵉ `done` binaire si cible) ; `scheduler.py` (recap groupé par habitude, ligne `Nom X/N`).
- Bot : `/done` autorise la re-validation et affiche `X/N` pour une habitude à cible → `COMMANDS-INDEX.md` mis à jour (règle dure).
- Front : champ « Cible/jour » (formulaires création + édition), badge `X/N` (vert si atteint), bouton qui reste actif pour permettre le dépassement.
- Vérif : 113 tests existants OK + 5 nouveaux (`test_habit_daily_target.py`) ; smoke test API bout-en-bout (créer cible 2 → 3 logs acceptés → `today_count=3`, discipline=15) ; migration appliquée aux DB locales et à la DB du conteneur Docker (`ALTER TABLE habits ADD COLUMN daily_target INTEGER`). **Pi : migration à appliquer côté hôte** (`docker compose exec`), ne jamais utiliser `down -v`.
- Docs : log.md ✔ · COMMANDS-INDEX.md ✔ · VISION.md — · docs/wiki à régénérer (affichage X/N) ⏳
- Commit : branche `codex/fix-docs-serving` → merge `master`

## 2026-06-14 — docs(notes): cadrage de la feature 7x7 (reflex drills) — décision de ne pas sur-ingénierer

- Session de brainstorm sur la feature **7x7** (option sur un softskill épinglé au Recap 3-3-3 : un micro-réflexe à répéter ~7×/jour pendant 7 jours, déclenché par DM Telegram).
- **Décision** : ne pas construire le moteur complet (random scheduler restart-safe + callbacks inline + throttling) — prémisse « 7×7 crée un réflexe » à moitié mythe, risque de sur-ingénierie sur un Pi 40 Mo. Si poursuite, uniquement via un MVP minimal testé 1 semaine sur soi.
- Memo d'analyse complet (prémisse science, mismatch modèle softskill vs habit, réalité du scheduler mono-cron, fatigue de notif, questions de design ouvertes) : `docs/notes/7x7-reflex-drills-analysis.md`.
- Docs : log.md ✔ · VISION.md ✔ (lien ajouté au bullet 7x7, ligne ~64) · docs/notes/7x7-reflex-drills-analysis.md (nouveau) ✔ · docs/wiki — (rien d'implémenté) · COMMANDS-INDEX.md —
- Commit : non commité (analyse, aucun changement de code)

## 2026-06-14 — docs(wiki): diagnostic et résolution du serving de la documentation sur le Pi

- **Diagnostic de la documentation sur le Pi** : Résolution du problème d'accès aux pages de documentation (`/docs`) sur la Raspberry Pi. Le fichier `docker-compose.yml` étant marqué `skip-worktree` pour conserver les réglages par-machine, la définition du volume `- ./docs/wiki:/app/docs/wiki:ro` n'était pas synchronisée sur la Pi. Sans ce montage, le dossier `/app/docs/wiki` n'existait pas dans le conteneur `api`, empêchant FastAPI de monter la route statique `/docs` et causant une erreur JSON `{"detail": "Not Found"}`.
- **Résolution** : Fourniture de la configuration YAML fusionnée et sans doublon pour modifier le `docker-compose.yml` local directement sur la Pi, et consignes de relance du conteneur (`docker compose down && docker compose up -d --build`).
- Docs : log.md ✔ · docs/wiki — · docker-compose.yml (modifié localement sur la Pi, non commité) ✔
- Commit : non commité (résolution de configuration de déploiement)

## 2026-06-13 — feat(softskills,plugin): placement auto des compétences + télécommande IA Codex

- **Placement automatique des softskills** : le backend calcule désormais la position de chaque nœud dans la vue globale au lieu de coordonnées fixes saisies au front. `softskill_service.py` gagne un moteur de layout (`allocate_skill_position`, `repair_skill_positions`, `_branch_anchor_x`, `_skill_order`) — X dérivé de l'ancre de la branche, Y dérivé de `execution_order`, avec évitement de collision sur le slot libre le plus proche. Le front (`app.js`) n'envoie plus `x:0, y:0` à la création/édition.
- Nouvel endpoint `POST /api/v1/softskills/branches-with-skills` (création d'une branche entière + ses compétences en un appel, positions allouées automatiquement). Nouvelle skill agent `.agents/skills/habit-tracker-softskill-layout/`.
- **Télécommande IA sans MCP (plugin Codex `habit-tracker-control`)** : plugin local (`plugins/habit-tracker-control/`, déclaré dans `.agents/plugins/marketplace.json`) qui pilote l'instance du Pi via son API HTTP, avec CLI déterministe `habitctl.py`. Côté backend : modèle `RemoteOperation` + middleware `IdempotencyMiddleware` (clés d'idempotence), migration `v9_remote_operations.sql`, endpoints `GET /capabilities`, `GET /remote-operations/{idempotency_key}`, `POST /goals/with-substeps`.
- Doc contributeur du plugin déjà rédigée : `docs/adr/002-plugin-habit-tracker-control.md`, `docs/notes/habit-tracker-control-plugin.md`, `docs/notes/database-v9-remote-operations.md` ; renvois ajoutés dans `README.md` et `AGENTS.md`.
- Vérif : aucune commande **bot Telegram** modifiée (`git diff backend/src/bot/` vide) → COMMANDS-INDEX.md non concerné. Tests ajoutés/étendus : `test_softskills.py`, `test_habitctl.py`, `test_remote_control_api.py`.
- Docs : log.md ✔ · VISION.md — (périmètre inchangé : skills LLM & visualisation des skills déjà dans la Vision) · docs/wiki à régénérer (placement auto) ⏳ · COMMANDS-INDEX.md —
- Commit : non commité (working tree, branche `007-recap-3-3-3`)

## 2026-06-12 — docs(wiki): migrer le wiki HTML par-page vers Markdown + page Recap 3-3-3

- Migration de `docs/wiki/` de l'ancienne architecture (un fichier HTML autonome par page) vers l'architecture standard du skill `documentation` : `pages/*.md` (contenu en Markdown) + coquille `index.html` unique (routage par hash `#/slug`, rendu via `marked.js`) + `serve.sh`.
- Contenu des 13 pages converti fidèlement depuis les anciens HTML (ton et découpage préservés) ; 11 fichiers `*.html` par-page supprimés, `index.html`/`mindmap.html` régénérés comme coquilles.
- Nouvelle page `pages/recap-3-3-3.md` documentant le panneau Recap 3-3-3 (feature `007-recap-3-3-3`) : 3 sous-étapes d'objectifs + 3 softskills épinglées + 3 allostasies du jour, épinglage `PUT /api/v1/profile/pins` (`pinned_substeps` / `pinned_softskills`), navigation au clic, switch daily/weekly. Nœud ajouté au mindmap.
- Rafraîchissements ponctuels : `regles-et-variables.md` (commandes `/shop`, `/buy` jusqu'alors absentes), sections « Épinglage Recap 3-3-3 » dans `objectifs.md` et `softskills.md`, raccourci de validation dans `boutique-recompenses.md`.
- Vérif : 13 routes, 0 lien mort ; chaîne coquille → `pages/*.md` → assets servie en 200 via serveur local (`file://` reste bloqué par CORS, d'où `serve.sh`).
- Docs : log.md ✔ · VISION.md — · docs/wiki régénéré ✔ · COMMANDS-INDEX.md —
- Commit : non commité (sur branche `007-recap-3-3-3`)
