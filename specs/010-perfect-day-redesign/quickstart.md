# Quickstart: Perfect Day Redesign (Effort Budget Allocator)

This guide helps you verify the implementation of the new effort budget allocator.

## Backend Verification

### 1. Database Seeding & Migrations
Run the seed/migration script to update schemas and insert initial day-type templates:
```bash
# Set PYTHONPATH and run seed.py to perform schema upgrades
PYTHONPATH=backend python3 backend/src/database/seed.py
```

### 2. Run Backend Tests
Run the pytest test suite to verify the logic:
```bash
# Run tests for profile/template scoring
PYTHONPATH=backend pytest backend/tests/
```

---

## Frontend Manual Verification

### 1. Launch the Application
Start the FastAPI server:
```bash
PYTHONPATH=backend python3 backend/src/main.py
```
Then navigate to: http://localhost:5000/

### 2. Verify settings tab
1. Go to the settings tab.
2. Select the "Perfect Days" template settings.
3. Configure thresholds for the `rest`, `regular`, and `hustle` day-types:
   - Target focus hours
   - Ceilings per effort type
   - Minimum rest hours
4. Save and verify they are stored.

### 3. Verify habit/quest and sub-step editor
1. Create or edit a habit (Quête).
2. Set its effort type tag and duration. Leave duration empty and ensure it defaults to 1.0.
3. Edit/create a sub-step and set its effort type tag and duration.

### 4. Verify dashboard gauge and warning indicators
1. Go to the dashboard.
2. Change the active template to `regular`. Schedule habits. Observe the effort gauges and verify limits.
3. Switch template to `hustle`. Plan activities exceeding 11.2 hours. Verify that the hustle day displays an "Invalid Day" warning because the unplanned time is below 30%.
