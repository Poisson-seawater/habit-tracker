# Diagnostic Habit Tracker Control - Passation du 14 juin 2026

## Résumé

Le plugin `habit-tracker-control` n'est pas encore utilisable contre l'instance
distante `http://192.168.0.199:5000`.

La connexion réseau fonctionne et le serveur trouve bien l'utilisateur `Gabriel`.
L'échec survient à l'étape suivante :

```text
GET /api/v1/users         -> 200
GET /api/v1/capabilities  -> 404
```

Le CLI exige le protocole distant version `1`, annoncé par
`GET /api/v1/capabilities`. Le backend actuellement déployé est antérieur aux
changements de télécommande et ne fournit pas cet endpoint.

La cause racine est donc un décalage de version entre le plugin et le backend
déployé, pas un problème de réseau, d'utilisateur ou de parsing des softskills.

## Demande initiale

La demande était de consulter les compétences actuellement suivies avec le plugin.
La commande attendue est :

```bash
python3 plugins/habit-tracker-control/scripts/habitctl.py query softskills
```

Le CLI n'était pas configuré. La tentative de configuration a d'abord produit un
`404` sans indiquer quel endpoint avait échoué, ce qui a rendu le premier diagnostic
imprécis.

## Diagnostic effectué

### Configuration et cible

- Cible par défaut du CLI : `http://192.168.0.199:5000`
- Utilisateur demandé : `Gabriel`
- Fichier de configuration normal :
  `~/.config/habit-tracker-control/config.json`
- Aucun fichier de configuration valide n'a été créé.

La cible distante répond à `/api/v1/users`. Un test avec un utilisateur inexistant a
retourné correctement :

```json
{"status":"error","error":"No user matches '__plugin_probe_nonexistent__'."}
```

Cela confirme que le CLI atteint bien le serveur et reçoit sa liste d'utilisateurs.

### Contrat manquant

Le test réel isolé contre le Pi retourne maintenant :

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

Le fichier temporaire utilisé pour ce test n'a pas été créé, ce qui confirme que
`configure` reste transactionnel en cas d'incompatibilité.

### Écart entre le code et les conteneurs

Le code source actuel contient déjà :

- `GET /api/v1/capabilities`
- `GET /api/v1/remote-operations/{idempotency_key}`
- le middleware `IdempotencyMiddleware`
- les opérations atomiques de création d'objectif et de branche de softskills
- le modèle et la migration `remote_operations`

Le conteneur Docker local observé utilisait une image construite le 12 juin vers
18:26, alors que les changements du protocole ont été écrits vers 22:36-22:48. Son
code embarqué contenait `/api/v1/users`, mais pas `/api/v1/capabilities`.

L'instance distante présente le même symptôme et doit être considérée comme
antérieure au protocole version `1`.

## Correctif appliqué au CLI

Le diagnostic du plugin a été renforcé sans déployer ni reconfigurer le Pi.

Dans `plugins/habit-tracker-control/scripts/habitctl.py` :

- `ApiError` conserve maintenant la méthode HTTP et le chemin ;
- toutes les erreurs API gardent les champs JSON existants ;
- les champs `method` et `path` sont ajoutés lorsqu'ils sont connus ;
- un `404` sur `/api/v1/capabilities` reçoit un conseil de déploiement explicite ;
- la validation du protocole est partagée par `configure` et `doctor` ;
- une incompatibilité indique les versions attendue et reçue ;
- aucun fichier de configuration n'est écrit si les capacités sont absentes ou
  incompatibles.

La documentation de référence a été mise à jour dans
`docs/notes/habit-tracker-control-plugin.md`.

## Vérification

Résultats obtenus le 13 juin 2026 :

```text
backend/tests/test_habitctl.py  -> 12 tests réussis
backend/tests                   -> 91 tests réussis
python3 -m py_compile           -> réussi
git diff --check                -> réussi
contrôle des lignes > 88        -> aucune nouvelle ligne signalée
```

