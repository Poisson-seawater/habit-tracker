# Habit RPG Tracker

Habit tracker auto-hébergé façon RPG + système de responsabilité, tournant sur un **Raspberry Pi 5**. Un bot Telegram et un dashboard web analytique partagent une même base **SQLite** locale et rapide.


## 🎯 Vision & Philosophie

### Pourquoi ce projet existe

Un habit tracker auto-hébergé, façon RPG, construit pour notre usage perso afin de se tenir mutuellement responsables de nos habitudes quotidiennes, avec un système de points, de stats, de streaks et de « journées parfaites ». Le pilotage se fait soit par le **bot Telegram**, les **skills LLM** ou le **dashboard web**.

L'idée de base : transformer la discipline quotidienne en jeu (XP, niveaux, or, quêtes) pour que tenir ses habitudes soit motivant plutôt que pénible.

### Définir le succès d'une quête

Une quête doit pouvoir expliquer ce qui compte comme un succès. Le titre seul ne
suffit pas toujours : une quête comme « tâche hustle », « admin » ou « avancer
projet » ne dit pas quoi faire concrètement, ni à quel moment la validation est
méritée.

Besoin produit à garder en tête : ajouter un mécanisme léger de mini-note ou de
post-it attaché à une quête, ou à son occurrence du jour. Cette note servirait à
préciser l'intention du jour, le résultat attendu, le seuil minimum acceptable ou
les critères de validation, sans transformer chaque quête en grosse fiche de
projet.

Exemples :
- « tâche hustle » -> « envoyer 3 messages de prospection ou finaliser 1
  follow-up client ».
- « sport » -> « 20 minutes minimum, même si l'intensité est faible ».
- « deep work » -> « 90 minutes sans distraction sur la landing page ».

### Public cible

- Amis et réseau proche.
- Usage **quotidien** : logger ses habitudes, voir son statut du jour, suivre ses streaks.
- Non développeurs.

### Ce que le projet N'EST PAS

- **Pas un SaaS.** 
- **Pas une plateforme générique.** Tout est personnalisé pour nos besoins.

### Non-goals explicites

- Pas de scaling horizontal, de microservices, de Kubernetes.
- Pas de mobile natif — le bot Telegram couvre les usages mobiles simples, et le
  dashboard web reste l'interface complète.
- Pas d'optimisation pour des milliers d'utilisateurs : on optimise pour la **RAM du Pi**, pas pour la charge.

### Améliorations livrées en juillet 2026

Le cadrage détaillé et son statut sont conservés dans [`specs/next-steps-multi-agent-brief.md`](specs/next-steps-multi-agent-brief.md). Il couvre le filtrage des quêtes par type de journée, les habitudes ratées et leur pénalité XP, la correction d'hier, les suggestions de créneaux biologiques, la durée d'authentification de 90 jours et le retrait du champ d'effort des sous-étapes.

### Planification automatique des types de journée

Le type du jour n'est plus choisi manuellement dans le dashboard ou Telegram.
Chaque utilisateur configure à l'avance une semaine normale et une semaine moins
intense dans un cycle fixe de quatre semaines. Par défaut, les trois premières
semaines sont `regular` du lundi au vendredi, `hustle` le samedi et `rest` le
dimanche; la quatrième retire le Hustle Day. Le bouton **Feel off today** transforme
exceptionnellement aujourd'hui en Rest Day et permet ensuite de revenir au planning.

### Correction livrée — durée des quêtes dans l'agenda

La durée d'une quête modifiée est maintenant synchronisée avec ses placements
datés et ses placements par défaut dans les templates `rest`, `regular` et
`hustle`. Le bloc visuel de l'agenda reflète donc bien une durée comme 120
minutes, y compris pour les quêtes déjà placées dans un template.


## NEXT ACTIONS
- Pour objectifs "Social" j'ai plusieurs reflexe a prendre - comme routine avant de sortir de la maison. Des objectifs: parler a plusieurs inconnues. Et des options: bibliotheques, bars, meet up etc ... . Trouver un systeme pour les ranger visuellement dans le tableau de bord
- Rédiger une description claire de l'application, centrée sur le parcours utilisateur, l'expérience vécue et les grandes intentions de design (sans code ni détails techniques). Décrire notamment l'utilisateur et son besoin, le parcours quotidien de la planification à la validation, les moments clés du dashboard et du bot, ainsi que les principes UX recherchés : clarté, motivation, responsabilité et absence de surcharge.



