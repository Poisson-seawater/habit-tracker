# Quickstart: Reward Shop (Boutique de Récompenses)

Follow these steps to run, interact with, and verify the Reward Shop feature.

## 1. Local Setup

Make sure you are in the virtual environment and dependencies are installed:
```bash
source .venv/bin/activate
uv pip install -r backend/requirements.txt
```

Run SQLite migrations to create the new `rewards` table (if testing an existing DB):
```bash
sqlite3 backend/data/habit_tracker.db < backend/src/database/migrations/v6_rewards.sql
```
*(Note: If starting with an empty/new database, `init_db()` at API startup will automatically create the table based on `models.py`).*

## 2. Running the Application

### Start the FastAPI Backend (API & Static Dashboard server)
```bash
PYTHONPATH=backend python3 backend/src/main.py
```
Open your browser at `http://localhost:5000` to access the dashboard. A new "Boutique" tab will be visible.

### Start the Telegram Bot Listener (Optional / Local test)
```bash
PYTHONPATH=backend python3 backend/src/bot/listener.py
```

## 3. Testing and Verification

### Run Automated Tests
A comprehensive test suite is included in `backend/tests/test_rewards.py`. Run it using PyTest:
```bash
PYTHONPATH=backend .venv/bin/pytest backend/tests/test_rewards.py
```

### Manual Verification via Dashboard UI
1. Go to `http://localhost:5000` and switch to the **Boutique** tab.
2. View your current gold balance at the top of the Boutique tab.
3. Click "Créer une Récompense" to open the creation modal/form.
4. Add a reward with title "Massage", cost 100 gold, no requirements.
5. Save. The reward appears as an unlocked card with a "Acheter" button.
6. Try to purchase the reward. If you have enough gold, the gold balance is updated, and the "Acheter" count increments. If you have insufficient gold, an error message is displayed.
7. Try to add a reward with a requirement (e.g. require an uncompleted goal or softskill). Verify it displays as locked with the lock reason, and the "Acheter" button is disabled.

### Manual Verification via Telegram Bot
1. Send `/shop` to the bot (either in the authorized group or DM if whitelisted).
2. The bot responds with the list of available rewards, their costs, status (unlocked/locked), and IDs.
3. Send `/buy 1` to purchase reward with ID 1.
4. Verify the bot's success message showing the gold spent and new balance, or appropriate error messages.
