# Index des Commandes (Habit Tracker Bot)

Ce document centralise toutes les commandes disponibles pour le bot Telegram.

> **⚠️ NOTE IMPORTANTE POUR LES AGENTS IA :**
> **Ce fichier est l'INDEX OFFICIEL des commandes.** 
> Dès que vous ajoutez, modifiez, ou supprimez une commande du bot dans le code (ou dans le contrat `specs/001-habit-tracker-bot/contracts/bot-commands.md`), vous **DEVEZ IMPÉRATIVEMENT** mettre à jour ce document pour qu'il reste synchronisé avec la réalité du système.

---

## 📋 Commandes Utilisateur (Bot Telegram)

| Commande | Arguments | Description | Exemple |
|----------|-----------|-------------|---------|
| `/done` | `[nom_habitude]` | Valide une habitude **binaire** (faite / pas faite). Refuse si déjà faite aujourd'hui ou si l'habitude est quantitative. | `/done routine_matin` |
| `/log` | `[nom_habitude] [valeur][unité]` | Enregistre une habitude **quantitative** avec une mesure. Vérifie que l'unité correspond. | `/log lecture 30min` |
| `/skip` | `[nom_habitude] raison: [texte]` | Saute une habitude pour aujourd'hui **sans casser le streak**. La raison est obligatoire. | `/skip nage raison: fatigue extreme` |
| `/status` | *(aucun)* | Affiche le statut du jour : Perfect Day ou non, seuils, streak, or, niveau/XP, quêtes faites / skippées / restantes. | `/status` |
| `/set-day` *(alias `/template`)* | `[nom_template]` | Change le « type de journée » et réajuste les seuils. Templates : `semaine`, `weekend`, `recovery`, `sick`. | `/template sick` |

---

## ⚙️ Détails et Fonctionnement

* **Multi-utilisateur** : Chaque membre du groupe est identifié par son `chat_id` Telegram. Un nouvel utilisateur est créé automatiquement au premier message (niveau 1, 0 XP, 0 Gold).
* **Base de données partagée** : Il n'y a pas de communication directe bot ↔ site. Les deux écrivent et lisent la même base SQLite (`./data/`). Tout ce que le bot enregistre apparaît sur le site web instantanément.
* **Récapitulatif automatique** : À 23h59, le scheduler calcule le score final de chaque joueur, attribue de l'XP et publie le bilan de la guilde dans le groupe.
* **Sécurité & DM** : En production, le bot ignore tout message venant d'un chat non autorisé. Les messages privés (DM) sont autorisés automatiquement dès qu'un membre a posté au moins 1 fois dans le groupe public.
