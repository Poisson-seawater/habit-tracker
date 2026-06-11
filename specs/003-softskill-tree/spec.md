# Feature Specification: Softskill Progress Tree

**Feature Branch**: `003-softskill-tree`

**Created**: 2026-06-11

**Status**: Draft

**Input**: User description: "on a definir les objectifs maintenant il manque la visualiation du proges en softskill. Exemple: je veux etre un meilleur orateur je dois etre moins timide, articulier, augmenter mon vocabulaire etc ... sois que du travail sur moi. contrairement a objectif et graph, tout les softskill sont sur la meme. Et on separe 2 progression de softskill avec une couleur. Ex; le softskill vente est en rouge, et demande le softskill ecoute - rouge pale. comme la vente et orateur sont similiaire, je peux les relier ensemble. Le but est uniquement visualisation esthetique comme les skill tree dans les jeu video"

## Clarifications

### Session 2026-06-11

- Q: How is progress/unlocking updated? (Manual toggles vs automatic calculations based on habits/todos) → A: Progress is updated manually by the user. Each softskill includes a custom success description (a "test" sentence, e.g., "talk to 10 strangers without feeling burned out") that the user defines as their criteria for unlocking/completing the skill.
- Q: How is the skill tree layout defined? (Static configuration file vs dynamic editor UI) → A: The skill tree structure, branch colors, connections, and layout coordinates are defined in a static configuration file loaded by the backend.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Viewing the Softskill Tree (Priority: P1)

As a user, I want to see all my softskills and their connections on a single visual dashboard page, so that I can comprehend my overall self-development roadmap at a glance.

**Why this priority**: This is the core value of the feature; without the visual tree, there is no visualization.

**Independent Test**: The user navigates to the "Softskills" tab on the dashboard, and a visual node graph renders showing all skills, their connections, and their current state (locked, unlocked, in progress) with appropriate colors.

**Acceptance Scenarios**:

1. **Given** a user with a defined set of softskills and connections, **When** they load the softskills page, **Then** all skills are displayed on a single canvas, grouped and colored by progression paths.
2. **Given** a skill that is unlocked, **When** viewed on the tree, **Then** it is rendered with its full branch color (e.g. vibrant red).
3. **Given** a skill that is locked, **When** viewed on the tree, **Then** it is rendered in a faded or grayscale state.
4. **Given** a skill that is a prerequisite for another, **When** viewed, **Then** a connecting line points from the prerequisite to the dependent skill.

---

### User Story 2 - Viewing Skill Details (Priority: P2)

As a user, I want to click on a softskill node to see its details, description, prerequisites, and my custom success test sentence, so that I understand what that skill involves and what I need to achieve to unlock it.

**Why this priority**: Allows understanding individual skills and their success tests without cluttering the main tree view.

**Independent Test**: The user clicks on a skill node, and a modal or side panel opens showing details and the custom success test sentence of the selected skill.

**Acceptance Scenarios**:

1. **Given** the softskill tree is displayed, **When** the user clicks on a skill node, **Then** a detail panel or modal appears.
2. **Given** the detail panel is open, **When** viewing the skill details, **Then** the title, description, progress level, list of prerequisites, next connected skills, and the user's custom success test sentence are shown.

---

### User Story 3 - Updating Softskill Progress (Priority: P3)

As a user, I want to write/edit my custom success test sentence and manually mark a skill as completed once I pass my test, so that my visual tree reflects my actual self-work achievements.

**Why this priority**: Necessary to make the visualization dynamic rather than static.

**Independent Test**: The user edits their success test sentence or marks the skill as complete in the UI, and the node's visual style immediately updates on the tree.

**Acceptance Scenarios**:

1. **Given** the detail panel of a softskill is open, **When** the user inputs a custom success sentence (e.g., "talk to 10 strangers without feeling burned out") and saves it, **Then** the sentence is persisted.
2. **Given** a locked softskill whose prerequisites are met, **When** the user manually marks the success test as completed/unlocked, **Then** the progress state updates in the database and the visual node style changes to reflect the unlocked state.

---

### Edge Cases

- **Cyclical Dependencies**: What happens if a skill has cyclical prerequisites (e.g., A requires B, and B requires A)? The configuration/validation must prevent circular dependencies to avoid rendering loops.
- **Locked Prerequisites**: What happens if a user tries to unlock a skill whose prerequisites are not yet completed? The system should display a message/warning that prerequisites are required, or keep the unlock action disabled.
- **Cross-Path Layout Overlap**: How are skills with multiple connections across different paths rendered? Links should draw smoothly between paths without overlapping text labels or node circles.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST render all softskills and their connections on a single visual dashboard page/view.
- **FR-002**: The visualization MUST represent skills as nodes and connections as lines, styled like an RPG skill tree.
- **FR-003**: The system MUST support color-coding of progression branches/paths (e.g., one branch is red, another is blue).
- **FR-004**: Nodes in a branch MUST use color intensity or shading to indicate their level or prerequisite status (e.g., prerequisite is light/pale red, main skill is deep red).
- **FR-005**: The system MUST support connecting nodes across different branches (cross-branch links).
- **FR-006**: The system MUST persist user progress (levels, completion status) for each softskill.
- **FR-007**: The system MUST allow the user to view detailed information for any softskill (name, description, progress, connections, and custom success test) in a modal/panel upon interaction.
- **FR-008**: The system MUST allow users to manually update their progress and toggle completion status for any softskill whose prerequisites are met.
- **FR-009**: The system MUST load the skill tree structure, node layout coordinates, colors, and connections from a static configuration file on the backend.
- **FR-010**: The system MUST allow users to define and display a custom success test/criteria sentence (e.g., "talk to 10 strangers without feeling burned out") for each softskill.

### Key Entities *(include if feature involves data)*

- **Softskill**: Represents a personal development attribute (e.g., "Écoute", "Vente", "Orateur").
  - Attributes: ID, name, description, branch/category, base_color (hex or CSS variable), required_level, position_x, position_y (coordinates on tree).
- **PrerequisiteLink**: Represents a dependency or connection between two softskills.
  - Attributes: parent_skill_id, child_skill_id, type (prerequisite, related/similar).
- **UserSoftskillProgress**: Stores a specific user's progress on a softskill.
  - Attributes: user_id, softskill_id, success_criteria_test (custom user text), current_level/progress, completed/unlocked (boolean), updated_at.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The softskill tree page loads and renders all nodes and links in under 500ms on the local Raspberry Pi.
- **SC-002**: 100% of defined softskills and their prerequisite connections are correctly visualized according to their coordinates and branch colors.
- **SC-003**: The status of any skill node (locked, in-progress, unlocked) matches the database state 100% of the time, updating dynamically on status change.

## Assumptions

- The layout is primarily optimized for desktop/dashboard view, as RPG skill trees require significant screen real estate.
- There are no monetization or public registration concerns since this is a private multi-user app.
- Standard SVG elements or canvas will be used for connections, keeping dependencies minimal to respect the 40MB memory limit of the Pi.
