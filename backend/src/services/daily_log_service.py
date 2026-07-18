import datetime
from collections import defaultdict

from sqlalchemy.orm import Session

from src.database.models import DailyScore, Habit, HabitLog, Streak, User
from src.services.agenda_service import is_habit_eligible_on_date, resolve_day_type
from src.services.score_service import (
    add_user_xp,
    calculate_daily_score,
    deduct_user_xp,
    update_streaks,
)

HABIT_FAILURE_XP_PENALTY = 5


class DailyLogError(ValueError):
    pass


class DailyLogConflict(DailyLogError):
    pass


def resolve_target_date(
    target_date: datetime.date | None, *, today: datetime.date | None = None
) -> datetime.date:
    today = today or datetime.date.today()
    resolved = target_date or today
    if resolved not in {today, today - datetime.timedelta(days=1)}:
        raise DailyLogError("Only today or yesterday can be corrected.")
    return resolved


def timestamp_on_date(
    date_value: datetime.date, *, now: datetime.datetime | None = None
) -> datetime.datetime:
    now = now or datetime.datetime.now()
    return datetime.datetime.combine(date_value, now.time())


def _logs_for_date(
    db: Session, *, user_id: int, habit_id: int, date_value: datetime.date
) -> list[HabitLog]:
    start_dt = datetime.datetime.combine(date_value, datetime.time.min)
    end_dt = datetime.datetime.combine(date_value, datetime.time.max)
    return (
        db.query(HabitLog)
        .filter(
            HabitLog.user_id == user_id,
            HabitLog.habit_id == habit_id,
            HabitLog.timestamp >= start_dt,
            HabitLog.timestamp <= end_dt,
        )
        .all()
    )


def active_habit_failure(
    db: Session, *, user_id: int, habit_id: int, date_value: datetime.date
) -> HabitLog | None:
    return next(
        (
            log
            for log in _logs_for_date(
                db, user_id=user_id, habit_id=habit_id, date_value=date_value
            )
            if log.log_type == "failed" and log.cancelled_at is None
        ),
        None,
    )


def habit_target_completed(habit: Habit, logs: list[HabitLog]) -> bool:
    target = habit.daily_target if habit.daily_target and habit.daily_target > 1 else 1
    completions = sum(
        1
        for log in logs
        if log.log_type in {"done", "log"} and log.cancelled_at is None
    )
    return completions >= target


def create_habit_log(
    db: Session,
    *,
    user_id: int,
    habit: Habit,
    log_type: str,
    date_value: datetime.date,
    amount: int | None = None,
    reason: str | None = None,
) -> tuple[HabitLog, bool]:
    logs = _logs_for_date(db, user_id=user_id, habit_id=habit.id, date_value=date_value)
    if any(log.log_type == "failed" and log.cancelled_at is None for log in logs):
        raise DailyLogConflict("Undo the habit failure before logging progress.")

    has_target = habit.daily_target is not None and habit.daily_target > 1
    if habit.type == "binary" and log_type == "done" and not has_target:
        existing = next(
            (
                log
                for log in logs
                if log.log_type == "done" and log.cancelled_at is None
            ),
            None,
        )
        if existing:
            return existing, False

    log = HabitLog(
        user_id=user_id,
        habit_id=habit.id,
        log_type=log_type,
        amount=amount,
        unit=habit.unit if habit.type == "quantitative" else None,
        reason=reason,
        timestamp=timestamp_on_date(date_value),
    )
    db.add(log)
    db.flush()
    return log, True


def mark_habit_failed(
    db: Session, *, user_id: int, habit: Habit, date_value: datetime.date
) -> tuple[HabitLog, bool]:
    logs = _logs_for_date(db, user_id=user_id, habit_id=habit.id, date_value=date_value)
    existing = next(
        (log for log in logs if log.log_type == "failed" and log.cancelled_at is None),
        None,
    )
    if existing:
        return existing, False
    if habit_target_completed(habit, logs):
        raise DailyLogConflict("A completed habit cannot be marked as failed.")
    if any(log.log_type == "skip" and log.cancelled_at is None for log in logs):
        raise DailyLogConflict("A skipped habit cannot be marked as failed.")

    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise DailyLogConflict("User not found.")
    available_xp = user.xp + 10 * ((2 ** (user.level - 1)) - 1)
    xp_penalty = min(HABIT_FAILURE_XP_PENALTY, available_xp)

    log = HabitLog(
        user_id=user_id,
        habit_id=habit.id,
        log_type="failed",
        timestamp=timestamp_on_date(date_value),
        xp_penalty=xp_penalty,
    )
    db.add(log)
    deduct_user_xp(user, xp_penalty)
    db.flush()
    return log, True


def cancel_habit_failure(
    db: Session, *, user_id: int, habit: Habit, date_value: datetime.date
) -> tuple[HabitLog | None, bool]:
    failure = active_habit_failure(
        db, user_id=user_id, habit_id=habit.id, date_value=date_value
    )
    if not failure:
        return None, False
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise DailyLogConflict("User not found.")
    if failure.xp_penalty:
        add_user_xp(user, failure.xp_penalty)
    failure.cancelled_at = datetime.datetime.now()
    db.flush()
    return failure, True


