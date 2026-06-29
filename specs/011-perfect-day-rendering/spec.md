# Feature Specification: Perfect Day Rendering (Vue Rendu)

**Feature Branch**: `011-perfect-day-rendering`

**Created**: 2026-06-28

**Status**: Clarified

**Input**: User description: "Perfect day rendu ! En haut je veux la journée type selon mes facilités biologiques — c'est totalement indépendant. À gauche je veux voir le recap de la journée avec les activités définies."

## Clarifications

### Session 2026-06-28

- Q: Where should the biological zone configuration UI live? → A: In the existing Settings tab, as a new "Biological Day" configuration section.
- Q: Are biological zone types and effort tags (from spec 010) the same system or separate? → A: Separate systems — biological zones describe biological capacity windows; effort tags describe activity energy cost. Alignment is visual only.
- Q: What occupies the right side of the layout? → A: The right panel shows the effort budget gauge and validation alerts (from spec 010), pairing naturally with the left recap.
- Q: Is the P2 alignment insight (bio zones vs activities) in scope? → A: Deferred entirely to a future spec. This spec focuses on rendering only.
- Q: Must biological zones cover the full 24 hours or are gaps allowed? → A: Gaps allowed — unassigned time renders as neutral empty space on the timeline.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Biological Ideal Day Timeline (Priority: P1)

As a user, I want to see a visual timeline at the top of my Perfect Day view showing my ideal day structured around my biological ease — my chronotype and natural energy peaks/troughs. This timeline is a **read-only, independently configured reference** that represents the biological rhythm I should aim to follow (e.g., deep focus mornings, physical energy afternoons, creative evenings). It does not change with the daily recap below; it is a static personal compass.

**Why this priority**: This is the anchor of the view — the user explicitly asked for a biological rhythm timeline at the top, independent of anything else. It gives the user a permanent reference of when their biology supports specific types of effort.

**Independent Test**: Can be tested by configuring biological time slots (e.g., "Deep Focus: 08:00–12:00", "Physical Peak: 14:00–16:00", "Creative Zone: 20:00–22:00") and verifying the timeline renders them correctly with appropriate labels and colors at the top of the Perfect Day view.

**Acceptance Scenarios**:
1. **Given** the user has configured their biological ideal day slots, **When** they navigate to the Perfect Day view, **Then** a horizontal 24h timeline is displayed at the top with color-coded blocks representing each biological zone.
2. **Given** the biological timeline is displayed, **When** the user modifies their daily recap activities below, **Then** the biological timeline remains unchanged — it is fully independent.
3. **Given** the user has not yet configured any biological slots, **When** they visit the Perfect Day view, **Then** a sensible default biological day is displayed (e.g., Sleep 23:00–07:00, Morning Focus 08:00–12:00, Afternoon Physical 14:00–17:00, Evening Creative 20:00–22:00).

---

### User Story 2 - Daily Activity Recap Panel (Priority: P1)

As a user, I want to see a left panel listing the recap of my day with all defined activities — the scheduled habits, quests, and blocks I've planned. This recap shows the actual activities assigned to my day template, with their time ranges, effort types, and categories. It provides a scrollable, ordered view of how my real day is structured.

**Why this priority**: This is the main working area where the user sees what they've actually planned for the day, distinct from the biological ideal. It is the operational view.

**Independent Test**: Can be tested by having planned activities (from existing Perfect Day templates/blocks) and verifying they appear as an ordered list on the left side of the view with time range badges, activity names, effort tags, and category labels.

**Acceptance Scenarios**:
1. **Given** the user has planned blocks for the active day template, **When** they open the Perfect Day rendering view, **Then** a left panel displays all blocks in chronological order, each showing its time range, title, effort tag, and focus category.
2. **Given** no blocks are planned for the active template, **When** the user opens the Perfect Day rendering view, **Then** the left panel shows an empty state message inviting the user to plan their day.
3. **Given** many blocks are planned (more than fit on screen), **When** the user scrolls the left panel, **Then** the list scrolls independently without affecting the biological timeline at the top or any right-side panels.

---

### User Story 3 - Effort Budget Gauge Panel (Priority: P2)

As a user, I want to see a right-side panel displaying my effort budget gauge and validation alerts for the active day. This panel shows my planned effort cost versus my day-type budget (rest/regular/hustle), with visual warnings when ceilings are exceeded. It complements the left recap panel by providing a quantitative summary of the day's energy allocation.

**Why this priority**: Builds on P1 stories and the effort budget system from spec 010. Provides the operational feedback loop but requires the recap panel to be functional first.

**Independent Test**: Can be tested by scheduling activities with effort durations, switching day-type templates, and verifying the gauge reflects accurate totals with appropriate warnings when ceilings are breached.

