import datetime
from sqlalchemy.orm import Session
from src.database.models import User, Habit, HabitLog, DayTemplate, DailyScore, Streak

ALL_12_STATS = [
    "force", "endurance", "mobilite", "discipline", "creativite", 
    "connaissance", "sociabilite", "sante_mentale", "finance", 
    "organisation", "spiritualite", "repos"
]

def calculate_daily_score(db: Session, user_id: int, date: datetime.date, template_id: int = None) -> DailyScore:
    """
    Evaluates the daily score for a user on a given date.
    Calculates points, checks thresholds, and updates the DailyScore record.
    """
    # 1. Determine active template
    if not template_id:
        # Determine default template by day of the week (1=Mon, 7=Sun in isoweekday)
        # In python isoweekday: Mon=1, Tue=2, Wed=3, Thu=4, Fri=5, Sat=6, Sun=7
        weekday = date.isoweekday()
        if weekday in [6, 7]:
            template_id = 2  # Weekend
        else:
            template_id = 1  # Semaine
            
    template = db.query(DayTemplate).filter_by(id=template_id).first()
    if not template:
        # Fallback to Semaine template if not found
        template = db.query(DayTemplate).filter_by(id=1).first()
        if not template:
            # Fallback to an empty template structure if DB is completely unseeded
            template = DayTemplate(id=1, name="Semaine", acceptable_thresholds={}, perfect_thresholds={})

    # 2. Get all logs for the user on this date
    # Start and end timestamps for the date
    start_dt = datetime.datetime.combine(date, datetime.time.min)
    end_dt = datetime.datetime.combine(date, datetime.time.max)
    
    logs = db.query(HabitLog).filter(
        HabitLog.user_id == user_id,
        HabitLog.timestamp >= start_dt,
        HabitLog.timestamp <= end_dt
    ).all()

    # 3. Calculate points per habit with daily caps
    actual_stats = {stat: 0 for stat in ALL_12_STATS}
    
    # Group logs by habit
    logs_by_habit = {}
    for log in logs:
        if log.log_type in ["done", "log"]:
            logs_by_habit.setdefault(log.habit_id, []).append(log)

    for habit_id, habit_logs in logs_by_habit.items():
        habit = db.query(Habit).filter_by(id=habit_id).first()
        if not habit or not habit.is_active:
            continue
            
        habit_stats = {stat: 0 for stat in ALL_12_STATS}
        
        if habit.type == "binary":
            # For binary habits, we only award points once (avoid double-logging)
            has_done = any(l.log_type == "done" for l in habit_logs)
            if has_done:
                for stat, val in habit.point_rewards.items():
                    stat_key = stat.lower()
                    if stat_key in actual_stats:
                        habit_stats[stat_key] = val
                        
        elif habit.type == "quantitative":
            # For quantitative habits, we sum points for each log entry but apply daily cap
            for log in habit_logs:
                if log.log_type == "log":
                    for stat, val in habit.point_rewards.items():
                        stat_key = stat.lower()
                        if stat_key in actual_stats:
                            habit_stats[stat_key] += val
                            
            # Apply daily cap to the cumulative points for each stat from this habit
            if habit.daily_cap is not None:
                for stat in habit_stats:
                    habit_stats[stat] = min(habit_stats[stat], habit.daily_cap)

        # Merge habit points into actual stats
        for stat, val in habit_stats.items():
            actual_stats[stat] += val

    # 4. Evaluate status against template thresholds
    # Check Acceptable thresholds
    acceptable_valid = True
    for stat, thresh in template.acceptable_thresholds.items():
        stat_key = stat.lower()
        if actual_stats.get(stat_key, 0) < thresh:
            acceptable_valid = False
            break
            
    # Check Perfect thresholds
    perfect_valid = True
    for stat, thresh in template.perfect_thresholds.items():
        stat_key = stat.lower()
        if actual_stats.get(stat_key, 0) < thresh:
            perfect_valid = False
            break

    # Determine status
    if perfect_valid and template.perfect_thresholds:
        status = "Perfect"
    elif acceptable_valid and template.acceptable_thresholds:
        status = "Acceptable"
    else:
        status = "Failed"

    # 5. Save or update DailyScore
    score = db.query(DailyScore).filter_by(user_id=user_id, date=date).first()
    if not score:
        score = DailyScore(
            user_id=user_id,
            date=date,
            status=status,
            active_template_id=template.id,
            actual_stats=actual_stats
        )
        db.add(score)
    else:
        score.status = status
        score.active_template_id = template.id
        score.actual_stats = actual_stats

    db.commit()
    return score

