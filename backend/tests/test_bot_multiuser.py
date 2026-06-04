import pytest
import datetime
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.session import Base
from src.database.models import User, Habit, HabitLog, PerfectDayTemplate, DailyScore
from src.bot.listener import route_command

@pytest.fixture
def db_session(monkeypatch):
    # Use an in-memory SQLite database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Seed test templates
        semaine = PerfectDayTemplate(
            user_id=1,
            template_name="week",
            thresholds_json={"discipline": 2}
        )
        session.add(semaine)

        # Seed Gabriel's routine_matin habit (habits are per-user since user isolation)
        h = Habit(
            id=1,
            user_id=1,
            name="routine_matin",
            type="binary",
            frequency="daily",
            scheduled_days="0,1,2,3,4,5,6",
            point_rewards={"discipline": 2},
            is_active=True
        )
        session.add(h)

        # Seed Gabriel (User ID 1)
        gabriel = User(id=1, username="Gabriel", chat_id="111", xp=105, level=2, gold=100)
        session.add(gabriel)
        session.commit()

        # Monkeypatch the SessionLocal inside listener.py to return this test session
        monkeypatch.setattr("src.bot.listener.SessionLocal", lambda: session)
        monkeypatch.setattr("src.bot.listener.TELEGRAM_GROUP_ID", "")
        
        # Mock datetime module in listener.py to return standard UTC date from date.today()
        import datetime as real_datetime
        class MockDateClass:
            @staticmethod
            def today():
                utc_date = real_datetime.datetime.utcnow().date()
                return real_datetime.date(utc_date.year, utc_date.month, utc_date.day)
                
        class MockDatetimeModule:
            date = MockDateClass
            datetime = real_datetime.datetime
            time = real_datetime.time
            
        monkeypatch.setattr("src.bot.listener.datetime", MockDatetimeModule)

        yield session
    finally:
        session.close()

@pytest.mark.asyncio
async def test_bot_auto_registers_new_user(db_session):
    # Mock Telegram Update & Context for a new user "@Jeanne"
    update = MagicMock()
    update.message = MagicMock()
    update.message.text = "/status"
    update.effective_chat.id = 222
    
    from_user = MagicMock()
    from_user.username = "Jeanne"
    from_user.id = 222
    update.message.from_user = from_user

    # Mock reply_text to assert on sent message
    reply_mock = AsyncMock()
    update.message.reply_text = reply_mock

    context = MagicMock()

    # When Jeanne sends a command
    await route_command(update, context)

    # Then Jeanne should be registered automatically in the database
    jeanne = db_session.query(User).filter_by(username="Jeanne").first()
    assert jeanne is not None
    assert jeanne.chat_id == "222"
    assert jeanne.level == 1
    assert jeanne.xp == 0

    # She should receive a status report back
    reply_mock.assert_called_once()
    args, kwargs = reply_mock.call_args
    assert "Jeanne" in args[0]
    assert "Statut de la journée" in args[0]

@pytest.mark.asyncio
async def test_bot_command_user_isolation(db_session):
    # Ensure Jeanne exists
    jeanne = User(id=2, username="Jeanne", chat_id="222", xp=0, level=1, gold=50)
    db_session.add(jeanne)
    db_session.commit()

    # Jeanne owns her own routine_matin (habits are per-user since user isolation)
    jeanne_habit = Habit(
        id=2,
        user_id=2,
        name="routine_matin",
        type="binary",
        frequency="daily",
        scheduled_days="0,1,2,3,4,5,6",
        point_rewards={"discipline": 2},
        is_active=True
    )
    db_session.add(jeanne_habit)
    db_session.commit()

    # Jeanne logs routine_matin
    update = MagicMock()
    update.message = MagicMock()
    update.message.text = "/done routine_matin"
    update.effective_chat.id = 222
    
    from_user = MagicMock()
    from_user.username = "Jeanne"
    from_user.id = 222
    update.message.from_user = from_user
    
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    # Jeanne completes the habit
    await route_command(update, context)

    # Jeanne should have 1 habit log, Gabriel should have 0
    jeanne_logs = db_session.query(HabitLog).filter_by(user_id=2).all()
    gabriel_logs = db_session.query(HabitLog).filter_by(user_id=1).all()
    assert len(jeanne_logs) == 1
    assert len(gabriel_logs) == 0

    # Jeanne should have points/score updated, Gabriel's score should not change
    jeanne_score = db_session.query(DailyScore).filter_by(user_id=2).first()
    gabriel_score = db_session.query(DailyScore).filter_by(user_id=1).first()
    assert jeanne_score is not None
    assert jeanne_score.actual_stats.get("discipline", 0) == 2
    assert gabriel_score is None
