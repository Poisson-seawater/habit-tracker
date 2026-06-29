# Research: Perfect Day Rendering

**Feature**: 011-perfect-day-rendering | **Date**: 2026-06-28

## R1: Biological Zone Storage Strategy

**Decision**: Store biological zones as individual rows in a new `biological_zones` table, one row per zone per user.

**Rationale**: Compared to a single JSON column on the User model, individual rows enable:
- SQL-level overlap validation (can query for conflicting zones)
- Individual CRUD operations without full-column read-modify-write
- Future extensibility (add metadata per zone, e.g., color overrides, notes)

**Alternatives considered**:
- `bio_zones_json` column on `users` table — simpler but prevents SQL overlap checks, makes concurrent edits risky, and mixes user metadata concerns.
- Embedded in `PerfectDayTemplate` — rejected because biological zones are user-level and template-independent (clarified in spec).

## R2: Overnight Zone Handling

**Decision**: Zones spanning midnight (e.g., Sleep 23:00–07:00) are stored with `start_time > end_time`. Overlap detection treats this as two virtual segments: [start → 24:00] and [00:00 → end].

**Rationale**: This is the simplest approach that avoids splitting a single conceptual zone into two database rows. The rendering code already handles this pattern (the existing mockup in spec 009 has blocks like 22:00–24:00 + 00:00–07:00).

**Alternatives considered**:
- Split into two rows — more SQL complexity, confusing to edit.
- Only allow zones within 00:00–24:00, no wrapping — too limiting for sleep blocks.

## R3: Overlap Detection Algorithm

**Decision**: Check overlap between two time ranges, accounting for midnight wrapping:
1. Normalize each range to minute-from-midnight pairs.
2. If a range wraps midnight, split it into two segments for comparison.
3. Two segments overlap if `seg1_start < seg2_end AND seg2_start < seg1_end`.

**Rationale**: This handles all edge cases (both ranges wrapping, one wrapping, neither wrapping) with simple arithmetic.

## R4: Default Biological Day Preset

**Decision**: Seed a "standard morning-focused" chronotype for new users:

| Zone | Type | Start | End |
|------|------|-------|-----|
| Sommeil | sleep | 23:00 | 07:00 |
| Focus Profond Matin | deep_focus | 08:00 | 12:00 |
| Repos / Déjeuner | rest | 12:00 | 13:00 |
| Pic Physique | physical_peak | 14:00 | 17:00 |
| Zone Créative | creative | 20:00 | 22:00 |

**Rationale**: Based on common ultradian rhythm patterns. Gaps at 07:00–08:00, 13:00–14:00, 17:00–20:00, and 22:00–23:00 are intentional transitional periods (spec clarification: gaps are allowed and render as neutral space).

## R5: Frontend Layout Architecture

**Decision**: Use a CSS Grid layout for the rendering view:
- Row 1 (full width): Biological timeline bar (fixed height ~60px)
- Row 2, Column 1 (~60%): Daily activity recap panel (scrollable)
- Row 2, Column 2 (~40%): Effort budget gauge panel

**Rationale**: Matches the mockup from spec 009 with the timeline at top. CSS Grid handles the asymmetric column widths cleanly and collapses to single-column on narrow viewports.

## R6: Settings UI for Bio Zone Configuration

**Decision**: Add a "Journée Biologique" section in the existing Settings tab, below the existing Perfect Day budget configuration. The section contains:
- A list of current zones with inline edit/delete buttons
- An "Add Zone" form with: name (text), type (select), start time (time input), end time (time input)

**Rationale**: Keeps configuration centralized in Settings (per spec clarification Q1). The rendering view remains purely read-only for the bio timeline.
