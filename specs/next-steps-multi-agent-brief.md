# Brief multi-agents - prochains concepts Habit RPG Tracker

Date de cadrage : 2026-07-17  
Source : pistes futures de `README.md`, clarifiees avec Gabriel.  
Statut : **implémenté le 2026-07-17**. Document conservé comme référence de cadrage; le code courant, les tests, `COMMANDS-INDEX.md` et la documentation wiki décrivent le comportement livré.

## Résultat d'implémentation

- Le champ d'effort des sous-étapes est masqué sans supprimer les données existantes.
- Les habitudes acceptent plusieurs types de journées avec fallback sur les trois types.
- Une habitude peut être déclarée ratée aujourd'hui; la pénalité appliquée est de 5 XP maximum, restaurée à l'annulation, avec idempotence persistée dans le log.
- L'agenda, l'API et Telegram corrigent les validations de quêtes et les échecs No-Todo d'hier seulement.
- Les chevauchements de zones biologiques renvoient un prochain créneau libre sans sauvegarde silencieuse.
- Les sessions et approbations d'appareils expirent après 90 jours par défaut; une connexion applicative réussie auto-approuve le nouveau navigateur.
- Le système de punitions reste volontairement couvert par le statut d'habitude ratée, sans moteur séparé.

## Regles critiques pour les agents

- Lire `AGENTS.md`, `README.md`, `specs/ETAT_DES_SPECS.md`, `log.md` et le code courant avant d'implementer.
- Ne pas traiter les anciens dossiers Spec Kit comme source active par defaut. Plusieurs specs sont `implemented-stale` ou `superseded`.
- Stack actuelle : FastAPI + SQLAlchemy + SQLite, frontend vanilla HTML/CSS/JS sans build, bot Telegram, APScheduler.
- Contrainte Raspberry Pi : eviter les grosses dependances et les changements qui augmentent l'empreinte memoire.
- Nouveau champ DB : modifier `backend/src/database/models.py` et ajouter une migration idempotente dans `_run_migrations()` de `backend/src/database/seed.py`.
- Nouvelle route API : respecter `/api/v1`, les helpers d'auth existants et la compatibilite `X-User-ID`.
- Toute commande Telegram ajoutee, modifiee ou supprimee impose de mettre a jour `COMMANDS-INDEX.md`.
- Ne pas modifier `docker-compose.yml`, le header `X-User-ID`, les contrats API ou le schema DB sans justification explicite.

## Concepts retenus

Ordre issu du README apres retrait du concept deja implemente "Telechargement du plugin LLM".

1. Correction UI Sous-etapes Objectifs
2. Association des quetes aux types de journees
3. Habitude ratee
4. Systeme de punitions
5. Validation differee / correction d'hier
6. Debugging / correction Journee Biologique
7. Validation / securite moins agressive

## 1. Correction UI Sous-etapes Objectifs

### Intention

Dans l'onglet Objectifs, le champ "Duree d'effort (h)" ne doit plus apparaitre dans l'interface des sous-etapes.

### Decisions validees

- Le besoin concerne les sous-etapes dans l'onglet Objectifs, pas la creation d'habitudes.
- Le champ doit disparaitre a la creation et a l'edition d'une sous-etape.
- Les donnees existantes restent en base.
- L'API et le schema DB ne sont pas modifies.
- Traitement attendu : mini-fix frontend isole.

### Hors perimetre

- Migration DB.
- Suppression du champ cote backend.
- Refonte globale de l'onglet Objectifs.

### Verification attendue

- Depuis l'onglet Objectifs, creer une sous-etape : le champ "Duree d'effort (h)" n'apparait pas.
- Editer une sous-etape existante : le champ n'apparait pas.
- Les autres champs de sous-etape restent fonctionnels.

## 2. Association des quetes aux types de journees

### Intention

Permettre a chaque habitude / quete recurrente d'etre associee a un ou plusieurs types de journees. Exemples :

- "Echecs" : seulement `hustle`.
- "Ukulele" : `hustle`, `regular`/normal, `rest`.

Note vocabulaire : le code courant utilise `rest`, `regular`, `hustle`. Le cadrage utilisateur a employe "normal"; les agents doivent verifier le vocabulaire exact dans le code et conserver la compatibilite avec `regular`.

### Decisions validees

- Objet cible : habitudes / quetes recurrentes.
- Selection multi-types par quete.
- Par defaut, toutes les quetes existantes et nouvelles sont associees aux trois types.
- Si une quete n'est pas associee au type de journee courant :
  - elle n'apparait pas dans l'agenda;
  - elle ne compte pas pour le Perfect Day;
  - elle peut quand meme etre validee manuellement via commande/API;
  - cette validation manuelle produit un log et une recompense normale, mais ne modifie pas l'evaluation Perfect Day.
- La selection se fait dans le formulaire de creation/edition d'habitude.
- Le filtrage doit etre global : agenda, Perfect Day, recap Telegram, rappels et commandes bot.
- Implementation attendue : migration automatique + fallback defensif.