### 1. Revoir Cloudflare Access : arrêter la reconnexion quotidienne

Constat : l'authentification interne du Habit Tracker est déjà pensée pour des
sessions et appareils approuvés de 90 jours (`AUTH_SESSION_DAYS` et
`AUTH_DEVICE_DAYS`), mais Cloudflare Access redemande encore un code tous les
jours sur les mêmes téléphone et ordinateur.

Objectif produit : sur un appareil et un navigateur déjà connus, Cloudflare doit
se souvenir de la session environ 3 mois. Le code ne devrait réapparaître qu'en
cas d'expiration 90 jours, nouveau navigateur/appareil, révocation, nettoyage des
cookies ou changement volontaire de politique de sécurité.

À cadrer :
- vérifier la durée de session côté Cloudflare Access pour l'application Habit
  Tracker, et la distinguer de la durée des cookies internes de l'app ;
- vérifier si une policy Cloudflare, un fournisseur d'identité, une option MFA ou
  un paramètre navigateur force une reconnexion quotidienne ;
- documenter le réglage cible : même téléphone/ordinateur reconnus pendant 90
  jours, sans affaiblir le bootstrap admin ni l'accès machine `HABIT_API_TOKEN`.

### 2. Penser un système habits / No-Todo / réflexes de remplacement

Besoin : le modèle actuel couvre déjà des quêtes positives et des No-Todo
négatifs, mais il manque un cadre explicite pour travailler les réflexes :
déclencheur -> besoin réel -> mauvais réflexe -> réflexe de remplacement ->
preuve minimale de réussite.

Idée à explorer :
- `Habit` : action positive à installer ou maintenir ;
- `No-Todo` : mauvais réflexe à éviter ou à déclarer quand il arrive ;
- `Réflexe de remplacement` : action courte liée à un déclencheur précis, pensée
  comme alternative au mauvais réflexe plutôt que comme simple tâche de plus.

Exemples de cadrage :
- café : clarifier le besoin réel avant de scorer. Est-ce pour se réveiller,
  retrouver du focus, prendre une pause, ou éviter de méditer/bouger ? Selon la
  réponse, le café peut être une stratégie contrôlée, un excès à limiter ou un
  signal vers une action de remplacement ;
- stress -> scroll : le No-Todo est le scroll réflexe, mais le système devrait
  proposer une alternative concrète comme 10 minutes de ménage, respiration,
  marche courte ou méditation ;
- ménage : ne pas le traiter seulement comme une corvée, mais parfois comme un
  réflexe de régulation du stress.

Prochaine étape de réflexion : concevoir une fiche légère par réflexe avec ces
champs possibles : déclencheur, besoin, mauvais réflexe, coût du mauvais réflexe,
réflexe de remplacement, durée minimale, preuve de réussite, règle de scoring,
et lien éventuel avec un No-Todo existant.


### 4. Penser un système de simple compteur relié aux skills et objectifs

Besoin : certaines progressions ne sont pas de bonnes quêtes binaires. Il faut
parfois seulement compter des répétitions, des essais ou des unités utiles, sans
forcer une logique "fait/pas fait" trop lourde.

Exemples :
- nombre de reps de visualisation pour le social training ;
- nombre de bons pomodoros ;
- nombre de cold calls ;
- nombre d'expositions, de pratiques, de tentatives ou de répétitions liées à
  une compétence précise.

Image produit : une jar qui se remplit. Chaque unité ajoutée rend la progression
visible et concrète, même si aucune récompense majeure n'est déclenchée à chaque
fois. Le compteur peut servir à voir l'accumulation d'effort, motiver la
répétition et éviter que les petites reps disparaissent dans le système.

À cadrer :
- définir si le compteur est autonome, attaché à une quête, attaché à une
  softskill, ou attaché à un objectif ;
- permettre plusieurs types d'unités simples : reps, pomodoros, appels, essais,
  minutes, sessions ;
- prévoir des jalons lisibles, par exemple jar 25/100, série de 10 bons
  pomodoros, 50 cold calls, 30 visualisations ;
- relier les compteurs aux skills et objectifs définis pour que les reps
  nourrissent une progression plus grande au lieu d'être seulement des chiffres
  isolés.

