---
name: doc-sync
description: >-
  Passage de relecture documentation à lancer APRÈS une modif et AVANT un push.
  Écrit une entrée dans log.md (toujours), met à jour VISION.md seulement si le périmètre
  produit bouge, et régénère la doc docs/wiki/ — en déléguant au skill `documentation` —
  quand le changement est visible côté utilisateur. Vérifie aussi COMMANDS-INDEX.md si une
  commande bot a changé. Ne commit ni ne push jamais. Déclencher sur "doc-sync",
  "sync la doc", "mets à jour la doc avant de push", "journal + doc avant push", ou /doc-sync.
user-invocable: true
argument-hint: "[--no-vision] [--no-doc] (par défaut : décide selon le diff)"
allowed-tools:
  - Bash(git *)
  - Read
  - Edit
  - Write
  - Skill
---

# doc-sync — relecture documentation avant push

Tu es lancé **après une modification de code et avant un push**. Ton rôle : empêcher la
doc de dériver, en un seul passage groupé. Tu touches au plus **trois artefacts** —
`log.md` (toujours), `VISION.md` (si le périmètre bouge), `docs/wiki/` (si le changement
est visible côté utilisateur) — plus les règles dures déjà en place (`COMMANDS-INDEX.md`,
ADRs). Tu **n'écris pas le wiki toi-même** : tu délègues au skill `documentation`.

> « avant push » : si l'utilisateur dit « avant pull », c'est un lapsus pour **push** —
> on entretient la doc juste avant de pousser ses changements.

## Principe non négociable

- **Jamais de commit ni de push.** Tu prépares la doc ; l'utilisateur pousse à la main
  selon `CONTRIBUTING.md`.
- **Tu confirmes avant d'écrire `VISION.md`.** Biais d'action → tu sers de frein : propose
  l'édition, attends le feu vert.
- **Tu ne touches pas** `docker-compose.yml`, le schéma DB (`models.py`), ni les contrats
  API (`/api/v1/*`, schémas Pydantic). Ce sont des zones « pas sans discussion ».
- L'entrée `log.md` est sûre à écrire directement (factuelle, additive). Le reste se décide
  selon le diff.

Arguments optionnels : `--no-vision` saute la Phase 2, `--no-doc` saute la Phase 3.

## Phase 0 — Cadrer le changement

Lis l'état du dépôt pour résumer ce qui a changé depuis le dernier push :

```bash
git -C "<racine projet>" status --short
git -C "<racine projet>" log --oneline @{upstream}..HEAD 2>/dev/null \
  || git -C "<racine projet>" log --oneline -10
git -C "<racine projet>" diff --stat
```

Si `@{upstream}` n'existe pas (branche locale sans remote), tombe sur les derniers commits
+ le diff non commité. Construis un **résumé court** : fichiers touchés, nature du
changement.

**Classe le changement** — c'est ce qui pilote les Phases 2 et 3 :

| Classe | Exemples | Conséquence |
|--------|----------|-------------|
| **Visible utilisateur** | commande bot ajoutée/modifiée, endpoint `/api/v1/*`, front (`app.js`), mécanique de scoring/XP/streak, nouveau concept | Phase 3 = régénérer le wiki |
| **Interne** | refactor, infra, tests, déps, fix sans effet visible | Phase 3 = skip |
| **Périmètre produit** | public cible, non-goal levé, piste future engagée | Phase 2 = proposer édition VISION |

Une modif peut être plusieurs classes à la fois. Annonce ta classification avant d'agir.

## Phase 1 — Entrée `log.md` (toujours)

`log.md` vit à la **racine** du projet, anti-chronologique (entrée la plus récente en haut).

- S'il n'existe pas, crée-le avec ce chapô puis la première entrée :

  ```markdown
  # Journal des changements

  > Une entrée par session / push, anti-chronologique. Rédigé par `/doc-sync` avant push.
  > Format : date, résumé `type(scope): description`, ce qui a changé, docs touchés.
  ```

