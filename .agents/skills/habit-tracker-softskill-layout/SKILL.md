---
name: habit-tracker-softskill-layout
description: Recall, debug, and extend the Habit Tracker softskill global-view coordinate allocator. Use when working on softskill creation or editing, x/y coordinates, execution_order placement, overlap repair, branch layout, global tree rendering, softskills_tree.json persistence, or the frontend/API/habitctl softskill contracts.
---

# Habit Tracker Softskill Layout

## Rebuild Context

Read these files before changing behavior:

- `backend/src/services/softskill_service.py`: allocation, collision detection, repair, persistence, and CRUD.
- `backend/src/api/routes.py`: optional `x`/`y` request fields for skill creation and editing.
- `frontend/js/app.js`: global rendering from `x`/`y`; creation and editing intentionally omit coordinates.
- `backend/tests/test_softskills.py`: layout and API regression coverage.

Treat `backend/src/data/softskills_tree.json` as the tree configuration source.

## Preserve the Layout Contract

- Keep the global view coordinate-based.
- Keep branch-specific views grouped independently by `execution_order`.
- Let the backend own automatic placement; do not restore frontend defaults of
  `x: 0, y: 0`.
- Accept explicit positive coordinates for compatibility, but use them only when the
  position is free.
- Preserve coordinates during metadata-only edits.
- Reallocate after changing `branch` or `execution_order`, unless the request supplies a
  valid free position.
- Repair missing, non-positive, and overlapping positions while preserving valid nodes.
- Avoid a fixed slot count. The allocator must continue expanding beyond 50 skills.
- Keep the implementation dependency-free and lightweight for the Raspberry Pi.

## Recall the Algorithm

Use these constants from `softskill_service.py`:

```text
origin       = (100, 80)
grid step    = (200, 140)
node size    = (100, 112)
padding      = (40, 20)
y            = 80 + (execution_order - 1) * 140
```

Choose the horizontal anchor in this order:

1. Median `x` of same-branch prerequisites.
2. Median `x` of existing nodes in the branch.
3. First grid column after the globally used area for a new branch.

Search for a free slot around the anchor in this order:

```text
center, right 1, left 1, right 2, left 2, ...
```

Never search left of `x = 100`. Detect overlap using node dimensions plus padding, not
coordinate equality alone.

## Maintain Write Paths

Route creation and editing through `softskill_service.py`. Repair positions during config
loading and before saving. Validate prerequisite cycles before persisting. Do not change
the database schema for layout coordinates.

## Verify Changes

Run:

```bash
PYTHONPATH=backend .venv/bin/pytest backend/tests/test_softskills.py -q
PYTHONPATH=backend .venv/bin/pytest backend/tests -q
node --check frontend/js/app.js
git diff --check
```

Cover at minimum:

- creation without `x`/`y`;
- multiple skills at the same execution order without overlap;
- metadata edits preserving position;
- branch/order changes triggering reallocation;
- explicit free coordinates remaining supported;
- repair and persistence of `0:0` and collisions;
- more than 50 skills receiving unique positive positions.
