# Big Spec: Systeme de Punitions Constructives

Date: 2026-07-16
Status: Draft hors Spec Kit
Source: README.md, section "Pistes futures"
Scope: cadrage produit-technique, sans implementation

## 1. Intention

Le systeme de punitions doit rendre les echecs visibles et actionnables sans
transformer le Habit Tracker en outil de honte ou de decouragement. Le bon angle
produit est "reparation constructive" : quand un engagement est rate, le systeme
applique une consequence RPG mesuree et propose une action compensatoire claire.

L'objectif n'est pas de punir pour punir. L'objectif est de fermer la boucle de
responsabilite :

- j'avais un engagement;
- je l'ai rate ou brise;
- le systeme le reconnait;
- je paie un cout symbolique ou mecanique;
- je peux reparer par une quete utile.

Cette spec est volontairement hors Spec Kit. Elle sert de big spec exploratoire
pour valider l'idee avant de la transformer plus tard en plan d'implementation.

## 2. Probleme a resoudre

Aujourd'hui, le projet sait deja recompenser :

- XP pour les Todos / Primes terminees;
- Gold pour les substeps;
- Perfect Day et streaks;
- Boutique de recompenses;
- Allostasis rewards;
- No-Todos avec declaration d'echec.

Le trou produit est l'autre cote de la boucle : l'echec a une visibilite, mais
pas toujours une consequence claire ni une reparation concrete. Une quete non
faite peut simplement rester la. Un No-Todo echoue est marque, mais l'utilisateur
ne recoit pas forcement une action de retour vers le systeme.

Le systeme de punitions doit donc ajouter une consequence legere, lisible et
reversible par effort.

## 3. Principes de design

### 3.1 Constructif avant punitif

Une punition doit encourager un retour a l'action. Les meilleures punitions sont
des "quêtes de réparation" :

- ranger 10 minutes;
- marcher 20 minutes;
- ecrire un post-mortem de 3 lignes;
- faire une mini-session de la quete ratee;
- preparer l'environnement pour demain.

### 3.2 Couts RPG limites

Les pertes d'XP ou d'or doivent etre bornees. Le systeme ne doit jamais pouvoir
ruiner un profil, casser plusieurs niveaux d'un coup, ou rendre le jeu inutile.

### 3.3 Pas d'automatisation agressive en V1

En V1, les punitions doivent etre declenchees par des evenements deja connus :

- No-Todo declare comme echoue;
- Todo / Prime explicitement marquee comme ratee si cette feature existe;
- quete planifiee non faite au rollover de minuit, seulement si le systeme peut
  l'identifier sans ambiguite.

Les deductions automatiques massives et les heuristiques floues sont hors scope.

### 3.4 Controle utilisateur

L'utilisateur doit comprendre pourquoi une punition existe et comment la solder.
Une punition cachee ou inexplicable est un bug produit.

## 4. Non-scope explicite

- Pas de multi-agent dans cette feature.
- Pas de systeme de dette complexe avec interets, penalites composees ou score
  social.
- Pas de sanctions publiques humiliantes dans Telegram.
- Pas de deduction infinie d'XP.
- Pas de dependance externe.
- Pas de refonte du score quotidien.
- Pas de commande Telegram obligatoire en V1. Si une commande est ajoutee plus
  tard, `COMMANDS-INDEX.md` devra etre mis a jour.

## 5. Concepts cibles

### 5.1 Punishment Rule

Une regle de punition decrit quoi faire quand un type d'echec arrive.

Exemples :

- No-Todo echoue -> perdre 5 XP et creer une quete de reparation.
- Prime ratee -> perdre 50% de l'XP promise, plafonne a 20 XP.
- Perfect Day ratee -> aucune perte immediate, mais proposer une micro-quete de
  reset.

Champs conceptuels :

- nom;
- declencheur;
- cout XP optionnel;
- cout Gold optionnel;
- template de quete de reparation optionnel;
- severite;
- actif/inactif;
- plafond journalier.

### 5.2 Punishment Event

Un evenement de punition est l'instance creee quand une regle se declenche.

Il doit garder un historique :

- utilisateur;
- date;
- source de l'echec;
- regle appliquee;
- XP/Gold perdus;
- quete de reparation creee ou non;
- statut : `active`, `repaired`, `waived`.

### 5.3 Repair Quest

