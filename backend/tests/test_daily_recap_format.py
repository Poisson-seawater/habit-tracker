import os
import pytest
import datetime
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.session import Base, get_db
from src.database.models import User, Habit, HabitLog, Todo, NoTodo, Streak
from src.main import app

TEST_DB_FILE = "backend/tests/.test_daily_recap_format.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    app.dependency_overrides[get_db] = override_get_db
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    try:
        # Create user Gabriel
        u = User(id=1, username="Gabriel", chat_id="111", xp=0, level=1, gold=100)
        db.add(u)

        # Create user EmptyUser
        u2 = User(id=2, username="EmptyUser", chat_id="222", xp=0, level=1, gold=100)
        db.add(u2)

        # Create streaks
        s = Streak(user_id=1, streak_type="Perfect", current_streak=3, max_streak=5)
        db.add(s)
        s2 = Streak(user_id=2, streak_type="Perfect", current_streak=2, max_streak=5)
        db.add(s2)

        # Create some habits
        h1 = Habit(
            id=1,
            user_id=1,
            name="Mediter",
            type="binary",
            frequency="daily",
        )
        h2 = Habit(
            id=2,
            user_id=1,
            name="Lecture",
            type="quantitative",
            unit="pages",
            frequency="daily",
        )
        db.add(h1)
        db.add(h2)

        # Create a Todo
        t = Todo(
            id=1,
            user_id=1,
            title="Faire la vaisselle",
            is_completed=True,
            completed_at=datetime.datetime.now(),
        )
        db.add(t)

        # Create a NoTodo (failed)
        nt = NoTodo(
            id=1,
            user_id=1,
            title="Manger du fastfood",
            failed_at=datetime.datetime.now(),
        )
        db.add(nt)

        # Add habit logs for today
        log1 = HabitLog(
            user_id=1, habit_id=1, log_type="done", timestamp=datetime.datetime.now()
        )
        log2 = HabitLog(
            user_id=1,
            habit_id=2,
            log_type="log",
            amount=15,
            unit="pages",
            timestamp=datetime.datetime.now(),
        )
        db.add(log1)
        db.add(log2)

        db.commit()
    finally:
        db.close()

    yield

    if get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]

    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass


def test_daily_recap_formatting(monkeypatch):
    sent_messages = []

    class MockBot:
        def __init__(self, token):
            self.token = token

        async def send_message(self, chat_id, text, parse_mode=None):
            sent_messages.append(text)

    monkeypatch.setattr("src.bot.scheduler.Bot", MockBot)
    monkeypatch.setattr("src.bot.scheduler.TELEGRAM_BOT_TOKEN", "mock_token")
    monkeypatch.setattr("src.config.TELEGRAM_GROUP_ID", "mock_group_id")
    monkeypatch.setattr("src.bot.scheduler.SessionLocal", TestingSessionLocal)

    from src.bot.scheduler import publish_daily_recap

    asyncio.run(publish_daily_recap())

    assert len(sent_messages) > 0
    recap_msg = sent_messages[0]

    # Assertions on active user recap format (Gabriel)
    assert "Gabriel" in recap_msg
    assert "✅ Mediter" in recap_msg
    assert "✅ Lecture (15pages)" in recap_msg
    assert "✅ Faire la vaisselle 🌟" in recap_msg
    assert "⚠️ <b>No-To-Dos brisés :</b>\n• Manger du fastfood 🚫" in recap_msg

    # Assertions on empty user recap format (EmptyUser)
    assert "EmptyUser" in recap_msg
    assert "branleux fait mieux demain." in recap_msg
