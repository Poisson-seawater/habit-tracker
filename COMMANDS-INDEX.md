# Index des Commandes (Habit Tracker Bot)

Ce document centralise toutes les commandes disponibles pour le bot Telegram.

> **⚠️ NOTE IMPORTANTE POUR LES AGENTS IA :**
> **Ce fichier est l'INDEX OFFICIEL des commandes.** 
> Dès que vous ajoutez, modifiez, ou supprimez une commande du bot dans le code (ou dans le contrat `specs/001-habit-tracker-bot/contracts/bot-commands.md`), vous **DEVEZ IMPÉRATIVEMENT** mettre à jour ce document pour qu'il reste synchronisé avec la réalité du système.

---

## 📋 Commandes Utilisateur (Bot Telegram)

| Commande | Arguments | Description | Exemple |
|----------|-----------|-------------|---------|
| `/done` | `[nom_habitude] [--yesterday]` | Valide une habitude **binaire** pour aujourd'hui ou, avec `--yesterday`, pour hier. La validation manuelle reste permise même si la quête n'est pas prévue pour le type de journée ciblé. Refuse une habitude quantitative, un doublon sans cible/jour, ou une habitude actuellement marquée ratée. | `/done routine_matin --yesterday` |
| `/log` | `[nom_habitude] [valeur][unité] [--yesterday]` *(optionnel)* | Enregistre une habitude **quantitative** pour aujourd'hui ou, avec `--yesterday`, pour hier. La validation manuelle hors type de journée reste permise. **Sans argument : affiche un choix par bouton (Habitude/Todo) pour logger aujourd'hui.** | `/log lecture 30min --yesterday` |
| `/skip` | `[nom_habitude] raison: [texte]` | Saute une habitude pour aujourd'hui **sans casser le streak**. La raison est obligatoire. | `/skip nage raison: fatigue extreme` |
| `/status` | *(aucun)* | Affiche le statut du jour : Perfect Day ou non, streak, or, niveau/XP, quêtes faites / skippées / restantes, No-Todos échoués, et Life Lore accomplis aujourd'hui. Les quêtes restantes sont filtrées selon le type de journée courant. | `/status` |
| `/set-day` *(alias `/template`)* | `[nom_template]` *(optionnel)* | Change le « type de journée » et recalcule le Perfect Day. Templates : `rest`, `regular`, `hustle` (anciens alias acceptés : `semaine`, `weekend`, `recovery`, `sick`). **Sans argument : affiche 3 boutons de choix.** | `/set-day` ou `/template hustle` |
| `/aide` *(alias `/help`)* | *(aucun)* | Affiche le menu d'aide avec des boutons pour la documentation et la liste des commandes. | `/aide` ou `/help` |
| `/liste` | `[todo\|habit\|notodo]` *(optionnel)* | Liste les éléments restants à accomplir (todo/habit) ou les règles à ne pas enfreindre (notodo). La liste des habitudes est filtrée selon le type de journée courant. **Sans argument : affiche 3 boutons (Todos / Habitudes / No-Todos).** | `/liste` ou `/liste todo` |
| `/add` | `[todo\|notodo\|habit] [titre] [do:date] [due:date]` *(optionnel)* | Ajoute une nouvelle tâche ou règle. Les todos acceptent `do:` (date planifiée) et `due:` (date limite) au format `today`, `tomorrow`, `DD/MM` ou `YYYY-MM-DD`. **Sans argument : boutons de choix interactif.** | `/add todo Courses do:today due:tomorrow` |
| `/add_habit` | `[binary\|quant] [titre] [unité]` | Crée une habitude sans récompense de statistique. L'unité est optionnelle pour les habitudes quantitatives. | `/add_habit binary Lecture` |
| `/fail` | `[nom_notodo] [--yesterday]` | Marque une règle No-Todo comme ayant été transgressée pour aujourd'hui ou, avec `--yesterday`, pour hier. Crée un log daté et accepte des morceaux du nom. | `/fail snooze --yesterday` |
| `/fail_habit` | `[nom_habitude] [--undo]` *(optionnel)* | Marque une habitude comme ratée aujourd'hui et retire jusqu'à 5 XP, ou annule ce raté et restaure le montant avec `--undo`. Sans nom, affiche des boutons de sélection. Une habitude déjà complétée ou skippée ne peut pas être marquée ratée. | `/fail_habit Lecture` ou `/fail_habit Lecture --undo` |
| `/shop` | `[filtre]` *(optionnel)* | Affiche la boutique de récompenses avec leur coût et statut de verrouillage. Filtres : `toutes`, `dispos`, `verrouillees`. | `/shop dispos` |
| `/buy` | `[nom_recompense]` *(optionnel)* | Permet d'acheter une récompense ou valider une activité d'allostasie. Sans argument : affiche 3 boutons (Allostasie Day / Allostasie Week / Shop Basic) et n'affiche que ce qui est disponible ou abordable. | `/buy` ou `/buy Netflix` |
| `/motivation` | *(aucun)* | Liste tes objectifs à long terme pour garder le cap. | `/motivation` |
| `/softskill` *(alias `/softskills`, `/skills`)* | *(aucun)* | Ouvre le menu de gestion des softskills. Affiche les branches, permet d'ajouter un softskill ou de valider un test de softskill. | `/softskill` |

---

## ⚙️ Détails et Fonctionnement

* **Multi-utilisateur** : Chaque membre du groupe est identifié par son `chat_id` Telegram. Un nouvel utilisateur est créé automatiquement au premier message (niveau 1, 0 XP, 0 Gold).
* **Base de données partagée** : Il n'y a pas de communication directe bot ↔ site. Les deux écrivent et lisent la même base SQLite (`./data/`). Tout ce que le bot enregistre apparaît sur le site web instantanément.
* **Récapitulatif automatique** : À 21h30, le scheduler calcule le score final de chaque joueur, attribue de l'XP et publie le bilan de la guilde dans le groupe.
* **Sécurité & DM** : En production, le bot ignore tout message venant d'un chat non autorisé. Les messages privés (DM) sont autorisés automatiquement dès qu'un membre a posté au moins 1 fois dans le groupe public.