**Acceptance Scenarios**:
1. **Given** a "regular" day with planned activities, **When** the user views the Perfect Day rendering, **Then** the right panel displays a budget gauge showing total planned effort vs the day-type ceiling, broken down by effort tag.
2. **Given** any day-type where a single effort tag exceeds its ceiling, **When** the user views the rendering, **Then** a visual warning highlights the overflow on the gauge.

---

### Edge Cases

- **Overnight blocks**: Biological slots spanning midnight (e.g., Sleep 23:00–07:00) must wrap correctly on the 24h timeline.
- **Overlapping biological zones**: If a user configures overlapping zones, the system should warn and refuse the overlap.
- **Gaps in biological timeline**: Unassigned time between zones renders as neutral/empty space on the timeline. Full 24h coverage is not required.
- **Empty day**: If the user has zero planned activities but a configured biological timeline, the top timeline still renders normally; the left panel shows an empty state.
- **Template switching**: Switching between day-type templates (rest/regular/hustle) updates the left recap panel but does NOT affect the biological timeline.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST display a horizontal 24-hour timeline at the top of the Perfect Day view representing the user's biological ideal day with labeled, color-coded blocks.
- **FR-002**: The biological timeline MUST be fully independent from the daily activity recap — changing the day template or daily activities MUST NOT affect the biological timeline.
- **FR-003**: The system MUST allow the user to configure their biological ideal day in a dedicated "Biological Day" section within the existing Settings tab, by defining named time slots with start/end times and a biological zone type (e.g., Deep Focus, Physical Peak, Creative Zone, Rest, Social, Sleep). The Perfect Day rendering view itself remains read-only for the biological timeline.
- **FR-004**: The system MUST display a left-side panel listing all planned activities for the active day template in chronological order, showing each activity's time range, title, effort type, and focus category.
- **FR-005**: The left panel activity list MUST be independently scrollable when content exceeds the viewport height.
- **FR-006**: The system MUST provide sensible defaults for the biological ideal day when the user has not customized it (a preset based on common chronotype patterns).
- **FR-007**: The system MUST persist the user's biological ideal day configuration so it survives page reloads and application restarts.
- **FR-008**: The biological zone types MUST be visually distinct via color coding and icons/emojis (e.g., 🧠 Deep Focus = purple, 💪 Physical Peak = cyan, 🎨 Creative Zone = gold, 😴 Sleep = grey, 🧘 Rest = green, 🤝 Social = warm orange).
- **FR-009**: The biological zone type system (deep_focus, physical_peak, creative, rest, social, sleep) MUST remain independent from the effort tag system (musculaire, cerveau, emotionnel_social, creatif_divergent). There is no formal mapping between the two — any perceived alignment between them is purely visual and informational.
- **FR-010**: The system MUST display a right-side panel showing the effort budget gauge for the active day-type, including per-tag effort totals, overall planned hours versus the day-type ceiling, and visual warning indicators when any ceiling is exceeded.
- **FR-011**: The biological timeline MUST allow gaps (unassigned time periods) between zones. Gaps MUST render as neutral empty space. Full 24-hour coverage is NOT required.

### Key Entities

- **BiologicalZone**: A named time block in the user's ideal biological day.
  - `id`: unique identifier
  - `user_id`: owner of the configuration
  - `zone_name`: user-facing label (e.g., "Deep Focus Morning")
  - `zone_type`: category (deep_focus, physical_peak, creative, rest, social, sleep)
  - `start_time`: HH:MM start of the zone
  - `end_time`: HH:MM end of the zone
  - `color`: optional override color

- **PerfectDayBlock** (existing, from templates): Time-slotted activity already defined in the current agenda system, displayed in the left recap panel.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can view the full biological timeline and daily recap within 1 second of navigating to the Perfect Day view.
- **SC-002**: Users can configure their biological ideal day (add/edit/delete zones) in under 30 seconds per zone.
- **SC-003**: The biological timeline and daily recap panel display correctly on screen widths from 768px to 1920px without layout breakage.
- **SC-004**: 100% of planned activities are accurately reflected in the left recap panel when switching between day-type templates.

## Assumptions

- The biological ideal day is a personal, per-user configuration — it does not change across day-type templates (rest/regular/hustle). It is always the same biological reference.
- The existing Perfect Day template/block system (from spec 009 and 010) provides the data source for the left recap panel; no new activity data model is needed for the recap.
- The biological zone configuration is a new, lightweight data entity separate from Perfect Day templates.
- The view is read-only by default for the daily recap (editing activities is handled elsewhere); the biological timeline is configured from the Settings tab (not inline on the rendering view).
- Biological zone types and effort tags (spec 010) are two independent taxonomies. No formal mapping or foreign-key relationship exists between them.
- Mobile layouts (below 768px) are deferred to a future iteration; the initial rendering targets desktop/tablet viewports.