`black` n'était pas installé dans `.venv`, donc `black --check` n'a pas pu être
exécuté.

Le smoke test distant a été lancé avec `HABIT_TRACKER_CONFIG` pointant vers `/tmp`.
Il a confirmé le `404` ciblé et l'absence de fichier de configuration résiduel.

## État Git à surveiller

Les fichiers de la télécommande sont actuellement non suivis dans le worktree,
notamment :

```text
plugins/habit-tracker-control/
backend/src/api/idempotency.py
backend/src/database/migrations/v9_remote_operations.sql
backend/tests/test_habitctl.py
backend/tests/test_remote_control_api.py
docs/adr/002-plugin-habit-tracker-control.md
docs/notes/database-v9-remote-operations.md
docs/notes/habit-tracker-control-plugin.md
```

Le backend contient aussi des modifications non commitées dans `routes.py`,
`models.py`, `main.py` et `softskill_service.py`.

Ne pas reconstruire ou déployer depuis une révision Git qui n'inclut pas l'ensemble
cohérent de ces fichiers. Ne pas mélanger ce travail avec les autres suppressions et
modifications présentes dans le worktree sans revoir leur portée.

## Attention mémoire

Le service API est limité à 40 Mo. Une commande d'inspection ayant importé
`src.main:app` dans un second processus Python à l'intérieur du conteneur a dépassé
la marge disponible; le processus a terminé avec le code `137` et le conteneur API a
redémarré automatiquement.

Pour les prochains diagnostics :

- utiliser `habitctl.py`, les endpoints HTTP et `docker logs` ;
- éviter d'importer toute l'application dans un `docker exec python ...` ;
- vérifier `docker compose ps` après toute inspection lourde ;
- ne pas modifier les limites mémoire de `docker-compose.yml`.

## Travail restant pour rendre le plugin opérationnel

1. Revoir le diff complet de la télécommande et séparer les changements sans rapport.
2. S'assurer que tous les fichiers de protocole listés ci-dessus sont suivis et
   inclus dans la branche à déployer.
3. Relancer :

   ```bash
   PYTHONPATH=backend .venv/bin/pytest backend/tests
   ```

4. Déployer le backend contenant le protocole version `1` sur le Pi selon le workflow
   Git normal du projet.
5. Après déploiement, vérifier les endpoints légers :

   ```bash
   python3 plugins/habit-tracker-control/scripts/habitctl.py configure \
     --base-url http://192.168.0.199:5000 \
     --username Gabriel

   python3 plugins/habit-tracker-control/scripts/habitctl.py doctor
   ```

6. La réponse de `doctor` doit contenir :

   ```json
   {
     "status": "ok",
     "capabilities": {
       "protocol_version": 1
     }
   }
   ```

7. Tester enfin la demande initiale :

   ```bash
   python3 plugins/habit-tracker-control/scripts/habitctl.py query softskills
   ```

8. Vérifier que la réponse compacte contient les branches et les compétences de
   Gabriel, puis répondre à l'utilisateur en français.

## Critères de résolution

Le diagnostic est résolu lorsque :

- `configure` termine avec `status: configured` ;
- `doctor` termine avec `status: ok` et `protocol_version: 1` ;
- `query softskills` retourne les compétences sans accès direct à SQLite ;
- aucune modification de données métier n'est nécessaire pour effectuer la lecture ;
- l'API et le bot restent sous leurs limites mémoire après le déploiement.

## Hors périmètre réalisé

Conformément au choix fait pendant le diagnostic :

- aucun déploiement Pi n'a été effectué ;
- aucune configuration persistante du plugin n'a été écrite ;
- aucune donnée Habit Tracker n'a été modifiée ;
- aucun contrat API existant n'a été renommé ;
- aucun changement de commande Telegram n'a été effectué ;
- `COMMANDS-INDEX.md` n'avait donc pas à être modifié.
