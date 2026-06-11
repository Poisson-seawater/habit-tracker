# Vision — Habit RPG Tracker

## Pourquoi ce projet existe

Un habit tracker auto-hébergé, façon RPG, qui tourne **en local** sur un Raspberry Pi 5.
On l'a construit pour notre usage perso : se tenir mutuellement responsables sur nos habitudes quotidiennes, avec un système de points, de stats, de streaks et de
« journées parfaites ». Le pilotage se fait soit par le **bot Telegram**, **skills LLM** ou par le
**dashboard web**.

L'idée de base : transformer la discipline quotidienne en jeu (XP, niveaux, or, quêtes)
pour que tenir ses habitudes soit motivant plutôt que pénible.

## Public cible

- Amis et réseaux proche.
- Usage **quotidien** : logger ses habitudes, voir son statut du jour, suivre ses streaks.
- Non dev

## Ce que le projet N'EST PAS

- **Pas un SaaS.** Aucune intention de vendre, d'héberger pour des tiers, ni de scaler.
- **Pas multi-tenant.** « Multi-utilisateur » = nous deux, sur une seule instance, une
  seule DB SQLite. Pas d'organisations, de rôles, de facturation.
- **Pas une app publique.** Tourne derrière notre réseau / tunnel. Pas de hardening
  niveau prod publique (CORS ouvert, auth par simple header `X-User-ID`).
- **Pas une plateforme générique.** Tout est personnalisé pour nos besoin. 


## Non-goals explicites

- Pas d'inscription publique ni d'onboarding grand public.
- Pas de paiement, d'abonnement, de plan freemium.
- Pas de support multi-DB (Postgres, MySQL…) — SQLite suffit pour deux personnes.
- Pas de scaling horizontal, de microservices, de Kubernetes.
- Pas de mobile natif — le bot Telegram + la Mini App couvrent le besoin mobile.
- Pas d'i18n complète — FR/EN au fil de l'eau, sans framework de traduction.
- Pas d'optimisation pour des milliers d'utilisateurs : on optimise pour la **RAM du Pi**,
  pas pour la charge.

## Pistes futures (non engagées)

> Idées issues du cahier des charges initial, conservées ici en attendant d'être
> éventuellement cadrées dans `specs/`. Rien de tout ça n'est décidé.

**V3 — intégrations externes**

- Connexion à un calendrier externe (ex. calendrier employeur → tâches → rappel bot → recap).
- Connexion à une app de todo externe.
- API externe + intégrations avec des outils professionnels.
- Synchronisation avec des systèmes tiers.

**À réconcilier avec le graphe d'objectifs V2** (cf. [`specs/002-multiuser-rpg-v2/spec.md`](./specs/002-multiuser-rpg-v2/spec.md))

- Fin d'objectif par cumul de succès (ex. 180 succès ≈ 6 mois), en plus du streak complet.
- Statuts de fin d'objectif : abandonné / terminé avec déblocage du suivant / terminé sans suite.

## Brain Drop V3 — Fonctionnalités en vue (À cadrer)

> Ce brainstorm contient les idées brutes du projet à structurer pour une future session de code. Chaque fonctionnalité est définie par son objectif et son gain de valeur directe.

- **Gamification des seuils d'ancrage (30J / 90J)** :
  - **Objectif** : Valoriser le passage des paliers de formation d'une habitude (30 jours pour l'adoption initiale, 90 jours pour l'ancrage définitif).
  - **Gain** : Maintenir l'engagement à long terme en évitant le découragement après les premiers jours de streak. Offrir un sentiment de progression psychologique clair (ex: évolution visuelle ou titre honorifique de l'habitude).
- **Règle d'initialisation des 7x7 (Démarrage rapide)** :
  - **Objectif** : Conditionner rapidement le cerveau à un nouveau comportement durant la phase critique de départ en exigeant 7 répétitions quotidiennes pendant les 7 premiers jours.
  - **Gain** : Vaincre la friction de démarrage et créer un automatisme fort dès la première semaine via une sur-activation temporaire mais intense.
- **Planification quotidienne 3-3-3** :
  - **Objectif** : Structurer la journée idéale de manière équilibrée en répartissant les tâches selon trois niveaux d'efforts distincts : 3 objectifs majeurs (priorités de la journée), 3 tâches courtes (gains rapides) et 3 activités de maintenance (santé, rangement, routines).
  - **Gain** : Éviter la surcharge mentale en offrant un cadre de priorisation simple et réaliste. Assurer un équilibre de vie en forçant la réalisation de tâches de maintenance souvent négligées au profit de la productivité pure.
- **Régulation de la charge cognitive (Anti-surcharge)** :
  - **Objectif** : Limiter le nombre maximum de projets et d'habitudes actifs simultanément pour éviter la dispersion de l'attention et le burn-out de la volonté.
  - **Gain** : Maximiser le taux de succès sur les engagements pris en forçant l'utilisateur à se concentrer sur l'essentiel (finir ce qui est en cours avant d'en démarrer d'autres).
- **Système de Visualisation des Skills** :
  - **Objectif** : Cartographier et suivre le développement des compétences personnelles et professionnelles en cours de développement, de manière similaire aux objectifs à long terme.
  - **Gain** : Rendre tangible la progression des compétences (ex. cuisine, programmation, sport, dessin) en reliant les actions quotidiennes à des gains de niveaux de compétence clairs, offrant ainsi une vision globale de son propre développement.
- **Système de Punitions & Récompenses** :
  - **Objectif** : Créer un mécanisme équilibré de conséquences positives (rewards) et négatives (punitions) face au respect ou à l'échec des engagements. Les récompenses proposent une boutique d'achats cosmétiques ou d'activités réelles, tandis que les punitions imposent des actions compensatoires utiles.
  - **Gain** : Renforcer l'implication en donnant une valeur tangible (récompenses) et une conséquence constructive (punitions) aux comportements quotidiens, tout en évitant la culpabilité stérile grâce aux actions compensatoires.

