import datetime

from sqlalchemy.orm import Session

from src.database.models import NoTodo, NoTodoLog


def record_notodo_failure(
    db: Session,
    *,
    user_id: int,
    notodo: NoTodo,
    occurred_at: datetime.datetime | None = None,
) -> NoTodoLog:
    occurred_at = occurred_at or datetime.datetime.now()
    failure_date = occurred_at.date()
    notodo.failed_at = occurred_at

    existing = (
        db.query(NoTodoLog)
        .filter(
            NoTodoLog.user_id == user_id,
            NoTodoLog.notodo_id == notodo.id,
            NoTodoLog.date == failure_date,
        )
        .first()
    )
    if existing:
        existing.timestamp = occurred_at
        existing.title_snapshot = notodo.title
        return existing

    log = NoTodoLog(
        user_id=user_id,
        notodo_id=notodo.id,
        title_snapshot=notodo.title,
        date=failure_date,
        timestamp=occurred_at,
    )
    db.add(log)
    return log


def get_notodo_failures_on_date(
    db: Session, *, user_id: int, date: datetime.date
) -> list[NoTodoLog]:
    logs = (
        db.query(NoTodoLog)
        .filter(NoTodoLog.user_id == user_id, NoTodoLog.date == date)
        .order_by(NoTodoLog.timestamp.asc(), NoTodoLog.id.asc())
        .all()
    )
    logged_notodo_ids = {log.notodo_id for log in logs if log.notodo_id is not None}

    start_dt = datetime.datetime.combine(date, datetime.time.min)
    end_dt = datetime.datetime.combine(date, datetime.time.max)
    legacy_notodos = (
        db.query(NoTodo)
        .filter(
            NoTodo.user_id == user_id,
            NoTodo.failed_at >= start_dt,
            NoTodo.failed_at <= end_dt,
        )
        .order_by(NoTodo.failed_at.asc(), NoTodo.id.asc())
        .all()
    )
    for notodo in legacy_notodos:
        if notodo.id in logged_notodo_ids:
            continue
        logs.append(
            NoTodoLog(
                user_id=notodo.user_id,
                notodo_id=notodo.id,
                title_snapshot=notodo.title,
                date=date,
                timestamp=notodo.failed_at,
            )
        )

    return sorted(logs, key=lambda log: (log.timestamp, log.id or 0))
