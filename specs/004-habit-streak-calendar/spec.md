# Feature Specification: Habit Streak Counter & Calendar

**Feature Branch**: `004-habit-streak-calendar`

**Created**: 2026-06-12

**Status**: Draft

**Input**: User description: "chaque habitude a un compteur de succès pour passer le cap des 30j et 90j. Le calendrier permet de montrer le succès (avoir fait) l'habitude à chaque jour."

## Clarifications

### Session 2026-06-12

- Q: Où le calendrier apparaît-il dans l'interface ? → A: Le calendrier s'ouvre dans un panneau/modal dédié quand l'utilisateur clique sur une habitude (vue détail), pas inline dans la liste.
- Q: Quel est le comportement du streak quand une habitude est désactivée ? → A: Le streak gèle, mais pour un maximum de 14 jours. Si l'habitude reste désactivée plus de 14 jours, le streak se réinitialise à 0.
- Q: Comment les jours non planifiés s'affichent-ils sur le calendrier ? → A: Les jours non planifiés s'affichent avec un état visuel distinct et grisé/hachuré (différent des jours manqués ou réussis).
- Q: Comment le streak est-il mis à jour lors de modifications dans le passé ? → A: La mise à jour est uniquement incrémentale (temps réel) ; les modifications dans le passé n'entraînent pas de recalcul rétroactif du streak actuel.
- Q: Les paliers de 30j et 90j octroient-ils des récompenses RPG ? → A: Oui, atteindre 30j de streak donne +100 XP et +50 Or, et atteindre 90j donne +300 XP et +150 Or.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Habit Streak Counter (Priority: P1)

As a user, I want to see a running success counter on each of my habits so I know how many consecutive days I have completed them, and I feel motivated to keep going toward the 30-day and 90-day milestones.

When viewing my list of habits (dashboard or habit detail), each habit displays its current streak count (e.g., "🔥 12 jours"). Milestones at 30 days and 90 days are visually highlighted to give a sense of accomplishment.

**Why this priority**: The streak counter is the core motivational mechanic. Without it, users have no visibility into their consistency, and the 30/90-day milestones have no meaning.

**Independent Test**: Can be fully tested by logging a habit multiple consecutive days and verifying the counter increments. Delivers immediate motivational feedback.

**Acceptance Scenarios**:

1. **Given** a habit with 0 previous "done" logs, **When** the user logs it today, **Then** the streak counter displays "1".
2. **Given** a habit with a current streak of 29 days, **When** the user logs it today (day 30), **Then** the counter shows "30" and a 30-day milestone badge/celebration is displayed.
3. **Given** a habit with a current streak of 5 days, **When** the user misses a day (no log yesterday), **Then** the streak resets to 0 and the previous streak is preserved as history.
4. **Given** a habit with a current streak of 89 days, **When** the user logs it today (day 90), **Then** the counter shows "90" and a 90-day milestone celebration is displayed, distinct from the 30-day one.
5. **Given** a habit logged with "skip" type, **When** viewing the streak, **Then** the skip does NOT break the streak (skips are intentional rest days and preserve continuity).

---

### User Story 2 - Habit Completion Calendar (Priority: P1)

As a user, I want to see a monthly calendar view for each habit that shows which days I successfully completed it, so I can visualize my consistency at a glance.

When the user clicks on a habit in the list, a detail panel or modal opens showing the habit's streak counter and a monthly calendar. The calendar displays the current month with each day color-coded: completed days are highlighted (e.g., green), missed days are neutral or marked (e.g., grey/red), and future days remain unmarked. The user can navigate to previous months to review their history.

**Why this priority**: The calendar is a direct visual representation of the habit data and is the primary way the user requested to "montrer le succès à chaque jour". It complements the streak counter.

**Independent Test**: Can be fully tested by logging a habit on specific days and verifying the calendar correctly marks those days as completed.

**Acceptance Scenarios**:

1. **Given** a habit with logs on June 1, 3, 4, 5, **When** viewing the June calendar for that habit, **Then** June 1, 3, 4, 5 are marked as completed and June 2 is marked as missed.
2. **Given** the calendar is showing the current month, **When** the user taps/clicks the left arrow, **Then** the previous month is displayed with its historical data.
3. **Given** a day is in the future, **When** viewing the calendar, **Then** future days are visually distinct (neither completed nor missed).
4. **Given** a habit was logged with "skip" on a given day, **When** viewing the calendar, **Then** that day is marked with a distinct "skipped" indicator (not as completed, not as missed).
5. **Given** a quantitative habit was logged with an amount, **When** viewing the calendar, **Then** the completed day optionally shows the logged amount.
6. **Given** a habit is only scheduled on certain days (e.g., Mon/Wed/Fri), **When** viewing the calendar, **Then** non-scheduled days (Tue/Thu/Sat/Sun) are displayed in a distinct grayed-out/hashed style.

---

### User Story 3 - Milestone Celebrations & History (Priority: P2)

As a user, when I reach the 30-day or 90-day streak milestone, I want a celebratory acknowledgment so I feel rewarded for my consistency. I also want to see my past best streaks to track my progress over time.

**Why this priority**: While the core counter exists in P1, the celebration/reward experience and streak history add the emotional payoff that drives long-term engagement.

**Independent Test**: Can be tested by simulating a 30-day streak completion and verifying the celebration UI appears, and by checking that the max streak is recorded and visible.

**Acceptance Scenarios**:

