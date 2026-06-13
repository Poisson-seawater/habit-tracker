# Règles & variables

Cette page liste les pièces du jeu : les commandes, les options, et surtout comment elles s'imbriquent. Lis-la pour avoir le système entier en tête, sans ouvrir le code.

## La boucle, en bref

Tu logges des [habitudes](#/habitudes) et tu coches des [primes](#/primes-todo). Ça remplit tes 12 [stats](#/stats-xp-niveau-or) du jour, qu'on compare ensuite aux seuils du [template](#/templates-de-jour) actif. Si tous les seuils sont atteints, c'est un [Perfect Day](#/perfect-day) (+5 XP). Puis, à 23h59, la journée se fige et les stats repartent à zéro.

## Commandes du bot Telegram

| Commande | Arguments | Effet |
|---|---|---|
| `/done` | `<habitude>` | Valide une habitude binaire (refuse si déjà faite, ou si quantitative) |
| `/log` | `<habitude> <valeur><unité>` | Enregistre une habitude quantitative (vérifie l'unité) |
| `/skip` | `<habitude> raison: <texte>` | Saute une habitude sans casser le streak (raison obligatoire) |
| `/status` | *(aucun)* | Perfect Day, seuils, streak, or, niveau/XP, quêtes faites/skippées/restantes, No-Todos échoués |
| `/set-day` *(alias `/template`)* | `<template>` | Change le type de journée : `semaine`, `weekend`, `recovery`, `sick` |
| `/liste` | `todo` \| `habit` \| `notodo` | Liste ce qui reste (todo/habit) ou les règles à tenir (notodo) |
| `/add` | `todo` \| `notodo` \| `habit` `<titre>` | Ajoute une tâche, une règle, ou guide la création d'une habitude |
| `/add_habit` | `binary` \| `quant` `<titre> [unité]` | Crée une habitude avec des valeurs par défaut |
| `/fail` | `<notodo>` | Marque une règle No-Todo comme enfreinte aujourd'hui |
| `/shop` | *(aucun)* | Affiche toutes les récompenses de la boutique avec leur état |
| `/shop dispos` | *(aucun)* | Filtre uniquement les items disponibles à l'achat ou à la rédemption |
| `/shop verrouillees` | *(aucun)* | Affiche uniquement les items verrouillés par des prérequis |
| `/buy` | `[nom]` | Achète ou réclame un item par son titre (ou une portion unique du titre) |
| `/aide` *(alias `/help`)* | *(aucun)* | Menu d'aide (documentation + liste des commandes) |

## Variables & options clés

| Élément | Valeurs | Rôle |
|---|---|---|
| Type d'habitude | binaire / quantitative | binaire = `/done` ; quantitative = `/log` avec unité |
| Fréquence d'habitude | jours de la semaine | l'habitude n'est due que les jours planifiés |
| Plafond journalier (cap) | points max / jour | borne l'apport d'une habitude quantitative |
| Récompense d'habitude | points par stat | combien chaque stat monte quand l'habitude est faite |
| Template de jour | semaine / weekend / recovery / sick | fixe les seuils du Perfect Day du jour |
| Seuils du template | points par stat | la barre à atteindre ce jour-là |
| XP de prime | 1 à 40 | XP direct gagné en cochant la prime |
| `is_private` (habitude) | oui / non | comptée pour toi, masquée du recap public |
| `is_reportable` | oui / non | apparaît ou non dans le bilan du groupe |
| Pins recap 3-3-3 | listes d'IDs | sous-étapes et softskills épinglées, persistées via `PUT /api/v1/profile/pins` |

## Comment ça interagit (le modèle mental)

**Deux horizons séparés.** Le [Perfect Day](#/perfect-day) (quotidien, éphémère) et les [objectifs](#/objectifs) (long terme, permanents via l'Or) ne se calculent pas l'un l'autre. Le lien est d'**intention** : les [habitudes](#/habitudes) construisent la régularité qui rend les objectifs atteignables, à ton rythme.

**Le Perfect Day vient de deux sources.** Stats des [habitudes](#/habitudes) + stats des [primes](#/primes-todo), comparées aux seuils du [template](#/templates-de-jour) du jour. Aucune des deux seule ne suffit.

**XP ≠ Or.** L'XP (et le niveau) mesure la **régularité** (Perfect Days + primes). L'Or mesure l'**avancement réel** des projets (sous-étapes d'objectifs). Deux monnaies, deux significations.

**Le template protège les jours off.** Basculer en `recovery` / `sick` abaisse les seuils : un jour de repos reste « réussissable ».

**Le streak récompense la constance.** Un `/skip` justifié préserve le streak ; un seuil raté le casse.

**Données partagées bot ↔ site.** Le bot et le site lisent et écrivent dans la même base. Du coup, un `/log` Telegram apparaît aussitôt sur le site.

**Le Recap 3-3-3 agrège sans dupliquer.** Le panneau [Recap 3-3-3](#/recap-3-3-3) lit directement les données existantes — sous-étapes d'[objectifs](#/objectifs), nœuds de [softskills](#/softskills), récompenses d'allostasie de la [Boutique](#/boutique-recompenses) — et les affiche en un seul endroit. Valider une allostasie depuis le recap a le même effet que la valider depuis la boutique.

## Multi-utilisateur & confidentialité

Chaque membre du groupe est un joueur. Son profil se crée tout seul à son premier message (niveau 1, 0 XP, 0 Or). Une habitude `is_private` compte pour son Perfect Day, mais reste hors du recap public. Et le bot accepte les messages privés (DM) dès qu'un membre a posté au moins une fois dans le groupe autorisé.