def update_streaks(db: Session, user_id: int, date: datetime.date):
    """
    Updates the running and max streaks for a user based on the DailyScore for that date.
    """
    score = db.query(DailyScore).filter_by(user_id=user_id, date=date).first()
    if not score:
        return

    yesterday = date - datetime.timedelta(days=1)

    # 1. Update Acceptable Streak
    acc_streak = db.query(Streak).filter_by(user_id=user_id, streak_type="Acceptable").first()
    if not acc_streak:
        acc_streak = Streak(user_id=user_id, streak_type="Acceptable", current_streak=0, max_streak=0)
        db.add(acc_streak)

    # Prevent double-processing same day
    if acc_streak.last_incremented != date:
        if score.status in ["Acceptable", "Perfect"]:
            if acc_streak.last_incremented == yesterday:
                acc_streak.current_streak += 1
            elif acc_streak.last_incremented == date:
                pass # Already processed
            else:
                acc_streak.current_streak = 1
            acc_streak.max_streak = max(acc_streak.max_streak, acc_streak.current_streak)
            acc_streak.last_incremented = date
        else:
            # Streak broken if Failed (unless it's processed out of order, but in standard flow it resets)
            if acc_streak.last_incremented == yesterday or acc_streak.last_incremented is None:
                acc_streak.current_streak = 0

    # 2. Update Perfect Streak
    perf_streak = db.query(Streak).filter_by(user_id=user_id, streak_type="Perfect").first()
    if not perf_streak:
        perf_streak = Streak(user_id=user_id, streak_type="Perfect", current_streak=0, max_streak=0)
        db.add(perf_streak)

    if perf_streak.last_incremented != date:
        if score.status == "Perfect":
            if perf_streak.last_incremented == yesterday:
                perf_streak.current_streak += 1
            elif perf_streak.last_incremented == date:
                pass
            else:
                perf_streak.current_streak = 1
            perf_streak.max_streak = max(perf_streak.max_streak, perf_streak.current_streak)
            perf_streak.last_incremented = date
        else:
            if perf_streak.last_incremented == yesterday or perf_streak.last_incremented is None:
                perf_streak.current_streak = 0

    # 3. Update Individual Habit Streaks
    # Get all active habits scheduled for this day
    weekday = date.weekday() # 0 = Monday, 6 = Sunday in python date.weekday()
    # In modelscheduled_days: 0 = Sunday, 1 = Monday, ..., 6 = Saturday
    # Convert weekday to model scheduled day index: (weekday + 1) % 7
    model_day_idx = (weekday + 1) % 7
    
    habits = db.query(Habit).filter_by(is_active=True).all()
    for habit in habits:
        scheduled = str(model_day_idx) in [day.strip() for day in habit.scheduled_days.split(",")]
        if not scheduled:
            continue

        # Check completed logs
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

        if h_streak.last_incremented != date:
            if is_done:
                if h_streak.last_incremented == yesterday:
                    h_streak.current_streak += 1
                else:
                    h_streak.current_streak = 1
                h_streak.max_streak = max(h_streak.max_streak, h_streak.current_streak)
                h_streak.last_incremented = date
            elif is_skipped:
                # Streak preserved but not incremented, last_incremented becomes today so it doesn't break
                h_streak.last_incremented = date
            else:
                # Streak broken!
                if h_streak.last_incremented == yesterday or h_streak.last_incremented is None:
                    h_streak.current_streak = 0

    db.commit()
