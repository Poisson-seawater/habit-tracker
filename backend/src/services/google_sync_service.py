import os
import base64
import httpx
import datetime
from typing import Optional, List
from sqlalchemy.orm import Session

from src.config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    GOOGLE_ENCRYPTION_KEY,
    TIMEZONE,
)
from src.database.models import User, Todo, BiologicalZone
from src.services.agenda_service import build_agenda_response


# Helper to convert HH:MM to minutes since midnight
def time_to_minutes(t_str: str) -> int:
    parts = t_str.split(":")
    return int(parts[0]) * 60 + int(parts[1])


# XOR token obfuscation/encryption
def encrypt_token(token: str) -> str:
    if not token:
        return ""
    key = GOOGLE_ENCRYPTION_KEY
    xor_bytes = bytes(
        [ord(token[i]) ^ ord(key[i % len(key)]) for i in range(len(token))]
    )
    return base64.b64encode(xor_bytes).decode("utf-8")


def decrypt_token(encrypted_token: str) -> str:
    if not encrypted_token:
        return ""
    key = GOOGLE_ENCRYPTION_KEY
    try:
        xor_bytes = base64.b64decode(encrypted_token.encode("utf-8"))
        decrypted_chars = [
            chr(xor_bytes[i] ^ ord(key[i % len(key)])) for i in range(len(xor_bytes))
        ]
        return "".join(decrypted_chars)
    except Exception:
        return encrypted_token


def get_google_auth_url(user_id: int) -> str:
    scopes = " ".join(
        [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/tasks",
        ]
    )
    # prompt=consent guarantees refresh_token is sent
    url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        "response_type=code&"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={GOOGLE_REDIRECT_URI}&"
        f"scope={scopes}&"
        "access_type=offline&"
        "prompt=consent&"
        f"state={user_id}"
    )
    return url


async def exchange_auth_code(user_id: int, code: str, db: Session):
    url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=data)
        if response.status_code != 200:
            raise Exception(f"Failed to exchange OAuth code: {response.text}")

        token_data = response.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise Exception("User not found")

        user.google_access_token = encrypt_token(access_token)
        if refresh_token:
            user.google_refresh_token = encrypt_token(refresh_token)
        user.google_token_expiry = datetime.datetime.now() + datetime.timedelta(
            seconds=expires_in
        )
        db.commit()

        # Build Calendar & Tasks lists
        await setup_google_resources(user_id, db)


async def get_valid_access_token(user_id: int, db: Session) -> Optional[str]:
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.google_refresh_token:
        return None

    # Check expiry with 5 minutes buffer
    if user.google_access_token and user.google_token_expiry:
        if datetime.datetime.now() < user.google_token_expiry - datetime.timedelta(
            minutes=5
        ):
            return decrypt_token(user.google_access_token)

    # Refresh token
    refresh_token = decrypt_token(user.google_refresh_token)
    url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=data)
        if response.status_code != 200:
            print(f"Failed to refresh Google token for user {user_id}: {response.text}")
            return None

        token_data = response.json()
        new_access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 3600)

        user.google_access_token = encrypt_token(new_access_token)
        user.google_token_expiry = datetime.datetime.now() + datetime.timedelta(
            seconds=expires_in
        )
        db.commit()

        return new_access_token


async def setup_google_resources(user_id: int, db: Session):
    token = await get_valid_access_token(user_id, db)
    if not token:
        return

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return

    headers = {"Authorization": f"Bearer {token}"}

    # 1. Calendar Setup
    if not user.google_calendar_id:
        async with httpx.AsyncClient() as client:
            list_resp = await client.get(
                "https://www.googleapis.com/calendar/v3/users/me/calendarList",
                headers=headers,
            )
            calendar_id = None
            if list_resp.status_code == 200:
                calendars = list_resp.json().get("items", [])
                for cal in calendars:
                    if cal.get("summary") == "Habit RPG Tracker" and not cal.get(
                        "deleted", False
                    ):
                        calendar_id = cal.get("id")
                        break

            if not calendar_id:
                create_resp = await client.post(
                    "https://www.googleapis.com/calendar/v3/calendars",
                    headers=headers,
                    json={"summary": "Habit RPG Tracker"},
                )
                if create_resp.status_code == 200:
                    calendar_id = create_resp.json().get("id")

            if calendar_id:
                user.google_calendar_id = calendar_id
                db.commit()

    # 2. Tasks List Setup
    if not user.google_tasks_list_id:
        async with httpx.AsyncClient() as client:
            list_resp = await client.get(
                "https://www.googleapis.com/tasks/v1/users/@me/lists", headers=headers
            )
            tasks_list_id = None
            if list_resp.status_code == 200:
                task_lists = list_resp.json().get("items", [])
                for tl in task_lists:
                    if tl.get("title") == "Habit RPG Tracker":
                        tasks_list_id = tl.get("id")
                        break

            if not tasks_list_id:
                create_resp = await client.post(
                    "https://www.googleapis.com/tasks/v1/users/@me/lists",
                    headers=headers,
                    json={"title": "Habit RPG Tracker"},
                )
                if create_resp.status_code == 200:
                    tasks_list_id = create_resp.json().get("id")

            if tasks_list_id:
                user.google_tasks_list_id = tasks_list_id
                db.commit()