Une quete de reparation est un Todo cree automatiquement ou semi-automatiquement.
Elle doit etre petite, concrete et faisable le jour meme ou le lendemain.

Elle peut donner 0 XP, ou redonner une partie de la perte si on veut un effet
"rachat".

Recommandation V1 : creer une Todo de reparation a 0 XP ou faible XP, plutot que
donner un gros bonus de rattrapage. La reparation doit etre la remise en route,
pas une opportunite d'exploit.

## 6. Declencheurs recommandes

### 6.1 No-Todo echoue

Declencheur le plus naturel pour V1, car il existe deja :

- endpoint `POST /api/v1/notodos/{notodo_id}/fail`;
- service `record_notodo_failure`;
- historique `NoTodoLog`;
- affichage dashboard deja present.

Comportement cible :

1. L'utilisateur declare l'echec d'une regle No-Todo.
2. Le systeme enregistre le `NoTodoLog`.
3. Le systeme applique une punition configuree.
4. Le dashboard montre la consequence et la quete de reparation.

### 6.2 Prime / Todo ratee

Le README mentionne deja l'idee "Habitude ratée" et "Validation différée ou
retour en arrière". Pour eviter les conflits, la V1 des punitions ne devrait pas
deviner qu'une prime est ratee uniquement parce qu'elle n'est pas completee.

Option recommandee :

- ajouter plus tard une action explicite "Declarer ratee" sur une Todo;
- declencher la punition seulement sur cette action.

### 6.3 Quete planifiee non faite

Plus delicat. Les quetes/habitudes peuvent dependre du type de jour, des
eligibilites, et d'une validation tardive.

Recommandation :

- hors V1 automatique;
- a reconsiderer apres la feature de validation differee / retour en arriere.

## 7. Consequences RPG

### 7.1 Perte XP

Le projet a deja `deduct_user_xp`, donc techniquement la perte XP est possible.
Mais elle doit etre bornee.

Regles recommandees :

- perte par defaut : 5 XP;
- perte max par evenement : 20 XP;
- perte max par jour : 30 XP;
- ne jamais descendre sous niveau 1;
- afficher le nouveau niveau si level-down.

### 7.2 Perte Gold

La perte d'or peut etre plus douce psychologiquement que la perte XP, car l'or
est deja une monnaie de depense.

Regles recommandees :

- perte optionnelle selon severite;
- ne jamais rendre l'or negatif;
- perte max par jour configurable;
- eviter la double peine XP + Gold par defaut.

### 7.3 Creation de quete de reparation

La consequence principale devrait etre la reparation.

Exemples de templates :

- "Réparation: 10 minutes de rangement";
- "Réparation: mini-session de 15 minutes sur la quête ratée";
- "Réparation: écrire pourquoi j'ai échoué et ce que je change demain";
- "Réparation: marche de reset 20 minutes".

Chaque template peut definir :

- titre;
- description;
- XP de completion;
- date de planification par defaut;
- lien avec la source d'echec.

## 8. UX cible

### 8.1 Dashboard

Ajouter un panneau "Punitions / Réparations" ou une section dans les vues
existantes :

- punitions actives aujourd'hui;
- cout deja applique;
- quetes de reparation ouvertes;
- historique recent;
- bouton "Marquer réparée" si la reparation n'est pas une Todo automatique;
- bouton "Ignorer / annuler" reserve a l'utilisateur admin/local.

### 8.2 No-Todo

Quand l'utilisateur clique "Declarer Echec" :

- confirmer l'action si elle applique une perte;
- afficher clairement la consequence;
- creer et afficher la quete de reparation;
- rafraichir profil XP/Gold et score du jour.

### 8.3 Telegram

V1 peut se limiter au recap existant :

- mentionner les No-Todos echoues;
- mentionner les reparations ouvertes;
- ne pas ajouter de commande.

Si une commande est ajoutee plus tard, exemples possibles :

- `/repairs` pour voir les reparations ouvertes;
- `/repair_done <id>` pour solder une reparation.

Toute commande ajoutee devra mettre a jour `COMMANDS-INDEX.md`.

## 9. Donnees possibles

Cette section est exploratoire, pas une instruction d'implementation immediate.
Le schema final devra etre valide avant modification DB.

### 9.1 `punishment_rules`

Champs possibles :

