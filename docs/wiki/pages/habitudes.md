# Habitudes (Quêtes)

Les quêtes récurrentes sont des **Must**, socle du [Perfect Day](#/perfect-day), ou des **Compétences** avec une pratique et un streak propres. Épingler une compétence crée sa quête quotidienne liée. Pour les objectifs, le [Recap](#/recap-3-3-3) affiche jusqu'à trois sous-étapes choisies librement parmi le Top 3 : ces quêtes se terminent avec **Valider la quête** dans le Recap ou dans Objectifs & Graphes, avec leur Or habituel, sans validation quotidienne ni streak. Les anciennes quêtes quotidiennes de rôle Objectif restent en pause avec leur historique conservé.

## Deux types

| Type | Validation | Commande |
|---|---|---|
| Binaire | faite / pas faite (une fois par jour) | `/done <habitude>` |
| Quantitative | une mesure (ex. 30min, 5km) | `/log <habitude> <valeur><unité>` |

## Suivi libre dans le dashboard

Une quête binaire peut afficher dans le dashboard un seul outil de suivi auxiliaire :

- un **compteur libre**, pour saisir directement une valeur absolue avec son unité (par exemple `12 pages`) ;
- une **checklist**, pour cocher les éléments préparés sur la quête.

Ces deux modes sont mutuellement exclusifs sur une même quête. La checklist est réservée aux quêtes Must ; les quêtes Objectif et Compétence n'en ont pas. Le compteur libre et la checklist sont disponibles uniquement dans le dashboard : les commandes Telegram continuent d'utiliser la validation habituelle.

Le suivi est séparé pour **aujourd'hui** et **hier**, puis repart sur un nouvel état chaque jour. Modifier le compteur ou cocher un élément ne valide pas la quête, ne donne ni XP ni Or, et ne modifie ni le score du jour ni le streak. Pour déclarer la quête accomplie et faire progresser le jeu, utilise toujours explicitement **Valider / Fait** dans le dashboard ou `/done <habitude>` sur Telegram.

## Valider en un clic depuis Telegram

`/quetes` (alias `/habitudes`, `/habits` et `/quests`) affiche le **panneau des quêtes du jour** : un bouton par habitude prévue aujourd'hui, plus celles déjà traitées même hors planning. Chaque bouton porte son état : ⬜ à faire, ✅ validée, `(1/3)` pour une habitude à cible multiple, 📊 avec le total loggé, ⏭️ skippée, ❌ ratée. Au-delà de 20 quêtes, les flèches permettent de changer de page.

Un clic sur une habitude binaire la valide immédiatement et redessine le panneau sur place. Une habitude quantitative demande d'abord la valeur (ex. `30`), puis actualise le panneau d'origine. Une fois sa cible atteinte, ou si elle est skippée ou ratée, la quête reste visible mais son bouton ne crée plus de validation. Les répétitions supplémentaires d'une quête à cible restent possibles avec `/done` ou `/log`. Le bouton **🔄 Rafraîchir** recharge l'état sans rien valider, et une habitude déjà ratée doit d'abord être annulée avec `/fail_habit <nom> --undo`.

Chaque panneau appartient à la personne qui l'a ouvert : un autre membre du groupe ne peut ni le remplacer par ses propres quêtes ni utiliser ses boutons. Les quêtes privées apparaissent sous le nom « Chose secrète 🔒 », comme dans `/status`, car le panneau peut vivre dans le groupe.

## Planning

Une habitude n'est due que certains jours (tous les jours, ou par ex. lundi + mercredi). Elle peut aussi être associée à un ou plusieurs types de journée : `rest`, `regular` et `hustle`. Les trois sont sélectionnés par défaut, y compris pour les anciennes habitudes.

Le réglage **Types de journée** est réservé aux Must. Les quêtes Compétence sont disponibles dans les trois types de journée, y compris les anciennes quêtes restreintes. Leur fréquence et leur épingle Recap déterminent quand elles sont dues. Les sous-étapes choisies restent visibles jusqu'à leur validation dans le Recap ou le graphe, ou leur retrait de la sélection.

Le jour venu, le panneau « Must du jour » et le Perfect Day ne retiennent que les quêtes Must compatibles avec le planning et le type de journée actif. Une quête `hustle` n'apparaît donc pas dans la liste d'un jour `rest` et ne bloque pas son Perfect Day.

Tu peux quand même valider manuellement une habitude hors type de journée avec `/done`, `/log`, l'API ou les contrôles du dashboard. Le log reste visible et la progression normale du streak s'applique, mais cette habitude ne devient pas une exigence du Perfect Day de ce jour.

## Tags

Une Must peut rester sans tag ou recevoir plusieurs tags. Les [objectifs](#/objectifs), les branches de [softskills](#/softskills) et les compétences précises existantes forment le catalogue : aucun tag personnalisé séparé n'est nécessaire.

Le petit menu **Choisir les tags** du formulaire permet de les sélectionner. Sur la quête, ils apparaissent ensuite comme des badges en lecture seule : il faut rouvrir ce menu pour les modifier. `Routine_matin` peut donc rester sans tag, tandis que `Hustle` peut recevoir plusieurs tags d'objectifs ou de branches.

Les tags sont communs à toutes les étapes V1/V2 d'une même quête : changer d'étape ne les retire pas. Ils n'ajoutent ni validation, ni XP, ni score, ni streak; seule la validation normale de la quête produit ses effets habituels.

Une ancienne quête quotidienne d'Objectif conserve le tag de son objectif ; une quête Compétence reçoit celui de la compétence précise, pas seulement de sa branche. Ce tag reste coché et porte la mention **Imposé par le lien** dans le formulaire. Les autres tags restent modifiables. Les noms des badges suivent les renommages des sources. Les quêtes liées existantes sont complétées sans perdre leurs tags manuels.

## Banque des quêtes

Sur le Home, **Must du jour** réunit les quêtes Must prévues pour la date affichée, qu'elles aient ou non un ancien placement horaire. Les quêtes restantes apparaissent avant celles déjà traitées. Le bouton **Banque** liste les Must actifs qui ne sont pas prévus pour cette date, avec la raison : mauvais jour de semaine, mauvais type de journée ou quête mensuelle pas encore due. L'horaire « Journée type » à droite montre les blocs et le temps libre en lecture seule.

Chaque carte Must affiche sa **durée prévue** près de la description, par exemple `30 min` ou `1 h 30`. Sans description, la durée reste visible sous le titre. Elle utilise le réglage existant de la quête et reste affichée après validation.

La banque est séparée des archives : une quête « pas ce jour » reste active et peut revenir automatiquement à sa prochaine date prévue. Une quête archivée, elle, a été retirée explicitement du quotidien.

## Effort et Perfect Day

Les quêtes Must alimentent le [Perfect Day](#/perfect-day) par leur statut : validée, loggée, skippée, ratée ou restante. Une quête quantitative peut avoir un **plafond de log par jour** (daily cap) et une unité. Certaines portent aussi un type et une durée d'effort (`musculaire`, `cerveau`, `emotionnel_social`, `creatif_divergent`) pour les budgets de journée. Aucune quête ne donne d'XP immédiat à chaque validation — contrairement aux [primes](#/primes-todo).

## Archiver une quête

Depuis le dashboard, le bouton **Archives** ouvre la liste des quêtes archivées. Une quête archivée disparaît de « Quêtes du jour » et des placements sauvegardés dans les templates de jour. C'est fait pour retirer une quête du quotidien sans la supprimer définitivement.

La liste Archives affiche la date d'archive, la fréquence, la source et les groupes de noms proches ou identiques. Le badge « actif aussi » signale qu'une quête active porte le même nom normalisé qu'une archive.

Le bouton **Désarchiver** remet la quête parmi les quêtes actives. Si elle est éligible à la date affichée, elle revient dans « Quêtes du jour ». Ses anciens créneaux ne sont pas restaurés.

Le Recap 3-3-3 affiche les sous-étapes sélectionnées et les quêtes de compétences épinglées. Les anciennes quêtes auto-générées par les tags restent des archives historiques distinctes.

## Déclarer une habitude ratée

Une habitude prévue peut être marquée **ratée** depuis « Quêtes du jour », l'onglet Habitudes, l'API ou Telegram avec `/fail_habit <nom>`. Cette action est refusée si l'habitude est déjà complétée ou skippée aujourd'hui. Le statut raté retire **jusqu'à 5 XP** (sans passer sous le niveau 1 à 0 XP), empêche le Perfect Day et remet immédiatement le streak de cette habitude à 0. Répéter l'action ne retire pas d'XP supplémentaire.

Tu peux annuler ce statut le même jour depuis l'interface, l'API ou avec `/fail_habit <nom> --undo`. Le montant d'XP réellement retiré est restauré une seule fois. Il faut d'abord annuler l'échec avant de logger une progression. L'annulation retire le statut raté, mais le streak n'est pas restauré immédiatement : il reste à 0 jusqu'au recalcul de fin de journée.

## Corriger hier

Le sélecteur **Hier / Aujourd'hui** de « Quêtes du jour » permet de revenir sur la veille pour enregistrer une quête réellement accomplie mais oubliée. Sur Telegram, ajoute `--yesterday` à `/done` ou `/log`. La fenêtre est volontairement limitée à aujourd'hui et hier : une date plus ancienne est refusée.

Une correction d'hier recalcule la journée concernée, notamment son Perfect Day et les streaks. Elle ne permet pas d'éditer librement tout l'historique.

## Exécution séparée des objectifs

Les habitudes récurrentes et les [objectifs](#/objectifs) gardent des validations **séparées** : valider un Must ou une pratique de compétence ne termine aucune sous-étape. Une quête de sous-étape du Recap, elle, est la sous-étape elle-même : la valider dans le Recap ou dans le graphe termine la même étape. Les tags donnent du contexte sans créer un second état d'accomplissement.

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