async def create_due_date_event(
    user_id: int, todo_title: str, due_date, db: Session
) -> Optional[str]:
    token = await get_valid_access_token(user_id, db)
    if not token:
        return None

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.google_calendar_id:
        return None

    headers = {"Authorization": f"Bearer {token}"}
    date_str = due_date.isoformat() if hasattr(due_date, "isoformat") else str(due_date)
    event_body = {
        "summary": f"🏆 {todo_title}",
        "description": "Date limite de validation (Due Date) synchronisée depuis Habit RPG Tracker.",
        "start": {"date": date_str},
        "end": {"date": date_str},
        "extendedProperties": {"private": {"origin": "habit-tracker-todo-due"}},
    }

    async with httpx.AsyncClient() as client:
        url = f"https://www.googleapis.com/calendar/v3/calendars/{user.google_calendar_id}/events"
        resp = await client.post(url, headers=headers, json=event_body)
        if resp.status_code == 200:
            return resp.json().get("id")
        return None


async def update_due_date_event(
    user_id: int, event_id: str, todo_title: str, due_date, db: Session
):
    token = await get_valid_access_token(user_id, db)
    if not token:
        return

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.google_calendar_id:
        return

    headers = {"Authorization": f"Bearer {token}"}
    date_str = due_date.isoformat() if hasattr(due_date, "isoformat") else str(due_date)
    event_body = {
        "summary": f"🏆 {todo_title}",
        "start": {"date": date_str},
        "end": {"date": date_str},
    }

    async with httpx.AsyncClient() as client:
        url = f"https://www.googleapis.com/calendar/v3/calendars/{user.google_calendar_id}/events/{event_id}"
        await client.patch(url, headers=headers, json=event_body)


async def delete_due_date_event(user_id: int, event_id: str, db: Session):
    token = await get_valid_access_token(user_id, db)
    if not token:
        return

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.google_calendar_id:
        return

    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        url = f"https://www.googleapis.com/calendar/v3/calendars/{user.google_calendar_id}/events/{event_id}"
        await client.delete(url, headers=headers)


async def create_do_date_task(
    user_id: int, todo_title: str, do_date, db: Session
) -> Optional[str]:
    token = await get_valid_access_token(user_id, db)
    if not token:
        return None

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.google_tasks_list_id:
        return None

    headers = {"Authorization": f"Bearer {token}"}
    date_str = do_date.isoformat() if hasattr(do_date, "isoformat") else str(do_date)
    task_body = {
        "title": f"⚔️ {todo_title}",
        "notes": "Planifié pour (Do Date) synchronisée depuis Habit RPG Tracker.",
        "due": f"{date_str}T00:00:00Z",
    }

    async with httpx.AsyncClient() as client:
        url = f"https://www.googleapis.com/tasks/v1/lists/{user.google_tasks_list_id}/tasks"
        resp = await client.post(url, headers=headers, json=task_body)
        if resp.status_code == 200:
            return resp.json().get("id")
        return None


async def update_do_date_task(
    user_id: int, task_id: str, todo_title: str, do_date, completed: bool, db: Session
):
    token = await get_valid_access_token(user_id, db)
    if not token:
        return

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.google_tasks_list_id:
        return

    headers = {"Authorization": f"Bearer {token}"}
    task_body = {
        "title": f"⚔️ {todo_title}",
        "status": "completed" if completed else "needsAction",
    }
    if do_date:
        date_str = (
            do_date.isoformat() if hasattr(do_date, "isoformat") else str(do_date)
        )
        task_body["due"] = f"{date_str}T00:00:00Z"
    else:
        task_body["due"] = None

    async with httpx.AsyncClient() as client:
        url = f"https://www.googleapis.com/tasks/v1/lists/{user.google_tasks_list_id}/tasks/{task_id}"
        await client.patch(url, headers=headers, json=task_body)


