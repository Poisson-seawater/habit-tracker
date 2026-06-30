# XP, niveau & or

Le jeu garde des compteurs permanents, mais les anciennes statistiques RPG quotidiennes ont été retirées. Le [Perfect Day](#/perfect-day) se calcule maintenant avec les habitudes planifiées : validées, loggées ou skippées avec une raison.

---

## XP & niveau

L'XP mesure ta régularité globale et te permet de monter de niveau.

### Comment gagner de l'XP ?

* **Compléter des Todos / Primes :** terminer un Todo rapporte son montant d'XP paramétré (configurable de `0` à `40` XP ; par défaut `10` XP).
* **Réussir un Perfect Day :** lors du bilan quotidien de la guilde (à 21h30), si ta journée est "Perfect", tu obtiens **`+5 XP`**.
* **Paliers de formation d'habitude :** maintenir tes habitudes sur la durée te récompense lors des paliers d'adoption et d'ancrage :
  * **30 jours de streak** : **`+100 XP`**
  * **90 jours de streak** : **`+300 XP`**

### Formule de niveau

La montée de niveau est exponentielle. Pour passer du niveau $L$ au niveau $L+1$, l'XP requise est :

$$\text{XP requis}(L \rightarrow L+1) = 10 \times 2^{L-1}$$

* **Niveau 1 → 2 :** 10 XP
* **Niveau 2 → 3 :** 20 XP
* **Niveau 3 → 4 :** 40 XP
* **Niveau 4 → 5 :** 80 XP
* **Niveau 5 → 6 :** 160 XP

L'XP acquise est **permanente**.

---

## Or (Gold)

L'Or mesure l'avancement concret de tes projets et de tes objectifs.

### Comment gagner de l'Or ?

* **Compléter des sous-étapes d'objectifs :** valider une sous-étape liée à un objectif rapporte sa récompense en or (valeur par défaut de **`50 Gold`**, entièrement personnalisable).
* **Paliers de formation d'habitude :**
  * **30 jours de streak** : **`+50 Gold`**
  * **90 jours de streak** : **`+150 Gold`**

### Comment dépenser l'Or ?

L'Or sert de monnaie d'échange dans la [Boutique de Récompenses](#/boutique-recompenses) pour acheter des récompenses réelles ou des activités :

* Les **récompenses classiques** déduisent leur coût en or (`gold_cost`) de ton solde.
* Les **items d'allostasie** coûtent `0 Gold` mais sont limités à un achat par période (jour ou semaine) pour suivre tes habitudes de récupération.
* Certaines récompenses peuvent être **verrouillées** tant qu'un objectif ou une compétence (softskill) requise n'a pas été complété.

L'Or acquis est permanent et n'est perdu que lors de tes achats.
