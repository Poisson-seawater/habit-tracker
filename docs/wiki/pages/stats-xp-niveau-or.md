# Stats, XP, niveau & or

Le jeu a plusieurs compteurs, et chacun mesure une chose différente. Les **stats** sont éphémères : on les évalue chaque jour. L'**XP** et le **niveau** mesurent ta régularité dans le temps. L'**Or**, lui, suit l'avancement concret de tes objectifs à long terme.

---

## Stats (éphémères)

Dans un RPG, ton personnage a des statistiques : force, intelligence... Ici, le personnage, c'est toi. Et chaque action de ta vraie vie développe une facette de toi.

Une statistique est une **dimension de ta vie**, mesurée en points. Il y en a 6 :
- **Forme physique** 💪 : Force, endurance, cardio, mobilité, entraînements sportifs.
- **Santé (mental, alimentation)** 🧠 : Sommeil, repos, nutrition, méditation, bien-être mental, récupération.
- **Social** 🤝 : Relations, amitiés, famille, communication, réseautage, sociabilité.
- **Finance** 💰 : Budget, investissements, épargne, business, gestion de l'argent.
- **Apprendre** 📚 : Lecture, étude, veille technique, softskills, créativité, apprentissage de nouvelles compétences.
- **Discipline** ⚔️ : Routines du matin/soir, organisation, focus, respect des règles, productivité générale.

### Cumul et réinitialisation
Quand tu valides une [habitude](#/habitudes) ou que tu coches une [prime (todo)](#/primes-todo), cela ajoute des points à une ou plusieurs de ces dimensions.
Les statistiques **repartent à zéro chaque matin**. Elles servent à valider tes seuils de la journée définis par ton [Template de Jour](#/templates-de-jour) (Week, Weekend, Recup, Malade). Si tous tes seuils de la journée sont atteints, ta journée est qualifiée de [Perfect Day](#/perfect-day), ce qui te rapporte de l'XP à 21h30.

---

## XP & niveau (permanents)

L'XP mesure ta régularité globale et te permet de monter de niveau.

### 📈 Comment gagner de l'XP ?
*   **Compléter des Todos / Primes :** Terminer un Todo te rapporte son montant d'XP paramétré (configurable de `0` à `40` XP ; par défaut `10` XP).
*   **Réussir un « Perfect Day » :** Lors du bilan quotidien de la guilde (à 21h30), si ta journée est "Perfect", tu obtiens **`+5 XP`**.
*   **Paliers de formation d'habitude (Habit Streaks) :** Maintenir tes habitudes sur la durée te récompense lors des paliers d'adoption et d'ancrage :
    *   **30 jours de streak** : **`+100 XP`**
    *   **90 jours de streak** : **`+300 XP`**

### ⚙️ Formule de Niveau
La montée de niveau est exponentielle. Pour passer du niveau $L$ au niveau $L+1$, l'XP requise est :
$$\text{XP requis}(L \rightarrow L+1) = 10 \times 2^{L-1}$$

*   **Niveau 1 → 2 :** 10 XP
*   **Niveau 2 → 3 :** 20 XP
*   **Niveau 3 → 4 :** 40 XP
*   **Niveau 4 → 5 :** 80 XP
*   **Niveau 5 → 6 :** 160 XP ...

L'XP acquise est **permanente** (aucune punition ne peut faire perdre d'XP).

---

## Or (Gold, permanent)

L'Or mesure l'avancement concret de tes projets et de tes objectifs.

### 📈 Comment gagner de l'Or ?
*   **Compléter des sous-étapes d'objectifs (Substeps) :** Valider une sous-étape liée à un objectif te rapporte sa récompense en or (valeur par défaut de **`50 Gold`**, entièrement personnalisable).
*   **Paliers de formation d'habitude (Habit Streaks) :** Les jalons de régularité te rapportent également de l'Or :
    *   **30 jours de streak** : **`+50 Gold`**
    *   **90 jours de streak** : **`+150 Gold`**

### ⚙️ Comment dépenser l'Or ?
L'Or sert de monnaie d'échange dans la [Boutique de Récompenses](#/boutique-recompenses) pour acheter des récompenses réelles ou des activités :
*   Les **récompenses classiques** déduisent leur coût en or (`gold_cost`) de ton solde.
*   Les **items d'allostasie** coûtent `0 Gold` mais sont limités à un achat par période (jour ou semaine) pour suivre tes habitudes de récupération.
*   Certaines récompenses peuvent être **verrouillées** tant qu'un objectif ou une compétence (softskill) requise n'a pas été complété.

L'Or acquis est permanent et n'est perdu que lors de tes achats.