async def delete_do_date_task(user_id: int, task_id: str, db: Session):
    token = await get_valid_access_token(user_id, db)
    if not token:
        return

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.google_tasks_list_id:
        return

    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        url = f"https://www.googleapis.com/tasks/v1/lists/{user.google_tasks_list_id}/tasks/{task_id}"
        await client.delete(url, headers=headers)


async def export_typical_day_timeline(
    user_id: int, start_date: datetime.date, end_date: datetime.date, db: Session
):
    token = await get_valid_access_token(user_id, db)
    if not token:
        raise Exception("Google Account not connected or invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.google_calendar_id:
        raise Exception("Dedicated Google calendar not set up")

    headers = {"Authorization": f"Bearer {token}"}
    calendar_id = user.google_calendar_id

    async with httpx.AsyncClient() as client:
        # 1. Delete existing timeline events in this range
        url_list = (
            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
        )
        params = {
            "privateExtendedProperty": "origin=habit-tracker-timeline",
            "timeMin": f"{start_date.isoformat()}T00:00:00Z",
            "timeMax": f"{end_date.isoformat()}T23:59:59Z",
            "maxResults": 250,
        }
        resp = await client.get(url_list, headers=headers, params=params)
        if resp.status_code == 200:
            events = resp.json().get("items", [])
            for event in events:
                event_id = event.get("id")
                await client.delete(
                    f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}",
                    headers=headers,
                )

        # 2. Iterate each day and insert events
        current_date = start_date
        while current_date <= end_date:
            # A. Fetch biological zones
            zones = (
                db.query(BiologicalZone)
                .filter(BiologicalZone.user_id == user_id)
                .order_by(BiologicalZone.display_order)
                .all()
            )
            for z in zones:
                t_start = datetime.time.fromisoformat(z.start_time)
                t_end = datetime.time.fromisoformat(z.end_time)
                dt_start = datetime.datetime.combine(current_date, t_start)
                if t_end < t_start:
                    dt_end = datetime.datetime.combine(
                        current_date + datetime.timedelta(days=1), t_end
                    )
                else:
                    dt_end = datetime.datetime.combine(current_date, t_end)

                event_body = {
                    "summary": f"🧠 {z.zone_name}",
                    "description": f"Zone biologique type ({z.zone_type}) importee de Habit RPG Tracker.",
                    "start": {"dateTime": dt_start.isoformat(), "timeZone": TIMEZONE},
                    "end": {"dateTime": dt_end.isoformat(), "timeZone": TIMEZONE},
                    "extendedProperties": {
                        "private": {"origin": "habit-tracker-timeline"}
                    },
                }
                await client.post(
                    f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                    headers=headers,
                    json=event_body,
                )

            # B. Fetch agenda response details (template segments + placed quests)
            try:
                agenda_dict, _ = build_agenda_response(db, user_id, current_date)
            except Exception:
                agenda_dict = None

            if agenda_dict:
                # Placed quests
                for item in agenda_dict.get("placed_quests", []):
                    start_time_str = item.get("start_time")
                    duration_min = item.get("duration_minutes", 60)
                    if not start_time_str:
                        continue
                    try:
                        start_min = time_to_minutes(start_time_str)
                        dt_start = datetime.datetime.combine(
                            current_date, datetime.time(start_min // 60, start_min % 60)
                        )
                        dt_end = dt_start + datetime.timedelta(minutes=duration_min)

                        event_body = {
                            "summary": f"🎯 {item['name']}",
                            "description": "Placements d'agenda (Quete / Habitude) planifiee.",
                            "start": {
                                "dateTime": dt_start.isoformat(),
                                "timeZone": TIMEZONE,
                            },
                            "end": {
                                "dateTime": dt_end.isoformat(),
                                "timeZone": TIMEZONE,
                            },
                            "extendedProperties": {
                                "private": {"origin": "habit-tracker-timeline"}
                            },
                        }
                        await client.post(
                            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                            headers=headers,
                            json=event_body,
                        )
                    except Exception as ex:
                        print(f"Error exporting placed quest: {ex}")

                # Template segments
                for seg in agenda_dict.get("segments", []):
                    start_str = seg.get("start")
                    end_str = seg.get("end")
                    if not start_str or not end_str:
                        continue
                    try:
                        t_start = datetime.time.fromisoformat(start_str)
                        t_end = datetime.time.fromisoformat(end_str)
                        dt_start = datetime.datetime.combine(current_date, t_start)
                        if t_end < t_start:
                            dt_end = datetime.datetime.combine(
                                current_date + datetime.timedelta(days=1), t_end
                            )
                        else:
                            dt_end = datetime.datetime.combine(current_date, t_end)

                        event_body = {
                            "summary": f"📅 {seg['title']}",
                            "description": f"Segment type de Perfect Day ({seg.get('category')})",
                            "start": {
                                "dateTime": dt_start.isoformat(),
                                "timeZone": TIMEZONE,
                            },
                            "end": {
                                "dateTime": dt_end.isoformat(),
                                "timeZone": TIMEZONE,
                            },
                            "extendedProperties": {
                                "private": {"origin": "habit-tracker-timeline"}
                            },
                        }
                        await client.post(
                            f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events",
                            headers=headers,
                            json=event_body,
                        )
                    except Exception as ex:
                        print(f"Error exporting template segment: {ex}")

            current_date += datetime.timedelta(days=1)


# Background task hooks
async def sync_todo_created(user_id: int, todo_id: int, db_session_factory):
    db = db_session_factory()
    try:
        todo = db.query(Todo).filter(Todo.id == todo_id).first()
        if not todo:
            return
        # If due_date is set, create calendar event
        if todo.due_date:
            event_id = await create_due_date_event(
                user_id, todo.title, todo.due_date, db
            )
            if event_id:
                todo.google_due_event_id = event_id
                db.commit()
        # If do_date is set, create task list task
        if todo.do_date:
            task_id = await create_do_date_task(user_id, todo.title, todo.do_date, db)
            if task_id:
                todo.google_do_task_id = task_id
                db.commit()
    except Exception as e:
        print(f"Error in sync_todo_created: {e}")
    finally:
        db.close()


async def sync_todo_updated(user_id: int, todo_id: int, db_session_factory):
    db = db_session_factory()
    try:
        todo = db.query(Todo).filter(Todo.id == todo_id).first()
        if not todo:
            return

        # Due Date calendar event sync
        if todo.due_date:
            if todo.google_due_event_id:
                await update_due_date_event(
                    user_id, todo.google_due_event_id, todo.title, todo.due_date, db
                )
            else:
                event_id = await create_due_date_event(
                    user_id, todo.title, todo.due_date, db
                )
                if event_id:
                    todo.google_due_event_id = event_id
                    db.commit()
        else:
            if todo.google_due_event_id:
                await delete_due_date_event(user_id, todo.google_due_event_id, db)
                todo.google_due_event_id = None
                db.commit()

        # Do Date task list sync
        if todo.do_date:
            if todo.google_do_task_id:
                await update_do_date_task(
                    user_id,
                    todo.google_do_task_id,
                    todo.title,
                    todo.do_date,
                    todo.is_completed,
                    db,
                )
            else:
                task_id = await create_do_date_task(
                    user_id, todo.title, todo.do_date, db
                )
                if task_id:
                    todo.google_do_task_id = task_id
                    db.commit()
        else:
            if todo.google_do_task_id:
                await delete_do_date_task(user_id, todo.google_do_task_id, db)
                todo.google_do_task_id = None
                db.commit()
    except Exception as e:
        print(f"Error in sync_todo_updated: {e}")
    finally:
        db.close()


async def sync_todo_completed(user_id: int, todo_id: int, db_session_factory):
    db = db_session_factory()
    try:
        todo = db.query(Todo).filter(Todo.id == todo_id).first()
        if not todo:
            return
        if todo.google_do_task_id:
            await update_do_date_task(
                user_id,
                todo.google_do_task_id,
                todo.title,
                todo.do_date,
                todo.is_completed,
                db,
            )
    except Exception as e:
        print(f"Error in sync_todo_completed: {e}")
    finally:
        db.close()


async def sync_todo_deleted(
    user_id: int, event_id: Optional[str], task_id: Optional[str], db_session_factory
):
    db = db_session_factory()
    try:
        if event_id:
            await delete_due_date_event(user_id, event_id, db)
        if task_id:
            await delete_do_date_task(user_id, task_id, db)
    except Exception as e:
        print(f"Error in sync_todo_deleted: {e}")
    finally:
        db.close()
