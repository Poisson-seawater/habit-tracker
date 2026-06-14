# Journal des changements

> Une entrée par session / push, anti-chronologique. Rédigé par `/doc-sync` avant push.
> Format : date, résumé `type(scope): description`, ce qui a changé, docs touchés.

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
