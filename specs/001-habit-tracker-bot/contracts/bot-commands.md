# Telegram Bot Command Contracts: habit-tracker-bot

This document defines the strict syntax, parsing rules, and expected bot responses for the V1 Telegram chat interface.

## Core Command Set

All commands are strictly validated. If a command does not match the specifications below, the bot MUST reply with a helpful usage guide and correct examples.

---

### 1. `/done` Command
Logs completion of a binary (yes/no) habit.

- **Syntax**: `/done [habit_name]`
- **Example**: `/done routine_matin`
- **Validation**:
  - `[habit_name]` must match an active habit name in the database.
  - The habit must be of type `binary`.
- **Expected Response (Success)**:
  ```txt
  ✅ Gabriel a complété la routine "routine_matin" ! 
  ✨ Stats obtenues : +2 Discipline, +1 Organisation
  ```

---

### 2. `/log` Command
Logs quantitative data with a value and strict units.

- **Syntax**: `/log [habit_name] [value][unit]`
- **Example**: `/log lecture 30min`
- **Validation**:
  - `[habit_name]` must match an active quantitative habit in the database.
  - The value must be a positive integer.
  - `[unit]` must match the expected unit metadata defined for that habit in the DB (e.g. `min` or `km`).
- **Expected Response (Success)**:
  ```txt
  📚 Gabriel a loggé 30min pour la quête "lecture" !
  ✨ Stats obtenues : +5 Créativité, +2 Discipline (Platonique - Cap atteint)
  ```

---

### 3. `/skip` Command
Excuses a scheduled habit for a specific day with a reason.

- **Syntax**: `/skip [habit_name] raison: [text]`
- **Example**: `/skip nage raison: fatigue extreme`
- **Validation**:
  - `[habit_name]` must match an active habit scheduled for today.
  - A non-empty reason must be specified after `raison:`.
- **Expected Response (Success)**:
  ```txt
  ⏭️ Gabriel a skippé la tâche "nage" pour aujourd'hui.
  📝 Raison : fatigue extreme (Le streak n'est pas rompu !)
  ```

---

### 4. `/status` Command
Returns the current day's progress and stats summary.

- **Syntax**: `/status today`
- **Expected Response**:
  ```txt
  ⚔️ Gabriel — Statut du Jour (Template : Semaine)

  Acceptable Day : 🟩 Validé (Discipline: 6/5, Force: 12/10)
  Perfect Day : 🟥 En cours (Discipline: 6/8, Force: 12/20)

  Quêtes accomplies :
  - routine_matin (done)
  - lecture (30min)

  Quêtes restantes :
  - nage ( quantitative, 0/1km )
  - ukulele ( binary, 0/1 )
  ```

---

### 5. `/set-day` Command
Manually overrides the active day template.

- **Syntax**: `/set-day [template_name]` — `[template_name]` is **optional**.
- **Example**: `/set-day sick` or `/set-day` (no argument).
- **Validation**:
  - `[template_name]` must match one of the defined templates: `semaine`, `weekend`, `recovery`, `sick`.
- **No-argument behaviour**: replies with 4 inline buttons (Semaine / Weekend / Recovery / Sick);
  clicking one applies that template (callback_data `setday:week|weekend|recup|malade`).
- **Expected Response (Success)**:
  ```txt
  🩹 Template de journée mis à jour vers : "sick".
  ✨ Les seuils de points ont été allégés pour aujourd'hui !
  ```

---

### 6. `/aide` Command
Displays the help menu with interactive buttons.

- **Syntax**: `/aide` or `/help`
- **Validation**: None
- **Expected Response (Success)**:
  ```txt
  Besoin d'aide ? Choisissez une option :
  [Aide Documentation] [Liste des commandes]
  ```
  Clicking "Aide Documentation" returns:
  ```txt
  📖 Pour ouvrir le tableau de bord, va sur http://localhost:5000
  ```
  Clicking "Liste des commandes" returns (HTML-formatted) the full command list
  (`/done`, `/log`, `/skip`, `/status`, `/set-day`, `/liste`, `/add`, `/add_habit`,
  `/fail`, `/motivation`, `/app`, `/aide`, `/help`).

---

### 7. `/liste` Command
Lists the user's items.

- **Syntax**: `/liste [todo|habit|notodo]` — the type is **optional**.
- **Example**: `/liste todo` or `/liste` (no argument).
- **No-argument behaviour**: replies with 3 inline buttons (Todos / Habitudes / No-Todos);
  clicking one renders that list (callback_data `liste:todo|habit|notodo`).

---

### 8. `/add` Command
Adds a Todo, a No-Todo, or a Habit.

- **Syntax**: `/add [todo|notodo|habit] [titre]` — arguments are **optional**.
- **Example**: `/add todo Courses` or `/add` (no argument).
- **No-argument behaviour (button flow)**:
  1. Replies with 3 buttons [Todo] [No-Todo] [Habitude] (`add:todo|notodo|habit`).
  2. For **Habitude**, a 2nd choice: [Oui/Non (binaire)] [Quantitatif (log)] (`addhabit:binary|quant`).
  3. The bot then asks for the **title**, which the user types in the next message.
     For a quantitative habit the message is `nom unité` (unit optional, e.g. `lecture min`).
  - Pending state is kept per-user in `context.user_data["pending_add"]`; sending a new
    `/command` instead of a title aborts the flow.
