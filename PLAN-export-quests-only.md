# Plan — Purger les vieux événements bio/segment de l'agenda Google

## Contexte

L'export Google Calendar (les DEUX boutons : « jour » du dashboard et « période »
des Paramètres) doit n'afficher QUE des quêtes (🎯), jamais de zones biologiques
(🧠) ni de segments Perfect Day (📅).

Le code actuel (working tree, non commité) ne **crée** déjà que des quêtes. Le
problème n'est donc pas la création mais le **nettoyage** :

- L'ancienne version (commit HEAD) de `export_typical_day_timeline` créait bio +
  segments + quêtes, tous tagués `extendedProperties.private.origin =
  "habit-tracker-timeline"`.
- La nouvelle version ne supprime, avant de réécrire, que les événements tagués
  `origin=habit-tracker-quest`. Les vieux `origin=habit-tracker-timeline`
  (🧠 bio + 📅 segments) créés par l'ancienne version **ne sont jamais supprimés**
  et restent indéfiniment dans l'agenda.
- Résultat : le bouton « période » couvre des jours contenant ces résidus →
  l'utilisateur croit que le bouton ré-exporte bio+segments.

Les deux boutons appellent la même fonction, donc le correctif profite aux deux.

## Changement (1 seul fichier)

`backend/src/services/google_sync_service.py` — fonction
`export_typical_day_timeline` (~ligne 377-396), phase « 1. Delete existing quest
events in this range ».

Actuellement le nettoyage fait un seul passage sur `origin=habit-tracker-quest`.
Le rendre multi-origine : supprimer AUSSI les événements legacy
`origin=habit-tracker-timeline` sur la même plage.

Contrainte API : les paramètres `privateExtendedProperty` multiples sont combinés
en **ET** (pas OU) par l'API Google Calendar. Il faut donc **deux passages de
list+delete distincts**, un par origine. Implémentation : boucler la requête
list+delete existante sur la liste `["habit-tracker-quest",
"habit-tracker-timeline"]` (le `timeMin`/`timeMax`/`maxResults` restent
identiques, seule la valeur `privateExtendedProperty` change).

La phase « 2. insert placed quests only » (lignes 398+) reste **inchangée** :
toujours quêtes uniquement.

Aucun autre fichier à toucher. Les textes UI/docstring ont déjà été corrigés.

## Vérification (localhost)

1. **Redémarrer le serveur** pour charger le code (le working tree a un gros diff
   non commité ; si le serveur tournait sur l'ancien code, c'est aussi une cause) :
   `PYTHONPATH=backend python3 backend/src/main.py`
2. Dans l'agenda Google « Agenda des Quêtes », vérifier qu'il reste des vieux
   🧠/📅 sur quelques jours passés (état avant fix).
3. Cliquer « Lancer l'exportation » (Paramètres) sur une plage couvrant ces jours.
4. Rafraîchir Google Calendar : les 🧠 et 📅 doivent avoir **disparu**, seules les
   quêtes 🎯 placées restent.
5. Re-cliquer le bouton « jour » du dashboard sur un de ces jours → toujours
   uniquement des 🎯, idempotent (pas de doublon).

Note : correctif self-healing et one-shot — après un export sur une plage, les
résidus legacy sont supprimés définitivement.
