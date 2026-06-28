import datetime
from sqlalchemy.orm import Session
from src.database.models import (
    User,
    Habit,
    HabitLog,
    PerfectDayTemplate,
    DailyScore,
    Streak,
    Todo,
    SubStep,
)

ALL_6_STATS = [
    "forme_physique",
    "sante",
    "social",
    "finance",
    "apprendre",
    "discipline",
]

DEFAULT_THRESHOLDS = {
    "week": {"discipline": 11, "apprendre": 6},
    "weekend": {"sante": 8, "social": 4, "apprendre": 3},
    "recup": {"sante": 8},
    "malade": {"sante": 3},
}


def calculate_daily_score(
    db: Session, user_id: int, date: datetime.date, template_name: str = None
) -> DailyScore:
    """
    Evaluates the daily score for a user on a given date.
    A Perfect Day is achieved if all active, scheduled habits for that day are logged (completed or skipped).
    We also sum the counts of tags validated today.
    """
    # 1. Resolve template name (always default/week for backward compatibility)
    if not template_name:
        existing_score = (
            db.query(DailyScore).filter_by(user_id=user_id, date=date).first()
        )
        if existing_score:
            template_name = existing_score.template_used
        else:
            template_name = "default"

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

    # 3. Get all active habits for the user
    habits = db.query(Habit).filter_by(user_id=user_id, is_active=True).all()

    # 4. Check if all scheduled habits are completed/skipped today
    weekday = date.weekday()
    model_day_idx = (weekday + 1) % 7 # 0=Sun, 1=Mon, ..., 6=Sat

    scheduled_habits = []
    for h in habits:
        scheduled = str(model_day_idx) in [d.strip() for d in h.scheduled_days.split(",")]
        if scheduled:
            scheduled_habits.append(h)

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

    # 5. Populate actual_stats with tag counts
    actual_stats = {stat: 0 for stat in ALL_6_STATS}

    # Count tags from completed habit logs
    for log in logs:
        if log.log_type in ["done", "log"]:
            habit = db.query(Habit).filter_by(id=log.habit_id, user_id=user_id).first()
            if habit:
                tags = []
                if isinstance(habit.point_rewards, list):
                    tags = habit.point_rewards
                elif isinstance(habit.point_rewards, dict):
                    tags = list(habit.point_rewards.keys())
                
                for tag in tags:
                    tag_key = tag.lower()
                    actual_stats[tag_key] = actual_stats.get(tag_key, 0) + 1

    # Count tags from completed Todos today
    completed_todos = (
        db.query(Todo)
        .filter(
            Todo.user_id == user_id,
            Todo.is_completed == True,
            Todo.completed_at >= start_dt,
            Todo.completed_at <= end_dt,
        )
        .all()
    )

    for todo in completed_todos:
        for t_tag in [todo.stat_reward_1, todo.stat_reward_2]:
            if t_tag:
                tag_key = t_tag.lower()
                actual_stats[tag_key] = actual_stats.get(tag_key, 0) + 1

    # Count tags from completed SubSteps today
    completed_substeps = (
        db.query(SubStep)
        .filter(
            SubStep.user_id == user_id,
            SubStep.completed == True,
            SubStep.completed_at >= start_dt,
            SubStep.completed_at <= end_dt,
        )
        .all()
    )

    for substep in completed_substeps:
        substep_tags = []
        if isinstance(substep.stats_json, list):
            substep_tags = substep.stats_json
        elif isinstance(substep.stats_json, dict):
            substep_tags = list(substep.stats_json.keys())
        
        for s_tag in substep_tags:
            if s_tag:
                tag_key = s_tag.lower()
                actual_stats[tag_key] = actual_stats.get(tag_key, 0) + 1

    # 6. Save or update DailyScore
    score = db.query(DailyScore).filter_by(user_id=user_id, date=date).first()
    if not score:
        score = DailyScore(
            user_id=user_id,
            date=date,
            status=status,
            template_used=template_name,
            actual_stats=actual_stats,
        )
        db.add(score)
    else:
        score.status = status
        score.template_used = template_name
        score.actual_stats = actual_stats

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

    # 2. Update Individual Habit Streaks
    weekday = date.weekday()
    model_day_idx = (weekday + 1) % 7

    habits = db.query(Habit).filter_by(user_id=user_id, is_active=True).all()
    for habit in habits:
        scheduled = str(model_day_idx) in [
            day.strip() for day in habit.scheduled_days.split(",")
        ]
        if not scheduled:
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
            t_weekday = test_date.weekday()
            t_model_day_idx = (t_weekday + 1) % 7
            if str(t_model_day_idx) in [
                day.strip() for day in habit.scheduled_days.split(",")
            ]:
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