### Implications probables

- Ajouter un champ persistant sur les habitudes pour stocker les types de journees autorises.
- Migration idempotente dans `seed.py`.
- Fallback : une habitude sans champ/valeur doit etre interpretee comme compatible avec tous les types.
- Adapter les services qui construisent l'agenda et calculent le Perfect Day.
- Adapter les flux Telegram quotidiens.
- Mettre a jour `COMMANDS-INDEX.md` si les commandes bot changent.

### Hors perimetre

- Filtrage des todos ponctuels.
- Forcer une interdiction de validation manuelle hors type de journee.
- Changement des noms canoniques des templates sans migration explicite.

### Verification attendue

- Une quete `hustle` seule apparait un jour `hustle` et disparait un jour `rest`.
- Une quete compatible avec les trois types apparait toujours.
- Une quete hors journee ne bloque pas le Perfect Day.
- Une validation manuelle hors journee reste possible, cree un log et attribue la recompense normale sans rendre la quete requise pour Perfect Day.

## 3. Habitude ratee

### Intention

Permettre de declarer explicitement qu'une habitude / quete est ratee pour la journee.

### Decisions validees

- Un rate est visible dans l'UI.
- Un rate rend la journee non eligible au Perfect Day.
- Un rate retire l'XP que l'habitude aurait normalement rapporte.
- Un rate remet le streak de cette habitude a 0 immediatement.
- Une habitude deja completee aujourd'hui ne peut pas etre marquee ratee.
- Le rate peut etre annule le meme jour.
- A l'annulation :
  - l'XP retiree est restauree immediatement;
  - le streak est recalcule/finalise a minuit, pas restaure immediatement.
- Action disponible depuis :
  - agenda;
  - onglet Habitudes;
  - Telegram;
  - API.
- Telegram : prevoir une commande dediee et des boutons inline.
- Toute modification de commande bot impose une mise a jour de `COMMANDS-INDEX.md`.

### Implications probables

- Modeliser un etat journalier "failed" ou equivalent pour une habitude.
- Eviter les doubles effets XP lors de plusieurs appels ou annulations.
- Respecter l'idempotence et les recalculs existants du score.
- Verifier l'interaction avec le rollover minuit introduit dans les changements recents.
- Adapter le recap et les cartes UI pour distinguer `done`, `pending`, `failed`.

### Hors perimetre

- Systeme de sanctions configurable.
- Actions compensatoires automatiques.
- Marquer comme rate une habitude deja completee aujourd'hui.

### Verification attendue

- Marquer une habitude non completee comme ratee :
  - affiche le statut rate;
  - retire l'XP attendue;
  - met le streak a 0;
  - empeche Perfect Day.
- Tenter de marquer ratee une habitude deja completee est bloque.
- Annuler le rate le meme jour restaure l'XP.
- Le streak est coherent apres rollover de minuit.

## 4. Systeme de punitions

### Decision

Ne pas developper comme feature distincte pour l'instant.

### Interpretation validee

Le comportement attendu est couvert par "Habitude ratee" :

- perte d'XP;
- streak remis a 0;
- journee non-Perfect.

### Hors perimetre

- Actions compensatoires constructives.
- Punitions configurables.
- Quetes automatiques de compensation.
- Moteur de sanctions separe.

## 5. Validation differee / correction d'hier

### Intention

Permettre de corriger le lendemain une action oubliee, uniquement pour la journee precedente.

### Decisions validees

- Fenetre autorisee : hier seulement.
- Objets concernes :
  - quetes faites hier mais oubliees;
  - no-todos echoues hier mais oublies.
- Pour les no-todos, la correction differee sert a declarer un echec pour hier.
- La correction doit recalculer completement la journee d'hier :
  - score;
  - XP;
  - Perfect Day;
  - streaks.
- Disponible dans :
  - dashboard;
  - Telegram;
  - API.
- Telegram : utiliser une option sur les commandes existantes, par exemple `--yesterday`.
- Dashboard : ajouter un bouton "Hier" dans l'agenda pour basculer sur la journee precedente et corriger quetes/no-todos.
- Pas de confirmation speciale.
- Toute modification de commande bot impose une mise a jour de `COMMANDS-INDEX.md`.

### Implications probables

- Les endpoints ou services de logging doivent accepter explicitement une date cible limitee a hier.
- Les recalculs doivent etre idempotents et eviter de doubler l'XP.
- Les validations doivent refuser les dates plus anciennes qu'hier.
- L'agenda doit pouvoir afficher au moins aujourd'hui et hier, sans ouvrir un historique complet.

### Hors perimetre

- Edition libre des 7 derniers jours.
- Retour en arriere complet sur toute une journee au-dela d'hier.
- Correction positive des no-todos "respectes".

### Verification attendue

