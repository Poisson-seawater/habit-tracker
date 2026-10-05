# Cahier des charges — quêtes liées, Must et journée type

**Statut :** sections 1, 2, 3 et 5 implémentées le 2026-10-04. La section 4 « Journée type » est reportée explicitement par Gabriel ; ses besoins restent conservés ci-dessous pour plus tard.

## Contexte vérifié

- Une quête peut avoir le rôle `must`, `goal` (Objectif) ou `skill` (Compétence). Épingler un objectif ou une compétence crée déjà sa quête liée dans le Recap 3-3-3.
- Les tags existants pointent vers un **objectif** ou une **branche de compétences**. Ils sont actuellement choisis dans un menu du formulaire. Un tag n'est pas un lien de validation : il ne donne ni XP, ni score, ni accomplissement de l'objectif ou de la compétence.
- Le formulaire de quête expose actuellement « Types de journée » pour tous les rôles. Les quêtes liées créées automatiquement sont initialisées pour Repos, Régulière et Hustle.
- Une carte « Must du jour » affiche la description lorsqu'elle existe. La durée prévue est déjà enregistrée sur la quête, mais n'est pas affichée à côté de cette description.

## But

Réduire les réglages inutiles des quêtes Objectif/Compétence, rendre visible la durée des Must et utiliser la « Journée type » pour estimer le temps que prend théoriquement une journée.

## Besoins fonctionnels

### 1. Tags des quêtes Objectif et Compétence

- À la création d'une quête liée à un objectif, sélectionner automatiquement le tag de **cet objectif**.
- À la création d'une quête liée à une compétence, sélectionner automatiquement le tag de **cette compétence précise**. Le catalogue actuel ne propose que des tags de branche : cette demande ajoute donc un nouveau type de référence de tag, à définir dans le futur contrat API et dans sa persistance.
- Afficher le tag choisi comme les autres badges de quête.
- Le tag correspondant au lien Objectif/Compétence est **imposé par ce lien** : il reste présent et ne peut pas être retiré ou remplacé dans le formulaire de la quête. Les éventuels autres tags manuels restent indépendants.
- Préserver la séparation actuelle entre `focus_role`/lien Recap et tags : le tag reste une information d'organisation.
- Appliquer aussi cette règle aux quêtes liées déjà existantes, sans retirer leurs autres tags et sans créer de doublons. Les différentes versions V1/V2 d'une même quête doivent conserver le même ensemble de tags.
- Le libellé du tag suit le nom actuel de l'objectif ou de la compétence ; le lien repose sur son identifiant, pas sur son texte.

### 2. Types de journée des quêtes Objectif et Compétence

- Ne plus présenter le réglage « Types de journée » dans les formulaires de création et d'édition de ces deux rôles.
- Ces quêtes doivent rester disponibles pendant les trois types de journée (`rest`, `regular`, `hustle`), comme lors de leur création automatique actuelle. Leur épingle Recap et leur fréquence continuent de déterminer si elles sont actives et dues aujourd'hui.
- Les quêtes Must conservent leur réglage actuel.
- Les anciennes quêtes liées ayant une restriction enregistrée doivent aussi devenir disponibles sur les trois types de journée. Le choix technique de normalisation ou de lecture forcée appartient à l'étape d'implémentation.

### 3. Durée visible dans « Must du jour »

- Afficher la **durée prévue de chaque quête** à côté de sa description sur chaque carte Must du jour, avec une unité lisible (par exemple « 30 min » ou « 1 h 30 »).
- Utiliser la durée prévue déjà enregistrée pour la quête (`agenda_duration_minutes`), ou la durée effective de secours déjà calculée par l'application lorsqu'elle est absente. Ce changement ne demande pas un nouveau champ de saisie.
- Si la description est vide, afficher tout de même la durée sous le titre de la quête.
- Le texte doit rester lisible sur écran étroit et lorsque la description est longue.

### 4. Journée type

