# Quickstart Guide: habit-tracker-bot

This document gets your local development environment running on a Raspberry Pi 5 under a strict 2GB memory budget.

## Prerequisites

- **Docker** and **Docker Compose** installed on the Pi.
- **Telegram Bot Token**: Create a bot via `@BotFather` and obtain a Token.
- **Telegram Group ID**: Add the bot to your target chat group and get its Group Chat ID.

## 1. Project Directory Layout

Ensure your directories are set up as follows in the workspace root:

```text
habit-tracker/
├── Dockerfile.api         # FastAPI server build context
├── Dockerfile.bot         # Bot daemon build context
├── docker-compose.yml     # Container orchestration definition
├── .env                  # Configuration and bot keys (secrets)
├── src/
│   ├── api/              # FastAPI application logic
│   ├── bot/              # Telegram bot listener code
│   └── database/         # SQLite schema, queries, SQLAlchemy setup
├── frontend/             # Static web dashboard assets
│   ├── index.html
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
└── data/                 # Mounted host volume holding sqlite.db
```

## 2. Setting Up Configurations (`.env`)

Create a `.env` file in the project root:

```env
TELEGRAM_BOT_TOKEN="your_bot_token_here"
TELEGRAM_GROUP_ID="your_group_chat_id_here"
API_PORT=5000
DATABASE_URL="sqlite:////data/habit_tracker.db"
ENV="production"
```

## 3. Spinning Up the Containers

Run the following command from the repository root:

```bash
docker-compose up -d --build
```

### Resource Allocation Safeguard
To guarantee compliance with the **Pi 5 2GB RAM** limits, both services in `docker-compose.yml` are configured with memory limits:

```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "${API_PORT}:5000"
    volumes:
      - ./data:/data
    restart: always
    deploy:
      resources:
        limits:
          memory: 40M

  bot:
    build:
      context: .
      dockerfile: Dockerfile.bot
    volumes:
      - ./data:/data
    restart: always
    deploy:
      resources:
        limits:
          memory: 35M
```
*(Combined memory limit is 75MB, well below the 100MB target and negligible for a 2GB RAM system.)*

## 4. Verification

- **API & Dashboard**: Open your browser and navigate to `http://localhost:5000/`. You should see the premium RPG visual dashboard character sheet loaded without errors.
- **Telegram Bot**: Type `/status today` in your chat group. The bot should fetch state from the shared SQLite DB and reply with your active stats.
