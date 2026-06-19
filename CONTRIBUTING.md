# Contribuer

Projet perso à deux, en vibe coding avec Claude Code. But de ce doc : qu'on bosse en
parallèle sans se marcher dessus et sans casser la prod.

## Branches

| Branche | Rôle |
|---------|------|
| `main` | Prod stable. C'est ce qui tourne sur le Pi. On n'y pousse **jamais** en direct. |
| `dev` | Intégration. Les features finies arrivent ici avant `main`. |
| `feat/nom-court` | Une feature = une branche. Ex. `feat/streak-counter`, `feat/edit-habit`. |

Autres préfixes (même logique) : `fix/...` (correction), `docs/...` (doc),
`refactor/...` (refonte sans changement de comportement).

Flux normal :

```
feat/ma-feature  →  PR vers  dev  →  (test OK)  →  PR vers  main
```

> ⚠️ Le repo utilise encore `master` comme branche par défaut. Pour adopter cette
> convention : `git branch -m master main` puis pousser et mettre à jour la branche
> par défaut côté GitHub. En attendant, la CI tourne aussi sur `master`.

## Pull Requests

- **Toute** fusion vers `dev` ou `main` passe par une PR. Pas de merge direct.
- **1 review minimum** avant de merger (l'autre frère relit).
- Remplir le template de PR (`.github/pull_request_template.md`).
- La CI doit être verte (voir `.github/workflows/ci.yml`).
- On garde les PRs **petites** : plus c'est petit, plus c'est vite relu.

## Commits

Format simple, type conventionnel :

```
type(scope): description courte à l'impératif
```

- **type** : `feat`, `fix`, `refactor`, `docs`, `test`, `chore`.
- **scope** : la partie touchée — `front`, `api`, `bot`, `db`, `ci`, `docs`…
- **description** : courte, à l'impératif, en minuscule.

Exemples :

```
feat(front): add streak counter
fix(api): correct habit delete endpoint
refactor(bot): split parser from listener
docs(readme): add local setup section
```

## Avant de commencer une feature : créer une issue

1. Ouvrir une **issue GitHub** décrivant **le quoi** et **le pourquoi** (pas le comment).
2. Pour une vraie feature produit, vérifier qu'elle colle à la vision décrite dans [`README.md`](./README.md).
3. Créer la branche `feat/...` liée à l'issue.
4. Coder, ouvrir la PR, lier l'issue (`Closes #12`).

Pour les features cadrées via Spec Kit, créer la spec dans `specs/` avant de coder.
Pour un petit fix, l'issue peut rester ultra-légère.

## Rappels spécifiques au projet

- **Schéma DB et contrats d'API** : on ne touche pas sans en parler d'abord (cf. `CLAUDE.md`).
- **Commandes du bot Telegram** : si tu ajoutes / modifies une commande, mets à jour
  `COMMANDS-INDEX.md` (règle dure du projet).
- **`docker-compose.yml`** : marqué `skip-worktree` (réglages par-machine). Ne pas le
  dé-skip ni committer tes valeurs locales.
- **Décisions d'archi** : si un choix structurant est pris, l'écrire dans `docs/adr/`.
