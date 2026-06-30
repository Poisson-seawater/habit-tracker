# Plugin Habit Tracker Control

Ce document est la référence technique pour comprendre, maintenir et utiliser la
télécommande IA du Habit Tracker. Le plugin n'utilise ni MCP, ni accès direct à
SQLite, ni webhook.

## Architecture

```text
Question utilisateur
  -> skill spécialisé
  -> plugins/habit-tracker-control/scripts/habitctl.py
  -> HTTP(S) + X-User-ID + Idempotency-Key
  -> API FastAPI /api/v1
  -> SQLite ou /data/softskills_tree.json
```

Fichiers principaux :

| Fichier | Responsabilité |
|---|---|
| `plugins/habit-tracker-control/.codex-plugin/plugin.json` | manifeste du plugin |
| `plugins/habit-tracker-control/skills/habit-tracker-query/SKILL.md` | lectures |
| `plugins/habit-tracker-control/skills/habit-tracker-action/SKILL.md` | actions courantes |
| `plugins/habit-tracker-control/skills/habit-tracker-manage/SKILL.md` | modifications structurelles |
| `plugins/habit-tracker-control/scripts/habitctl.py` | protocole déterministe |
| `.agents/plugins/marketplace.json` | marketplace locale `personal` |
| `backend/src/api/idempotency.py` | journal et replay des mutations |
| `backend/src/api/routes.py` | capacités, récupération et routes atomiques |

## Pourquoi trois skills

`habit-tracker-query` charge uniquement les règles de consultation et produit une
réponse française concise. `habit-tracker-action` exécute immédiatement une action
explicite et bornée. `habit-tracker-manage` impose un aperçu et une confirmation pour
toute modification de structure.

Cette séparation évite de charger toutes les instructions à chaque demande et rend le
comportement prévisible selon le niveau de risque.

## Configuration

Le CLI se configure une fois :

```bash
python3 plugins/habit-tracker-control/scripts/habitctl.py configure \
  --base-url http://192.168.0.199:5000 \
  --username Gabriel
```

La configuration est enregistrée avec les permissions `0600` dans
`~/.config/habit-tracker-control/config.json`. Elle contient l'URL, le nom
d'utilisateur, son ID résolu et la version du protocole.

Le CLI refuse HTTP pour une adresse publique. HTTP est autorisé pour localhost, une
IP privée ou un nom `.local`. Les variables suivantes permettent d'isoler les tests :

- `HABIT_TRACKER_CONFIG` : chemin alternatif du fichier de configuration ;
- `HABIT_TRACKER_STATE_DIR` : répertoire alternatif des plans ;
- `XDG_STATE_HOME` : racine standard utilisée si la variable précédente est absente.

Vérification :

```bash
python3 plugins/habit-tracker-control/scripts/habitctl.py doctor
```

`doctor` vérifie `/health`, l'utilisateur et `/api/v1/capabilities`. Le protocole
actuel est la version `1`.

Les erreurs HTTP conservent le format JSON existant et indiquent aussi la méthode et
le chemin en cause. Si le serveur ne fournit pas `/api/v1/capabilities`, le CLI
retourne par exemple :

```json
{
  "status": "api_error",
  "http_status": 404,
  "error": {"detail": "Not Found"},
  "method": "GET",
  "path": "/api/v1/capabilities",
  "hint": "The Habit Tracker server does not expose protocol version 1. Deploy a backend version that provides GET /api/v1/capabilities before configuring this plugin."
}
```

Une version de protocole incompatible précise les versions attendue et reçue. Dans
les deux cas, `configure` n'écrit aucun fichier de configuration.

## Lectures

```bash
python3 plugins/habit-tracker-control/scripts/habitctl.py query goals
python3 plugins/habit-tracker-control/scripts/habitctl.py query goals \
  --name "Tour du monde"
```

Ressources : `status`, `profile`, `goals`, `habits`, `habit-calendar`, `todos`,
`notodos`, `softskills`, `rewards`, `history`, `templates`, `potentials`.

Les listes volumineuses sont compactées. Un nom est résolu dans cet ordre :

