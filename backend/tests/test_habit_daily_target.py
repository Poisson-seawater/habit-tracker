import pytest
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.session import Base
from src.database.models import User, Habit, HabitLog
from src.services.score_service import calculate_daily_score


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        session.add(
            User(id=1, username="Gabriel", chat_id="123456", gold=0, xp=0, level=1)
        )
        # Binary habit with a daily target of 2.
        session.add(
            Habit(
                id=1,
                user_id=1,
                name="jogging",
                type="binary",
                frequency="daily",
                scheduled_days="0,1,2,3,4,5,6",
                daily_target=2,
                is_active=True,
            )
        )
        session.commit()
        yield session
    finally:
        session.close()


def _log(session, habit_id, n):
    for _ in range(n):
        session.add(
            HabitLog(
                user_id=1,
                habit_id=habit_id,
                log_type="done",
                timestamp=datetime.datetime.now(),
            )
        )
    session.commit()


def test_one_rep_below_target_is_failed(db_session):
    """A targeted habit must reach its daily target for Perfect Day."""
    _log(db_session, 1, 1)
    score = calculate_daily_score(db_session, user_id=1, date=datetime.date.today())
    assert score.status == "Failed"


def test_target_reached_validates_perfect_day(db_session):
    """Reaching the target validates the scheduled habit for Perfect Day."""
    _log(db_session, 1, 2)
    score = calculate_daily_score(db_session, user_id=1, date=datetime.date.today())
    assert score.status == "Perfect"


def test_exceeding_target_stays_perfect(db_session):
    """Going past the target remains a completed Perfect Day input."""
    _log(db_session, 1, 3)
    score = calculate_daily_score(db_session, user_id=1, date=datetime.date.today())
    assert score.status == "Perfect"


def test_skip_counts_as_handled_for_targeted_habit(db_session):
    """Skipping a scheduled targeted habit handles it for Perfect Day."""
    db_session.add(
        HabitLog(
            user_id=1,
            habit_id=1,
            log_type="skip",
            timestamp=datetime.datetime.now(),
            reason="Repos",
        )
    )
    db_session.commit()
    score = calculate_daily_score(db_session, user_id=1, date=datetime.date.today())
    assert score.status == "Perfect"
