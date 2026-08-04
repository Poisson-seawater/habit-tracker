# Habitudes (Quêtes)

Une habitude, c'est une action que tu répètes régulièrement, selon un planning. Chaque fois que tu la valides, elle traite une partie de ton [Perfect Day](#/perfect-day). Et sur la durée, c'est elle qui te fait avancer vers tes [objectifs](#/objectifs).

## Deux types

| Type | Validation | Commande |
|---|---|---|
| Binaire | faite / pas faite (une fois par jour) | `/done <habitude>` |
| Quantitative | une mesure (ex. 30min, 5km) | `/log <habitude> <valeur><unité>` |

## Suivi libre dans le dashboard

Une quête binaire peut afficher dans le dashboard un seul outil de suivi auxiliaire :

- un **compteur libre**, pour saisir directement une valeur absolue avec son unité (par exemple `12 pages`) ;
- une **checklist**, pour cocher les éléments préparés sur la quête.

Ces deux modes sont mutuellement exclusifs sur une même quête. Le compteur libre et la checklist sont disponibles uniquement dans le dashboard : les commandes Telegram continuent d'utiliser la validation habituelle.

Le suivi est séparé pour **aujourd'hui** et **hier**, puis repart sur un nouvel état chaque jour. Modifier le compteur ou cocher un élément ne valide pas la quête, ne donne ni XP ni Or, et ne modifie ni le score du jour ni le streak. Pour déclarer la quête accomplie et faire progresser le jeu, utilise toujours explicitement **Valider / Fait** dans le dashboard ou `/done <habitude>` sur Telegram.

## Valider en un clic depuis Telegram

`/quetes` (alias `/habitudes`, `/habits` et `/quests`) affiche le **panneau des quêtes du jour** : un bouton par habitude prévue aujourd'hui, plus celles déjà traitées même hors planning. Chaque bouton porte son état : ⬜ à faire, ✅ validée, `(1/3)` pour une habitude à cible multiple, 📊 avec le total loggé, ⏭️ skippée, ❌ ratée. Au-delà de 20 quêtes, les flèches permettent de changer de page.

Un clic sur une habitude binaire la valide immédiatement et redessine le panneau sur place. Une habitude quantitative demande d'abord la valeur (ex. `30`), puis actualise le panneau d'origine. Une fois sa cible atteinte, ou si elle est skippée ou ratée, la quête reste visible mais son bouton ne crée plus de validation. Les répétitions supplémentaires d'une quête à cible restent possibles avec `/done` ou `/log`. Le bouton **🔄 Rafraîchir** recharge l'état sans rien valider, et une habitude déjà ratée doit d'abord être annulée avec `/fail_habit <nom> --undo`.

Chaque panneau appartient à la personne qui l'a ouvert : un autre membre du groupe ne peut ni le remplacer par ses propres quêtes ni utiliser ses boutons. Les quêtes privées apparaissent sous le nom « Chose secrète 🔒 », comme dans `/status`, car le panneau peut vivre dans le groupe.

## Planning

Une habitude n'est due que certains jours (tous les jours, ou par ex. lundi + mercredi). Elle peut aussi être associée à un ou plusieurs types de journée : `rest`, `regular` et `hustle`. Les trois sont sélectionnés par défaut, y compris pour les anciennes habitudes.

Le jour venu, l'agenda, le Perfect Day, `/status` et `/liste habit` ne retiennent que les habitudes compatibles à la fois avec le planning et le type de journée actif. Une habitude `hustle` n'apparaît donc pas dans l'agenda d'un jour `rest` et ne bloque pas son Perfect Day.

Tu peux quand même valider manuellement une habitude hors type de journée avec `/done`, `/log`, l'API ou les contrôles du dashboard. Le log reste visible et la progression normale du streak s'applique, mais cette habitude ne devient pas une exigence du Perfect Day de ce jour.

## Banque des quêtes

Depuis le dashboard, le bouton **Banque** dans le panneau « Quêtes à placer » liste les quêtes actives qui existent mais ne sont pas visibles pour la date affichée. Chaque ligne indique pourquoi elle est absente : mauvais jour de semaine, mauvais type de journée, quête mensuelle pas encore due, skill non épinglée, ou ancien format de quête d'objectif.

La banque est séparée des archives : une quête « pas ce jour » reste active et peut revenir automatiquement à sa prochaine date prévue. Une quête archivée, elle, a été retirée explicitement du quotidien.

## Effort et Perfect Day

Les habitudes alimentent le [Perfect Day](#/perfect-day) par leur statut : validée, loggée, skippée, ratée ou restante. Une habitude quantitative peut avoir un **plafond de log par jour** (daily cap) et une unité. Certaines habitudes portent aussi un type et une durée d'effort (`musculaire`, `cerveau`, `emotionnel_social`, `creatif_divergent`) pour les budgets de journée. Elles ne donnent **pas** d'XP direct — contrairement aux [primes](#/primes-todo).

## Archiver une quête

Depuis le dashboard, le bouton **Archives** dans le panneau « Quêtes à placer » ouvre la liste des quêtes archivées. Une quête archivée disparaît de l'[agenda](#/agenda-timeline), de « Quêtes à placer » et des placements sauvegardés dans les templates de jour. C'est fait pour retirer une quête du quotidien sans la supprimer définitivement.

La liste Archives affiche la date d'archive, la fréquence, la source et les groupes de noms proches ou identiques. Le badge « actif aussi » signale qu'une quête active porte le même nom normalisé qu'une archive.

Le bouton **Désarchiver** remet la quête dans la banque active si elle est encore éligible à la date affichée, mais il ne restaure pas ses anciens créneaux : elle revient non placée, à replacer manuellement si besoin.

## Déclarer une habitude ratée

Une habitude prévue peut être marquée **ratée** depuis l'agenda, l'onglet Habitudes, l'API ou Telegram avec `/fail_habit <nom>`. Cette action est refusée si l'habitude est déjà complétée ou skippée aujourd'hui. Le statut raté retire **jusqu'à 5 XP** (sans passer sous le niveau 1 à 0 XP), empêche le Perfect Day et remet immédiatement le streak de cette habitude à 0. Répéter l'action ne retire pas d'XP supplémentaire.

Tu peux annuler ce statut le même jour depuis l'interface, l'API ou avec `/fail_habit <nom> --undo`. Le montant d'XP réellement retiré est restauré une seule fois. Il faut d'abord annuler l'échec avant de logger une progression. L'annulation retire le statut raté, mais le streak n'est pas restauré immédiatement : il reste à 0 jusqu'au recalcul de fin de journée.

## Corriger hier

Le sélecteur **Hier / Aujourd'hui** de l'agenda permet de revenir sur la veille pour enregistrer une quête réellement accomplie mais oubliée. Sur Telegram, ajoute `--yesterday` à `/done` ou `/log`. La fenêtre est volontairement limitée à aujourd'hui et hier : une date plus ancienne est refusée.

Une correction d'hier recalcule la journée concernée, notamment son Perfect Day et les streaks. Elle ne permet pas d'éditer librement tout l'historique.

## Séparées des objectifs

Les habitudes et les [objectifs](#/objectifs) sont **séparés** : faire des habitudes ne valide pas tout seul une sous-étape d'objectif. Le lien est d'**intention** — la régularité construite par les habitudes rend les objectifs atteignables.

## Paliers d'ancrage (30J / 90J)

Pour récompenser la constance et vous motiver à installer des habitudes sur le long terme, le jeu intègre des paliers de continuité (streaks) :
- **Seuil des 30 jours (Adoption initiale) :** Atteindre un streak de 30 jours consécutifs sur une habitude déclenche une célébration visuelle et vous octroie **+100 XP** et **+50 Or**.
- **Seuil des 90 jours (Ancrage définitif) :** Atteindre un streak de 90 jours consécutifs déclenche une célébration majeure et vous octroie **+300 XP** et **+150 Or**.

### Comment fonctionne le streak d'une habitude ?

Le streak (votre série de succès consécutifs) est géré selon les règles suivantes :

* **Progression (+1) :** Chaque fois que vous validez l'habitude (`/done` ou `/log`), votre streak progresse selon la suite des validations attendues. Une validation manuelle hors type de journée reste comptabilisée.
* **Gel (Pause) :** Si vous ne pouvez pas faire l'habitude un jour où elle est due, vous pouvez utiliser la commande `/skip <habitude> raison: <texte>`. Votre streak est mis en pause (il ne retombe pas à 0, mais n'augmente pas non plus).
* **Réinitialisation (0) :** Marquer explicitement l'habitude ratée remet le streak à 0 immédiatement. Une habitude prévue laissée sans traitement est finalisée à 0 lors du passage de minuit.
* **Jours non-planifiés :** Une journée où l'habitude n'est requise ni par son planning ni par son type de journée ne brise pas le streak. Si tu la valides quand même manuellement, cette validation est conservée.