### 5. Mettre en place la matrice d'Eisenhower

Besoin : aider à choisir quoi faire maintenant quand les quêtes, objectifs,
to-do et urgences se mélangent. Le système devrait distinguer clairement
l'important de l'urgent pour éviter que les tâches bruyantes prennent toute la
place dans l'agenda.

Idée produit : ajouter une vue 2x2 de type matrice d'Eisenhower :
- urgent + important : à faire en priorité, potentiellement visible dans
  l'agenda du jour ;
- important + non urgent : à planifier volontairement avant que ça devienne une
  urgence ;
- urgent + non important : à déléguer, réduire ou transformer en tâche courte ;
- non urgent + non important : à supprimer, archiver ou laisser hors focus.

À cadrer :
- décider si la matrice classe uniquement les to-do, ou aussi les quêtes,
  sous-étapes d'objectifs et réflexes de remplacement ;
- définir les champs nécessaires sans alourdir la création : importance, urgence,
  échéance, impact objectif/skill, énergie requise ;
- prévoir une interaction rapide depuis le dashboard pour déplacer un item entre
  les quadrants ;
- relier la matrice au Perfect Day : les items importants non urgents doivent
  pouvoir être planifiés dans les zones biologiques adaptées au lieu d'être
  oubliés.




## ROADMAP

### Direction retenue : une seule action exécutable, plusieurs couches de sens

Les objets ne doivent pas se remplacer ou se valider entre eux :

| Couche | Rôle | Exemple « Corps / heal » |
| --- | --- | --- |
| Objectif et sous-étapes | résultat durable et jalons à atteindre | « Guérir le tendon », « reprendre la course sans douleur » |
| Compétence et branche | capacité à développer et preuve de maîtrise | branche « Réhabilitation », compétence « gérer une reprise progressive » |
| Quête | action récurrente, planifiable et validable au quotidien | tendon, natation, vélo, marche/course adaptée |
| To-do / prime | action ponctuelle avec date ou échéance | prendre le rendez-vous physio, acheter une bande élastique |

Une quête reste donc l'unité d'exécution récurrente. Les objectifs et les
branches de compétences restent des **tags de contexte** : ils expliquent
pourquoi l'action compte, sans créer une seconde quête, ni déclencher une
validation, XP, Or ou streak supplémentaire. Les épingles 3-3-3 restent une
couche de focus indépendante, et ne deviennent pas des tags automatiques.

À étudier ensuite : faire adopter aux To-dos le même catalogue de tags que les
quêtes (objectif + branche de compétence), pour qu'une vue comme Eisenhower ou
le bocal puisse regrouper les actions par intention. Une sous-étape est un
jalon, pas une action à mélanger automatiquement dans ces vues.

### Now — vues de recul, sans nouvelle mécanique de score

#### My Life in Weeks

**Livré dans le dashboard** : un onglet affiche une case par semaine, de la
naissance à un âge de référence choisi. La semaine actuelle est distinguée; la
date de naissance et l'âge choisi restent dans le navigateur et peuvent être
effacés. Les repères de vie et horizons d'objectifs optionnels restent à explorer.

