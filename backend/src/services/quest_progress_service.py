import datetime
import re
import threading
import uuid
from contextlib import contextmanager
from typing import Any, Iterable, Optional

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from src.database.models import Habit, HabitDailyProgress, HabitLog


VALID_PROGRESS_MODES = {"standard", "free_counter", "checklist"}
MAX_COUNTER_VALUE = 9_007_199_254_740_991
CHECKLIST_ITEM_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
MAX_CHECKLIST_ITEMS = 50
MAX_CHECKLIST_LABEL_LENGTH = 200
MAX_UNIT_LENGTH = 64
_PROGRESS_LOCKS = tuple(threading.RLock() for _ in range(64))


class QuestProgressError(ValueError):
    pass


class QuestProgressConflict(QuestProgressError):
    pass


def progress_mode(habit: Habit) -> str:
    value = (habit.progress_mode or "standard").strip()
    return value if value in VALID_PROGRESS_MODES else "standard"


def is_enriched(habit: Habit) -> bool:
    return progress_mode(habit) != "standard"


def is_enriched_on_date(habit: Habit, date_value: datetime.date) -> bool:
    return progress_config_for_date(habit, date_value)["mode"] != "standard"


def completion_log_types(habit: Habit) -> set[str]:
    # Counters and checklist checks are intentionally auxiliary. Only the explicit
    # quest completion action can satisfy scoring/streak/agenda completion.
    return {"done"} if is_enriched(habit) else {"done", "log"}


def progress_config_for_date(habit: Habit, date_value: datetime.date) -> dict:
    fallback = {
        "effective_from": (
            habit.created_at.date().isoformat()
            if habit.created_at is not None
            else date_value.isoformat()
        ),
        "mode": progress_mode(habit),
        "type": habit.type,
        "unit": habit.unit,
        "daily_target": max(habit.daily_target or 1, 1),
        "checklist_items": normalized_checklist_items(habit.checklist_items),
    }
    candidates = []
    for raw_entry in habit.progress_config_history or []:
        if not isinstance(raw_entry, dict):
            continue
        try:
            effective_from = datetime.date.fromisoformat(
                str(raw_entry.get("effective_from"))
            )
        except (TypeError, ValueError):
            continue
        if effective_from <= date_value:
            candidates.append((effective_from, raw_entry))
    if not candidates:
        return fallback
    _effective_from, entry = max(candidates, key=lambda candidate: candidate[0])
    mode = str(entry.get("mode") or "standard")
    if mode not in VALID_PROGRESS_MODES:
        mode = "standard"
    return {
        "effective_from": _effective_from.isoformat(),
        "mode": mode,
        "type": entry.get("type") or ("binary" if mode != "standard" else habit.type),
        "unit": entry.get("unit"),
        "daily_target": max(int(entry.get("daily_target") or 1), 1),
        "checklist_items": normalized_checklist_items(
            entry.get("checklist_items") or []
        ),
    }


def progress_config_history_after_update(
    habit: Habit, *, config: dict, effective_from: datetime.date
) -> list[dict]:
    history = [
        dict(entry)
        for entry in (habit.progress_config_history or [])
        if isinstance(entry, dict)
    ]
    if not history:
        created_on = habit.created_at.date() if habit.created_at else effective_from
        history.append(
            {
                "effective_from": created_on.isoformat(),
                "mode": progress_mode(habit),
                "type": habit.type,
                "unit": habit.unit,
                "daily_target": max(habit.daily_target or 1, 1),
                "checklist_items": normalized_checklist_items(habit.checklist_items),
            }
        )
    history = [
        entry
        for entry in history
        if str(entry.get("effective_from")) != effective_from.isoformat()
    ]
    history.append(progress_config_entry(config, effective_from))
    return sorted(history, key=lambda entry: str(entry.get("effective_from") or ""))


def progress_config_entry(config: dict, effective_from: datetime.date) -> dict:
    return {
        "effective_from": effective_from.isoformat(),
        "mode": config["progress_mode"],
        "type": config["type"],
        "unit": config["unit"],
        "daily_target": max(config["daily_target"] or 1, 1),
        "checklist_items": [dict(item) for item in config["checklist_items"]],
    }


