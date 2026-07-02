---
name: habit-tracker-auth-security
description: Recall and safely extend the Habit Tracker web authentication and approved-device implementation. Use when working on login, passwords, auth cookies, device approval/revocation, HABIT_API_TOKEN machine access, X-User-ID behavior, habitctl protocol auth, or Pi rollout security.
---

# Habit Tracker Auth Security

## Core Model

Treat MAC filtering as unavailable from the browser. The implemented device gate is cookie-based:

- `habit_device`: HttpOnly long-lived device secret, stored only as SHA-256 in SQLite.
- `habit_session`: HttpOnly session secret, stored only as SHA-256 in SQLite.
- Approved devices are site-wide; passwords remain per account.
- New devices start `pending` and must be approved by an admin device.

Key schema:

- `users.password_hash`, `users.password_salt`, `users.password_changed_at`, `users.is_admin`
- `auth_devices`: pending/approved/revoked browser devices
- `auth_sessions`: expiring web sessions tied to a user and approved device

## Current Auth Contract

Use these rules when changing auth-sensitive code:

- Browser API access must resolve through session cookies.
- Machine clients must send `Authorization: Bearer <HABIT_API_TOKEN>` plus `X-User-ID`.
- `X-User-ID` alone is only legacy fallback when no password exists and `AUTH_BOOTSTRAP_CODE` is unset.
- `/api/v1/capabilities` protocol is `2` and advertises machine auth.
- `habitctl.py configure` requires `--api-token` and stores it in its `0600` config.

Public auth endpoints:

- `GET /api/v1/auth/status`
- `POST /api/v1/auth/bootstrap`
- `POST /api/v1/auth/devices/request`
- `POST /api/v1/auth/login`

Protected auth endpoints:

- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/users`
- `GET /api/v1/auth/devices`
- `POST /api/v1/auth/devices/{id}/approve`
- `POST /api/v1/auth/devices/{id}/revoke`
- `POST /api/v1/auth/password`
- `POST /api/v1/auth/users/{id}/password`

## Files To Check

Auth behavior is intentionally centralized:

- `backend/src/api/routes.py`: auth helpers, endpoints, and `get_current_user_id()`
- `backend/src/api/idempotency.py`: skips auth endpoints; idempotence still works with authenticated/session or legacy `X-User-ID`
- `backend/src/database/models.py`: `AuthDevice`, `AuthSession`, user auth fields
- `backend/src/database/seed.py`: idempotent migration v24
- `frontend/js/app.js`, `frontend/index.html`, `frontend/css/style.css`: bootstrap/login/device UI
- `plugins/habit-tracker-control/scripts/habitctl.py`: protocol v2 API-token client
- `.env.example`, `README.md`, `docs/notes/habit-tracker-control-plugin.md`, `docs/adr/002-plugin-habit-tracker-control.md`: rollout docs

## Safe Change Checklist

Before finishing any auth change:

1. Preserve the no-lockout bootstrap path: `AUTH_BOOTSTRAP_CODE` creates the first admin password and approves the current device.
2. Keep cookies `HttpOnly`, `SameSite=Lax`, and `Secure` controlled by `AUTH_COOKIE_SECURE`.
3. Do not re-open protected API routes to plain `X-User-ID` once auth is configured.
4. Keep local legacy mode only for unconfigured dev/test databases.
5. Update `habitctl` and protocol docs if the machine-auth contract changes.
6. Do not update `COMMANDS-INDEX.md` unless Telegram bot commands are added, removed, or changed.

## Verification

Run focused checks after edits:

```bash
PYTHONPATH=backend .venv/bin/pytest backend/tests/test_auth.py backend/tests/test_habitctl.py backend/tests/test_remote_control_api.py -q
node --check frontend/js/app.js
```

For broad safety:

```bash
PYTHONPATH=backend .venv/bin/pytest backend/tests -q
```

Useful smoke test pattern:

```bash
DATABASE_URL=sqlite:////tmp/habit-auth-smoke.db \
AUTH_BOOTSTRAP_CODE=smoke-code \
HABIT_API_TOKEN=smoke-token \
.venv/bin/uvicorn src.main:app --app-dir backend --host 127.0.0.1 --port 5001
```