def _award_new_habit_milestone(
    user: User, habit: Habit, old_max: int, current_streak: int
) -> dict | None:
    rewards = {30: (50, 100), 90: (150, 300), 180: (200, 500)}
    milestone = next(
        (value for value in sorted(rewards) if old_max < value <= current_streak),
        None,
    )
    if milestone is None:
        return None
    gold, xp = rewards[milestone]
    user.gold += gold
    add_user_xp(user, xp)
    if not user.chat_id:
        return None
    return {
        "chat_id": user.chat_id,
        "habit_id": habit.id,
        "habit_name": habit.name,
        "milestone": milestone,
    }


def rebuild_streak_projections(
    db: Session,
    *,
    user_id: int,
    through_date: datetime.date,
    finalizing: bool = False,
) -> list[dict]:
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        return []

    start_date = user.created_at.date() if user.created_at else through_date
    scores = (
        db.query(DailyScore)
        .filter(
            DailyScore.user_id == user_id,
            DailyScore.date >= start_date,
            DailyScore.date <= through_date,
        )
        .all()
    )
    scores_by_date = {score.date: score for score in scores}
    perfect_current = 0
    perfect_max = 0
    perfect_last = None
    cursor = start_date
    while cursor <= through_date:
        score = scores_by_date.get(cursor)
        if score and score.status == "Perfect":
            perfect_current += 1
            perfect_max = max(perfect_max, perfect_current)
            perfect_last = cursor
        elif finalizing or cursor < through_date:
            perfect_current = 0
        cursor += datetime.timedelta(days=1)

    perfect_streak = (
        db.query(Streak).filter_by(user_id=user_id, streak_type="Perfect").first()
    )
    if not perfect_streak:
        perfect_streak = Streak(user_id=user_id, streak_type="Perfect")
        db.add(perfect_streak)
    perfect_streak.current_streak = perfect_current
    perfect_streak.max_streak = max(perfect_streak.max_streak or 0, perfect_max)
    perfect_streak.last_incremented = perfect_last

    habits = (
        db.query(Habit)
        .filter(
            Habit.user_id == user_id,
            Habit.is_active == True,
            Habit.archived_at == None,
        )
        .all()
    )
    all_logs = (
        db.query(HabitLog)
        .filter(
            HabitLog.user_id == user_id,
            HabitLog.timestamp
            <= datetime.datetime.combine(through_date, datetime.time.max),
        )
        .all()
    )
    logs_by_habit_date = defaultdict(list)
    for log in all_logs:
        logs_by_habit_date[(log.habit_id, log.timestamp.date())].append(log)

    milestone_events = []
    day_types_by_date = {}
    for habit in habits:
        habit_start = max(
            start_date,
            habit.created_at.date() if habit.created_at else start_date,
        )
        current = 0
        computed_max = 0
        last_progress = None
        cursor = habit_start
        while cursor <= through_date:
            logs = logs_by_habit_date.get((habit.id, cursor), [])
            active_failed = any(
                log.log_type == "failed" and log.cancelled_at is None for log in logs
            )
            cancelled_failed = any(
                log.log_type == "failed" and log.cancelled_at is not None
                for log in logs
            )
            skipped = any(
                log.log_type == "skip" and log.cancelled_at is None for log in logs
            )
            completed = habit_target_completed(habit, logs)
            if cursor not in day_types_by_date:
                day_types_by_date[cursor] = resolve_day_type(db, user_id, cursor)
            is_required = is_habit_eligible_on_date(
                habit,
                cursor,
                user,
                day_types_by_date[cursor],
            )
            if not is_required and not completed:
                cursor += datetime.timedelta(days=1)
                continue

            if active_failed or (
                cancelled_failed and cursor == through_date and not finalizing
            ):
                current = 0
            elif completed:
                current += 1
                computed_max = max(computed_max, current)
                last_progress = cursor
            elif skipped:
                last_progress = cursor
            elif finalizing or cursor < through_date:
                current = 0
            cursor += datetime.timedelta(days=1)

        streak = (
            db.query(Streak)
            .filter_by(user_id=user_id, streak_type=f"habit:{habit.id}")
            .first()
        )
        if not streak:
            streak = Streak(user_id=user_id, streak_type=f"habit:{habit.id}")
            db.add(streak)
        old_max = streak.max_streak or 0
        streak.current_streak = current
        streak.max_streak = max(old_max, computed_max)
        streak.last_incremented = last_progress
        event = _award_new_habit_milestone(user, habit, old_max, current)
        if event:
            milestone_events.append(event)

    db.commit()
    return milestone_events


def recalculate_day(
    db: Session,
    *,
    user_id: int,
    date_value: datetime.date,
    finalizing: bool = False,
    force_rebuild: bool = False,
    recalculate_score: bool = True,
) -> tuple[DailyScore | None, list[dict]]:
    score = (
        calculate_daily_score(db, user_id=user_id, date=date_value)
        if recalculate_score
        else db.query(DailyScore).filter_by(user_id=user_id, date=date_value).first()
    )
    today = datetime.date.today()
    if (
        recalculate_score
        and date_value == today
        and not finalizing
        and not force_rebuild
    ):
        return score, update_streaks(db, user_id=user_id, date=date_value)
    replay_through = max(date_value, today)
    milestone_events = rebuild_streak_projections(
        db,
        user_id=user_id,
        through_date=replay_through,
        finalizing=finalizing and replay_through == date_value,
    )
    return score, milestone_events
