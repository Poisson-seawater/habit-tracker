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