def completion_target(habit: Habit, date_value: datetime.date) -> int:
    return progress_config_for_date(habit, date_value)["daily_target"]


def completion_count(habit: Habit, logs: Iterable[HabitLog]) -> int:
    logs = [log for log in logs if log.cancelled_at is None]
    count = 0
    for log in logs:
        date_value = (
            log.timestamp.date() if log.timestamp is not None else datetime.date.today()
        )
        config = progress_config_for_date(habit, date_value)
        accepted_types = {"done"} if config["mode"] != "standard" else {"done", "log"}
        if log.log_type in accepted_types:
            count += 1
    return count


def _progress_lock(user_id: int, habit_id: int, date_value: datetime.date):
    key = hash((user_id, habit_id, date_value.toordinal()))
    return _PROGRESS_LOCKS[key % len(_PROGRESS_LOCKS)]


@contextmanager
def progress_write_lock(user_id: int, habit_id: int, date_value: datetime.date):
    """Serialize one daily aggregate through the caller's database commit."""
    with _progress_lock(user_id, habit_id, date_value):
        yield


def normalized_checklist_items(value: Any) -> list[dict]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise QuestProgressError("checklist_items must be a list.")
    if len(value) > MAX_CHECKLIST_ITEMS:
        raise QuestProgressError(
            f"A checklist may contain at most {MAX_CHECKLIST_ITEMS} items."
        )

    result = []
    seen_ids = set()
    for raw_item in value:
        if not isinstance(raw_item, dict):
            raise QuestProgressError("Each checklist item must be an object.")
        label = str(raw_item.get("label") or "").strip()
        if not label:
            raise QuestProgressError("Each checklist item requires a label.")
        if len(label) > MAX_CHECKLIST_LABEL_LENGTH:
            raise QuestProgressError(
                "Checklist item labels must be at most "
                f"{MAX_CHECKLIST_LABEL_LENGTH} characters."
            )
        item_id = str(raw_item.get("id") or uuid.uuid4().hex).strip()
        if not item_id:
            item_id = uuid.uuid4().hex
        if not CHECKLIST_ITEM_ID_PATTERN.fullmatch(item_id):
            raise QuestProgressError(
                "Checklist item IDs may only contain letters, numbers, '_' or '-' "
                "and must be at most 64 characters."
            )
        if item_id in seen_ids:
            raise QuestProgressError("Checklist item IDs must be unique.")
        seen_ids.add(item_id)
        result.append({"id": item_id, "label": label, "position": len(result)})
    return result


def validate_and_normalize_config(
    *,
    mode: Optional[str],
    habit_type: Optional[str],
    unit: Optional[str],
    daily_target: Optional[int],
    daily_cap: Optional[int],
    checklist_items: Any,
) -> dict:
    normalized_mode = (mode or "standard").strip()
    if normalized_mode not in VALID_PROGRESS_MODES:
        accepted = ", ".join(sorted(VALID_PROGRESS_MODES))
        raise QuestProgressError(f"Invalid progress_mode. Valid values: {accepted}.")

    normalized_items = normalized_checklist_items(checklist_items)
    normalized_unit = unit.strip() if isinstance(unit, str) else unit
    if normalized_unit == "":
        normalized_unit = None
    if normalized_unit and len(normalized_unit) > MAX_UNIT_LENGTH:
        raise QuestProgressError(f"Units must be at most {MAX_UNIT_LENGTH} characters.")

    if normalized_mode != "standard":
        habit_type = "binary"
        daily_target = None
        daily_cap = None
    if normalized_mode == "free_counter":
        if not normalized_unit:
            raise QuestProgressError("A free_counter habit requires a unit.")
        if normalized_items:
            raise QuestProgressError("free_counter cannot include checklist_items.")
        normalized_items = []
    elif normalized_mode == "checklist":
        if not normalized_items:
            raise QuestProgressError("A checklist habit requires checklist_items.")
        normalized_unit = None
    else:
        if normalized_items:
            raise QuestProgressError(
                "standard progress cannot include checklist_items."
            )
        normalized_items = []

    return {
        "progress_mode": normalized_mode,
        "type": habit_type,
        "unit": normalized_unit,
        "daily_target": daily_target,
        "daily_cap": daily_cap,
        "checklist_items": normalized_items,
    }