- La « Journée type » doit montrer combien de temps les **Must du jour** prennent théoriquement. C'est son objectif principal ; le total doit être identifiable sans additionner mentalement les cartes.
- Le total des Must reste **distinct** : il n'additionne pas les heures de job, les créneaux des lieux ni le temps de transport. Aucun total unique de « temps occupé » n'est demandé.
- Ce total additionne les durées prévues de tous les Must dus pour la date affichée. Il conserve la charge théorique de la journée et ne diminue pas au fil des validations.
- Elle doit inclure les heures de travail salarié et les lieux où Gabriel veut aller, par exemple la bibliothèque, avec le temps de transport associé. Ces éléments sont saisis directement dans Habit Tracker. Les heures de job prévues et les Must du jour restent identiques dans les trois aperçus ; les lieux souhaités, et les transports associés, sont configurés **par type de journée** et se répètent pour ce type. Chaque lieu a une heure d'arrivée, une heure de départ et **une seule durée de transport aller-retour**.
- Le temps de transport est affiché comme un total associé au lieu, sans le répartir avant l'arrivée et après le départ et sans calculer d'heures de trajet.
- Si un lieu prévu dans le type aperçu chevauche les heures de job de la date affichée, signaler le conflit et conserver les deux créneaux tels que saisis. L'utilisateur ajuste les heures ; aucun déplacement automatique ni masquage du lieu.
- Chaque dimanche, **seuls les horaires de job** de la semaine suivante sont à confirmer. Habit Tracker propose les mêmes horaires que ceux déjà enregistrés (par exemple lundi à vendredi, 8 h–16 h) ; Gabriel peut les valider tels quels ou modifier les jours et les heures avant validation. L'exemple 8 h–16 h n'est pas un horaire imposé.
- Dès le dimanche, un **encart sur le Home** présente les horaires proposés pour la semaine suivante, avec les actions **« Confirmer » / « Modifier »**. Il reste visible tant que les horaires de la semaine concernée sont à confirmer, y compris après le dimanche si la confirmation a été oubliée.
- Si les horaires ne sont pas confirmés le dimanche, les anciens horaires restent visibles pour la nouvelle semaine avec la mention **« À confirmer »** jusqu'à validation ou modification. Ils ne sont pas validés automatiquement.
- Une seule heure de coucher peut être renseignée comme repère facultatif. Elle est commune à toutes les dates et à tous les types de journée ; changer d'aperçu ne la modifie pas.
- Un switch permet de voir un **aperçu** des trois types de journée : Repos, Régulière et Hustle. Il change uniquement la vision de la « Journée type ». Il ne change ni le type actif du jour, ni la liste ou le total des Must réellement dus aujourd'hui, ni les calculs du Perfect Day.
- Les Must apparaissent dans la « Journée type » sous forme d'un **total de durée théorique** pour la date affichée, sans blocs horaires individuels ni placement à une heure précise. Leur validation n'est pas liée à cet affichage.

### 5. Note « Rules »

- Pouvoir écrire **une seule note globale** intitulée « Rules », limitée à **500 caractères**.
- Cette note est indépendante du type de journée et de la date : le même texte s'applique à tous les aperçus et à toutes les dates. Une entrée **« Rules » distincte dans le menu principal** ouvre l'écran où elle est visible et modifiable ; elle ne se trouve pas dans la carte « Journée type ».
- Le texte enregistré s'affiche aussi sur le dashboard, juste au-dessus du panneau **⚔️ Tableau des Primes (Aujourd'hui)**. Les retours à la ligne sont conservés et une note vide masque cet affichage.

## État du cadrage

Les sections livrées couvrent les critères 1 à 7, 12 et 13. Les tags acceptent désormais `kind: "softskill"` avec l'identifiant de la compétence ; les réponses indiquent `locked` pour les tags imposés. La normalisation des quêtes liées préserve les tags manuels et ouvre les trois types de journée. La migration v38 ajoute `users.rules_text` ; `GET`/`PUT /api/v1/profile/rules` utilisent `{ "text": "…" }`, avec une limite de 500 caractères. Les choix de persistance de la Journée type restent à cadrer lors de sa reprise.

## Clarifications

### Session 2026-10-04

- Le switch Repos/Régulière/Hustle est un aperçu uniquement ; il ne modifie pas le type actif ni les conséquences sur les quêtes ou le Perfect Day.
- L'aperçu ne modifie pas les Must du jour : leur liste et leur durée totale restent celles de la date affichée, même si l'aperçu montre un autre type de journée.
- Les heures de travail prévues restent affichées sans changement quand on bascule entre les trois aperçus.
- Correction du cadrage : les lieux souhaités, comme la bibliothèque, se répètent selon le type de journée. Ils peuvent donc changer dans l'aperçu, contrairement aux Must du jour et aux heures de job.
- Chaque lieu configuré par type de journée comporte une heure d'arrivée et une heure de départ, pas seulement une durée flottante.
- Pour chaque lieu, un seul temps de transport couvre l'aller-retour ; il n'y a pas de saisie distincte pour l'aller et le retour.
- Le transport est présenté comme une durée totale, sans déduction d'heures de départ ou de retour.
- La durée des Must constitue un total séparé ; les autres occupations ne s'y ajoutent pas et il n'y a pas de total global demandé.
- Il existe une seule note « Rules » de 500 caractères maximum, commune à toutes les dates et à tous les types de journée.
- L'heure de coucher facultative est unique et commune à toutes les dates et à tous les types de journée.
- La note « Rules » possède sa propre entrée dans le menu principal, ouvrant son écran de lecture et d'édition.
- Les Must sont affichés sous forme d'un total théorique, sans placement horaire de chaque quête.
- Les heures de travail, les lieux et les transports sont saisis dans Habit Tracker ; ils ne sont pas importés automatiquement de Google Calendar.
- Le rituel du dimanche porte uniquement sur le job. Les horaires déjà enregistrés sont proposés à nouveau pour la semaine suivante ; on les valide tels quels ou on les modifie, jour par jour si nécessaire.
- Sans confirmation le dimanche, les anciens horaires restent affichés avec la mention « À confirmer » jusqu'à validation ou modification.
- Un chevauchement entre le job et un lieu est signalé ; les deux créneaux restent visibles sans modification automatique.
- Le total des Must conserve toutes les durées prévues pour la journée et ne diminue pas lors des validations.
- La confirmation hebdomadaire du job prend la forme d'un encart sur le Home, avec « Confirmer » et « Modifier », visible jusqu'à confirmation.

