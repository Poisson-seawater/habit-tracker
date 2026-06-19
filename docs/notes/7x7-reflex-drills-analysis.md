# Memo — Feature « 7x7 » (reflex drills) : analyse & décision

> Statut : **idée cadrée, non implémentée.** Conclusion de la session de brainstorm du 2026-06-14.
> Verdict court : le mécanisme vaut le coup pour une **catégorie étroite** de comportements, mais
> l'implémenter « en grand » serait du **sur-ingénierie** au service d'une prémisse à moitié mythe.
> Référence Vision : [README.md → Vision & Philosophie](../../README.md).

## 1. L'idée de départ

Quand on crée un **softskill** et qu'on l'épingle dans le **Recap 3-3-3**, on pourrait cocher une option
« 7x7 » : un exercice à répéter plusieurs fois dans la journée. Concept invoqué — *pour créer un
réflexe, le répéter 7 fois aléatoirement dans la journée, 7 jours d'affilée*. Le bot enverrait des
**messages privés (DM)** pour déclencher les 7 répétitions.

## 2. La prémisse : ce qui est faux, ce qui est vrai

**Faux / à ne pas vendre.** « 7×7 crée un réflexe » est une formule pop-psycho. La référence sérieuse
(Lally et al., 2010) donne une **médiane de ~66 jours** pour atteindre l'automatisme, avec une variance
énorme (18 à 254 j). Les chiffres ronds (21 j, 7×7…) ne sont pas fondés. Risque concret : conclure que
l'app « ne marche pas » alors que c'est la théorie qui était fausse.

**Vrai, pour une catégorie étroite.** Le mécanisme « prompt aléatoire plusieurs fois/jour » est
pertinent — pas pour son volume, mais parce que :

- la valeur est dans la **répétition du lien cue → réponse**, pas dans le cumul ;
- l'**aléatoire** simule l'imprévisibilité réelle → le réflexe se **généralise** au lieu de s'ancrer à
  un seul contexte (pratique variée / interleaved, c'est légitime) ;
- le buzz du bot est un **échafaudage de déclencheur artificiel** qu'on transfère ensuite à des cues
  naturels.

**Marche pour** : posture (redresser le dos), respiration/reset, reformulation mentale, relâcher les
épaules, remplacer un tic verbal, sourire.
**Ne marche pas pour** : tout ce qui prend du temps (« 30 min de sport », « écrire »).
→ **Réserver le 7x7 aux micro-réflexes**, sinon il devient une usine à culpabilité.

## 3. Le vrai problème est architectural

Le 7x7 **ne rentre dans aucun des deux modèles existants** :

| Modèle | Ce qu'il est | Ce qui manque pour 7x7 |
|--------|--------------|------------------------|
| `UserSoftskillProgress` | arbre de progression (`current_level`, `completed`, `success_criteria_test`) | **aucun mécanisme de log** |
| `Habit` + `HabitLog` | logging, mais conçu pour **1 validation/jour** (`reminder_time` unique, recap du soir) | pas de notion « 7 reps/jour » ni de compteur sur 7 jours |

Le 7x7 est un **troisième objet** : rattaché à un softskill, mais qui se logge ~7×/jour comme une
habitude haute-fréquence, avec un compteur sur 7 jours.

**Reco (Pi 40 Mo, pas de sur-ingénierie)** : **ne pas créer de nouvelle table.** Modéliser le drill
comme une `Habit` spéciale (`type="reflex"`, `daily_cap=7`, liée à un `softskill_id`) et réutiliser
`HabitLog` — chaque rep = un log `"log"`. On récupère gratuitement le logging, le recap du soir, les
stats. Une table `ReflexDrill`/`ReflexRep` dédiée serait plus « propre » sémantiquement mais c'est du
code + de la RAM en plus pour rien à cette échelle.

## 4. La réalité du scheduler (2ᵉ mur technique)

Aujourd'hui : **un seul cron, à 21:30** (`scheduler.py`, `publish_daily_recap`). Le 7x7 fait changer
d'échelle :

- **Tirer N horaires aléatoires/jour** dans une fenêtre d'éveil (ex. 08:00–22:00 — jamais à 3h ; le
  scheduler a déjà la `TIMEZONE`, la réutiliser).
- **Espacement minimum** entre deux prompts, sinon le random envoie 3 buzz en 10 min.
- **Persistance** : APScheduler est ici **en mémoire**. Si le bot/Pi redémarre en milieu de journée, le
  planning du jour est perdu — il faut soit **stocker les horaires tirés**, soit les **recalculer de
  façon déterministe** (seed = `user_id` + date).
- **Scalabilité** : coût en `users × drills × 7`. OK pour 1 user (Gabriel), à noter pour le multi-user.

## 5. Risque n°1 : la fatigue de notifications

7 pings/jour pour **un** drill. 3 softskills 7x7 dans le 3-3-3 → **21 notifications/jour**. On finit par
les ignorer, ce qui (a) tue le réflexe et (b) entraîne à ignorer le bot en général.

- **Limiter à 1 (max 2) drill 7x7 actif à la fois.** Contre-intuitif, mais c'est ce qui sauve la feature.
- DM avec **boutons inline ✅/⏭️** (1 tap pour logger — il faut que le listener gère les
  `callback_query`, **à vérifier**, le bot semble aujourd'hui purement command/parser).
- **Snooze** « plus tard » + **mode pause** (malade/voyage).
- 7x7 **toujours en DM**, jamais dans le groupe.

## 6. Questions de design à trancher avant tout code

1. **Jour réussi = combien ?** 7/7 est brutal (on craque jour 1). Viser un **seuil (ex. 5/7)**.
2. **Un jour raté casse-t-il le streak ?** La prémisse « 7 d'affilée » dit oui — démoralisant et non
   fondé. Alternative plus douce : « 7 jours **qualifiants**, pas forcément consécutifs ».
3. **Fin du drill** : à 7 jours validés → softskill level-up + le drill **s'archive** (sinon il buzz à
   vie). Boucle de fermeture **essentielle**.
4. **Estompage de l'échafaudage** (v2) : réduire les prompts au fil des jours (7 le jour 1 → 2-3 le
   jour 7) à mesure que le cue naturel prend le relais ; idéalement capter « je l'ai fait
   spontanément ». Puissant mais coûteux → reporté.

## 7. Décision

**Ne pas construire le moteur complet** (random scheduler restart-safe + callbacks + throttling) pour
une théorie comportementale à moitié mythe. Si on poursuit, **seulement via un test réduit** qui valide
les vrais risques (fatigue de notif + UX de log + robustesse scheduler) avant tout investissement :

> **MVP 7x7 minimal** — 1 seul drill actif → une `Habit` `type="reflex"` liée à un softskill,
> `daily_cap=7` → chaque matin, tirage de N horaires (fenêtre fixe + espacement min, **stockés**) → DM
> avec ✅/⏭️ → recap du soir affiche `X/7` et `jour 3/7`. **Tester 1 semaine sur soi** sur un seul
> réflexe concret (ex. posture). Si dès le jour 4 on ignore les buzz → réponse obtenue avant d'avoir
> écrit le gros du code.

**Deux questions ouvertes qui conditionnent la suite :**
- 7x7 réservé aux **micro-réflexes**, ou ouvert à n'importe quel softskill (ça change tout) ?
- **1 drill actif à la fois** : acceptable, ou rédhibitoire ?
