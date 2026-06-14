---
name: habit-pi-miniapp-tunnel
description: Prepare Gabriel's Raspberry Pi Habit Tracker Telegram Mini App tunnel workflow. Use when resuming at home to expose the Pi-hosted habit-tracker Mini App over HTTPS, configure TELEGRAM_WEB_APP_URL, verify Docker/FastAPI/API routes, and test the Telegram /app button end to end.
---

# Habit Pi Mini App Tunnel

## Goal

Prepare the Pi-hosted `habit-tracker` so Telegram can open the Mini App through an HTTPS tunnel while frontend, backend API, and SQLite remain on the Pi.

Do not use DualFlow for this flow unless the user explicitly wants a static-only demo. For the real app, the tunnel should point to the same FastAPI server that serves both:

```text
/mini-app/
/api/v1/*
```

## Resume Checklist

1. Connect to the Pi and locate the `habit-tracker` repo.
2. Inspect state before changing anything:
   ```bash
   git status --short
   docker compose ps
   ```
3. Ensure the current code contains:
   - `frontend/mini-app/`
   - `TELEGRAM_WEB_APP_URL` in config/env
   - `/api/v1/telegram-webapp/session`
   - Telegram bot command `/app`
4. Build/restart the app:
   ```bash
   docker compose up -d --build
   docker compose ps
   ```
5. Verify locally on the Pi:
   ```bash
   curl -I http://localhost:5000/mini-app/
   curl -s http://localhost:5000/health
   curl -s -X POST http://localhost:5000/api/v1/telegram-webapp/session \
     -H 'Content-Type: application/json' \
     -d '{"id":123456,"first_name":"TunnelTest"}'
   ```

## Tunnel Setup

Prefer Cloudflare Tunnel for the Pi. Use ngrok only for a quick disposable test.

The tunnel target must be the FastAPI HTTP service on the Pi, usually:

```text
http://localhost:5000
```

The resulting public URL should be used like:

```ini
TELEGRAM_WEB_APP_URL=https://<tunnel-host>/mini-app/
```

After editing `.env`, restart the bot/API containers:

```bash
docker compose up -d --build
docker compose logs --tail=80 bot
docker compose logs --tail=80 api
```

## External Verification

From outside the Pi, verify the tunnel:

```bash
curl -I https://<tunnel-host>/mini-app/
curl -s https://<tunnel-host>/health
curl -s -X POST https://<tunnel-host>/api/v1/telegram-webapp/session \
  -H 'Content-Type: application/json' \
  -d '{"id":123456,"first_name":"TunnelTest"}'
```

Then open Telegram and send:

```text
/app
```

Success means the button opens the Mini App and profile, habits, stats, and logging all work.

## Diagnostics

- Mini App opens but data is empty: frontend is reachable, but API is not; check tunnel target, `API_BASE`, CORS if using a separate API host, and `/api/v1/*` from the public URL.
- `/app` does not show a web app button: `TELEGRAM_WEB_APP_URL` is missing, malformed, not HTTPS, or bot was not restarted after `.env` changed.
- Telegram refuses to open: URL is not public HTTPS or tunnel is down.
- Local curl works but public curl fails: tunnel is not running or points to the wrong port/container.
- Existing dashboard works but Mini App fails: check `/mini-app/` static files and whether the deployed Pi code includes the Mini App copy.

## Security Note

The current prototype may use `Telegram.WebApp.initDataUnsafe.user` for quick testing. Before public/production usage, implement backend validation of raw Telegram `initData` before trusting user identity.