def _checklist_snapshot(habit: Habit, items: Any = None) -> list[dict]:
    configured_items = habit.checklist_items if items is None else items
    return [
        {
            "id": item["id"],
            "label": item["label"],
            "position": position,
            "checked": False,
        }
        for position, item in enumerate(normalized_checklist_items(configured_items))
    ]


def get_progress_row(
    db: Session, *, user_id: int, habit_id: int, date_value: datetime.date
) -> HabitDailyProgress | None:
    return (
        db.query(HabitDailyProgress)
        .filter_by(user_id=user_id, habit_id=habit_id, date=date_value)
        .first()
    )


def _create_progress_row(
    db: Session, *, user_id: int, habit: Habit, date_value: datetime.date
) -> HabitDailyProgress:
    config = progress_config_for_date(habit, date_value)
    mode = config["mode"]
    if mode == "standard":
        raise QuestProgressConflict("Standard habits do not use auxiliary progress.")
    now = datetime.datetime.now()
    statement = (
        sqlite_insert(HabitDailyProgress)
        .values(
            user_id=user_id,
            habit_id=habit.id,
            date=date_value,
            mode_snapshot=mode,
            unit_snapshot=config["unit"] if mode == "free_counter" else None,
            counter_value=0,
            checklist_state=(
                _checklist_snapshot(habit, config["checklist_items"])
                if mode == "checklist"
                else None
            ),
            created_at=now,
            updated_at=now,
        )
        .on_conflict_do_nothing(index_elements=["user_id", "habit_id", "date"])
    )
    db.execute(statement)
    db.flush()
    row = get_progress_row(
        db, user_id=user_id, habit_id=habit.id, date_value=date_value
    )
    if row is None:
        raise QuestProgressConflict("Unable to initialize daily progress.")
    return row


def daily_progress_is_locked(
    db: Session, *, user_id: int, habit_id: int, date_value: datetime.date
) -> bool:
    start = datetime.datetime.combine(date_value, datetime.time.min)
    end = datetime.datetime.combine(date_value, datetime.time.max)
    return (
        db.query(HabitLog.id)
        .filter(
            HabitLog.user_id == user_id,
            HabitLog.habit_id == habit_id,
            HabitLog.timestamp >= start,
            HabitLog.timestamp <= end,
            HabitLog.cancelled_at == None,
            HabitLog.log_type.in_(["skip", "failed"]),
        )
        .first()
        is not None
    )


def ensure_progress_row(
    db: Session, *, user_id: int, habit: Habit, date_value: datetime.date
) -> HabitDailyProgress:
    with _progress_lock(user_id, habit.id, date_value):
        row = get_progress_row(
            db, user_id=user_id, habit_id=habit.id, date_value=date_value
        )
        return row or _create_progress_row(
            db, user_id=user_id, habit=habit, date_value=date_value
        )


def progress_payload(
    habit: Habit,
    date_value: datetime.date,
    row: HabitDailyProgress | None = None,
) -> dict | None:
    config = progress_config_for_date(habit, date_value)
    mode = row.mode_snapshot if row else config["mode"]
    if mode == "standard" and row is None:
        if progress_mode(habit) == "standard":
            return None
        return {
            "date": date_value.isoformat(),
            "mode": "standard",
            "counter_value": 0,
            "unit": None,
            "checklist_items": [],
        }
    checklist_state = row.checklist_state if row else None
    if mode == "checklist" and checklist_state is None:
        checklist_state = _checklist_snapshot(habit, config["checklist_items"])
    return {
        "date": date_value.isoformat(),
        "mode": mode,
        "counter_value": int(row.counter_value or 0) if row else 0,
        "unit": (
            row.unit_snapshot
            if row
            else (config["unit"] if mode == "free_counter" else None)
        ),
        "checklist_items": list(checklist_state or []),
    }


