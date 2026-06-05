# Aventurier Gabriel — Habit RPG Tracker 🧙‍♂️⚔️

Self-hosted RPG-style habit tracker and accountability system running on a **Raspberry Pi 5**. Both a Telegram bot listener and an analytical web dashboard share a fast, local **SQLite** persistent schema.

---

## 🛠️ Tech Stack & Architecture

- **Backend**: FastAPI (Python), SQLAlchemy ORM, Uvicorn, Python-Telegram-Bot, APScheduler, PyTest.
- **Frontend**: Responsive Vanilla HTML5 & CSS3 with HSL dark-palette colors, modern glassmorphism tokens, and interactive ES6 Fetch logic.
- **Hardware Constraints**: Restricts maximum hardware boundaries to **40MB** RAM (API) and **35MB** RAM (Telegram daemon) via Docker Compose configurations.
- **Persistence**: Singular local SQLite database mounted at `/data/habit_tracker.db` with standard concurrency locks.

---

## 🔑 Environment Configuration

Copy `.env.example` to `.env` at the root level of your workspace, then fill in
the Telegram values:

```ini
# --- Telegram Configurations ---
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_GROUP_ID=your_telegram_group_id_here
TELEGRAM_WEB_APP_URL=https://your-public-domain.example/mini-app/

# --- Server Configurations ---
API_PORT=5000
ENV=production

# --- SQLite Persistent Parameters (Host Override) ---
DATABASE_URL=sqlite:////data/habit_tracker.db
```

---

## 🚀 Localhost Execution (with `uv` & virtual envs)

1. **Setup environment & download dependencies**:
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -r backend/requirements.txt
   ```

2. **Run PyTest unit & integration suites**:
   ```bash
   PYTHONPATH=backend .venv/bin/pytest backend/tests
   ```

3. **Launch the FastAPI Server locally**:
   ```bash
   PYTHONPATH=backend python3 backend/src/main.py
   ```
   *The server automatically initializes tables, runs startup seeders, mounts frontend static folders, and starts serving the dashboard at [http://localhost:5000](http://localhost:5000).*

4. **Launch the Telegram daemon locally**:
   ```bash
   PYTHONPATH=backend python3 backend/src/bot/listener.py
   ```

5. **Test the Telegram Mini App**:
   Expose the API server over HTTPS, set `TELEGRAM_WEB_APP_URL` to the public
   `/mini-app/` URL, then send `/app` to the bot.

---

## 🐳 Docker Orchestration (Pi 5 Production-grade Compose)

Run the entire suite inside ultra-light virtual environments utilizing resource limits:

```bash
# Build and run containers in background polling loops
docker compose up -d --build
```

On the Raspberry Pi, update an existing deployment with:

```bash
git pull --ff-only
docker compose up -d --build
docker compose ps
```

If the committed SQLite snapshot must replace the Pi data, restore it explicitly
after pulling and before restarting the stack:

```bash
docker compose down
python3 ops/db/habit_tracker_db_admin.py restore-snapshot
docker compose up -d --build
docker compose ps
```

The restore command creates a timestamped backup under `data/backups/` before
replacing `data/habit_tracker.db`.

---

## 📦 Automated Backups & Rotations

The system executes daily SQLite rotations via `/app/backend/src/database/backup.py` and copies timestamped records under `/data/backups/`. It automatically purges older historical database archives to ensure only the latest **5 copies** reside on disk to protect Raspberry Pi storage bounds.