- **Préprends** une nouvelle entrée en haut (sous le chapô), format :

  ```markdown
  ## 2026-06-10 — type(scope): résumé une ligne à l'impératif

  - <ce qui a changé, factuel, 1 puce par point notable>
  - Docs : <log.md ✔ · VISION.md ✔/—  · docs/wiki régénéré ✔/—  · COMMANDS-INDEX.md ✔/—>
  - Commit : `<hash court>` (ou « non commité » si rien n'est encore commité)
  ```

  Utilise la **date système** (aujourd'hui : `2026-06-10`) et le format de commit déjà
  utilisé dans le projet (`type(scope): description`, cf. `CONTRIBUTING.md`). Ton factuel,
  concis, zéro marketing.

## Phase 2 — `VISION.md` (conditionnel)

Saute si `--no-vision`, ou si la classe **Périmètre produit** n'est pas déclenchée (cas le
plus fréquent → no-op, dis-le et passe).

Sinon : repère la section concernée de `VISION.md` (`Public cible`, `Ce que le projet
N'EST PAS`, `Non-goals explicites`, `Pistes futures`), **propose une édition minimale**,
montre le diff proposé, et **attends confirmation explicite avant d'écrire**. N'invente
jamais une orientation produit non décidée.

## Phase 3 — Documentation `docs/wiki/` (conditionnel, délégué)

Saute si `--no-doc`, ou si la classe **Visible utilisateur** n'est pas déclenchée (→
explique pourquoi tu ne régénères pas, et passe).

Sinon :

1. **Délègue au skill `documentation`** (outil Skill, skill `documentation`) sur la racine
   du projet pour régénérer `docs/wiki/`. Ce skill a sa **propre porte de confirmation**
   (objectif ≤ 2 phrases, cas particuliers, langue) — tu passes le relais, tu ne réécris
   pas le HTML toi-même.
2. ⚠️ **Migration au 1er passage** : le wiki actuel est *un fichier HTML autonome par
   page* (`habitudes.html`, `objectifs.html`, …) ; le skill `documentation` produit une
   autre architecture (`pages/*.md` + **une seule** coquille `index.html` + `serve.sh`).
   La première régénération **remplace** donc le HTML par-page. **Préviens l'utilisateur**
   et propose, si c'est le premier passage, de lancer `documentation` à la main d'abord
   pour migrer et relire — puis `doc-sync` n'entretiendra que cette architecture.
3. Si la modif n'a changé **que le récit de la page d'accueil** (pas de nouveau concept),
   tu peux préférer le skill `documentation:moc` (refonte du MOC seul) plutôt qu'une
   régénération complète.

**Règles dures à honorer en plus** (indépendantes du wiki) :

- **Commande bot ajoutée / modifiée / supprimée** → vérifie et mets à jour
  `COMMANDS-INDEX.md` (règle dure du projet, rappelée dans `CLAUDE.md` et `CONTRIBUTING.md`).
- **Décision structurante** (stack, archi, contrat) → **suggère** (sans forcer) un ADR
  dans `docs/adr/` en copiant `docs/adr/000-template.md`.

## Phase 4 — Récap & étape suivante

Termine par un rapport court :

- Entrée `log.md` ajoutée (oui).
- `VISION.md` : édité après confirmation / non concerné.
- `docs/wiki/` : régénéré (via `documentation`) / non concerné (+ pourquoi) / migration
  proposée.
- `COMMANDS-INDEX.md` : mis à jour / non concerné.
- ADR : suggéré / non concerné.

Puis rappelle : **relis le diff, puis commit/push à la main** selon `CONTRIBUTING.md`
(`type(scope): description`, branche `feat/...` → PR). **Tu ne commits ni ne push pas.**

## Garde-fous (récap)

- Aucun commit, aucun push.
- Pas de `VISION.md` sans confirmation.
- Pas de toucher à `docker-compose.yml`, `models.py`, contrats `/api/v1/*`.
- Pas de fichier doc superflu : on n'écrit que `log.md`, et le wiki via `documentation`.
- Reste factuel, concis, sans marketing — cohérent avec le ton de la doc existante.
