import pytest
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.session import Base
from src.database.models import (
    User,
    Habit,
    HabitLog,
    DailyScore,
    Streak,
)
from src.services.score_service import calculate_daily_score, update_streaks


@pytest.fixture
def db_session():
    # Use an in-memory SQLite database for testing V2
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Seed test user
        user = User(id=1, username="Gabriel", chat_id="123456", gold=0, xp=0, level=1)
        session.add(user)

        h1 = Habit(
            id=1,
            user_id=1,
            name="routine_matin",
            type="binary",
            frequency="daily",
            scheduled_days="0,1,2,3,4,5,6",
            is_active=True,
        )
        h2 = Habit(
            id=2,
            user_id=1,
            name="lecture",
            type="quantitative",
            frequency="daily",
            scheduled_days="0,1,2,3,4,5,6",
            daily_cap=3,
            unit="min",
            is_active=True,
        )
        h3 = Habit(
            id=3,
            user_id=1,
            name="musculation",
            type="binary",
            frequency="daily",
            scheduled_days="0,1,2,3,4,5,6",
            is_active=True,
        )
        session.add_all([h1, h2, h3])
        session.commit()
        yield session
    finally:
        session.close()


def test_daily_score_calculation_incomplete(db_session):
    # Given no logs
    today = datetime.date.today()

    # When calculating daily score using V2 week template
    score = calculate_daily_score(
        db_session, user_id=1, date=today, template_name="week"
    )

    # Then Gabriel is in "Failed" state (incomplete)
    assert score.status == "Failed"


def test_daily_score_calculation_perfect_day(db_session):
    today = datetime.date.today()

    # Log all scheduled habits.
    log1 = HabitLog(
        user_id=1, habit_id=1, log_type="done", timestamp=datetime.datetime.now()
    )
    log2 = HabitLog(
        user_id=1, habit_id=3, log_type="done", timestamp=datetime.datetime.now()
    )
    log3 = HabitLog(
        user_id=1,
        habit_id=2,
        log_type="log",
        amount=1,
        timestamp=datetime.datetime.now(),
    )
    db_session.add_all([log1, log2, log3])
    db_session.commit()

    # When calculating
    score = calculate_daily_score(
        db_session, user_id=1, date=today, template_name="week"
    )

    # Then status is Perfect
    assert score.status == "Perfect"


def test_streak_increment_on_perfect_day(db_session):
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    # Setup initial streak
    streak = Streak(
        user_id=1,
        streak_type="Perfect",
        current_streak=2,
        max_streak=2,
        last_incremented=yesterday,
    )
    db_session.add(streak)
    db_session.commit()

    # When perfect score is registered today
    score = DailyScore(user_id=1, date=today, status="Perfect", template_used="week")
    db_session.add(score)
    db_session.commit()

    update_streaks(db_session, user_id=1, date=today)

    # Streak should increment to 3
    updated_streak = (
        db_session.query(Streak).filter_by(user_id=1, streak_type="Perfect").first()
    )
    assert updated_streak.current_streak == 3
    assert updated_streak.max_streak == 3


def test_dynamic_xp_transitions(db_session):
    today = datetime.date.today()
    user = db_session.query(User).filter_by(id=1).first()
    user.level = 10
    user.xp = 10
    db_session.commit()

    # Initially, Gabriel has habits h1, h2, h3, none are logged, so state is Failed.
    score = calculate_daily_score(db_session, user_id=1, date=today)
    assert score.status == "Failed"
    assert user.xp == 10  # No change

    # Log all scheduled habits.
    log1 = HabitLog(user_id=1, habit_id=1, log_type="done", timestamp=datetime.datetime.now())
    log2 = HabitLog(user_id=1, habit_id=3, log_type="done", timestamp=datetime.datetime.now())
    log3 = HabitLog(user_id=1, habit_id=2, log_type="log", amount=1, timestamp=datetime.datetime.now())
    db_session.add_all([log1, log2, log3])
    db_session.commit()

    # Transition to Perfect
    score2 = calculate_daily_score(db_session, user_id=1, date=today)
    assert score2.status == "Perfect"
    assert user.xp == 15  # +5 XP awarded dynamically!

    # Transition back to Failed (simulate by deleting logs in DB)
    db_session.delete(log1)
    db_session.commit()

    score3 = calculate_daily_score(db_session, user_id=1, date=today)
    assert score3.status == "Failed"
    assert user.xp == 10  # -5 XP deducted dynamically!


@pytest.mark.asyncio
async def test_midnight_streak_rollover(db_session, monkeypatch):
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    # 1. Seed initial streaks for yesterday
    perf_streak = Streak(user_id=1, streak_type="Perfect", current_streak=5, max_streak=5, last_incremented=yesterday)
    h1_streak = Streak(user_id=1, streak_type="habit:1", current_streak=5, max_streak=5, last_incremented=yesterday)
    db_session.add_all([perf_streak, h1_streak])
    db_session.commit()

    # 2. Update streaks today - but today is incomplete.
    # Because of our late-logging decoupling, updating streaks during the day on Failed status should NOT reset streak to 0.
    score = calculate_daily_score(db_session, user_id=1, date=today)
    assert score.status == "Failed"

    update_streaks(db_session, user_id=1, date=today)
    assert perf_streak.current_streak == 5  # Maintained during the day!
    assert h1_streak.current_streak == 5  # Maintained during the day!

    # 3. Simulate midnight rollover. We patch datetime to represent "today" is now tomorrow,
    # so "yesterday" refers to the day we just failed.
    import datetime as real_datetime
    class MockDateClass:
        @staticmethod
        def today():
            return today + datetime.timedelta(days=1)

    class MockDatetimeModule:
        date = MockDateClass
        datetime = real_datetime.datetime
        time = real_datetime.time
        timedelta = real_datetime.timedelta

    # Mock datetime in finalize_day_streaks
    from src.bot import scheduler
    monkeypatch.setattr(scheduler, "datetime", MockDatetimeModule)
    monkeypatch.setattr(scheduler, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)

    # Run midnight rollover
    await scheduler.finalize_day_streaks()

    # Streaks should now be reset to 0 since yesterday (today) was failed and had no logs
    db_session.refresh(perf_streak)
    db_session.refresh(h1_streak)
    assert perf_streak.current_streak == 0
    assert h1_streak.current_streak == 0