Une grille personnelle où chaque case représente une semaine de vie : les
semaines vécues, la semaine courante et les semaines restantes jusqu'à un âge
de référence choisi par l'utilisateur. C'est une vue de perspective et de
réflexion, non un calendrier de productivité : aucune note rouge/verte ni
pression de "semaine parfaite". Des repères optionnels (moments de vie et
horizons d'objectifs à 1, 3 ou 5 ans) peuvent relier le présent à la vision
long terme, sans promettre une date de complétion.

Les données sensibles nécessaires (date de naissance, âge de référence,
événements) devront rester privées et minimales. La grille peut partir du
concept popularisé par « Your Life in Weeks » : une petite case par semaine,
plutôt qu'une prédiction sur la durée de vie.

#### The Jar of Life — les gros cailloux d'abord

Une vue hebdomadaire d'allocation de l'attention, inspirée de
[The Jar of Life: First Things First](https://balancedaction.me/2012/10/17/the-jar-of-life-first-things-first/).
Elle rend visible ce qui entre dans la capacité volontairement disponible de la
semaine :

- les **gros cailloux** : jusqu'à 3 priorités choisies (santé, relation,
  projet décisif) et leurs créneaux protégés ;
- les **galets** : obligations et routines importantes ;
- le **sable** : petites tâches, administration et demandes opportunistes ;
- l'espace restant : repos, social, imprévu et marge — pas une ressource à
  remplir à 100 %.

La vue s'appuie d'abord sur les créneaux réellement placés dans l'agenda et les
To-dos avec un jour de travail, puis laisse l'utilisateur classer explicitement
ses priorités. Elle ne déduit pas l'importance depuis les XP, les tags ou le
nombre de validations. Son test de réussite est simple : les gros cailloux ont
une place avant que le sable ne prenne toute la semaine.

Le compteur auxiliaire déjà disponible sur une quête reste l'outil pour les
répétitions (« 25/100 appels », « 7/10 expositions »). Il ne faut pas le
confondre avec le Jar of Life, qui est une visualisation de priorités et de
capacité, pas un bocal de reps.

### Next — préparer des actions mieux reliées

- Ajouter, au-dessus ou en parallèle du planificateur de journée, un **mode de
  période de vie** choisi explicitement par l'utilisateur : période de travail,
  vacances, congé sabbatique, période entrepreneuriale ou autre contexte sans
  emploi régulier. Ce mode doit aider à interpréter et organiser le planning sans
  remplacer les types de journée `rest`, `regular` et `hustle`.
- Étendre le tagging commun aux To-dos, en gardant un lien optionnel et
  multi-tags : une même action peut contribuer à « Corps / heal » et à une
  branche « Réhabilitation ».
- Donner à chaque To-do/quête un minimum de contexte utilisable pour les vues :
  durée estimée ou créneau, importance choisie, urgence/échéance et note de
  succès légère. Ne pas demander tous ces champs pour toute création.
- Concevoir la matrice d'Eisenhower sur les **actions** (To-dos et occurrences
  de quêtes), pas sur les objectifs ou compétences eux-mêmes. Les tags servent
  à expliquer l'impact d'une action dans la matrice.
- Ajouter un **diagramme de Gantt** pour suivre la progression dans le temps et
  rendre lisibles les liens entre objectifs, jalons et projections d'ambition.
  Explorer aussi d'autres visualisations de progression personnelle afin de ne
  pas perdre le présent au milieu de tous les objectifs et horizons futurs.
- Ajouter un **compteur pour les activités libres** qui ne sont ni des To-dos ni
  des quêtes obligatoires, ainsi qu'une réserve d'idées ou d'actions aléatoires à
  faire apparaître le dimanche, inspirée de la méthode du « 8e jour de la
  semaine » de Fabien Olicard.
- Garder l'UX de recherche des archives et doublons de quêtes comme amélioration
  de maintenance, séparée de la stratégie de priorisation.

### Later — pistes à ne pas mélanger au noyau personnel

- Réflexes de remplacement liés aux No-Todos : fiche légère déclencheur →
  besoin → alternative → preuve minimale.
- Une version professionnelle avec To-dos partagés et agenda/Google Calendar
  séparés : sujet distinct, à cadrer seulement après avoir validé le modèle
  personnel d'actions, tags et priorités.



## 👥 Collaboration & développement

Projet perso. Avant de contribuer, lire :

