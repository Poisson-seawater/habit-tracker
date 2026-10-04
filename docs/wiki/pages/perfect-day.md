# Perfect Day

Le Perfect Day représente les **Must** de la journée : les actions de base à traiter chaque jour tout en gardant du temps libre. Chaque Must prévu doit être validé, loggé ou skippé avec une raison. Les quêtes liées aux objectifs et compétences sont suivies à part.

Une journée sans Must est neutre : elle ne donne pas les 5 XP, ne compte pas comme un échec et met le streak Perfect Day en pause. L'horaire « Journée type » à droite des Must est une référence en lecture seule ; ses blocs ne se cochent pas.

## Comment il se calcule

1. Le système regarde uniquement les quêtes **Must** actives prévues pour la date et compatibles avec le type de journée actif.
2. Chaque habitude prévue doit être validée (`/done`), loggée (`/log`) ou skippée (`/skip ... raison:`).
3. Le [template](#/templates-de-jour) actif (`rest`, `regular`, `hustle`) donne le contexte de la journée et les budgets d'effort.
4. Si **toutes** les habitudes prévues sont traitées, c'est un Perfect Day.

Une habitude marquée ratée rend la journée non parfaite. À l'inverse, une habitude hors type de journée ne bloque pas le Perfect Day, même si tu la valides manuellement : son log et sa progression restent enregistrés sans l'ajouter aux exigences du jour.

Sur le Home, [« Quêtes du jour »](#/agenda-timeline) montre toutes les habitudes prévues pour la date, avec leur statut et leurs actions de validation. Aucun placement horaire n'est nécessaire pour le Perfect Day.

> Les primes donnent de l'XP direct, mais elles ne remplacent pas les habitudes prévues pour le Perfect Day.

## Récompense et clôture

- Un Perfect Day décroché te donne **+5 XP** permanents (voir [XP, niveau & or](#/stats-xp-niveau-or)).
- La journée se fige à **21h30** : le score du jour est calculé, l'XP attribuée, et le bot publie le bilan de la guilde dans le groupe. À **00:00**, un second passage regarde la veille et remet à 0 le streak de chaque habitude prévue qui n'a été ni traitée ni skippée.

## Corriger la veille

Dans « Quêtes du jour », les boutons **Hier / Aujourd'hui** ouvrent une fenêtre de correction limitée à la veille. Tu peux y enregistrer une quête accomplie ou un No-Todo échoué qui avait été oublié. Telegram offre la même correction avec `--yesterday` sur `/done`, `/log` et `/fail`.

La correction recalcule la journée d'hier : statut du Perfect Day, récompense de 5 XP si ce statut change, et streaks concernés. Avant-hier et les dates plus anciennes restent verrouillés.

## Streak

Le streak compte les Perfect Days consécutifs. Un [skip](#/regles-et-variables) justifié ne l'interrompt pas ; laisser une habitude prévue sans traitement, si.
