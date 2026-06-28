import pytest
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.session import Base
from src.database.models import (
    User,
    Habit,
    HabitLog,
    PerfectDayTemplate,
    DailyScore,
    Streak,
    Todo,
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
        # Seed test custom template thresholds for "week"
        week_template = PerfectDayTemplate(
            user_id=1,
            template_name="week",
            thresholds_json={"discipline": 8, "forme_physique": 10},
        )
        session.add(week_template)

        # Seed test user
        user = User(id=1, username="Gabriel", chat_id="123456", gold=0, xp=0, level=1)
        session.add(user)

        # Seed test habits
        # 1. routine_matin: binary, daily, rewards discipline: 2
        h1 = Habit(
            id=1,
            user_id=1,
            name="routine_matin",
            type="binary",
            frequency="daily",
            scheduled_days="0,1,2,3,4,5,6",
            point_rewards={"discipline": 2},
            is_active=True,
        )
        # 2. lecture: quantitative, daily, unit min, rewards discipline: 2 (cap 3)
        h2 = Habit(
            id=2,
            user_id=1,
            name="lecture",
            type="quantitative",
            frequency="daily",
            scheduled_days="0,1,2,3,4,5,6",
            point_rewards={"discipline": 2},
            daily_cap=3,
            unit="min",
            is_active=True,
        )
        # 3. musculation: binary, daily, rewards forme_physique: 6
        h3 = Habit(
            id=3,
            user_id=1,
            name="musculation",
            type="binary",
            frequency="daily",
            scheduled_days="0,1,2,3,4,5,6",
            point_rewards={"forme_physique": 6},
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
    assert score.actual_stats.get("discipline", 0) == 0


def test_daily_score_calculation_perfect_day(db_session):
    today = datetime.date.today()

    # Log routine_matin (+1 discipline), musculation (+1 forme_physique), lecture (+1 discipline)
    # And we log a Todo (+1 forme_physique, +1 discipline)
    log1 = HabitLog(
        user_id=1, habit_id=1, log_type="done", timestamp=datetime.datetime.now()
    )
    log2 = HabitLog(
        user_id=1, habit_id=3, log_type="done", timestamp=datetime.datetime.now()
    )
    log3 = HabitLog(
        user_id=1, habit_id=2, log_type="log", amount=1, timestamp=datetime.datetime.now()
    )
    todo = Todo(
        user_id=1,
        title="Test Todo",
        xp_reward=20,
        is_completed=True,
        completed_at=datetime.datetime.now(),
        stat_reward_1="forme_physique",
        points_reward_1=1,
        stat_reward_2="discipline",
        points_reward_2=1,
    )

    db_session.add_all([log1, log2, log3, todo])
    db_session.commit()

    # When calculating
    score = calculate_daily_score(
        db_session, user_id=1, date=today, template_name="week"
    )

    # Then status is Perfect
    assert score.status == "Perfect"
    assert score.actual_stats["discipline"] == 3
    assert score.actual_stats["forme_physique"] == 2


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
    score = DailyScore(
        user_id=1, date=today, status="Perfect", template_used="week", actual_stats={}
    )
    db_session.add(score)
    db_session.commit()

    update_streaks(db_session, user_id=1, date=today)

    # Streak should increment to 3
    updated_streak = (
        db_session.query(Streak).filter_by(user_id=1, streak_type="Perfect").first()
    )
    assert updated_streak.current_streak == 3
    assert updated_streak.max_streak == 3
