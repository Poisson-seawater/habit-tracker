# Spec Checklist: Allostasis Rewards

Use this checklist to verify that the feature specification is complete, robust, and contains no implementation leaks.

## 1. Scope & Rules Validation
- [x] **Zero Gold Cost**: Verified that daily/weekly allostasis items are defined as costing 0 gold.
- [x] **Category Capping**: Enforces maximum of 3 items per user for `allostasis_daily` and 3 items for `allostasis_weekly`.
- [x] **Recurrence & Reset**: Defines reset logic: daily items reset at midnight user-local time, weekly items reset Monday midnight.
- [x] **Daily Guild/User Recap Integration**: The specs clearly outline that purchased allostasis items for the day will be included in the daily recap.
- [x] **Telegram Bot Command Rule**: Remember that if any bot commands are added/modified, we MUST update `COMMANDS-INDEX.md` (Checked).

## 2. No Implementation Leakage
- [x] The specification describes *what* the system should do, rather than *how* the code is structured (e.g., it mentions the fields and limits functionally, not specific Python imports or JS function names).
- [x] The test scenarios are specified using black-box inputs/outputs (Given/When/Then, clicking UI elements, running bot commands).

## 3. Testability
- [x] Each User Story contains an Independent Test that a QA engineer or automated test script can verify.
- [x] Success Criteria are measurable (limits, load times, timezone reset behaviors).
- [x] Boundary conditions like trying to add a 4th item or double-redeeming an item are explicitly defined.