1. égalité normalisée, insensible aux accents et à la casse ;
2. correspondance partielle unique ;
3. erreur explicite si aucune ou plusieurs correspondances existent.

## Actions directes

```bash
python3 plugins/habit-tracker-control/scripts/habitctl.py act \
  habit-done --target "Routine matin"
```

Actions : `habit-done`, `habit-log`, `habit-skip`, `todo-complete`,
`notodo-fail`, `substep-complete`, `softskill-complete`, `softskill-reset`,
`reward-purchase`, `template-set`.

Chaque appel génère une clé d'idempotence. Si le client reçoit un timeout après
l'envoi, il retourne `status: ambiguous`. Il ne faut jamais répéter l'action :

```bash
python3 plugins/habit-tracker-control/scripts/habitctl.py recover KEY
```

## Modifications avec confirmation

Une modification structurelle suit toujours deux commandes :

```bash
python3 plugins/habit-tracker-control/scripts/habitctl.py plan \
  softskill-branch-with-skills \
  --data '{"name":"Bon vivant","skills":["Danse","Karaoké","Ukulélé"]}'

python3 plugins/habit-tracker-control/scripts/habitctl.py apply PLAN_ID
```

Le plan stocke la requête, une clé d'idempotence et le hash de l'état distant dans
`~/.local/state/habit-tracker-control/plans/`. Il expire après 10 minutes. `apply`
refuse de continuer si la cible, l'utilisateur ou l'état distant a changé.

Opérations disponibles :

- objectifs : `goal-create`, `goal-with-substeps`, `goal-update`, `goal-delete` ;
- sous-étapes : `substep-create`, `substep-update`, `substep-delete`, `substep-link` ;
- habitudes : `habit-create`, `habit-update`, `habit-delete` ;
- tâches : `todo-create`, `notodo-create` ;
- profil : `template-save`, `pins-update` ;
- récompenses : `reward-create`, `reward-update`, `reward-delete` ;
- softskills : `softskill-branch-create`, `softskill-branch-with-skills`,
  `softskill-branch-update`, `softskill-branch-delete`, `softskill-create`,
  `softskill-update`, `softskill-delete`, `softskill-test`.

Le CLI génère de façon stable les slugs et les couleurs de branche. Il n'invente pas
de description, récompense, effort, prérequis ou relation métier.

## Contrat serveur ajouté

`GET /api/v1/capabilities` annonce la version du protocole, le support de
l'idempotence et les opérations atomiques.

`GET /api/v1/remote-operations/{key}` permet d'inspecter une mutation. Une même clé
et une même requête terminée rejouent la réponse mémorisée avec
`Idempotency-Replayed: true`. Une clé réutilisée pour une autre requête retourne
`409`. Une opération encore `in_progress` ou devenue `uncertain` retourne également
`409` lors d'un retry.

Les anciens clients restent compatibles : le middleware n'intervient que lorsqu'une
mutation contient `Idempotency-Key`.

## Persistance des softskills

Les branches et nœuds sont des définitions globales, tandis que leur progression est
par utilisateur dans SQLite. En production, les définitions mutables sont conservées
dans `/data/softskills_tree.json`.

Au premier démarrage, le fichier packagé est copié vers `/data` s'il n'existe pas.
Les changements utilisent `flock`, un fichier temporaire, `fsync` puis
`os.replace`. Le cache surveille la date de modification afin que les processus API
et bot voient les changements.

## Maintenance

Lors d'une nouvelle capacité distante :

1. ajouter ou adapter la route API sans casser le contrat existant ;
2. ajouter l'opération déterministe dans `habitctl.py` ;
3. affecter l'opération au bon skill ;
4. incrémenter `protocol_version` seulement en cas d'incompatibilité ;
5. compléter les tests API et CLI ;
6. mettre à jour ce document et, si nécessaire, l'ADR.

Déployer le backend avant de lancer `configure` contre le Pi. Une absence de
`/api/v1/capabilities` signifie que le serveur distant n'a pas encore cette version.

## Limites de sécurité

`X-User-ID` est un mécanisme de sélection d'utilisateur, pas une authentification.
Le plugin est conçu pour un réseau privé. Une exposition Internet exige HTTPS et une
authentification placée devant l'API.
