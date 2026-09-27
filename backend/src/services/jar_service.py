"""Weekly attention plans. A reservation never changes its source action."""

import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.database.models import Habit, JarWeek, Todo, User
from src.services import agenda_service


BLOCK_PARTS = ("morning", "afternoon", "evening")
BLOCK_KEYS = frozenset(f"{day}-{part}" for day in range(7) for part in BLOCK_PARTS)


def require_monday(week_start: datetime.date) -> None:
    if week_start.weekday() != 0:
        raise HTTPException(status_code=400, detail="week_start must be a Monday")


def empty_plan(week_start: datetime.date) -> dict:
    return {
        "week_start": week_start.isoformat(),
        "available_blocks": [],
        "items": [],
        "placements": {},
        "updated_at": None,
    }


def plan_payload(row: JarWeek | None, week_start: datetime.date) -> dict:
    if row is None:
        return empty_plan(week_start)
    return {
        "week_start": week_start.isoformat(),
        "available_blocks": row.available_blocks or [],
        "items": row.items or [],
        "placements": row.placements or {},
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def week_candidates(db: Session, user_id: int, week_start: datetime.date) -> list[dict]:
    user = db.query(User).filter_by(id=user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    habits = (
        db.query(Habit)
        .filter(
            Habit.user_id == user_id,
            Habit.is_active.is_(True),
            Habit.archived_at.is_(None),
        )
        .order_by(Habit.id)
        .all()
    )
    # A version group contributes only its latest active quest.
    latest = {}
    for habit in habits:
        latest[habit.relationship_root_id or habit.id] = habit

    days = [week_start + datetime.timedelta(days=offset) for offset in range(7)]
    day_types = {day: agenda_service.resolve_day_type(db, user_id, day) for day in days}
    candidates = []
    for habit in latest.values():
        scheduled = [
            day.isoformat()
            for day in days
            if agenda_service.is_habit_eligible_on_date(
                habit, day, user, day_types[day]
            )
        ]
        if scheduled:
            candidates.append(
                {
                    "source_type": "habit",
                    "source_id": habit.id,
                    "title": habit.name,
                    "days": scheduled,
                }
            )

    todos = (
        db.query(Todo)
        .filter(
            Todo.user_id == user_id,
            Todo.is_completed.is_(False),
            Todo.do_date >= week_start,
            Todo.do_date <= week_start + datetime.timedelta(days=6),
        )
        .order_by(Todo.do_date, Todo.id)
        .all()
    )
    for todo in todos:
        candidates.append(
            {
                "source_type": "todo",
                "source_id": todo.id,
                "title": todo.title,
                "days": [todo.do_date.isoformat()],
            }
        )
    return candidates


def validate_sources(
    db: Session, user_id: int, items: list[dict], old_items: list
) -> None:
    old_refs = {
        (item.get("source_type"), item.get("source_id"))
        for item in old_items or []
        if item.get("source_type") and item.get("source_id")
    }
    for item in items:
        source_type = item.get("source_type")
        source_id = item.get("source_id")
        if source_type is None:
            continue
        if (source_type, source_id) in old_refs:
            continue  # Preserve a historical link even if its source was deleted.
        model = Habit if source_type == "habit" else Todo
        if (
            db.query(model.id)
            .filter(model.id == source_id, model.user_id == user_id)
            .first()
            is None
        ):
            raise HTTPException(status_code=400, detail="Source action not found")