1. **Given** a habit reaches exactly 30 consecutive days, **When** the milestone is triggered, **Then** a visual celebration (animation, badge, or banner) is displayed to the user, and they are awarded +100 XP and +50 Gold.
2. **Given** a habit reaches exactly 90 consecutive days, **When** the milestone is triggered, **Then** a more prominent celebration is displayed, distinct from the 30-day one, and they are awarded +300 XP and +150 Gold.
3. **Given** a habit had a previous max streak of 45 days that was broken, **When** viewing the habit detail, **Then** the user can see both the current streak and the all-time best streak.
4. **Given** a user has multiple habits, **When** viewing the habits overview, **Then** each habit independently shows its own streak — streaks are per-habit, not global.

---

### Edge Cases

- What happens when a user logs a habit twice on the same day? → The streak counter counts only once per day; duplicate logs do not inflate the count.
- What happens when a habit is only scheduled on certain days (e.g., Mon/Wed/Fri)? → Only scheduled days are considered when evaluating streak continuity. A Tuesday gap on a Mon/Wed/Fri habit does NOT break the streak.
- What happens when a habit was created recently (e.g., 3 days ago) and the calendar shows the full month? → Days before the habit was created are shown as neutral (not missed).
- What happens on timezone changes or late-night logging? → The system uses the date based on the user's configured timezone (or server default). A log at 11:55 PM counts for that day.
- What happens when a habit is deactivated (is_active = false)? → The streak freezes for a maximum of 14 days. If the habit is reactivated within 14 days, the streak resumes from its previous value. If reactivated after more than 14 days, the streak is reset to 0.
- What happens if a user edits or deletes a historical habit log in the past? → The current streak is not recalculated or updated retroactively; changes to past logs do not impact the current active streak count.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST maintain a per-habit streak counter that increments each consecutive scheduled day the habit is logged as "done" or "log".
- **FR-002**: System MUST reset the streak counter to 0 when a scheduled day passes without a "done" or "log" entry (unless the habit was logged as "skip").
- **FR-003**: System MUST preserve the maximum (all-time best) streak value separately from the current streak for each habit.
- **FR-004**: System MUST display the current streak prominently alongside each habit in the user interface.
- **FR-005**: System MUST visually distinguish the 30-day and 90-day milestones with celebration indicators when those thresholds are reached.
- **FR-006**: System MUST provide a monthly calendar view per habit, accessible via a detail panel/modal when clicking on a habit, showing completion status for each day (completed, missed, skipped, non-scheduled, future, or pre-creation).
- **FR-007**: System MUST allow the user to navigate between months in the calendar view to review historical data.
- **FR-008**: System MUST respect the habit's scheduled days when calculating streak continuity — non-scheduled days do not break or contribute to the streak.
- **FR-009**: System MUST treat "skip" logs as streak-preserving — they do not break the streak nor increment the counter.
- **FR-010**: System MUST handle habits created mid-month by not counting pre-creation days as missed in the calendar or streak calculation.
- **FR-011**: System MUST freeze the streak of a deactivated habit for up to 14 days, after which it MUST reset the streak to 0.
- **FR-012**: System MUST update streaks incrementally in real-time; updates or deletions to historical logs (prior to today) MUST NOT trigger retroactive recalculation of the current active streak.
- **FR-013**: System MUST award the user +100 XP and +50 Gold when a habit reaches a 30-day streak milestone.
- **FR-014**: System MUST award the user +300 XP and +150 Gold when a habit reaches a 90-day streak milestone.

### Key Entities

- **Habit Streak**: Represents the running consecutive-day count for a single habit. Attributes: current count, maximum (best) count, last incremented date, associated habit.
- **Habit Calendar Entry**: Represents one day's status for a habit. Derived from habit logs. States: completed, skipped, missed, non-scheduled, future, not-applicable (pre-creation).
- **Milestone**: A predefined streak threshold (30 days, 90 days) that triggers a celebration when reached. Associated with a specific habit's streak.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can see their current streak count for any habit within 1 second of opening the habit view.
- **SC-002**: 100% of streak calculations correctly account for scheduled days, skip logs, and habit creation date.
- **SC-003**: Users can view at least 6 months of calendar history per habit by navigating between months.
- **SC-004**: The 30-day and 90-day milestone celebrations display within 2 seconds of the qualifying log being recorded.
- **SC-005**: Users who reach the 30-day milestone report increased motivation to continue (qualitative — measured via engagement: does the user keep logging after hitting 30 days?).
- **SC-006**: The calendar view loads and renders for any given month in under 1 second, even for habits with 1+ year of log history.

## Assumptions

- The existing habit logging system (done/skip/log types) remains unchanged. This feature builds on top of existing log data.
- Streak calculation uses habit log records already stored in the system — no new logging mechanism is needed.
- The streak logic already partially exists in the system (Streak model with `streak_type = "habit:[habit_id]"`) and will be extended/leveraged.
- "Skip" entries are intentional rest days that preserve streak continuity (aligned with the existing skip mechanic in the app).
- The calendar and streak counter are displayed in the web dashboard. Telegram bot integration for streak display is out of scope for this feature.
- Milestones are fixed at 30 and 90 days for the initial version. Additional milestones (7, 180, 365 days) may be added later but are out of scope now.
- Only one user uses the system (single-user deployment on Raspberry Pi), so multi-user streak isolation is not a concern for this feature.
