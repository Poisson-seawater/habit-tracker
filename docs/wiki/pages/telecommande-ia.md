# Télécommande IA (sans MCP)

Un agent IA peut consulter et modifier l'instance distante du Habit Tracker (le Raspberry Pi) en passant par son **API HTTP** — sans MCP. C'est l'équivalent programmable du bot Telegram : lister les objectifs, valider une habitude, créer une branche de compétences, etc.

> [!note] Pour qui ? Cette page vise le profil **dev / power-user**. L'usage quotidien passe par le bot Telegram ou le dashboard.

## Le plugin `habit-tracker-control`

Le pilotage est packagé en **plugin Codex** local (`plugins/habit-tracker-control/`, déclaré dans `.agents/plugins/marketplace.json`). Il fournit :

- des **skills** compactes — formuler une intention en langage naturel (*« Valide mon habitude de lecture »*, *« Ajoute une branche de compétences Bon vivant »*) ;
- une **CLI déterministe** `habitctl.py` qui traduit ces intentions en appels HTTP vers l'API du Pi.

Déterministe = même commande → même appel → même effet. L'agent n'improvise pas le format des requêtes.

Ces appels passent par l'API, pas par un navigateur : ils s'authentifient avec l'en-tête `Authorization: Bearer <HABIT_API_TOKEN>` plutôt qu'avec le cookie d'appareil du dashboard. Voir [Authentification & appareils](#/authentification) pour le détail des couches.

## Lectures utiles

La CLI sait consulter les ressources courantes avec `habitctl.py query ...`. Exemples :

```bash
python3 plugins/habit-tracker-control/scripts/habitctl.py query agenda
python3 plugins/habit-tracker-control/scripts/habitctl.py query habits
python3 plugins/habit-tracker-control/scripts/habitctl.py query archived-habits
```

`archived-habits` est une lecture pure : elle liste les quêtes archivées avec leur `id`, nom, fréquence, date d'archive et source. Elle ne désarchive rien toute seule.

## Idempotence : rejouer sans casser

Chaque opération d'écriture porte une **clé d'idempotence**. Le backend mémorise l'opération (table `remote_operations`) : si la même requête est renvoyée (timeout réseau, reprise de l'agent), elle n'est **pas exécutée deux fois** — la réponse d'origine est rendue. On peut donc relancer une commande sans créer de doublon.

## Endpoints dédiés

- `GET /api/v1/capabilities` — ce que la télécommande sait faire (découverte par l'agent).
- `GET /api/v1/remote-operations/{idempotency_key}` — relire le résultat d'une opération déjà jouée.
- `POST /api/v1/goals/with-substeps` — créer un objectif et ses sous-étapes en un seul appel.
- `POST /api/v1/softskills/branches-with-skills` — créer une branche de compétences entière (positions allouées automatiquement, cf. [Softskills](#/softskills)).

## Où creuser

Le détail technique vit dans le dépôt (hors wiki) :

- Fonctionnement du plugin → `docs/notes/habit-tracker-control-plugin.md`
- Migration SQLite v9 (idempotence) → `docs/notes/database-v9-remote-operations.md`
- Décision d'architecture → `docs/adr/002-plugin-habit-tracker-control.md`
