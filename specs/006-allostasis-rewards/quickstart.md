# Quickstart Guide: Allostasis Rewards

Follow this guide to run, verify, and test the Allostasis Rewards feature.

## 1. Database Setup
Apply the SQLite schema update:
```bash
sqlite3 data/habit_tracker.db < backend/src/database/migrations/v7_allostasis_rewards.sql
```

## 2. Running the Server
Launch the FastAPI application:
```bash
PYTHONPATH=backend python3 backend/src/main.py
```

The web dashboard will be available at `http://localhost:5000`.

## 3. Testing with cURL

### Create Allostasis Reward (Daily)
```bash
curl -X POST http://localhost:5000/api/v1/rewards \
  -H "X-User-ID: 1" \
  -H "Content-Type: application/json" \
  -d '{"title": "25 min TV Show", "description": "Relaxation series", "gold_cost": 0, "category": "allostasis_daily"}'
```

### Redeem / Check off Allostasis Reward
```bash
curl -X POST http://localhost:5000/api/v1/rewards/1/purchase \
  -H "X-User-ID: 1"
```

## 4. Running Unit Tests
Verify all logic with pytest:
```bash
PYTHONPATH=backend .venv/bin/pytest backend/tests/test_allostasis_rewards.py
```
