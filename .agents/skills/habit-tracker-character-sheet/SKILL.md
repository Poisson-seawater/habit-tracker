---
name: "habit-tracker-character-sheet"
description: "Explain the ephemeral Character Sheet (Feuille de Personnage) system with its 6 stats: discipline, santé, finance, etc."
compatibility: "Habit Tracker MVP/V2"
metadata:
  purpose: "Explain the ephemeral Character Sheet stats, thresholds, and calculations"
---

# Habit Tracker - Feuille de Personnage (Éphémère)

Ce skill documente et explique le fonctionnement de la **Feuille de Personnage Éphémère** de l'Habit Tracker RPG V2. Il sert de guide pour comprendre comment les statistiques quotidiennes sont gagnées, stockées, réinitialisées et comparées aux objectifs de la journée (Perfect Days).

---

## 🔮 Le Concept : La Fiche Éphémère

Dans un RPG classique, le personnage possède des attributs permanents. Dans cet Habit Tracker, le personnage, c'est **vous**. 

*   **Réinitialisation Quotidienne (Tabula Rasa) :** Chaque matin au réveil, toutes vos statistiques retombent à **0**. La journée commence sur une page blanche.
*   **Objectif de la journée :** Remplir vos barres de statistiques quotidiennes en validant vos actions réelles de développement personnel.
*   **Finalité :** Atteindre les seuils requis par votre **Template de Jour** actif pour valider un **Perfect Day** (qui octroie un bonus précieux de **+5 XP** lors du bilan à 21h30).

---

## 📊 Les 6 Dimensions de Vie (Statistiques)

Le système mesure votre investissement à travers **6 dimensions clés** (`ALL_6_STATS` dans le code) :

1.  **Forme physique 💪 (`forme_physique`) :** Mesure le sport, l'endurance, le cardio, la musculation, les étirements et la mobilité.
2.  **Santé (mental & alimentation) 🧠 (`sante`) :** Mesure la nutrition, le sommeil, la méditation, la détente mentale et la récupération (allostasie).
3.  **Social 🤝 (`social`) :** Mesure les moments de partage en famille, les sorties entre amis, la communication et les activités de réseau.
4.  **Finance 💰 (`finance`) :** Mesure le suivi du budget personnel, les investissements, l'épargne et les actions de business/travail.
5.  **Apprendre 📚 (`apprendre`) :** Mesure la lecture de livres, l'étude, l'acquisition de softskills, la créativité et les projets de code.
6.  **Discipline ⚔️ (`discipline`) :** Mesure la tenue des routines du matin/soir, l'organisation, le focus profond et le respect des règles.

---

## 📈 Comment accumuler des points ?

Les statistiques grimpent au cours de la journée via deux mécanismes :

### 1. Les Quêtes Actives (Habitudes)
Chaque habitude possède un dictionnaire `point_rewards` associant des points à des statistiques (ex: `{"discipline": 2, "sante": 1}`).
*   **Habitude Binaire (`type="binary"`) :** Rapporte la récompense de points une seule fois lors de la validation. 
    *   *Cas particulier (cible quotidienne) :* Si l'habitude a un `daily_target` > 1 (ex: boire 3L d'eau), chaque validation intermédiaire donne des points supplémentaires, dans la limite éventuelle du `daily_cap`.
*   **Habitude Quantitative (`type="quantitative"`) :** Multiplie les points de récompense par la valeur saisie (ex: `30` minutes de lecture avec `+0.2 points/min` d'apprentissage = `+6 points`), plafonné par le `daily_cap` de l'habitude.

### 2. Le Tableau des Primes (Todos)
Les tâches uniques (Todos) permettent d'associer des bonus de statistiques éphémères pour la journée de complétion en plus de l'XP :
*   `stat_reward_1` / `points_reward_1` (ex: +5 Discipline)
*   `stat_reward_2` / `points_reward_2` (ex: +3 Finance)

---

## 🏆 Calcul et validation du "Perfect Day"

### ⚙️ Les Templates et Seuils
Les seuils requis de statistiques varient selon le type de journée pour rester réalistes. Par défaut, le backend définit les seuils suivants (`DEFAULT_THRESHOLDS`) :
*   **Semaine (`week`) :** `{"discipline": 11, "apprendre": 6}`
*   **Weekend (`weekend`) :** `{"sante": 8, "social": 4, "apprendre": 3}`
*   **Récupération (`recup`) :** `{"sante": 8}`
*   **Malade (`malade`) :** `{"sante": 3}`

L'utilisateur peut modifier et personnaliser ses seuils pour chaque template depuis l'écran des paramètres du Dashboard.

### 🧮 L'évaluation quotidienne (`score_service.py`)
À chaque validation d'action (habitude logguée ou todo terminé) :
1.  Le système récupère le template actif de l'utilisateur pour le jour donné.
2.  Il additionne tous les points de statistiques générés par les logs d'habitude de la journée (en tenant compte des caps individuels).
3.  Il additionne les bonus de statistiques issus des Todos complétés aujourd'hui.
4.  Il compare les totaux cumulés aux exigences du template actif :
    *   **Perfect Day réussi :** Si **toutes** les statistiques requises par le template atteignent ou dépassent leurs seuils. Le statut de la journée passe à `"Perfect"`.
    *   **Échec / Incomplet :** Si au moins un seuil requis n'est pas atteint. Le statut reste `"Failed"`.

---

## 🗄️ Implémentation Technique

### Modèles de Données SQLAlchemy (`backend/src/database/models.py`)

*   **`PerfectDayTemplate`** : Configuration des seuils par template et par utilisateur.
    ```python
    class PerfectDayTemplate(Base):
        __tablename__ = "perfect_day_templates"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, ForeignKey("users.id"))
        template_name = Column(String)  # "week", "weekend", "recup", "malade"
        thresholds_json = Column(JSON)  # ex: {"discipline": 11, "apprendre": 6}
    ```
*   **`DailyScore`** : Contient l'état historique de chaque journée.
    ```python
    class DailyScore(Base):
        __tablename__ = "daily_scores"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, ForeignKey("users.id"))
        date = Column(Date)
        status = Column(String)         # "Failed" ou "Perfect"
        template_used = Column(String)  # Le template actif ce jour-là
        actual_stats = Column(JSON)     # ex: {"discipline": 12, "sante": 4, ...}
    ```

### Flux API (`backend/src/api/routes.py`)

*   **`/api/v1/profile` (GET) :** Renvoie les statistiques accumulées aujourd'hui (`stats`), les seuils du template actif (`thresholds`), ainsi que l'état de validation de la journée (`scores.perfect_day_validated`).
*   **`/api/v1/profile/template` (POST) :** Change le template de la journée en cours et recalcule immédiatement les statistiques et statuts.

---

## 🤖 Interaction avec le Bot Telegram

L'aventurier peut piloter sa feuille de personnage directement par chat :
*   **`/status` :** Affiche un résumé visuel de la feuille de personnage éphémère (progression Actuel/Seuil par statistique requise), les habitudes complétées et l'état général du Perfect Day.
*   **`/log [nom_habitude] [valeur]` :** Enregistre une activité, recalculant les statistiques en arrière-plan.
*   **`/template [nom_template]` (ou `/set-day`) :** Change le template de la journée (ex: basculer en `recup` ou `malade` si besoin de repos) pour abaisser les exigences de statistiques.
