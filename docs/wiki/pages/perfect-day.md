# Perfect Day

Tu sais ce que c'est, une journée où tu as traité ce qui était prévu. Ici, ça porte un nom : le Perfect Day. C'est le jour où toutes tes habitudes planifiées sont validées, loggées ou skippées avec une raison, et il rapporte 5 XP.

## Comment il se calcule

1. Le système regarde les [habitudes](#/habitudes) actives prévues pour la date.
2. Chaque habitude prévue doit être validée (`/done`), loggée (`/log`) ou skippée (`/skip ... raison:`).
3. Le [template](#/templates-de-jour) actif (`rest`, `regular`, `hustle`) donne le contexte de la journée, l'agenda type et les budgets d'effort.
4. Si **toutes** les habitudes prévues sont traitées, c'est un Perfect Day.

> Les primes donnent de l'XP direct, mais elles ne remplacent pas les habitudes prévues pour le Perfect Day.

## Récompense et clôture

- Un Perfect Day décroché te donne **+5 XP** permanents (voir [XP, niveau & or](#/stats-xp-niveau-or)).
- La journée se fige à **23h59** (clôture automatique) ou via le bouton « Terminer la journée ». Le bot publie alors le bilan de la guilde dans le groupe.

## Streak

Le streak compte les Perfect Days consécutifs. Un [skip](#/regles-et-variables) justifié ne l'interrompt pas ; laisser une habitude prévue sans traitement, si.