- `id`
- `user_id`
- `name`
- `trigger_type`
- `severity`
- `xp_penalty`
- `gold_penalty`
- `daily_xp_cap`
- `daily_gold_cap`
- `repair_todo_title_template`
- `repair_todo_xp_reward`
- `is_active`
- `created_at`

### 9.2 `punishment_events`

Champs possibles :

- `id`
- `user_id`
- `rule_id`
- `source_type`
- `source_id`
- `source_title_snapshot`
- `date`
- `xp_penalty_applied`
- `gold_penalty_applied`
- `repair_todo_id`
- `status`
- `created_at`
- `repaired_at`
- `waived_at`

## 10. API possible

Endpoints candidats :

- `GET /api/v1/punishments/rules`
- `POST /api/v1/punishments/rules`
- `PUT /api/v1/punishments/rules/{rule_id}`
- `DELETE /api/v1/punishments/rules/{rule_id}`
- `GET /api/v1/punishments/events`
- `POST /api/v1/punishments/events/{event_id}/repair`
- `POST /api/v1/punishments/events/{event_id}/waive`

Integration prioritaire :

- `POST /api/v1/notodos/{notodo_id}/fail` declenche une punition si une regle
  active correspond.

## 11. Garde-fous anti-effets pervers

- Une punition ne doit jamais empecher d'utiliser l'app.
- Une punition ne doit jamais rendre une journee "irreparable".
- Un echec repete doit suggerer d'ajuster le systeme, pas seulement punir plus.
- Une punition ne doit pas donner plus d'XP de reparation que l'echec n'en a
  coute.
- Les punitions doivent etre plafonnees par jour.
- Il doit exister une action d'annulation locale/admin pour corriger les erreurs.

## 12. Alternatives evaluees

### Option A: perte XP simple

Simple a comprendre et facile a implementer.

Probleme : peut devenir demotivante si elle n'offre pas de chemin de retour.

Verdict : acceptable seulement si plafonnee et accompagnee d'une reparation.

### Option B: quete de reparation uniquement

Tres constructive, peu punitive.

Probleme : manque parfois de poids RPG; l'utilisateur peut ignorer la quete.

Verdict : bon mode doux, surtout pour Perfect Day ratee ou petits echecs.

### Option C: perte Gold

Bonne integration avec la boutique.

Probleme : moins impactant si l'or est abondant ou peu utilise.

Verdict : utile comme alternative configurable a la perte XP.

### Option D: dette cumulable

Une dette s'accumule jusqu'a reparation.

Probleme : complexite et risque de dette infinie.

Verdict : hors V1.

## 13. Recommandation V1

Implementer une V1 centree sur les No-Todos :

1. Une regle par defaut : No-Todo echoue -> -5 XP + creation d'une quete de
   reparation.
2. Plafond journalier : max -15 XP via No-Todos.
3. Repair Quest creee automatiquement comme Todo a 0 ou 5 XP.
4. Historique des punitions visible dans le dashboard.
5. Action admin "annuler" pour erreur de declaration.
6. Pas de commande Telegram en V1.
7. Pas de punition automatique des quetes non faites avant d'avoir clarifie la
   validation differee / retour en arriere.

Cette V1 donne une boucle complete sans trop toucher aux parties les plus
risquees du systeme.

## 14. Questions ouvertes

- La consequence par defaut doit-elle etre XP, Gold, ou seulement reparation ?
- Une quete de reparation doit-elle pouvoir redonner l'XP perdu ?
- Faut-il une seule regle globale ou des regles par No-Todo ?
- Qui peut annuler une punition dans un contexte multi-user prive ?
- Est-ce qu'une punition doit influencer le statut Perfect Day, ou seulement
  l'economie RPG ?

## 15. Definition of Done pour une future implementation

- Les echecs No-Todo peuvent declencher une punition idempotente.
- Les pertes XP/Gold sont plafonnees.
- Une reparation concrete est creee ou proposee.
- L'utilisateur voit pourquoi la punition existe.
- L'utilisateur voit comment la reparer.
- Les erreurs peuvent etre annulees.
- Les tests couvrent double-clic, double declaration, plafonds journaliers,
  level-down XP, gold insuffisant et isolation multi-user.
- Aucune commande Telegram n'est ajoutee sans mise a jour de
  `COMMANDS-INDEX.md`.