def progress_payload_for_date(
    db: Session, *, user_id: int, habit: Habit, date_value: datetime.date
) -> dict | None:
    row = get_progress_row(
        db, user_id=user_id, habit_id=habit.id, date_value=date_value
    )
    return progress_payload(habit, date_value, row)


def progress_rows_by_habit(
    db: Session,
    *,
    user_id: int,
    habit_ids: Iterable[int],
    date_value: datetime.date,
) -> dict[int, HabitDailyProgress]:
    ids = list(habit_ids)
    if not ids:
        return {}
    rows = (
        db.query(HabitDailyProgress)
        .filter(
            HabitDailyProgress.user_id == user_id,
            HabitDailyProgress.habit_id.in_(ids),
            HabitDailyProgress.date == date_value,
        )
        .all()
    )
    return {row.habit_id: row for row in rows}


def set_counter_value(
    db: Session,
    *,
    user_id: int,
    habit: Habit,
    date_value: datetime.date,
    value: int,
) -> HabitDailyProgress:
    if value < 0:
        raise QuestProgressError("Counter value must be positive or zero.")
    if value > MAX_COUNTER_VALUE:
        raise QuestProgressError("Counter value exceeds the storage limit.")
    with _progress_lock(user_id, habit.id, date_value):
        row = get_progress_row(
            db, user_id=user_id, habit_id=habit.id, date_value=date_value
        )
        if row is None:
            if progress_config_for_date(habit, date_value)["mode"] != "free_counter":
                raise QuestProgressConflict(
                    "This habit does not use free_counter progress."
                )
            row = _create_progress_row(
                db, user_id=user_id, habit=habit, date_value=date_value
            )
        if row.mode_snapshot != "free_counter":
            raise QuestProgressConflict("The daily snapshot is not a free counter.")
        row.counter_value = value
        row.updated_at = datetime.datetime.now()
        db.flush()
        return row


def set_checklist_item_checked(
    db: Session,
    *,
    user_id: int,
    habit: Habit,
    date_value: datetime.date,
    item_id: str,
    checked: bool,
) -> HabitDailyProgress:
    with _progress_lock(user_id, habit.id, date_value):
        row = get_progress_row(
            db, user_id=user_id, habit_id=habit.id, date_value=date_value
        )
        if row is None:
            if progress_config_for_date(habit, date_value)["mode"] != "checklist":
                raise QuestProgressConflict(
                    "This habit does not use checklist progress."
                )
            row = _create_progress_row(
                db, user_id=user_id, habit=habit, date_value=date_value
            )
        if row.mode_snapshot != "checklist":
            raise QuestProgressConflict("The daily snapshot is not a checklist.")

        state = [dict(item) for item in (row.checklist_state or [])]
        matched = False
        for item in state:
            if str(item.get("id")) == str(item_id):
                item["checked"] = bool(checked)
                matched = True
                break
        if not matched:
            raise QuestProgressError("Checklist item not found in the daily snapshot.")
        row.checklist_state = state
        row.updated_at = datetime.datetime.now()
        db.flush()
        return row


def reconcile_today_snapshot(
    db: Session, *, user_id: int, habit: Habit, today: datetime.date | None = None
) -> HabitDailyProgress | None:
    today = today or datetime.date.today()
    row = get_progress_row(db, user_id=user_id, habit_id=habit.id, date_value=today)
    if not row:
        return None

    mode = progress_mode(habit)
    if mode == "standard":
        db.delete(row)
        db.flush()
        return None
    row.mode_snapshot = mode
    row.unit_snapshot = habit.unit if mode == "free_counter" else None
    if mode == "checklist":
        previous = {
            str(item.get("id")): bool(item.get("checked"))
            for item in (row.checklist_state or [])
        }
        state = _checklist_snapshot(habit)
        for item in state:
            item["checked"] = previous.get(str(item["id"]), False)
        row.checklist_state = state
        row.counter_value = 0
    elif mode == "free_counter":
        row.checklist_state = None
    row.updated_at = datetime.datetime.now()
    db.flush()
    return row
