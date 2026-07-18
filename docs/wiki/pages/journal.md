# Journal des mises à jour

Chaque entrée résume ce qui a été intégré à la doc, du plus récent au plus ancien. Utile pour savoir « la doc date de quel commit, et qu'est-ce qui a bougé depuis ».

## 2026-07-07 — régénération complète (`d0147e2` → `eedf792`)

- **Nouveau modèle d'accueil** : [Accueil](#/) devient un hall léger (objectif + carte mentale + « Par où entrer ? ») ; la narration des concepts vit désormais dans trois sommaires : [Découvrir](#/new-user) (parcours pas à pas), [Utiliser](#/user) (usage avancé + objections), [Développer](#/dev) (architecture + mise en route).
- **[Carte de l'app](#/carte-de-l-app)** réorganisée par écrans réels du dashboard (⚔️ Dashboard, 🏆 Objectifs & Graphes, 🌳 Softskills, 🚫 NO To-Do, ⚙️ Perfect Days, 🛒 Boutique) + Bot Telegram + Automatismes + Télécommande IA, avec les tests existants conservés et de nouvelles lignes ajoutées (checkbox de validation depuis l'agenda, repos minimum éditable par template, sous-étape → quête auto, déliaison de sous-étape partagée).
- **Correction factuelle** : [Perfect Day](#/perfect-day) se fige à **21h30** (calcul du score + bilan de guilde), pas à 23h59 — un second passage à **00:00** finalise les streaks de la veille.
- **[Objectifs](#/objectifs)**, **[Agenda & timeline](#/agenda-timeline)** et **[Templates de jour](#/templates-de-jour)** mis à jour avec les nouveautés récentes : quête auto générée par l'épinglage d'une sous-étape, déliaison sans suppression, validation directe depuis l'agenda, repos minimum éditable par template.
- **[Templates de jour](#/templates-de-jour)** et **[Télécommande IA](#/telecommande-ia)** vérifiés à jour : contenu déjà exact, seule la phrase sur l'édition des templates a été rafraîchie.

## 2026-07-07 — ajout manuel de la Carte de l'app

- **Ajouté** : [Carte de l'app](#/carte-de-l-app) — inventaire de toutes les fonctions avec, pour chacune, un test de 30 secondes (action → résultat attendu) et un parcours de validation complet de ~10 minutes.

## 2026-07-02 — commit `0a47f0c` → `d0147e2`

Rafraîchissement après 14 commits de dérive : intégration Google Calendar/Tasks, agenda vertical, timeline biologique et refonte de l'authentification.

- **Ajouté** : [Synchronisation Google Calendar & Tasks](#/sync-google), [Agenda vertical & timeline biologique](#/agenda-timeline), [Authentification & appareils](#/authentification).
- **Mis à jour** : [Primes (Todos)](#/primes-todo) (do_date/due_date, formats de date, rappels), [Perfect Day](#/perfect-day) et [Templates de jour](#/templates-de-jour) (lien agenda vertical + budgets d'effort), [Règles & variables](#/regles-et-variables) (variables Google + auth), [Télécommande IA](#/telecommande-ia) (jeton machine), [Accueil](#/) (nouveaux concepts référencés).
- **Retiré** : rien — aucun concept n'a disparu depuis la dernière génération.
