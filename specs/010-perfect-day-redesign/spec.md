# Feature Specification: Perfect Day Redesign (Effort Budget Allocator)

**Feature Branch**: `010-perfect-day-redesign`

**Created**: 2026-06-28

**Status**: Ready

**Input**: User description: "Refonds la feature « Perfect Day » du Habit RPG Tracker."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure Day-Type Budgets (Priority: P1)

As a user, I want to configure the effort budgets for the 3 day-types (rest, regular, hustle) in my settings, defining focus hours, effort type ceilings, and minimum rest.
This allows me to establish my capacity boundaries for different types of days.

**Why this priority**: It is the foundation of the effort budget allocator; without configurable templates, daily validation cannot occur.

**Independent Test**: Can be tested by visiting the settings screen, selecting a day-type, editing the hours and ceilings, and saving them to the database.

**Acceptance Scenarios**:
1. **Given** the user is on the Settings page, **When** they select "regular" day-type and set target focus to 6 hours, creative ceiling to 3 hours, and minimum rest to 8 hours, **Then** these limits are persisted and used for future regular day evaluations.
2. **Given** a day-type configuration, **When** the user attempts to enter a ceiling exceeding 10 hours or total focus hours exceeding 24, **Then** the application rejects the input with a validation error.

---

### User Story 2 - Tag Quests and Sub-steps with Effort Types (Priority: P1)

As a user, I want to assign an effort type (musculaire, cerveau, émotionnel/social, créatif/divergent) and an effort duration (in hours) to my habits (quests) and sub-steps.
This allows the system to sum the daily energy cost when these items are scheduled or completed.

**Why this priority**: Required to calculate the total planned effort cost for a day.

**Independent Test**: Can be tested by creating or editing a habit/sub-step, selecting an effort type tag and setting its duration, and verifying it is saved.

**Acceptance Scenarios**:
1. **Given** the quest creation form, **When** the user selects the "cerveau" effort type and leaves the duration blank, **Then** the habit is successfully created with a default duration of 1.0 hour.
2. **Given** a sub-step, **When** the user updates its effort type to "musculaire" and duration to 1.5 hours, **Then** these values are persisted.

---

### User Story 3 - Daily Budget Gauge and Validation (Priority: P1)

As a user, I want to see a daily effort budget gauge comparing my planned effort cost against the active day-type budget. The system must display warnings if ceilings are exceeded (more than 4h of the same tag on a hustle day; more than 2h of the same tag on a regular day), or if a hustle day has less than 30% unplanned time (based on a 16-hour waking day).

**Why this priority**: Core feedback loop for daily planning, ensuring the user respects their sustainable energy thresholds.

**Independent Test**: Can be tested by planning a set of habits/sub-steps on the dashboard and verifying the visual indicators, alerts, and validity status.

**Acceptance Scenarios**:
1. **Given** a "regular" day, **When** the user plans quests totaling 2.5 hours of "cerveau" effort, **Then** a warning is displayed showing a budget overflow because it exceeds the 2-hour regular ceiling for a single tag.
2. **Given** a "hustle" day, **When** the total planned effort hours exceed 11.2 hours (leaving less than 4.8 hours unplanned, which is 30% of a 16-hour waking day), **Then** the hustle day is marked as invalid.

---

### Edge Cases

- **No scheduled activities**: If a day has no scheduled habits or sub-steps, the planned effort cost is 0. A "rest" day with 0 hours of planned effort is valid. A "hustle" day with 0 hours is invalid (as it lacks focus).
- **Overlapping schedules**: If multiple quantitative habit runs are logged, their durations must sum up correctly.
- **Missing day-type templates**: If a user has not customized templates, default budgets (e.g., regular: 6h focus, max 2h per type; hustle: 9h focus, max 4h per type; rest: 2h focus, max 1h per type) should be applied automatically.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST store three day-types: `rest`, `regular`, and `hustle` in the database, replacing the old RPG stat-based templates.
- **FR-002**: Each day-type MUST support the following budget parameters:
  - Target focus hours (float/decimal)
  - Ceilings per effort type: `musculaire`, `cerveau`, `emotionnel_social`, `creatif_divergent` (configurable, default 2h for regular, 4h for hustle)
  - Max total effort ceiling (configurable, default 10h)
  - Minimum rest hours (float/decimal)
- **FR-003**: The system MUST allow tagging any `Habit` (Quest) and `SubStep` with EXACTLY ONE of the 4 effort types:
  - `musculaire`
  - `cerveau` (analytical)
  - `emotionnel_social`
  - `creatif_divergent`
  - (Optional) `none` or `null` for activities with no effort cost.
- **FR-004**: The system MUST store an `effort_duration` (in hours, e.g., 0.5, 1.5) for each `Habit` and `SubStep`. This field is optional and defaults to 1.0 hour if not specified.
- **FR-005**: The system MUST compute the daily planned effort cost by summing the `effort_duration` of all active habits scheduled for that day and all sub-steps planned for that day.
- **FR-006**: The system MUST warn the user if:
  - On a `hustle` day, the sum of planned effort for any single type exceeds 4 hours (or the user-configured ceiling).
  - On a `regular` day, the sum of planned effort for any single type exceeds 2 hours (or the user-configured ceiling).
  - The total planned effort exceeds the day-type max total effort ceiling.
- **FR-007**: The system MUST mark a `hustle` day as invalid if the unplanned time is less than 30%. The unplanned time is calculated based on a fixed 16-hour waking day (meaning total planned effort hours across all activities cannot exceed 11.2 hours).

### Key Entities *(include if feature involves data)*

- **PerfectDayTemplate (Redesigned)**:
  - `id`: unique identifier
  - `user_id`: foreign key to users
  - `template_name`: "rest", "regular", or "hustle"
  - `focus_hours`: target focus duration
  - `ceilings_json`: JSON object storing ceilings per effort type and total (e.g., `{"musculaire": 2, "cerveau": 2, "emotionnel_social": 2, "creatif_divergent": 2, "total": 10}`)
  - `min_rest_hours`: minimum rest duration required
- **Habit (Modified)**:
  - `effort_type`: string/enum (`musculaire`, `cerveau`, `emotionnel_social`, `creatif_divergent`, null)
  - `effort_duration`: float (duration in hours, default 1.0)
- **SubStep (Modified)**:
  - `effort_type`: string/enum (`musculaire`, `cerveau`, `emotionnel_social`, `creatif_divergent`, null)
  - `effort_duration`: float (duration in hours, default 1.0)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can assign effort types and durations to a quest or sub-step in under 10 seconds.
- **SC-002**: Daily budget gauge calculation and UI rendering completes in under 100ms when switching templates or updating tasks.
- **SC-003**: 100% of planned budget limit breaches or validation errors are immediately surfaced with clear warning messages on the daily dashboard.

## Assumptions

- We assume that the user will plan their daily day-type manually or via the active template switcher on the dashboard.
- The historical logging of day-type per date is deferred to Palier 2, but the DB schema must support assigning a day-type to a date.
- RPG stats validation and points thresholds are completely ignored and will be cleaned up/removed.
