# Perfect Day

Tu sais ce que c'est, une journée où tu as traité ce qui était prévu. Ici, ça porte un nom : le Perfect Day. C'est le jour où toutes tes habitudes planifiées sont validées, loggées ou skippées avec une raison, et il rapporte 5 XP.

## Comment il se calcule

1. Le système regarde les [habitudes](#/habitudes) actives prévues pour la date et compatibles avec le type de journée actif.
2. Chaque habitude prévue doit être validée (`/done`), loggée (`/log`) ou skippée (`/skip ... raison:`).
3. Le [template](#/templates-de-jour) actif (`rest`, `regular`, `hustle`) donne le contexte de la journée, l'agenda type et les budgets d'effort.
4. Si **toutes** les habitudes prévues sont traitées, c'est un Perfect Day.

Une habitude marquée ratée rend la journée non parfaite. À l'inverse, une habitude hors type de journée ne bloque pas le Perfect Day, même si tu la valides manuellement : son log et sa progression restent enregistrés sans l'ajouter aux exigences du jour.

La vue « Perfect Day » du dashboard affiche aussi l'[agenda vertical et la timeline biologique](#/agenda-timeline) : ta référence de rythme perso en haut, l'agenda du jour à gauche, la jauge de budget d'effort à droite.

> Les primes donnent de l'XP direct, mais elles ne remplacent pas les habitudes prévues pour le Perfect Day.

## Récompense et clôture

- Un Perfect Day décroché te donne **+5 XP** permanents (voir [XP, niveau & or](#/stats-xp-niveau-or)).
- La journée se fige à **21h30** : le score du jour est calculé, l'XP attribuée, et le bot publie le bilan de la guilde dans le groupe. À **00:00**, un second passage regarde la veille et remet à 0 le streak de chaque habitude prévue qui n'a été ni traitée ni skippée.

## Corriger la veille

Depuis l'agenda, les boutons **Hier / Aujourd'hui** ouvrent une fenêtre de correction limitée à la veille. Tu peux y enregistrer une quête accomplie ou un No-Todo échoué qui avait été oublié. Telegram offre la même correction avec `--yesterday` sur `/done`, `/log` et `/fail`.

La correction recalcule la journée d'hier : statut du Perfect Day, récompense de 5 XP si ce statut change, et streaks concernés. Avant-hier et les dates plus anciennes restent verrouillés.

## Streak

Le streak compte les Perfect Days consécutifs. Un [skip](#/regles-et-variables) justifié ne l'interrompt pas ; laisser une habitude prévue sans traitement, si.
