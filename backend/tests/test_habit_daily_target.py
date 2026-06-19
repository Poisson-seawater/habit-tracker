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
        # Binary habit with a daily target of 2 (each rep = +5 discipline)
        session.add(
            Habit(
                id=1,
                user_id=1,
                name="jogging",
                type="binary",
                frequency="daily",
                scheduled_days="0,1,2,3,4,5,6",
                point_rewards={"discipline": 5},
                daily_target=2,
                is_active=True,
            )
        )
        # Plain binary habit (no target) for the no-regression check
        session.add(
            Habit(
                id=2,
                user_id=1,
                name="routine",
                type="binary",
                frequency="daily",
                scheduled_days="0,1,2,3,4,5,6",
                point_rewards={"discipline": 5},
                is_active=True,
            )
        )
        # Targeted binary with a daily_cap to verify the cap still applies
        session.add(
            Habit(
                id=3,
                user_id=1,
                name="capped",
                type="binary",
                frequency="daily",
                scheduled_days="0,1,2,3,4,5,6",
                point_rewards={"discipline": 5},
                daily_target=3,
                daily_cap=12,
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


def test_one_rep_no_penalty(db_session):
    """Doing a targeted habit once still counts and gives its base XP (no penalty)."""
    _log(db_session, 1, 1)
    score = calculate_daily_score(db_session, user_id=1, date=datetime.date.today())
    assert score.actual_stats["discipline"] == 5


def test_extra_reps_give_extra_xp(db_session):
    """Each validation of a targeted habit adds its full reward (2 reps = 2x)."""
    _log(db_session, 1, 2)
    score = calculate_daily_score(db_session, user_id=1, date=datetime.date.today())
    assert score.actual_stats["discipline"] == 10


def test_exceeding_target_keeps_awarding(db_session):
    """Going past the target (3/2) still awards XP for every rep."""
    _log(db_session, 1, 3)
    score = calculate_daily_score(db_session, user_id=1, date=datetime.date.today())
    assert score.actual_stats["discipline"] == 15


def test_plain_binary_awards_once(db_session):
    """A binary habit without a target is unchanged: awarded once regardless of reps."""
    _log(db_session, 2, 3)
    score = calculate_daily_score(db_session, user_id=1, date=datetime.date.today())
    assert score.actual_stats["discipline"] == 5


def test_daily_cap_respected_on_targeted_binary(db_session):
    """daily_cap still bounds the points of a targeted binary (3 reps x5 = 15 -> capped 12)."""
    _log(db_session, 3, 3)
    score = calculate_daily_score(db_session, user_id=1, date=datetime.date.today())
    assert score.actual_stats["discipline"] == 12
