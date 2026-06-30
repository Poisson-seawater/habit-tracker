import datetime
from sqlalchemy.orm import Session
from src.database.models import (
    User,
    Habit,
    HabitLog,
    DailyScore,
    Streak,
    Todo,
)
from src.services.agenda_service import is_habit_eligible_on_date


def calculate_daily_score(
    db: Session, user_id: int, date: datetime.date, template_name: str = None
) -> DailyScore:
    """
    Evaluates the daily score for a user on a given date.
    A Perfect Day is achieved if all active, scheduled habits for that day are logged (completed or skipped).
    """
    # 1. Resolve template name.
    if not template_name:
        existing_score = (
            db.query(DailyScore).filter_by(user_id=user_id, date=date).first()
        )
        if existing_score:
            template_name = existing_score.template_used
        else:
            template_name = "regular"

    if template_name == "default":
        template_name = "regular"

    # 2. Get today's logs
    start_dt = datetime.datetime.combine(date, datetime.time.min)
    end_dt = datetime.datetime.combine(date, datetime.time.max)

    logs = (
        db.query(HabitLog)
        .filter(
            HabitLog.user_id == user_id,
            HabitLog.timestamp >= start_dt,
            HabitLog.timestamp <= end_dt,
        )
        .all()
    )

    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        return None

    # 3. Get all active habits for the user
    habits = (
        db.query(Habit)
        .filter(
            Habit.user_id == user_id,
            Habit.is_active == True,
            Habit.archived_at == None,
        )
        .all()
    )

    # 4. Check if all scheduled habits are completed/skipped today
    scheduled_habits = [h for h in habits if is_habit_eligible_on_date(h, date, user)]

    # Group logs by habit
    logs_by_habit = {}
    for log in logs:
        logs_by_habit.setdefault(log.habit_id, []).append(log)

    perfect_valid = True
    for h in scheduled_habits:
        h_logs = logs_by_habit.get(h.id, [])
        is_skipped = any(l.log_type == "skip" for l in h_logs)
        if is_skipped:
            continue

        completions = sum(1 for l in h_logs if l.log_type in ["done", "log"])
        if h.daily_target and h.daily_target > 1:
            if completions < h.daily_target:
                perfect_valid = False
                break
        else:
            if completions < 1:
                perfect_valid = False
                break

    # If there are no scheduled habits, perfect_valid remains True

    status = "Perfect" if perfect_valid else "Failed"

    # 5. Save or update DailyScore
    score = db.query(DailyScore).filter_by(user_id=user_id, date=date).first()
    if not score:
        score = DailyScore(
            user_id=user_id,
            date=date,
            status=status,
            template_used=template_name,
        )
        db.add(score)
    else:
        score.status = status
        score.template_used = template_name

    db.commit()
    return score


def update_streaks(db: Session, user_id: int, date: datetime.date):
    """
    Updates perfect day streaks and individual habit streaks.
    """
    score = db.query(DailyScore).filter_by(user_id=user_id, date=date).first()
    if not score:
        return

    yesterday = date - datetime.timedelta(days=1)

    # 1. Update Perfect Day Streak
    perf_streak = (
        db.query(Streak).filter_by(user_id=user_id, streak_type="Perfect").first()
    )
    if not perf_streak:
        perf_streak = Streak(
            user_id=user_id, streak_type="Perfect", current_streak=0, max_streak=0
        )
        db.add(perf_streak)

    if perf_streak.last_incremented != date:
        if score.status == "Perfect":
            if perf_streak.last_incremented == yesterday:
                perf_streak.current_streak += 1
            else:
                perf_streak.current_streak = 1
            perf_streak.max_streak = max(
                perf_streak.max_streak, perf_streak.current_streak
            )
            perf_streak.last_incremented = date
        else:
            if (
                perf_streak.last_incremented == yesterday
                or perf_streak.last_incremented is None
            ):
                perf_streak.current_streak = 0

    habits = (
        db.query(Habit)
        .filter(
            Habit.user_id == user_id,
            Habit.is_active == True,
            Habit.archived_at == None,
        )
        .all()
    )
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        db.commit()
        return

    for habit in habits:
        if not is_habit_eligible_on_date(habit, date, user):
            continue

        start_dt = datetime.datetime.combine(date, datetime.time.min)
        end_dt = datetime.datetime.combine(date, datetime.time.max)

        habit_logs = (
            db.query(HabitLog)
            .filter(
                HabitLog.user_id == user_id,
                HabitLog.habit_id == habit.id,
                HabitLog.timestamp >= start_dt,
                HabitLog.timestamp <= end_dt,
            )
            .all()
        )

        is_done = any(l.log_type in ["done", "log"] for l in habit_logs)
        is_skipped = any(l.log_type == "skip" for l in habit_logs)

        h_streak = (
            db.query(Streak)
            .filter_by(user_id=user_id, streak_type=f"habit:{habit.id}")
            .first()
        )
        if not h_streak:
            h_streak = Streak(
                user_id=user_id,
                streak_type=f"habit:{habit.id}",
                current_streak=0,
                max_streak=0,
            )
            db.add(h_streak)

        # Find the most recent scheduled day before today
        test_date = date - datetime.timedelta(days=1)
        limit_date = (
            habit.created_at.date()
            if habit.created_at
            else (date - datetime.timedelta(days=365))
        )
        last_scheduled_date = None
        while test_date >= limit_date:
            if is_habit_eligible_on_date(habit, test_date, user):
                last_scheduled_date = test_date
                break
            test_date -= datetime.timedelta(days=1)

        if h_streak.last_incremented != date:
            if is_done:
                if (
                    h_streak.last_incremented == last_scheduled_date
                    or h_streak.last_incremented is None
                ):
                    h_streak.current_streak += 1
                else:
                    h_streak.current_streak = 1
                h_streak.max_streak = max(h_streak.max_streak, h_streak.current_streak)
                h_streak.last_incremented = date

                # Award milestone rewards
                user = db.query(User).filter_by(id=user_id).first()
                if h_streak.current_streak == 30:
                    user.gold += 50
                    add_user_xp(user, 100)
                elif h_streak.current_streak == 90:
                    user.gold += 150
                    add_user_xp(user, 300)
            elif is_skipped:
                h_streak.last_incremented = date
            else:
                if (
                    h_streak.last_incremented == last_scheduled_date
                    or h_streak.last_incremented is None
                ):
                    h_streak.current_streak = 0

    db.commit()


def add_user_xp(user: User, xp_gained: int) -> list:
    """
    Adds permanent XP to a user and handles exponential level-up.
    Level up formula: XP_needed(L -> L+1) = 10 * 2^(L-1)
    Returns a list of levels reached (e.g. [2] or [2, 3] or []).
    """
    levels_gained = []
    user.xp += xp_gained

    while True:
        # Exponential curve: 10 * (2 ** (level - 1))
        xp_needed = 10 * (2 ** (user.level - 1))
        if user.xp >= xp_needed:
            user.xp -= xp_needed
            user.level += 1
            levels_gained.append(user.level)
        else:
            break

    return levels_gained


def cleanup_completed_todos(db: Session, user_id: int):
    """
    Deletes completed todos that were completed before today (in local timezone).
    This preserves completed todos for today's daily score calculations and status recaps,
    but deletes them once the day is over.
    """
    today_start = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
    db.query(Todo).filter(
        Todo.user_id == user_id,
        Todo.is_completed == True,
        Todo.completed_at < today_start,
    ).delete(synchronize_session=False)
    db.commit()
