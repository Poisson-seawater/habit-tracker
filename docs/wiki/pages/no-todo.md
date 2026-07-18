# No-Todo (Règles à ne pas enfreindre)

Tu connais les bonnes résolutions du genre « aujourd'hui, pas de snooze ». Un No-Todo, c'est exactement ça : une règle que tu t'engages à ne pas enfreindre aujourd'hui. C'est l'inverse d'une [prime](#/primes-todo) : au lieu de faire, tu t'abstiens.

## Fonctionnement

- `/liste notodo` — voir les règles actives.
- `/add notodo <titre>` — ajouter une règle.
- `/fail <nom>` — déclarer que tu l'as enfreinte aujourd'hui (accepte un morceau du nom).
- `/fail <nom> --yesterday` — déclarer le lendemain un échec oublié pour hier.

Les No-Todos échoués apparaissent dans `/status`. Ils tracent les dérapages du jour, à côté du [Perfect Day](#/perfect-day).

Sur le dashboard, utilise le bouton **Hier** de l'agenda : les No-Todos affichent alors leur état pour la veille et peuvent y être déclarés échoués. Le bouton **Aujourd'hui** revient au jour courant. Comme pour les corrections de quêtes, la fenêtre est limitée à aujourd'hui et hier ; une date plus ancienne est refusée.