## Critères d'acceptation

1. Une quête créée par l'épinglage d'un objectif affiche automatiquement le tag de cet objectif.
2. Une quête créée par l'épinglage d'une compétence affiche automatiquement le tag de cette compétence précise, pas seulement celui de sa branche.
3. Le tag imposé par le lien ne peut pas être décoché ; les autres tags restent modifiables.
4. Une quête liée existante reçoit son tag manquant sans perdre ses autres tags.
5. Les formulaires des quêtes Objectif/Compétence n'affichent plus « Types de journée » ; les Must l'affichent toujours.
6. Une quête liée reste validable un jour Repos, Régulier ou Hustle lorsqu'elle est épinglée et prévue par sa fréquence, y compris si une ancienne restriction de type de journée avait été enregistrée.
7. Une carte Must du jour affiche clairement la durée prévue près de la description, ou seule sous le titre si la description est vide, sans changer la validation, le score ou le streak.
8. La « Journée type » affiche le total théorique des Must réellement dus pour la date affichée, sans leur attribuer d'heures, et ce total ne change pas quand l'aperçu bascule entre Repos, Régulière et Hustle.
9. Les heures de travail restent identiques dans les trois aperçus, tandis que les lieux et transports affichés suivent le type aperçu ; le switch ne modifie pas le type actif, les quêtes ni le Perfect Day.
10. Un lieu configuré pour un type de journée affiche les heures d'arrivée et de départ saisies et se répète dans chaque aperçu de ce type.
11. La « Journée type » affiche un total des Must qui exclut job, lieux et transport.
12. La note « Rules » reste la même dans tous les aperçus et à toutes les dates, et refuse un texte de plus de 500 caractères.
13. Une entrée « Rules » séparée du panneau « Journée type » est présente dans le menu principal et ouvre la note globale.
14. Sans confirmation des horaires de job le dimanche, la nouvelle semaine affiche les horaires précédents avec la mention « À confirmer » ; une validation ou modification les confirme pour cette semaine.
15. Si le job est prévu de 8 h à 16 h et un lieu de 10 h à 12 h, l'aperçu montre les deux créneaux et signale leur chevauchement, sans modifier leurs horaires.
16. Valider un Must ne réduit pas le total théorique affiché pour la journée.
17. Dès le dimanche, le Home propose les horaires de job de la semaine suivante dans un encart « Confirmer / Modifier » ; cet encart reste visible jusqu'à confirmation de la semaine concernée.
18. Le transport d'un lieu affiche une seule durée aller-retour, sans la répartir en créneaux ni calculer d'heures de trajet.
19. L'heure de coucher peut rester vide ; lorsqu'elle est renseignée, elle est identique dans les trois aperçus et à toutes les dates.

## Conséquences techniques à examiner lors de l'implémentation

- Étendre le catalogue, la validation et la lecture des tags pour référencer une compétence individuelle ; vérifier les consommateurs du contrat API avant de le modifier.
- Garantir côté serveur que le tag imposé ne disparaît pas si un ancien client envoie une liste de tags sans ce tag.
- Traiter la création automatique, les quêtes existantes et les mises à jour de manière idempotente. Préserver les tags manuels et les liens V1/V2.
- Vérifier les cas de renommage et de suppression d'un objectif ou d'une compétence pour éviter les badges orphelins.
- Vérifier l'affichage de la durée avec description longue, description vide et sur mobile.
- Définir la persistance des horaires de job par semaine et de leur confirmation, des lieux par type de journée, de l'heure de coucher commune et de la note globale. Tout nouveau champ DB nécessitera une migration idempotente ; les changements de schéma et de contrat API seront à discuter avant implémentation.
- Calculer le total des Must avec les mêmes règles d'éligibilité et de durée que la liste du jour ; le sélecteur d'aperçu et les validations ne doivent pas modifier ce calcul.
- Séparer l'aperçu du template du type réellement actif et signaler les chevauchements entre job et lieux sans déplacer les créneaux.

## Hors périmètre établi

- Changement de l'effet des tags sur les validations, scores ou XP.
- Changement du fonctionnement des quêtes Must selon le type de journée.
- Refonte du Recap ou des fréquences des quêtes.
