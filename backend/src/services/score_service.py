import datetime
from sqlalchemy.orm import Session
from src.database.models import User, Habit, HabitLog, PerfectDayTemplate, DailyScore, Streak, Todo

ALL_6_STATS = [
    "forme_physique", "sante", "social", "finance", "apprendre", "discipline"
]

DEFAULT_THRESHOLDS = {
    "week": {"discipline": 11, "apprendre": 6},
    "weekend": {"sante": 8, "social": 4, "apprendre": 3},
    "recup": {"sante": 8},
    "malade": {"sante": 3}
}

def calculate_daily_score(db: Session, user_id: int, date: datetime.date, template_name: str = None) -> DailyScore:
    """
    Evaluates the daily score for a user on a given date based on their ephemeral daily stats
    (from habits and completed todos) compared against their custom Perfect Day template.
    """
    # 1. Resolve template name
    if not template_name:
        # Check if DailyScore already exists with a template
        existing_score = db.query(DailyScore).filter_by(user_id=user_id, date=date).first()
        if existing_score:
            template_name = existing_score.template_used
        else:
            # Fallback to dynamic weekday/weekend
            weekday = date.isoweekday()  # Mon=1, ..., Sun=7
            template_name = "weekend" if weekday in [6, 7] else "week"
            
    # 2. Get user's custom template thresholds
    custom_template = db.query(PerfectDayTemplate).filter_by(user_id=user_id, template_name=template_name).first()
    if custom_template:
        thresholds = custom_template.thresholds_json
    else:
        thresholds = DEFAULT_THRESHOLDS.get(template_name, {})

    # 3. Sum stats from habits logged on this date
    start_dt = datetime.datetime.combine(date, datetime.time.min)
    end_dt = datetime.datetime.combine(date, datetime.time.max)
    
    logs = db.query(HabitLog).filter(
        HabitLog.user_id == user_id,
        HabitLog.timestamp >= start_dt,
        HabitLog.timestamp <= end_dt
    ).all()

    actual_stats = {stat: 0 for stat in ALL_6_STATS}
    
    # Group logs by habit
    logs_by_habit = {}
    for log in logs:
        if log.log_type in ["done", "log"]:
            logs_by_habit.setdefault(log.habit_id, []).append(log)

    for habit_id, habit_logs in logs_by_habit.items():
        habit = db.query(Habit).filter_by(id=habit_id, user_id=user_id).first()
        if not habit or not habit.is_active:
            continue
            
        habit_stats = {stat: 0 for stat in ALL_6_STATS}
        
        has_target = habit.daily_target is not None and habit.daily_target > 1

        if habit.type == "binary":
            # For binary habits, award points once — unless a daily_target is set,
            # in which case each validation counts (extra reps = extra XP, capped by daily_cap).
            done_count = sum(1 for l in habit_logs if l.log_type == "done")
            if done_count > 0:
                reps = done_count if has_target else 1
                for stat, val in habit.point_rewards.items():
                    stat_key = stat.lower()
                    if stat_key in actual_stats:
                        habit_stats[stat_key] = val * reps
                if has_target and habit.daily_cap is not None:
                    for stat in habit_stats:
                        habit_stats[stat] = min(habit_stats[stat], habit.daily_cap)

        elif habit.type == "quantitative":
            # For quantitative habits, sum and apply daily cap
            for log in habit_logs:
                if log.log_type == "log":
                    for stat, val in habit.point_rewards.items():
                        stat_key = stat.lower()
                        if stat_key in actual_stats:
                            habit_stats[stat_key] += val
                            
            if habit.daily_cap is not None:
                for stat in habit_stats:
                    habit_stats[stat] = min(habit_stats[stat], habit.daily_cap)

        for stat, val in habit_stats.items():
            actual_stats[stat] += val

    # 4. Sum stats from Todos completed on this date
    completed_todos = db.query(Todo).filter(
        Todo.user_id == user_id,
        Todo.is_completed == True,
        Todo.completed_at >= start_dt,
        Todo.completed_at <= end_dt
    ).all()
    
    for todo in completed_todos:
        if todo.stat_reward_1 and todo.stat_reward_1.lower() in actual_stats:
            actual_stats[todo.stat_reward_1.lower()] += todo.points_reward_1
        if todo.stat_reward_2 and todo.stat_reward_2.lower() in actual_stats:
            actual_stats[todo.stat_reward_2.lower()] += todo.points_reward_2

    # 5. Evaluate if the Perfect Day thresholds are met
    perfect_valid = True
    if not thresholds:
        perfect_valid = False  # No requirements means it cannot be a Perfect Day by default
    else:
        for stat, target in thresholds.items():
            stat_key = stat.lower()
            if actual_stats.get(stat_key, 0) < target:
                perfect_valid = False
                break

    status = "Perfect" if perfect_valid else "Failed"

    # 6. Save or update DailyScore
    score = db.query(DailyScore).filter_by(user_id=user_id, date=date).first()
    if not score:
        score = DailyScore(
            user_id=user_id,
            date=date,
            status=status,
            template_used=template_name,
            actual_stats=actual_stats
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
    perf_streak = db.query(Streak).filter_by(user_id=user_id, streak_type="Perfect").first()
    if not perf_streak:
        perf_streak = Streak(user_id=user_id, streak_type="Perfect", current_streak=0, max_streak=0)
        db.add(perf_streak)

    if perf_streak.last_incremented != date:
        if score.status == "Perfect":
            if perf_streak.last_incremented == yesterday:
                perf_streak.current_streak += 1
            else:
                perf_streak.current_streak = 1
            perf_streak.max_streak = max(perf_streak.max_streak, perf_streak.current_streak)
            perf_streak.last_incremented = date
        else:
            if perf_streak.last_incremented == yesterday or perf_streak.last_incremented is None:
                perf_streak.current_streak = 0

    # 2. Update Individual Habit Streaks
    weekday = date.weekday()
    model_day_idx = (weekday + 1) % 7
    
    habits = db.query(Habit).filter_by(user_id=user_id, is_active=True).all()
    for habit in habits:
        scheduled = str(model_day_idx) in [day.strip() for day in habit.scheduled_days.split(",")]
        if not scheduled:
            continue

        start_dt = datetime.datetime.combine(date, datetime.time.min)
        end_dt = datetime.datetime.combine(date, datetime.time.max)
        
        habit_logs = db.query(HabitLog).filter(
            HabitLog.user_id == user_id,
            HabitLog.habit_id == habit.id,
            HabitLog.timestamp >= start_dt,
            HabitLog.timestamp <= end_dt
        ).all()

        is_done = any(l.log_type in ["done", "log"] for l in habit_logs)
        is_skipped = any(l.log_type == "skip" for l in habit_logs)

        h_streak = db.query(Streak).filter_by(user_id=user_id, streak_type=f"habit:{habit.id}").first()
        if not h_streak:
            h_streak = Streak(user_id=user_id, streak_type=f"habit:{habit.id}", current_streak=0, max_streak=0)
            db.add(h_streak)

        # Find the most recent scheduled day before today
        test_date = date - datetime.timedelta(days=1)
        limit_date = habit.created_at.date() if habit.created_at else (date - datetime.timedelta(days=365))
        last_scheduled_date = None
        while test_date >= limit_date:
            t_weekday = test_date.weekday()
            t_model_day_idx = (t_weekday + 1) % 7
            if str(t_model_day_idx) in [day.strip() for day in habit.scheduled_days.split(",")]:
                last_scheduled_date = test_date
                break
            test_date -= datetime.timedelta(days=1)

        if h_streak.last_incremented != date:
            if is_done:
                if h_streak.last_incremented == last_scheduled_date or h_streak.last_incremented is None:
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
                if h_streak.last_incremented == last_scheduled_date or h_streak.last_incremented is None:
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