- 🎯 **[Vision & Philosophie](#-vision--philosophie)** — pourquoi ce projet existe, qui il vise, ce qu'il n'est pas (section ci-dessus).
- 🤖 **[CLAUDE.md](./CLAUDE.md)** — conventions et règles pour Claude Code / agents (symlink vers `AGENTS.md`).
- 🌿 **[CONTRIBUTING.md](./CONTRIBUTING.md)** — branches, PRs, format des commits.
 
On travaille par branches `feat/...` → PR vers `dev` → PR vers `main`, 1 review minimum.

---

## 🛠️ Stack (résumé)

- **Backend** : FastAPI + SQLAlchemy 2.0 + Uvicorn, `python-telegram-bot`, APScheduler, PyTest.
- **Frontend** : Vanilla HTML5 / CSS3 / JS ES6, sans framework ni build, servi en statique.
- **Données & déploiement** : SQLite unique ; Docker Compose (`api` + `bot`) sur Pi 5, limites RAM 40 / 35 Mo.

Détails et choix d'architecture → [CLAUDE.md](./CLAUDE.md) et [`specs/001-habit-tracker-bot/plan.md`](./specs/001-habit-tracker-bot/plan.md).

Télécommande IA sans MCP :
[fonctionnement du plugin](./docs/notes/habit-tracker-control-plugin.md),
[migration SQLite v9](./docs/notes/database-v9-remote-operations.md) et
[décision d'architecture](./docs/adr/002-plugin-habit-tracker-control.md).

- Plugin (recommandé) : [`plugins/habit-tracker-control/`](./plugins/habit-tracker-control/)
  — CLI `scripts/habitctl.py` + skills `query`/`action`/`manage`.
- Skill globale (ancienne, hors dépôt) : `~/.claude/skills/habit-tracker/SKILL.md`
  — parle à l'API en `curl` direct, sans passer par le CLI du plugin.

---

## 🚀 Setup local (≤ 5 commandes)

```bash
git clone <url-du-repo> habit-tracker
cd habit-tracker
cp .env.example .env          # puis remplir les valeurs Telegram
uv venv && source .venv/bin/activate && uv pip install -r backend/requirements.txt
PYTHONPATH=backend python3 backend/src/main.py   # dashboard → http://localhost:5000
```

Le serveur initialise les tables, lance les seeders de démarrage, monte le frontend statique
et sert le dashboard sur [http://localhost:5000](http://localhost:5000).

Le bot Telegram (optionnel en local) se lance à part :

```bash
PYTHONPATH=backend python3 backend/src/bot/listener.py
```

Les tests :

```bash
PYTHONPATH=backend .venv/bin/pytest backend/tests
```

---

## 🔑 Variables d'environnement

À mettre dans `.env` à la racine (copier depuis `.env.example`) :

| Variable | Exemple | Rôle |
|----------|---------|------|
| `TELEGRAM_BOT_TOKEN` | `123456:ABC-DEF...` | Token du bot (BotFather). |
| `TELEGRAM_GROUP_ID` | `-1003912636269` | ID du groupe Telegram autorisé. |
| `API_PORT` | `5000` | Port d'écoute de l'API / dashboard. |
| `ENV` | `development` | `development` en local, `production` sur le Pi. |
| `TIMEZONE` | `America/Toronto` | Fuseau pour les scores du jour et les rappels. |
| `DATABASE_URL` | `sqlite:////data/habit_tracker.db` | Chemin SQLite. À laisser vide en local : fallback auto vers `backend/data/`. |
| `AUTH_BOOTSTRAP_CODE` | `long-code-secret` | Code temporaire requis pour créer le premier mot de passe admin et approuver le premier appareil. |
| `HABIT_API_TOKEN` | `long-api-token` | Token machine pour le plugin `habit-tracker-control` et les appels API non navigateur. |
| `AUTH_SESSION_DAYS` | `90` | Durée des sessions web en jours. |
| `AUTH_DEVICE_DAYS` | `90` | Durée d'approbation d'un navigateur/appareil en jours. |
| `AUTH_COOKIE_SECURE` | `false` | Mettre `true` uniquement si le dashboard est servi en HTTPS. |

> En local, tu peux ne renseigner que les variables Telegram si tu veux garder le
> mode legacy non authentifié. Sur la Pi, définis `AUTH_BOOTSTRAP_CODE` et
> `HABIT_API_TOKEN` avant de déployer.

---

## 🐳 Docker (production Pi 5)

```bash
docker compose up -d --build      # build + run en arrière-plan
docker compose ps
```

Mettre à jour un déploiement existant sur le Pi :

```bash
git pull --ff-only
docker compose up -d --build
docker compose ps
```

Pour remplacer les données du Pi par le snapshot SQLite committé, restaurer **après** le pull
et **avant** de redémarrer la stack :

```bash
docker compose down
python3 ops/db/habit_tracker_db_admin.py restore-snapshot
docker compose up -d --build
docker compose ps
```

La commande de restore crée d'abord une sauvegarde horodatée sous `data/backups/` avant de
remplacer `data/habit_tracker.db`.

---

## 📦 Sauvegardes automatiques

Rotation SQLite quotidienne via `backend/src/database/backup.py` : copies horodatées sous
`/data/backups/`, avec purge automatique pour ne garder que les **5 dernières** (préserve le
stockage du Pi).
