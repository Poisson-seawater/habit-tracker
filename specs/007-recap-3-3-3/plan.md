# Implementation Plan: 3-3-3 Recap Dashboard Panel

**Branch**: `007-recap-3-3-3` | **Date**: 2026-06-12 | **Spec**: [specs/007-recap-3-3-3/spec.md](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/specs/007-recap-3-3-3/spec.md)

**Input**: Feature specification from `/specs/007-recap-3-3-3/spec.md`

## Summary

This feature adds a premium glassmorphic "3-3-3 Recap" widget directly above the Character Sheet (`stats-panel`) on the dashboard screen of Gabriel's Habit RPG Tracker. The widget focuses the user's attention on their top 3 active goal sub-steps (with edit modal and direct redirect), top 3 active softskills (with edit modal and direct redirect/focus), and top 3 daily or weekly allostasis activities (with switch button and direct validation/purchase capabilities). 

The user's pinned preferences are saved to the database in the `users` table via new JSON columns, and a new REST endpoint (`PUT /api/v1/profile/pins`) allows updating them.

## Technical Context

**Language/Version**: Python 3.12, Javascript ES6

**Primary Dependencies**: FastAPI, SQLAlchemy 2.0, python-telegram-bot

**Storage**: SQLite (`/data/habit_tracker.db` in Docker, `backend/data/` in local)

**Testing**: pytest

**Target Platform**: Linux server, Raspberry Pi 5 (ARM64)

**Project Type**: web-service, Telegram Bot

**Performance Goals**: Tab transitions/focus < 150ms, allostasis validation < 100ms

**Constraints**: Memory footprint < 40MB per service on Raspberry Pi

**Scale/Scope**: 1 user (Gabriel) for v1, extensible to multi-user

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Dual-Interface Design: Single source of truth database shared by FastAPI and Telegram Bot.
- [x] Flexible Point-Based Accountability: Pinned allostasis validations directly update daily stats/scores in the shared DB.
- [x] Multi-User Foundation & Privacy: Pins are associated directly with the authenticated `user_id` resolved via `X-User-ID`.
- [x] Self-Hosted Pi & Docker: SQLite migration files and lightweight static serves ensure low memory consumption.
- [x] Strict API Contract & Integration-Ready: Clean new endpoints with clear Pydantic schemas for updating user pins.

## Proposed Changes

### Database Layer

#### [MODIFY] [models.py](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/backend/src/database/models.py)
- Add columns to `User` class:
  ```python
  pinned_substeps = Column(JSON, nullable=True, default=list)
  pinned_softskills = Column(JSON, nullable=True, default=list)
  ```

#### [NEW] [v8_pinned_items.sql](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/backend/src/database/migrations/v8_pinned_items.sql)
- Migration script to add JSON columns to `users` table:
  ```sql
  -- Add pinned_substeps and pinned_softskills columns to users table
  ALTER TABLE users ADD COLUMN pinned_substeps TEXT DEFAULT '[]';
  ALTER TABLE users ADD COLUMN pinned_softskills TEXT DEFAULT '[]';
  ```

### API Layer

#### [MODIFY] [routes.py](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/backend/src/api/routes.py)
- Create schema `PinsUpdate` (Pydantic model):
  ```python
  class PinsUpdate(BaseModel):
      pinned_substeps: List[int]
      pinned_softskills: List[str]
  ```
- Modify `GET /profile` response to include:
  ```python
  "pinned_substeps": user.pinned_substeps or [],
  "pinned_softskills": user.pinned_softskills or []
  ```
- Implement `PUT /profile/pins`:
  ```python
  @router.put("/profile/pins")
  def update_pins(payload: PinsUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
      user = db.query(User).filter_by(id=user_id).first()
      if not user:
          raise HTTPException(status_code=404, detail="User not found")
      user.pinned_substeps = payload.pinned_substeps
      user.pinned_softskills = payload.pinned_softskills
      db.commit()
      return {"status": "success", "message": "Pins updated successfully"}
  ```

### Frontend UI Layer

#### [MODIFY] [index.html](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/frontend/index.html)
- Wrap `stats-panel` in a `left-column-container` div.
- Add `recap-panel` section right above `stats-panel`.
- Add a sidebar drawer modal `#recap-pin-drawer` at the bottom of the HTML containing checkboxes to configure pinned goals and softskills.

#### [MODIFY] [style.css](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/frontend/css/style.css)
- Implement grid layout for `recap-panel` (3 columns on desktop, 1 column on mobile).
- Add styles for checklist items inside the recap sections.
- Style edit drawer forms and checkbox lists for pin selectors.

#### [MODIFY] [app.js](file:///home/gabriel/Desktop/CS%20and%20programation/01-projets-actifs/habit-tracker/frontend/js/app.js)
- Extend `fetchProfile()` to parse `pinned_substeps` and `pinned_softskills`.
- Write `renderRecapWidget(profileData)` to render pinned sub-steps, softskills, and allostasis items.
- Write interaction handlers for:
  - Switching between daily and weekly views in the allostasis section.
  - Validation of allostasis items directly inside the recap widget (with instant stats refresh).
  - Open selection drawer and populate checkboxes dynamically.
  - Save pin selections through the API.
  - Tab navigation and auto-focusing elements when clicking items in the recap widget.

## Verification Plan

### Automated Tests
- Write test file `backend/tests/test_profile_pins.py` testing the API `PUT /profile/pins` and the updated fields in `GET /profile`.
- Command to run: `PYTHONPATH=backend pytest backend/tests/test_profile_pins.py`

### Manual Verification
- Visual inspection of the dashboard layout on desktop and mobile.
- Verify checkbox selectors and limit of 3 pins max per category.
- Verify clicking a pinned goal/sub-step correctly redirects to the visualizer and focuses the node.
- Verify clicking a pinned softskill correctly redirects to the softskills tree and focuses the node.
- Verify validating allostasis items directly in the recap panel triggers a successful API request and updates XP, level, gold, and thresholds.
