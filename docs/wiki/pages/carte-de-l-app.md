# Carte de l'app

Tout ce que l'app sait faire, sur une seule page. Chaque fonction vient avec un test de 30 secondes : tu fais l'action, tu vérifies le résultat attendu. Si le résultat n'est pas là, la fonction est cassée — tu sais quoi réparer avant de pousser.

## ⚔️ Dashboard

| Fonction | Ce qu'elle doit faire | Pour vérifier | Détail |
|---|---|---|---|
| Perfect Day | Toutes les habitudes prévues traitées = +5 XP, série qui continue | Valide/skippe tout ce qui reste pour aujourd'hui → le bilan de 21h30 compte un Perfect Day | [Perfect Day](#/perfect-day) |
| Valider une quête depuis l'agenda | La case à cocher sur la carte ou le bloc de la timeline valide directement, sans passer par le bot | Coche une quête binaire dans l'agenda → elle passe `✅ Fait` sans quitter le dashboard | [Agenda & timeline](#/agenda-timeline) |
| Paliers de streak | 30 j de streak = +100 XP +50 Or ; 90 j = +300 XP +150 Or | Au passage du palier → célébration + les compteurs XP/Or montent des montants exacts | [Habitudes](#/habitudes) |
| Recap 3-3-3 | 3 sous-étapes + 3 softskills épinglées + 3 allostasies, dès l'accueil | Épingle via le crayon → recharge la page → la sélection persiste ; clic sur un item → l'onglet cible s'ouvre, l'élément mis en valeur | [Recap 3-3-3](#/recap-3-3-3) |

## 🏆 Objectifs & Graphes

| Fonction | Ce qu'elle doit faire | Pour vérifier | Détail |
|---|---|---|---|
| Objectifs & sous-étapes | Valider une sous-étape rapporte de l'Or (défaut 50) ; les dépendances verrouillent (🔒) | Coche une sous-étape débloquée → ton Or monte ; une sous-étape dont le prérequis n'est pas validé reste 🔒 | [Objectifs](#/objectifs) |
| Sous-étape partagée | Une sous-étape liée à plusieurs objectifs se valide partout d'un coup | Valide-la dans un objectif → elle apparaît validée dans l'autre | [Objectifs](#/objectifs) |
| Délier une sous-étape partagée | Retire le lien à un objectif sans supprimer la sous-étape ni casser les autres liens | Sur une sous-étape liée à 2 objectifs, délie-la d'un seul → elle reste intacte dans l'autre ; tente de délier son dernier lien → refus | [Objectifs](#/objectifs) |
| Épingler une sous-étape → quête auto | Épingler une sous-étape en Recap 3-3-3 génère une quête quotidienne dans l'agenda | Épingle une sous-étape → une quête « Étape: … » apparaît dans l'agenda du jour ; désépingle → elle disparaît | [Objectifs](#/objectifs) |
| Montée de niveau | XP requis double à chaque niveau : 10, 20, 40, 80… | Passe le seuil → le niveau s'incrémente dans `/status` et sur le dashboard | [XP, niveau & or](#/stats-xp-niveau-or) |

## 🌳 Softskills

| Fonction | Ce qu'elle doit faire | Pour vérifier | Détail |
|---|---|---|---|
| Arbre de softskills | Une compétence se débloque quand ses parentes sont validées | Compétence 🔒 → valide sa parente → elle passe 🔓 ; complète-la → ✅ et ses enfants se débloquent | [Softskills](#/softskills) |
| Création de branche entière | Crée une branche avec toutes ses compétences, positions allouées automatiquement | Crée une branche avec 3 compétences → elle apparaît sur l'arbre sans chevauchement à placer à la main | [Softskills](#/softskills) |

## 🚫 NO To-Do

| Fonction | Ce qu'elle doit faire | Pour vérifier | Détail |
|---|---|---|---|
| No-Todo | `/fail` trace une règle enfreinte aujourd'hui | `/add notodo <titre>` puis `/fail <nom>` → l'échec apparaît dans `/status` | [No-Todo](#/no-todo) |

## ⚙️ Perfect Days (réglages)

| Fonction | Ce qu'elle doit faire | Pour vérifier | Détail |
|---|---|---|---|
| Template de jour | `rest` / `regular` / `hustle` change l'agenda type et les budgets d'effort | `/set-day rest` → la jauge de budget de la vue Perfect Day passe aux plafonds `rest` (1 h/type, 4 h total) | [Templates de jour](#/templates-de-jour) |
| Réglage du repos minimum par template | L'objectif de repos (`min_rest_hours`) de chaque template est éditable, pas seulement le focus | Ouvre ⚙️ Perfect Days → change la valeur du champ « Objectif Repos (h) » → sauvegarde → rechargée, la nouvelle valeur est bien celle affichée | [Templates de jour](#/templates-de-jour) |
| Zones biologiques | Zones configurables, pas de chevauchement, minuit géré | Crée deux zones qui se chevauchent → erreur 422 ; la zone Sommeil (23:00 → 07:00) s'affiche correctement | [Agenda & timeline](#/agenda-timeline) |
| Cycle hustle/repos | Recommandation 4 semaines (3 normales, 1 chill), jamais bloquante | La semaine affichée change de régime selon les semaines écoulées ; tu peux quand même choisir librement | [Agenda & timeline](#/agenda-timeline) |
| Connexion Google | OAuth2 relie ton compte Google Calendar & Tasks | `GET /api/v1/auth/google/login` → accepte sur ton appareil → retour sur ⚙️ Perfect Days, statut « connecté » | [Sync Google](#/sync-google) |
| Export agenda vers Google | Pousse les quêtes placées vers Calendar, sans doublon (idempotent) | Lance l'export deux fois sur le même jour → une seule série d'événements | [Sync Google](#/sync-google) |
| Mot de passe applicatif | Chaque joueur change son propre mot de passe | Change ton mot de passe dans ⚙️ Perfect Days → déconnecte-toi → l'ancien mot de passe est refusé | [Authentification](#/authentification) |
| Appareils auto-approuvés | Tout nouvel appareil est approuvé directement (depuis le 2026-07-02) | Ouvre le dashboard depuis un navigateur jamais utilisé → accès sans étape « en attente » | [Authentification](#/authentification) |
| Bootstrap unique | `AUTH_BOOTSTRAP_CODE` crée le premier admin, puis se ferme | Une fois un admin créé, `POST /auth/bootstrap` refuse toute nouvelle tentative | [Authentification](#/authentification) |

## 🛒 Boutique

| Fonction | Ce qu'elle doit faire | Pour vérifier | Détail |
|---|---|---|---|
| Récompenses classiques | Achat classique = Or déduit ; peut être verrouillée par un softskill ou un objectif requis | `/buy <item>` → Or déduit ; une récompense verrouillée refuse l'achat tant que le prérequis n'est pas validé | [Boutique](#/boutique-recompenses) |
| Allostasie daily/weekly | Gratuite, max 3 par catégorie, reset quotidien/hebdo | `/shop` → l'allostasie validée passe `[✓ Validé]`, puis redevient `[🔄 A valider]` le lendemain (daily) ou le lundi (weekly) | [Boutique](#/boutique-recompenses) |

## Bot Telegram (commandes)

| Fonction | Ce qu'elle doit faire | Pour vérifier | Détail |
|---|---|---|---|
| Valider une habitude binaire | `/done` marque l'habitude faite et fait avancer le Perfect Day | `/done <habitude>` un jour planifié → `/status` la montre validée, streak +1. Refaire `/done` → refus (déjà faite) | [Habitudes](#/habitudes) |
| Logger une habitude quantitative | `/log` enregistre une mesure, en vérifiant l'unité | `/log <habitude> 30min` → acceptée ; avec une mauvaise unité → refus | [Habitudes](#/habitudes) |
| Skipper sans casser la série | `/skip` avec raison excuse l'habitude du jour, streak gelé (pas remis à 0) | `/skip <habitude> raison: malade` → `/status` la montre skippée ; sans `raison:` → refus | [Habitudes](#/habitudes) |
| État de la journée | `/status` récapitule tout, à tout moment | `/status` → Perfect Day, streak, or, niveau/XP, quêtes faites/skippées/restantes, No-Todos échoués | [Règles & variables](#/regles-et-variables) |
| Primes (todos) | Cocher une prime rapporte son XP direct (défaut 10, max 40) | `/add todo <titre>` puis coche-la → l'XP du profil monte du montant paramétré | [Primes](#/primes-todo) |
| Prime → Google | `do_date` crée un événement `⚔️` sur Calendar ; `due_date` crée une tâche `🏆` cochable | `/add todo <titre> do:demain due:15/07` → l'événement et la tâche apparaissent côté Google (si connecté) | [Sync Google](#/sync-google) |
| Rappels d'échéance | À 09:00, rappel Telegram privé à J-7, J-3 et J-1 avant la `do_date` | Pose une prime avec `do_date` dans 3 jours → rappel privé demain à 09:00 | [Sync Google](#/sync-google) |
| Boutique en Telegram | `/shop` et `/buy` fonctionnent hors dashboard | `/shop dispos` → filtre les items disponibles ; `/buy <nom>` → achète par portion de titre | [Boutique](#/boutique-recompenses) |
| Menu d'aide | `/aide` (alias `/help`) ouvre la doc et la liste des commandes | `/aide` → boutons vers la doc et `COMMANDS-INDEX.md` | [Règles & variables](#/regles-et-variables) |

## Automatismes planifiés

Ces jobs tournent seuls. Si l'un d'eux ne s'est pas manifesté à l'heure dite, c'est un bug côté scheduler ou côté bot.

| Heure | Ce qui doit se passer |
|---|---|
| 09:00 | Rappels Telegram des primes à `do_date` proche (J-7 / J-3 / J-1) |
| 21:30 | Recap de la guilde publié dans le groupe (Perfect Days, XP) |
| 00:00 | Finalisation des streaks de la veille (Perfect Day + habitudes non traitées) |
| Lundi 00:00 | Fenêtre de reset des allostasies weekly (nouvelle semaine ISO disponible) |

## Télécommande IA

| Fonction | Ce qu'elle doit faire | Pour vérifier | Détail |
|---|---|---|---|
| Découverte des capacités | `GET /api/v1/capabilities` annonce ce que la télécommande sait faire | `habitctl.py doctor` → répond `ok` avec la version de protocole | [Télécommande IA](#/telecommande-ia) |
| Action idempotente | Rejouer la même clé d'idempotence ne double pas l'effet | Lance deux fois `habitctl.py act habit-done --target …` avec la même clé → un seul log créé | [Télécommande IA](#/telecommande-ia) |
| Plan puis apply | Une modification structurelle exige un plan confirmé | `habitctl.py plan …` puis `apply PLAN_ID` → refuse si l'état distant a changé entretemps | [Télécommande IA](#/telecommande-ia) |

## Parcours de validation complet (~10 min)

Le scénario qui traverse toute l'app de bout en bout. À dérouler après chaque grosse session de vibe coding : si les 10 étapes passent, le cœur de l'app est sain.

1. `/status` — l'état initial s'affiche sans erreur (streak, or, niveau, quêtes du jour).
2. Sur l'écran Objectifs, crée un objectif avec 2 sous-étapes — la seconde dépendante de la première : elle doit apparaître 🔒.
3. `/add_habit binary Test-validation` — l'habitude apparaît dans `/liste habit`.
4. `/done Test-validation` — `/status` la montre validée. Refais `/done` → refus attendu.
5. `/skip` une autre habitude avec `raison:` — skippée dans `/status`, streak intact.
6. `/add todo Course-test do:demain` — si Google est connecté, l'événement `⚔️ Course-test` apparaît sur le calendrier « Agenda des Quêtes ».
7. Coche la prime — ton XP monte ; côté Google, la tâche passe `completed` (si `due_date` posée).
8. Valide la première sous-étape de l'objectif — ton Or monte (+50 par défaut) et la seconde sous-étape se déverrouille.
9. `/shop` puis `/buy` d'une allostasie — elle passe `[✓ Validé]`, également visible dans le Recap 3-3-3.
10. À 21h30, le recap du groupe tombe et compte ta journée (Perfect Day, XP).

Étape cassée = la page liée dans les tableaux ci-dessus te dit comment la fonction est censée marcher, et sa colonne « Détail » où creuser.
