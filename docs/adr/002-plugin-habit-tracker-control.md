# ADR 002 — Télécommande IA déterministe sans MCP

- **Statut** : accepté
- **Date** : 2026-06-12
- **Décideurs** : Gabriel

## Contexte

Un agent IA doit pouvoir répondre à des questions sur le Habit Tracker et modifier
l'instance distante. Le mécanisme doit consommer peu de contexte, rester prévisible,
éviter les doubles écritures et fonctionner sur le Raspberry Pi sans ajouter de
serveur MCP ni de dépendance lourde.

Les demandes couvrent trois niveaux de risque :

- lecture de données, par exemple « quels sont mes objectifs ? » ;
- action courante et bornée, par exemple compléter une habitude ;
- modification de structure, par exemple créer une branche de softskills.

## Décision

Utiliser le plugin local `habit-tracker-control`, composé de trois skills courts et
d'un CLI Python standard library :

```text
agent -> skill -> habitctl.py -> API FastAPI -> SQLite ou softskills_tree.json
```

Les skills ne contiennent que les règles de décision :

- `habit-tracker-query` pour les lectures ;
- `habit-tracker-action` pour les actions explicites et bornées ;
- `habit-tracker-manage` pour les créations, modifications et suppressions.

Le CLI `plugins/habit-tracker-control/scripts/habitctl.py` porte toute la logique
déterministe : validation de cible, résolution des noms, construction des requêtes,
plans temporaires, vérification d'état et récupération après timeout.

Les lectures et actions explicites s'exécutent directement. Une modification de
structure suit obligatoirement `plan -> confirmation -> apply`. Un plan expire après
10 minutes et ne peut être appliqué si l'état distant observé a changé.

Chaque écriture reçoit une clé `Idempotency-Key`. L'API journalise la requête et sa
réponse dans `remote_operations`, ce qui permet de rejouer une réponse connue ou
d'inspecter une issue incertaine sans répéter l'action.

Deux opérations multi-objets sont atomiques :

- `POST /api/v1/goals/with-substeps` ;
- `POST /api/v1/softskills/branches-with-skills`.

Les définitions de softskills restent dans un fichier JSON. En production, ce fichier
mutable est placé dans `/data/softskills_tree.json`, sur le même volume persistant que
SQLite. Les écritures utilisent un verrou de fichier et un remplacement atomique.

Le réseau privé peut utiliser HTTP. Une cible HTTP publique est refusée par le CLI ;
elle doit utiliser HTTPS. Le header `X-User-ID` est conservé pour compatibilité.

## Alternatives envisagées

- **Serveur MCP** : rejeté, car il ajoute un processus, du protocole et de la
  configuration pour des opérations déjà exposées par l'API REST.
- **Webhooks** : rejetés pour le contrôle interactif. Ils conviennent aux événements
  poussés, pas aux questions et modifications synchrones initiées par l'agent.
- **Instructions uniquement dans un skill** : rejetées, car l'agent devrait reconstruire
  les requêtes HTTP et les règles de sécurité à chaque appel.
- **Accès SQLite distant direct** : rejeté, car il contourne la logique métier,
  l'idempotence et les validations de l'API.
- **Un seul skill universel** : rejeté, car il augmente le contexte chargé et mélange
  des niveaux de risque différents.

## Conséquences

- Le contexte chargé par l'agent reste faible et spécialisé.
- Les mutations sont prévisibles, auditables et résistantes aux retries.
- Le plugin dépend de la version de protocole annoncée par `/api/v1/capabilities`.
- Le backend doit être déployé avant de configurer le CLI contre une instance distante.
- `X-User-ID` identifie un utilisateur mais n'authentifie pas un appel : l'API doit
  rester sur un réseau privé ou être placée derrière une vraie couche d'authentification.
- Les CRUD absents de l'API restent indisponibles au plugin.