- Depuis dashboard, basculer sur hier et cocher une quete faite hier.
- Depuis Telegram, utiliser une commande existante avec `--yesterday`.
- Declarer un no-todo echoue hier.
- Verifier que le score/XP/Perfect Day/streaks d'hier sont recalcules.
- Verifier qu'avant-hier est refuse.

## 6. Debugging / correction Journee Biologique

### Intention

Transformer le besoin de "debugging" en feature utilisateur sur les zones de Journee Biologique, pour eviter les chevauchements lors de la configuration.

### Decisions validees

- Feature utilisateur, pas seulement outil admin/debug.
- Perimetre : zones de Journee Biologique seulement.
- Les items d'agenda ne sont pas concernes.
- En cas de chevauchement, l'app ne deplace rien silencieusement.
- L'app propose dans le formulaire le prochain creneau libre compatible.
- Le deplacement propose peut aller jusqu'a la fin de la journee biologique configuree.
- Si aucun espace libre suffisant n'existe, bloquer avec un message clair.
- Si l'utilisateur refuse la correction proposee, le formulaire reste ouvert avec erreur et l'utilisateur ajuste manuellement.

### Implications probables

- Ajouter une validation de chevauchement dans le formulaire ou le service qui gere les zones.
- Calculer le prochain creneau libre en conservant la duree demandee.
- Ne pas depasser la fin de la journee biologique configuree.
- Eviter les corrections silencieuses.

### Hors perimetre

- Reordonnancement automatique des items d'agenda.
- Passage au lendemain.
- Decalage en cascade d'autres zones.
- Raccourcissement automatique du creneau.

### Verification attendue

- Ajouter une zone qui chevauche une zone existante : proposition visible dans le formulaire.
- Accepter la proposition : la zone est sauvegardee au creneau propose.
- Refuser/ne pas accepter : sauvegarde bloquee et formulaire conserve.
- Ajouter une zone sans espace suffisant : message clair.

## 7. Validation / securite moins agressive

### Intention

Reduire la friction d'authentification et d'approbation d'appareils sans supprimer les garde-fous.

### Decisions validees

- Probleme principal : le systeme est trop agressif sur duree, navigateurs et appareils.
- Niveau vise : equilibre entre confort et securite.
- Apres Cloudflare Access + mot de passe applicatif, tout nouveau navigateur/appareil est auto-approuve.
- Les appareils approuves expirent apres 90 jours.
- A expiration, l'utilisateur repasse le flux complet Cloudflare + mot de passe, puis l'appareil est auto-approuve a nouveau.
- Garder une liste visible des appareils approuves avec revocation manuelle.
- En cas d'appareil inconnu ou expire, afficher un message simple : "Session expiree ou nouvel appareil. Reconnecte-toi."

### Implications probables

- Verifier l'implementation actuelle avant changement : la doc wiki mentionne deja des appareils auto-approuves depuis le 2026-07-02.
- Ajuster les durees/session/device si elles ne correspondent pas au cadrage 90 jours.
- Conserver la revocation manuelle.
- Eviter le fingerprinting intrusif pour regrouper plusieurs navigateurs.

### Hors perimetre

- Suppression de Cloudflare Access.
- Suppression du mot de passe applicatif.
- Fingerprinting machine avance.
- Appareils approuves indefiniment.

### Verification attendue

- Nouveau navigateur apres Cloudflare + mot de passe : auto-approbation.
- Appareil visible dans la liste des appareils approuves.
- Revocation manuelle fonctionnelle.
- Expiration simulee apres 90 jours : retour au flux complet.
- Message simple affiche pour appareil inconnu/expire.

## Ordre recommande de travail

1. Implementer le mini-fix UI Sous-etapes Objectifs.
2. Specifier puis implementer Association des quetes aux types de journees.
3. Specifier puis implementer Habitude ratee.
4. Marquer Systeme de punitions comme non-feature couverte par Habitude ratee.
5. Specifier puis implementer Validation differee / correction d'hier.
6. Specifier puis implementer Correction Journee Biologique.
7. Auditer puis ajuster Validation / securite moins agressive.

## Risques transverses

- Les concepts 2, 3 et 5 touchent le score, les streaks, le Perfect Day, le bot Telegram et potentiellement l'API. Ils doivent etre testes ensemble.
- Les concepts 3 et 5 peuvent interagir avec le rollover de minuit. Lire `score_service.py` et `scheduler.py` avant implementation.
- Les concepts 2, 3 et 5 risquent de modifier des commandes Telegram : `COMMANDS-INDEX.md` est obligatoire.
- Les changements DB doivent passer par `models.py` + `_run_migrations()` dans `seed.py`, pas par un fichier SQL seul.
- Ne pas supposer que les anciens specs de `specs/` representent l'etat courant.

## Questions explicitement fermees

- Telechargement du plugin LLM : deja implemente, retire du README, ne pas inclure comme prochain concept.
- Systeme de punitions : pas une feature separee pour l'instant.
- Validation differee : seulement hier, pas un historique libre.
- Journee Biologique : zones seulement, pas les items agenda.
