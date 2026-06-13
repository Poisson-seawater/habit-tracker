# Migration SQLite v9 — Remote Operations

La télécommande IA ajoute une seule table au schéma SQLite :
`remote_operations`. Aucune colonne ni contrainte d'une table métier existante n'a
été modifiée.

Fichiers concernés :

- `backend/src/database/models.py` : modèle SQLAlchemy `RemoteOperation` ;
- `backend/src/database/migrations/v9_remote_operations.sql` : migration SQL ;
- `backend/src/api/idempotency.py` : cycle de vie des enregistrements.

## Schéma ajouté

| Colonne | Type | Rôle |
|---|---|---|
| `id` | `INTEGER` | clé primaire |
| `user_id` | `INTEGER NOT NULL` | utilisateur, FK vers `users.id` avec cascade |
| `idempotency_key` | `VARCHAR(100) NOT NULL` | clé fournie par le client |
| `request_hash` | `VARCHAR(64) NOT NULL` | SHA-256 de la requête canonique |
| `method` | `VARCHAR(10) NOT NULL` | méthode HTTP |
| `path` | `VARCHAR(255) NOT NULL` | route appelée |
| `status` | `VARCHAR(20) NOT NULL` | état de l'opération |
| `http_status` | `INTEGER NULL` | statut de la réponse terminée |
| `response_body` | `TEXT NULL` | corps exact à rejouer |
| `created_at` | `DATETIME NOT NULL` | création |
| `updated_at` | `DATETIME NOT NULL` | dernière mise à jour |

La contrainte unique `(user_id, idempotency_key)` empêche deux opérations portant la
même clé pour un utilisateur. Un index existe sur `user_id`.

## Cycle de vie

1. Le middleware reçoit une mutation avec `Idempotency-Key`.
2. Il calcule un hash sur la méthode, le chemin, les paramètres, l'utilisateur et le
   corps JSON canonique.
3. Il crée et commit un enregistrement `in_progress` avant d'appeler la route.
4. Après la réponse, il stocke le statut HTTP et le corps, puis passe à `completed`.
5. Une exception non gérée fait passer l'enregistrement à `uncertain`.

États possibles :

- `in_progress` : requête enregistrée, résultat pas encore confirmé ;
- `completed` : réponse disponible et rejouable ;
- `uncertain` : le serveur ne peut pas garantir le résultat final.

Si une clé existante porte le même hash et est `completed`, la réponse enregistrée
est rejouée. Un hash différent ou un état non terminé produit un conflit `409`.

## Installation et démarrage

La migration SQL de référence est :

```bash
sqlite3 /chemin/habit_tracker.db \
  < backend/src/database/migrations/v9_remote_operations.sql
```

Le démarrage normal appelle aussi `Base.metadata.create_all()`. Une base existante
obtient donc la nouvelle table si elle manque, sans altérer ses tables existantes.

## Données qui ne sont pas dans cette migration

Les définitions de branches et de softskills ne sont pas déplacées dans SQLite.
Elles restent dans `softskills_tree.json` :

- local : `backend/src/data/softskills_tree.json` ;
- production : `/data/softskills_tree.json` ;
- surcharge possible : variable `SOFTSKILLS_CONFIG_PATH`.

SQLite conserve uniquement la progression utilisateur des softskills dans la table
existante `user_softskill_progress`.

## Sauvegarde et rétention

`remote_operations` est inclus automatiquement dans les snapshots SQLite existants.
La table peut croître avec le nombre de mutations distantes. Aucune purge automatique
n'est actuellement implémentée ; toute politique de rétention future devra conserver
assez longtemps les opérations pour couvrir les retries et diagnostics.

