# Feature Specification: habit-tracker-bot

**Feature Branch**: 001-habit-tracker-bot

**Created**: 2026-05-31

**Status**: Draft

**Input**: User description: "Système d'habitudes avec bot d'accountability et dashboard local, hébergé sur Raspberry Pi 5 avec Docker Compose."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Daily Habit Logging & accountability Bot (Priority: P1)

The primary daily interface is a Telegram bot running in a group chat with the user's friends.
The user (Gabriel) can log habit completion, quantity, or time easily using strict bot commands.
The bot tracks these actions, calculates point distributions, and publishes a public RPG-style daily
recap at the end of each day to enforce social accountability while keeping private habits hidden.

**Why this priority**: Core value of the application—low-friction logging and public group accountability
are the main drivers for behavioral reinforcement in V1.

**Independent Test**: Can be tested end-to-end using mock Telegram messages to the bot daemon,
verifying that database state updates correctly and that the correct structured daily recap is
returned to the chat group.

**Acceptance Scenarios**:

1. **Given** a binarized habit "routine_matin" exists for the user, **When** the user sends the command
   `/done routine_matin` in the group chat, **Then** the system records a completion log in the database
   and the bot replies in the group confirming the action.
2. **Given** a quantitative habit "lecture" (reading) exists, **When** the user sends `/log lecture 30min`
   to the bot, **Then** the system parses the time, logs +5 Creativity and +2 Discipline in the database,
   enforces the daily cap, and confirms the log.
3. **Given** the user has logged both public habits and private tasks, **When** the scheduled daily recap
   triggers at 23:59, **Then** the bot posts a formatted public RPG character-sheet message in the group
   showing public accomplishments, streaks, and current daily stats, but aggregates the private tasks
   under "Actions privées complétées : X" to protect privacy.

---

### User Story 2 - Localhost Character Dashboard (Priority: P2)

The local web interface displays Gabriel's progress using a video game character sheet aesthetic combined
with traditional analytical charts. It displays stats, level/XP metrics (V1 placeholders), calendar heatmaps
of successful days, streaks, and active quêtes (long-term goals).

**Why this priority**: Provides the visual payoff and gamification of the logged habits. Helps the user review
long-term trends, streaks, and "fragile habits" (frequently skipped or failed) in a central place.

**Independent Test**: Visited via a web browser at `http://localhost`, showing all data loaded directly
from the central database without errors.

**Acceptance Scenarios**:

1. **Given** the user has logged habits yielding 15 points in Force and 6 points in Creativity, **When** the
   user loads the localhost dashboard, **Then** the dashboard renders a character sheet displaying Gabriel
   with these custom stat levels and progress bars towards the "Acceptable Day" thresholds.
2. **Given** the user has maintained a 5-day streak of "Acceptable Days", **When** they view the dashboard calendar,
   **Then** those 5 days are highlighted in green, showing the streak count clearly.

---

### User Story 3 - Habit & Day-Template Configuration (Priority: P3)

The user can define new habits and day-types (Semaine, Weekend, Récupération, Malade) with specific stat
thresholds for validating "Acceptable Day" and "Perfect Day" statuses.

**Why this priority**: Allows customization of the system constraints so that the habit tracker adapts
to different day configurations (e.g., lower discipline thresholds when sick or on recovery days).

**Independent Test**: Adding/modifying habits via API routes or dashboard interfaces and verifying
that the database holds the new configurations.

**Acceptance Scenarios**:

1. **Given** the user is feeling unwell, **When** the user sends the command `/set-day sick` to the bot or updates it
   on the dashboard, **Then** the daily threshold for "Acceptable Day" dynamically switches to the lower
   thresholds specified by the "Malade" template.

---

### Edge Cases

- **Double-logging an action**: If a user logs a binary habit twice (e.g. `/done routine_matin`), the system
  should merge or safely ignore the second completion log, rather than duplicating the record or double-counting points.
- **Handling offline status or restart**: If the Raspberry Pi restarts or loses internet connection, the SQLite/PostgreSQL
  database must not corrupt, and the bot listener must automatically re-connect and process missed check-ins where possible.
- **Timezone boundary crossing**: If the user checks in past midnight, the system must support logging against
  "yesterday" (e.g., using special timestamps or commands like `/done routine_matin yesterday`).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST store and query all records in a local database (PostgreSQL or SQLite).
- **FR-002**: The bot interface MUST support strict command parsing for Telegram: `/done [habit]`, `/log [habit] [amount]`,
  `/skip [habit] [reason]`, `/status today`, `/set-day [template]`, and `/create-habit [metadata]`.
- **FR-003**: The system MUST maintain exactly 12 customizable stats, defaulted to: Force, Endurance, Mobilité,
  Discipline, Créativité, Connaissance, Sociabilité, Santé mentale, Finance, Organisation, Spiritualité, Repos.
- **FR-004**: Habits MUST allow linking to multiple stats with daily caps (e.g. Ukulele awards max +5 Creativity / day).
- **FR-005**: The system MUST evaluate the day at 23:59 as either "Ratée" (Failed), "Journée acceptable" (streak +1), or
  "Perfect day" (perfect streak +1) based on active template thresholds.
- **FR-006**: The system MUST support a "Privée" (Private) boolean flag on habits, ensuring private tasks are aggregated
  as counts (e.g. "Actions privées complétées : X") and hidden from the public chat recap.
- **FR-007**: The system MUST support a "Reportable" flag on tasks to allow transferring them to a future date without breaking streaks.

### Key Entities *(include if feature involves data)*

- **User**: Represents Gabriel or future multi-user participants. ID, username, creation date.
- **Habit**: Represents a scheduled habit. ID, name, description, type (binary/quantitative), frequency, scheduled days,
  reminder time, is_private, is_reportable, is_mandatory, point_rewards (JSON map of stats and points), daily_cap.
- **HabitLog**: Record of a completed habit. ID, user_id, habit_id, timestamp, log_type (done/skip/log), amount (optional), reason (optional).
- **DayTemplate**: Stat thresholds for days. ID, name (e.g. Semaine, Weekend), acceptable_thresholds (JSON map of stats/points), perfect_thresholds.
- **DailyScore**: Evaluation of a day. ID, user_id, date, status (Failed/Acceptable/Perfect), active_template_id.
- **Streak**: Tracks streak counts. ID, user_id, streak_type (Acceptable/Perfect/Habit), current_streak, max_streak.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can complete a habit check-off in under 5 seconds by sending a single strict bot command.
- **SC-002**: The Telegram bot and REST API daemon maintain an uptime of >99.9% when running persistently on a Raspberry Pi 5 under Docker Compose.
- **SC-003**: 100% of private habit entries are safely filtered from the public daily recaps, leaving no leaking descriptive data in the group logs.
- **SC-004**: The localhost dashboard loads and displays Gabriel's entire history, streaks, and RPG stats within 1 second.

## Assumptions

- The primary bot interface is Telegram, as it is simpler to configure and deploy initially on a local Pi.
- A single SQLite database is sufficient for V1 solo operation, easily mounted via Docker volumes for backups.
- Day templates default automatically (Semaine on Mon-Fri, Weekend on Sat-Sun) unless overridden manually.
- The hardware hosting environment is a Raspberry Pi 5 with 2GB of RAM, meaning the entire Docker Compose stack must be lightweight and optimized for a low memory footprint.
