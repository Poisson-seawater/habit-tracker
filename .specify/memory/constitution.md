<!--
SYNC IMPACT REPORT
==================
- Version change: Template → v1.0.0
- List of modified principles:
  * [PRINCIPLE_1_NAME] → I. Client-Side Local-First Architecture
  * [PRINCIPLE_2_NAME] → II. Premium Aesthetics & Modern Design
  * [PRINCIPLE_3_NAME] → III. Standard Tech Stack Discipline (Vanilla-First)
  * [PRINCIPLE_4_NAME] → IV. Robust State & Local Persistence
  * [PRINCIPLE_5_NAME] → V. Web Standards, SEO & Accessibility (a11y)
- Added sections:
  * Technical Constraints & Stack
  * Development Quality Gates
- Removed sections: None
- Templates requiring updates:
  * .specify/templates/plan-template.md (✅ updated)
  * .specify/templates/spec-template.md (✅ updated - no changes needed)
  * .specify/templates/tasks-template.md (✅ updated - no changes needed)
- Follow-up TODOs: None
-->

# habit-tracker Constitution

## Core Principles

### I. Client-Side Local-First Architecture
The application runs entirely in the user's browser without any server-side database or processing.
All data (habits, completion history, streaks) MUST be stored locally (e.g. in LocalStorage).
The application must remain fully functional offline and require no network connection.

### II. Premium Aesthetics & Modern Design
Visual excellence is non-negotiable. The user interface must feel premium, using HSL-based dark
theme colors by default, sleek modern typography (e.g., Outfit or Inter), smooth hover/active
transitions, subtle gradients, and responsive layouts. Micro-animations must highlight interaction.

### III. Standard Tech Stack Discipline (Vanilla-First)
The tech stack must remain clean and lightweight: standard HTML5 semantic elements, modular ES6+
JavaScript, and Vanilla CSS. Do not use framework libraries (like React/Vue) or CSS engines
(like TailwindCSS) unless explicitly requested by the user, ensuring zero build overhead.

### IV. Robust State & Local Persistence
State transitions must be managed deterministically and update both the DOM and LocalStorage. Data
integrity is critical: LocalStorage schemas must be versioned, and the application must gracefully
handle corrupted, empty, or migrated local state without crashing.

### V. Web Standards, SEO & Accessibility (a11y)
The project must adhere to modern web standards: exactly one H1 per page, structured HTML5 semantic
sections, appropriate page titles and meta tags, and unique, descriptive IDs for all interactive
components to enable seamless automated end-to-end browser testing.

## Technical Constraints & Stack

- **Runtime**: Modern web browsers supporting ES6+ modules and LocalStorage.
- **HTML**: Standard-compliant, structured semantic elements.
- **CSS**: Vanilla CSS using custom properties (variables) for theme tokens. Responsive design
  via Flexbox and CSS Grid.
- **JavaScript**: Modular, clean ES6+ JavaScript, running in strict mode.

## Development Quality Gates

- **Syntax Verification**: Run basic syntax checks (`npm run check` or equivalent linting) before
  commits.
- **Visual & Interaction Check**: Verify that all components have clean hover effects, transition
  states, and responsive layouts.
- **Browser Testing**: Verify that all interactive paths are functional without any console errors.

## Governance

- This constitution governs all development on the habit-tracker project.
- Any modifications to the principles or stack require an agreement and must result in a semantic
  version bump of the constitution.
- Refer to [PROJECT.md](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/PROJECT.md) for the active roadmap and feature scope.

**Version**: 1.0.0 | **Ratified**: 2026-05-31 | **Last Amended**: 2026-05-31
