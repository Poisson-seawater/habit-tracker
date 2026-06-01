import pytest
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.session import Base
from src.database.models import User, Habit, HabitLog, DayTemplate, DailyScore, Streak
from src.services.score_service import calculate_daily_score, update_streaks

@pytest.fixture
def db_session():
    # Use an in-memory SQLite database for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Seed test templates
        semaine = DayTemplate(
            id=1,
            name="Semaine",
            acceptable_thresholds={"discipline": 4, "force": 5},
            perfect_thresholds={"discipline": 8, "force": 10}
        )
        session.add(semaine)

        # Seed test user
        user = User(id=1, username="Gabriel", chat_id="123456")
        session.add(user)

        # Seed test habits
        # 1. routine_matin: binary, daily, rewards discipline: 2
        h1 = Habit(
            id=1,
            name="routine_matin",
            type="binary",
            frequency="daily",
            scheduled_days="0,1,2,3,4,5,6",
            point_rewards={"discipline": 2},
            is_active=True
        )
        # 2. lecture: quantitative, daily, unit min, rewards discipline: 2 (cap 3)
        h2 = Habit(
            id=2,
            name="lecture",
            type="quantitative",
            frequency="daily",
            scheduled_days="0,1,2,3,4,5,6",
            point_rewards={"discipline": 2},
            daily_cap=3,
            unit="min",
            is_active=True
        )
        # 3. musculation: binary, daily, rewards force: 6
        h3 = Habit(
            id=3,
            name="musculation",
            type="binary",
            frequency="daily",
            scheduled_days="0,1,2,3,4,5,6",
            point_rewards={"force": 6},
            is_active=True
        )
        session.add_all([h1, h2, h3])
        session.commit()
        yield session
    finally:
        session.close()

def test_daily_score_calculation_failed(db_session):
    # Given no logs
    today = datetime.date.today()
    
    # When calculating daily score
    score = calculate_daily_score(db_session, user_id=1, date=today, template_id=1)
    
    # Then Gabriel fails the day
    assert score.status == "Failed"
    assert score.actual_stats.get("discipline", 0) == 0

def test_daily_score_calculation_acceptable(db_session):
    # Given Gabriel logs routine_matin (+2 discipline) and lecture (+2 discipline)
    # Total discipline is 4 (threshold is 4), and he logs musculation (+6 force, threshold is 5)
    today = datetime.date.today()
    
    log1 = HabitLog(user_id=1, habit_id=1, log_type="done", timestamp=datetime.datetime.now())
    log2 = HabitLog(user_id=1, habit_id=2, log_type="log", amount=10, unit="min", timestamp=datetime.datetime.now())
    log3 = HabitLog(user_id=1, habit_id=3, log_type="done", timestamp=datetime.datetime.now())
    
    db_session.add_all([log1, log2, log3])
    db_session.commit()
    
    # When calculating
    score = calculate_daily_score(db_session, user_id=1, date=today, template_id=1)
    
    # Then status is Acceptable
    assert score.status == "Acceptable"
    assert score.actual_stats["discipline"] == 4
    assert score.actual_stats["force"] == 6

def test_daily_score_calculation_perfect_with_cap(db_session):
    # Given Gabriel logs routine_matin (+2 discipline), musculation (+6 force)
    # And he logs lecture twice (each +2 discipline, but daily cap is 3!)
    # Total discipline: 2 (routine) + min(2+2, 3) (lecture cap) = 5.
    # To hit Perfect day, he needs discipline: 8. So let's see. If we log more, it gets capped.
    # Let's seed another habit that gives discipline: 6
    h4 = Habit(
        id=4,
        name="autre_discipline",
        type="binary",
        point_rewards={"discipline": 6},
        is_active=True
    )
    db_session.add(h4)
    db_session.commit()
    
    today = datetime.date.today()
    log1 = HabitLog(user_id=1, habit_id=1, log_type="done", timestamp=datetime.datetime.now())
    log2 = HabitLog(user_id=1, habit_id=2, log_type="log", amount=10, unit="min", timestamp=datetime.datetime.now())
    log3 = HabitLog(user_id=1, habit_id=2, log_type="log", amount=20, unit="min", timestamp=datetime.datetime.now())
    log4 = HabitLog(user_id=1, habit_id=3, log_type="done", timestamp=datetime.datetime.now())
    log5 = HabitLog(user_id=1, habit_id=4, log_type="done", timestamp=datetime.datetime.now())
    
    db_session.add_all([log1, log2, log3, log4, log5])
    db_session.commit()
    
    # When calculating
    score = calculate_daily_score(db_session, user_id=1, date=today, template_id=1)
    
    # Then stats show correct capped discipline
    # discipline: 2 (routine) + 3 (capped lecture) + 6 (autre) = 11 (which is >= 8)
    # force: 6 (which is >= 10? No, force perfect threshold is 10! So force is 6/10. Wait, status is still Acceptable!)
    assert score.status == "Acceptable"
    assert score.actual_stats["discipline"] == 11
    assert score.actual_stats["force"] == 6

def test_daily_score_calculation_perfect_success(db_session):
    today = datetime.date.today()
    
    # Add a second musculation log or increase points to hit force: 10
    h_force = Habit(
        id=5,
        name="force_extreme",
        type="binary",
        point_rewards={"force": 10, "discipline": 8},
        is_active=True
    )
    db_session.add(h_force)
    db_session.commit()
    
    log = HabitLog(user_id=1, habit_id=5, log_type="done", timestamp=datetime.datetime.now())
    db_session.add(log)
    db_session.commit()
    
    score = calculate_daily_score(db_session, user_id=1, date=today, template_id=1)
    assert score.status == "Perfect"
    assert score.actual_stats["discipline"] == 8
    assert score.actual_stats["force"] == 10

def test_streak_increment_on_acceptable_day(db_session):
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    
    # Setup initial streak
    streak = Streak(user_id=1, streak_type="Acceptable", current_streak=2, max_streak=2, last_incremented=yesterday)
    db_session.add(streak)
    db_session.commit()
    
    # When streak is updated with an Acceptable score today
    score = DailyScore(user_id=1, date=today, status="Acceptable", active_template_id=1, actual_stats={})
    db_session.add(score)
    db_session.commit()
    
    update_streaks(db_session, user_id=1, date=today)
    
    # Streak should increment to 3
    updated_streak = db_session.query(Streak).filter_by(user_id=1, streak_type="Acceptable").first()
    assert updated_streak.current_streak == 3
    assert updated_streak.max_streak == 3
    assert updated_streak.last_incremented == today

def test_streak_broken_on_failed_day(db_session):
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    
    streak = Streak(user_id=1, streak_type="Acceptable", current_streak=4, max_streak=5, last_incremented=yesterday)
    db_session.add(streak)
    db_session.commit()
    
    # When today is Failed
    score = DailyScore(user_id=1, date=today, status="Failed", active_template_id=1, actual_stats={})
    db_session.add(score)
    db_session.commit()
    
    update_streaks(db_session, user_id=1, date=today)
    
    # Streak should reset to 0, but max_streak remains 5
    updated_streak = db_session.query(Streak).filter_by(user_id=1, streak_type="Acceptable").first()
    assert updated_streak.current_streak == 0
    assert updated_streak.max_streak == 5
