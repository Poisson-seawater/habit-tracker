import datetime
import html
from typing import Optional
import httpx
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

    perfect_valid = len(habits) > 0
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
        if status == "Perfect":
            add_user_xp(user, 5)
    else:
        old_status = score.status
        score.status = status
        score.template_used = template_name
        if old_status != "Perfect" and status == "Perfect":
            add_user_xp(user, 5)
        elif old_status == "Perfect" and status != "Perfect":
            deduct_user_xp(user, 5)

    db.commit()
    return score


def update_streaks(db: Session, user_id: int, date: datetime.date) -> list[dict]:
    """
    Updates perfect day streaks and individual habit streaks.
    Returns milestone notification events to dispatch after DB state is committed.
    """
    score = db.query(DailyScore).filter_by(user_id=user_id, date=date).first()
    if not score:
        return []

    yesterday = date - datetime.timedelta(days=1)
    milestone_events = []

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
        # No mid-day resets to 0. Streaks are reset at midnight.
    else:  # perf_streak.last_incremented == date
        if score.status != "Perfect":
            # Revert the streak increment if today's Perfect status was lost (e.g. template changes)
            perf_streak.current_streak = max(0, perf_streak.current_streak - 1)
            perf_streak.last_incremented = yesterday

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
        return []

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
                milestone = None
                if h_streak.current_streak == 30:
                    user.gold += 50
                    add_user_xp(user, 100)
                    milestone = 30
                elif h_streak.current_streak == 90:
                    user.gold += 150
                    add_user_xp(user, 300)
                    milestone = 90
                elif h_streak.current_streak == 180:
                    user.gold += 200
                    add_user_xp(user, 500)
                    milestone = 180

                if milestone and user.chat_id:
                    milestone_events.append(
                        {
                            "chat_id": user.chat_id,
                            "habit_id": habit.id,
                            "habit_name": habit.name,
                            "milestone": milestone,
                        }
                    )
            elif is_skipped:
                h_streak.last_incremented = date
            # No mid-day resets to 0. Streaks are reset at midnight.

    db.commit()
    return milestone_events


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


def deduct_user_xp(user: User, xp_lost: int):
    """
    Deducts permanent XP from a user and handles level-down.
    """
    user.xp -= xp_lost
    while user.xp < 0:
        if user.level > 1:
            user.level -= 1
            xp_needed = 10 * (2 ** (user.level - 1))
            user.xp += xp_needed
        else:
            user.xp = 0
            break




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


def split_habit_version_name(name: str) -> tuple[Optional[int], str]:
    cleaned_name = (name or "").strip()
    for prefix in ("Étape ", "Etape "):
        if cleaned_name.startswith(prefix):
            version_part, separator, base_name = cleaned_name[len(prefix) :].partition(
                " - "
            )
            if separator and version_part.isdigit() and base_name.strip():
                return int(version_part), base_name.strip()
    return None, cleaned_name


def build_habit_version_name(version_index: int, base_name: str) -> str:
    return f"Étape {version_index} - {base_name}"


