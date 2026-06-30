import os
import pytest
import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.session import Base, get_db
from src.database.models import User, Habit, HabitLog, PerfectDayTemplate, Streak
from src.main import app

TEST_DB_FILE = "backend/tests/.test_habit_streaks.db"
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
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    try:
        # Create Gabriel
        u = User(id=1, username="Gabriel", chat_id="111", xp=0, level=1, gold=100)
        db.add(u)

        # Perfect day template
        t1 = PerfectDayTemplate(user_id=1, template_name="regular")
        db.add(t1)
        db.commit()
    finally:
        db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield

    if get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]

    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass


client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_database():
    db = TestingSessionLocal()
    try:
        # Truncate tables for each test
        db.query(HabitLog).delete()
        db.query(Streak).delete()
        db.query(Habit).delete()
        # Reset user
        user = db.query(User).filter(User.id == 1).first()
        if user:
            user.xp = 0
            user.level = 1
            user.gold = 100
        db.commit()
    finally:
        db.close()


def test_deactivation_freeze_rules():
    db = TestingSessionLocal()
    try:
        # Create habit with a current streak
        h1 = Habit(
            id=10,
            user_id=1,
            name="Habit 10",
            type="binary",
            frequency="daily",
            is_active=True,
            created_at=datetime.datetime.now() - datetime.timedelta(days=100),
        )
        db.add(h1)
        # Create a streak record for it
        st = Streak(user_id=1, streak_type="habit:10", current_streak=5, max_streak=5)
        db.add(st)
        db.commit()
    finally:
        db.close()

    # 1. Soft-delete the habit (deactivates it)
    response = client.delete("/api/v1/habits/10", headers={"X-User-ID": "1"})
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"

    # Verify it is deactivated and deactivated_at is set
    db = TestingSessionLocal()
    try:
        habit = db.query(Habit).filter(Habit.id == 10).first()
        assert habit.is_active is False
        assert habit.deactivated_at is not None

        # Manually alter deactivated_at to 15 days ago to test the freeze reset
        habit.deactivated_at = datetime.datetime.now() - datetime.timedelta(days=15)
        db.commit()
    finally:
        db.close()

    # 2. Reactivate the habit after >14 days (should reset streak to 0)
    response = client.put(
        "/api/v1/habits/10", json={"is_active": True}, headers={"X-User-ID": "1"}
    )
    assert response.status_code == 200

    db = TestingSessionLocal()
    try:
        st_rec = db.query(Streak).filter(Streak.streak_type == "habit:10").first()
        assert st_rec.current_streak == 0
    finally:
        db.close()

    # 3. Repeat but reactivate within 14 days (should NOT reset streak)
    # Set streak back to 10
    db = TestingSessionLocal()
    try:
        st_rec = db.query(Streak).filter(Streak.streak_type == "habit:10").first()
        st_rec.current_streak = 10
        st_rec.last_incremented = datetime.date.today() - datetime.timedelta(days=1)
        db.commit()
    finally:
        db.close()

    # Deactivate it again
    response = client.delete("/api/v1/habits/10", headers={"X-User-ID": "1"})
    assert response.status_code == 200

    # Reactivate it immediately (deactivated_at is current, so <=14 days)
    response = client.put(
        "/api/v1/habits/10", json={"is_active": True}, headers={"X-User-ID": "1"}
    )
    assert response.status_code == 200

    db = TestingSessionLocal()
    try:
        st_rec = db.query(Streak).filter(Streak.streak_type == "habit:10").first()
        assert st_rec.current_streak == 10  # Preserved!
    finally:
        db.close()


