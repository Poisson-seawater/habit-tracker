---
name: habit-tracker-allostasis-rewards
description: "Gère la boutique d'allostasie (Allostasie Daily et Weekly) de Gabriel's Habit Tracker: limites à 3 items max, gratuité (0 Or), suivi du reset de rédemption (journalier à minuit, hebdomadaire le lundi à minuit) et affichage du statut de rédemption sur le bot Telegram et le dashboard."
compatibility: "Habit Tracker MVP/V3"
metadata:
  purpose: "Administering and validating Allostasis recovery rewards"
---

# Habit Tracker Allostasis Rewards

Ce skill couvre la gestion et le suivi des récompenses d'Allostasie (Daily et Weekly) de Gabriel's Habit Tracker.

## 🧠 Qu'est-ce que l'Allostasie ?

L'allostasie regroupe des activités de récupération et de bien-être (ex: regarder un épisode de série, prendre une bière le soir) configurées par l'utilisateur. 
Contrairement aux récompenses classiques :
1. Elles sont **gratuites** (coût de 0 Or forcé).
2. Elles sont **limitées à 3 items maximum par catégorie** (Daily et Weekly) par utilisateur.
3. Elles sont **répétables** mais soumises à une période de rédemption/reset :
   - **Allostasie Daily** : Réinitialisée chaque jour à minuit (heure locale).
   - **Allostasie Weekly** : Réinitialisée chaque lundi à minuit (heure locale).
4. Les items validés dans la journée sont affichés dans le **recap de fin de journée** sur Telegram.

---

## 🗄️ Colonnes DB concernées dans `rewards`

| Colonne | Type | Description |
|---|---|---|
| `category` | VARCHAR(50) | `'regular'`, `'allostasis_daily'`, ou `'allostasis_weekly'` (not null, par défaut `'regular'`) |
| `last_purchased_at` | DATETIME | Date et heure de la dernière rédemption (nullable) |

---

## 📡 REST API & Règles Métier

### 1. Création & Modification (`POST /api/v1/rewards` & `PUT /api/v1/rewards/{id}`)
- Si `category` vaut `'allostasis_daily'` ou `'allostasis_weekly'`, le `gold_cost` est **forcé à 0** et `is_one_time` est **forcé à False** (puisque ce sont des récompenses répétables et gratuites).
- Une validation stricte rejette la création ou la modification si le nombre total de récompenses de cette catégorie pour l'utilisateur dépasse **3**.

### 2. Achat / Rédemption (`POST /api/v1/rewards/{id}/purchase`)
- Bypasse la vérification et la déduction d'or de l'utilisateur (l'or de l'utilisateur reste intact).
- Met à jour `last_purchased_at` avec l'horodatage courant.
- Vérifie la disponibilité selon la période :
  - **Daily** : Bloqué si `last_purchased_at` est à la date locale d'aujourd'hui.
  - **Weekly** : Bloqué si `last_purchased_at` est dans la semaine courante (du lundi 00h00 au dimanche 23h59).

---

## 🤖 Interaction Bot Telegram

- `/shop` : Affiche les sections distinctes `Allostasie Daily` et `Allostasie Weekly` avant les récompenses classiques, avec des badges de statut :
  - `[✓ Validé]` si l'item a déjà été réclamé pour la période en cours.
  - `[🔄 A valider]` si l'item est disponible.
- `/buy [nom]` : Valide l'item d'allostasie sans déduire d'or et confirme la réclamation.
- **Daily Recap (Scheduler)** : Généré automatiquement à 21h30, il inclut les items d'allostasie validés aujourd'hui :
  `🧠 Allostasie : [titre_item] ✅`

---

## 💡 Opérations courantes

### Insérer un item d'allostasie en DB (Python)
```python
from src.database.session import SessionLocal
from src.database.models import Reward

db = SessionLocal()
try:
    # Note: L'API et le Service valident la limite des 3 items max.
    # Pour des insertions directes manuelles:
    new_item = Reward(
        user_id=1,
        title="25 min TV Show",
        description="Regarder un épisode",
        gold_cost=0,
        category="allostasis_daily",
        is_one_time=False
    )
    db.add(new_item)
    db.commit()
finally:
    db.close()
```