def perform_habit_levelup(
    db: Session,
    user_id: int,
    habit_id: int,
    description: Optional[str] = None,
    source_description: Optional[str] = None,
) -> Habit:
    source = db.query(Habit).filter_by(id=habit_id, user_id=user_id).first()
    if not source:
        raise ValueError("Habit not found.")

    try:
        _source_version_index, base_name = split_habit_version_name(source.name)
        used_names = set()
        max_version_index = 0
        unversioned_base_habit = None
        version_group_habits = []

        if source_description is not None:
            source.description = source_description
        new_description = description if description is not None else source.description

        for existing_habit in db.query(Habit).filter_by(user_id=user_id).all():
            used_names.add(existing_habit.name)
            v_idx, candidate_base_name = split_habit_version_name(existing_habit.name)
            if candidate_base_name != base_name:
                continue
            version_group_habits.append(existing_habit)
            if v_idx is None:
                max_version_index = max(max_version_index, 1)
                if existing_habit.name == base_name:
                    unversioned_base_habit = existing_habit
            else:
                max_version_index = max(max_version_index, v_idx)

        if unversioned_base_habit:
            first_version_name = build_habit_version_name(1, base_name)
            if first_version_name not in used_names:
                unversioned_base_habit.name = first_version_name
                used_names.add(first_version_name)

        next_version_index = max_version_index + 1
        next_version_name = build_habit_version_name(next_version_index, base_name)
        while next_version_name in used_names:
            next_version_index += 1
            next_version_name = build_habit_version_name(next_version_index, base_name)

        habit = Habit(
            user_id=user_id,
            name=next_version_name,
            type=source.type,
            description=new_description,
            frequency=source.frequency,
            scheduled_days=source.scheduled_days,
            reminder_time=source.reminder_time,
            is_private=source.is_private,
            is_reportable=source.is_reportable,
            is_mandatory=source.is_mandatory,
            daily_cap=source.daily_cap,
            daily_target=source.daily_target,
            unit=source.unit,
            effort_type=source.effort_type,
            effort_duration=source.effort_duration,
            source_type=source.source_type or "manual",
            source_ref=source.source_ref,
            auto_managed=bool(source.auto_managed),
            archived_at=source.archived_at,
            agenda_duration_minutes=source.agenda_duration_minutes,
            is_active=True,
        )
        db.add(habit)
        db.flush()

        now = datetime.datetime.now()
        for previous_habit in version_group_habits:
            if previous_habit.id == habit.id:
                continue
            if previous_habit.is_active:
                previous_habit.is_active = False
                previous_habit.deactivated_at = now

        source_streak = (
            db.query(Streak)
            .filter_by(user_id=user_id, streak_type=f"habit:{source.id}")
            .first()
        )
        if not source_streak:
            candidate_streaks = []
            for previous_habit in version_group_habits:
                candidate = (
                    db.query(Streak)
                    .filter_by(
                        user_id=user_id, streak_type=f"habit:{previous_habit.id}"
                    )
                    .first()
                )
                if candidate:
                    candidate_streaks.append(candidate)
            if candidate_streaks:
                source_streak = max(
                    candidate_streaks,
                    key=lambda s: (
                        s.current_streak or 0,
                        s.max_streak or 0,
                        s.last_incremented or datetime.date.min,
                    ),
                )

        if source_streak:
            new_streak = (
                db.query(Streak)
                .filter_by(user_id=user_id, streak_type=f"habit:{habit.id}")
                .first()
            )
            if not new_streak:
                new_streak = Streak(user_id=user_id, streak_type=f"habit:{habit.id}")
                db.add(new_streak)
            new_streak.current_streak = source_streak.current_streak
            new_streak.max_streak = source_streak.max_streak
            new_streak.last_incremented = source_streak.last_incremented

        db.commit()
        db.refresh(habit)
        return habit
    except Exception:
        db.rollback()
        raise


def send_milestone_notification(
    chat_id: str, habit_id: int, habit_name: str, milestone: int
):
    from src.config import TELEGRAM_BOT_TOKEN

    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return

    emoji = "🥉" if milestone == 30 else ("🥈" if milestone == 90 else "🥇")
    safe_habit_name = html.escape(habit_name or "")
    text = (
        f"Bravo pour le streak de {milestone}j pour '{safe_habit_name}' ! {emoji}\n"
        "Veux-tu monter le niveau de l'habitude ?"
    )

    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "Oui, monter le niveau", "callback_data": f"lvlup:{habit_id}"},
                {
                    "text": "Non, garder le niveau",
                    "callback_data": f"lvlkeep:{habit_id}",
                },
            ]
        ]
    }

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": reply_markup,
    }

    try:
        response = httpx.post(url, json=payload, timeout=5)
        response.raise_for_status()
    except Exception as e:
        print(f"Error sending milestone notification to Telegram: {e}")


def dispatch_milestone_notifications(events: list[dict]):
    for event in events or []:
        send_milestone_notification(
            event.get("chat_id"),
            int(event.get("habit_id")),
            event.get("habit_name") or "",
            int(event.get("milestone")),
        )
