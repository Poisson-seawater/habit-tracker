# Specs Index

This directory contains both active planning artifacts and historical Spec Kit
artifacts. Do not assume that an unchecked `tasks.md` means the feature is not in
the codebase; several features were implemented outside the original checklist.

Current source of truth for implemented behavior is the code plus `README.md`,
`AGENTS.md`, `COMMANDS-INDEX.md`, `log.md`, and `docs/wiki/pages/`.

## Status Legend

- `active`: still useful for near-term planning.
- `done`: implemented and useful as historical/design reference.
- `implemented-stale`: implemented, but the spec/task artifact is incomplete or
  contains stale assumptions.
- `superseded`: replaced by later specs or implementation direction.
- `draft`: idea/spec not yet validated for implementation.

## Specs

| Path | Status | Notes |
|---|---|---|
| `001-habit-tracker-bot/` | `done` | Initial bot/API/dashboard foundation. Tasks are checked; keep as historical reference. |
| `002-multiuser-rpg-v2/` | `implemented-stale` | Many goals/RPG/multi-user concepts exist, but the artifact has unchecked tasks and old assumptions. Do not use as current source of truth. |
| `003-softskill-tree/` | `done` | Softskill tree, progress, editing, and tests implemented. |
| `004-habit-streak-calendar/` | `implemented-stale` | Streak/calendar behavior is implemented and tested, but the spec has no `tasks.md`. |
| `005-reward-shop/` | `implemented-stale` | Reward shop exists in backend, frontend, tests, and bot/docs, but `tasks.md` remains unchecked. |
| `006-allostasis-rewards/` | `done` | Allostasis daily/weekly rewards implemented; tasks checked. |
| `007-recap-3-3-3/` | `implemented-stale` | Recap 3-3-3/pins/allostasis dashboard behavior exists, but `tasks.md` is unchecked. |
| `008-goal-dependency-display/` | `draft` | Incomplete Spec Kit lifecycle: spec/checklist only, no plan/tasks. Validate against current goal-link UI before implementing anything. |
| `009-perfect-day-agenda/` | `superseded` | Older agenda prototype and 4-template/stat-threshold assumptions. Superseded by specs 010/011 and the current agenda implementation. |
| `010-perfect-day-redesign/` | `done` | Current effort-budget model: `rest`, `regular`, `hustle`, effort ceilings, rest target, agenda JSON. |
| `011-perfect-day-rendering/` | `done` | Biological zones, Perfect Day rendering, daily recap, and budget gauge implemented; tasks checked. |
| `quest-agenda-fusion-plan.md` | `active` | Forward-looking plan around quest/agenda fusion. Validate against current agenda code before turning into tasks. |

## Current Planning Notes

- Google Calendar & Tasks integration is implemented in code and documented in
  `docs/wiki/pages/sync-google.md`. The old root brainstorm file is no longer an
  active planning source.
- The old daily RPG stat/threshold system was removed. Current progression uses
  persistent XP/level/gold plus effort budgets and scheduled-habit accountability.
- Current day templates are `rest`, `regular`, and `hustle`; old names such as
  `week`, `weekend`, `recup`, and `malade` are historical aliases/context only.