def test_streak_milestone_rewards():
    db = TestingSessionLocal()
    try:
        # Create daily habit
        h = Habit(
            id=20,
            user_id=1,
            name="Habit 20",
            type="binary",
            frequency="daily",
            is_active=True,
            created_at=datetime.datetime.now() - datetime.timedelta(days=100),
        )
        db.add(h)

        # Streak record at 29 days
        st = Streak(user_id=1, streak_type="habit:20", current_streak=29, max_streak=29)
        db.add(st)

        # Set user level to 10 to avoid level up and verify raw XP gain
        user = db.query(User).filter(User.id == 1).first()
        user.level = 10
        user.xp = 0
        user.gold = 100
        db.commit()
    finally:
        db.close()

    # Log completion for today
    response = client.post(
        "/api/v1/logs",
        json={"habit_id": 20, "log_type": "done"},
        headers={"X-User-ID": "1"},
    )
    assert response.status_code == 200

    # Check that current streak became 30 and rewards were awarded (+100 XP, +50 Gold)
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.id == 1).first()
        st_rec = db.query(Streak).filter(Streak.streak_type == "habit:20").first()
        assert st_rec.current_streak == 30
        assert user.xp == 100
        # Gold was 100 initialized + 50 reward = 150
        assert user.gold == 150
    finally:
        db.close()

    # Now test 90-day milestone
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.id == 1).first()
        user.level = 10
        user.xp = 0
        user.gold = 100
        st_rec = db.query(Streak).filter(Streak.streak_type == "habit:20").first()
        st_rec.current_streak = 89
        st_rec.last_incremented = datetime.date.today() - datetime.timedelta(days=1)

        # Clear logs first so we can log again
        db.query(HabitLog).filter(HabitLog.habit_id == 20).delete()
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/api/v1/logs",
        json={"habit_id": 20, "log_type": "done"},
        headers={"X-User-ID": "1"},
    )
    assert response.status_code == 200

    # Check 90 days rewards (+300 XP, +150 Gold)
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.id == 1).first()
        st_rec = db.query(Streak).filter(Streak.streak_type == "habit:20").first()
        assert st_rec.current_streak == 90
        assert user.xp == 300
        # Gold was 100 + 150 reward = 250
        assert user.gold == 250
    finally:
        db.close()


def test_calendar_endpoint():
    # Setup a custom frequency habit (Tuesdays only)
    db = TestingSessionLocal()
    try:
        # 2026-06-02 is a Tuesday, 2026-06-03 is a Wednesday
        h = Habit(
            id=30,
            user_id=1,
            name="Habit 30",
            type="binary",
            frequency="specific_days",
            scheduled_days="2",  # Tuesday (0=Sun, 1=Mon, 2=Tue, ..., 6=Sat)
            is_active=True,
            created_at=datetime.datetime(2026, 6, 1),
        )
        db.add(h)

        # Log done on Tuesday 2026-06-02
        db.add(
            HabitLog(
                user_id=1,
                habit_id=30,
                log_type="done",
                timestamp=datetime.datetime(2026, 6, 2, 12, 0),
            )
        )

        # Log skip on Tuesday 2026-06-09
        db.add(
            HabitLog(
                user_id=1,
                habit_id=30,
                log_type="skip",
                reason="Injury",
                timestamp=datetime.datetime(2026, 6, 9, 12, 0),
            )
        )

        db.commit()
    finally:
        db.close()

    # Query calendar for June 2026
    response = client.get(
        "/api/v1/habits/30/calendar?year=2026&month=6", headers={"X-User-ID": "1"}
    )
    assert response.status_code == 200
    data = response.json()

    assert "days" in data
    days = data["days"]

    # 2026-06-01 is Monday (not scheduled)
    assert days["1"] == "non-scheduled"

    # 2026-06-02 is Tuesday (scheduled and completed)
    assert days["2"] == "completed"

    # 2026-06-03 is Wednesday (not scheduled)
    assert days["3"] == "non-scheduled"

    # 2026-06-09 is Tuesday (scheduled and skipped)
    assert days["9"] == "skipped"

    # Let's check a day before creation date (e.g. May 2026)
    response = client.get(
        "/api/v1/habits/30/calendar?year=2026&month=5", headers={"X-User-ID": "1"}
    )
    assert response.status_code == 200
    data_may = response.json()
    assert data_may["days"]["15"] == "pre-creation"
