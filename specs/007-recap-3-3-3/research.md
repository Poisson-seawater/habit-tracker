# Research: 3-3-3 Recap Dashboard Panel

## Decisions & Rationale

### 1. Storing Pinned Preferences in the Database (JSON columns)
- **Decision**: Add `pinned_substeps` and `pinned_softskills` columns directly to the `User` database model.
- **Rationale**: Saving settings on the client-side (via localStorage) would cause settings to be lost if the user opens the application on another device (such as the Telegram bot interface, or a different computer/browser). Storing it in the DB allows full sync across all user interfaces.
- **Alternatives Considered**: 
  - *Client-side localStorage*: Simpler, but lacks cross-device persistence. Rejected because the user has a multi-user layout constraint and runs the system across Pi, Telegram bot, and dashboard.
  - *Separate UserSettings model*: Creates unnecessary complexity and query joins. Storing lists directly inside the User model as JSON is simple, compact, and performs exceptionally well on SQLite.

### 2. Layout Integration in the Left Column
- **Decision**: Group the recap widget and character sheet (`stats-panel`) together in a layout wrapper inside the left column of the dashboard.
- **Rationale**: The user requested the widget "just above the character sheet". The character sheet is located in the left column on desktop and occupies `1fr` width, whereas the main lists (Quests, Bounties, No-Todos) occupy the right column (`1.2fr`). Grouping the recap panel directly above the stats panel preserves the desktop layout structure and automatically translates to mobile responsiveness (where columns stack vertically, maintaining the recap widget right above the stats).

### 3. Drawer Overlay for Selecting Pinned Items
- **Decision**: Implement a slide-out drawer (`#recap-pin-drawer`) matching the existing styles of other drawers in the application (`#creators-drawer`, `#softskill-detail-drawer`).
- **Rationale**: Reusing the existing slide-out drawer layout maintains visual consistency and structure. The drawer will list checkboxes and programmatically limit selections to a maximum of 3 items per category.
