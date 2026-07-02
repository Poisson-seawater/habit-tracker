import datetime
import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import src.api.routes as routes
from src.database.models import (
    DailyScore,
    DayCyclePolicy,
    Habit,
    NoTodo,
    NoTodoLog,
    User,
)
from src.database.session import Base, get_db
from src.main import app
from src.services.day_cycle_service import cycle_info_for_date, monday_of_week


TEST_DB_FILE = "backend/tests/.test_history_cycle.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"


@pytest.fixture
def client_and_db(monkeypatch):
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)

    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(routes, "AUTH_BOOTSTRAP_CODE", "")
    monkeypatch.setattr(routes, "HABIT_API_TOKEN", "")
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    db = TestingSessionLocal()
    try:
        created_at = datetime.datetime.combine(
            datetime.date.today() - datetime.timedelta(days=35),
            datetime.time(hour=8),
        )
        db.add(User(id=1, username="Gabriel", chat_id="111", created_at=created_at))
        db.add(
            Habit(
                id=1,
                user_id=1,
                name="routine_matin",
                type="binary",
                frequency="daily",
                scheduled_days="0,1,2,3,4,5,6",
                is_active=True,
            )
        )
        db.commit()
        yield client, db
    finally:
        db.close()
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
        if os.path.exists(TEST_DB_FILE):
            os.remove(TEST_DB_FILE)


def _history_day(client, day):
    response = client.get("/api/v1/history", headers={"X-User-ID": "1"})
    assert response.status_code == 200
    return next(item for item in response.json() if item["date"] == day.isoformat())


def test_notodo_fail_api_creates_log_and_marks_perfect_day_broken(client_and_db):
    client, db = client_and_db
    today = datetime.date.today()
    notodo = NoTodo(user_id=1, title="Snooze")
    db.add(notodo)
    db.add(
        DailyScore(
            user_id=1,
            date=today,
            status="Perfect",
            template_used="hustle",
        )
    )
    db.commit()
    notodo_id = notodo.id

    response = client.post(
        f"/api/v1/notodos/{notodo_id}/fail", headers={"X-User-ID": "1"}
    )

    assert response.status_code == 200
    db.expire_all()
    log = db.query(NoTodoLog).filter_by(user_id=1, notodo_id=notodo_id).one()
    assert log.date == today
    assert log.title_snapshot == "Snooze"

    day = _history_day(client, today)
    assert day["status"] == "broken"
    assert day["template"] == "hustle"
    assert day["template_emoji"] == "🔥"


def test_history_failed_priority_over_broken(client_and_db):
    client, db = client_and_db
    today = datetime.date.today()
    db.add(NoTodo(user_id=1, title="Snooze"))
    db.add(
        DailyScore(
            user_id=1,
            date=today,
            status="Failed",
            template_used="rest",
        )
    )
    db.commit()
    notodo_id = db.query(NoTodo).filter_by(user_id=1).first().id

    response = client.post(
        f"/api/v1/notodos/{notodo_id}/fail", headers={"X-User-ID": "1"}
    )

    assert response.status_code == 200
    day = _history_day(client, today)
    assert day["status"] == "failed"
    assert day["template_emoji"] == "💤"


def test_cycle_pattern_three_normal_then_one_chill():
    anchor = monday_of_week(datetime.date(2026, 7, 6))
    policy = DayCyclePolicy(user_id=1, anchor_date=anchor, effective_from=anchor)

    assert cycle_info_for_date(policy, anchor)["cycle_week_type"] == "normal"
    assert (
        cycle_info_for_date(policy, anchor + datetime.timedelta(days=7))[
            "cycle_week_type"
        ]
        == "normal"
    )
    assert (
        cycle_info_for_date(policy, anchor + datetime.timedelta(days=14))[
            "cycle_week_type"
        ]
        == "normal"
    )
    assert (
        cycle_info_for_date(policy, anchor + datetime.timedelta(days=21))[
            "cycle_week_type"
        ]
        == "chill"
    )
    assert (
        cycle_info_for_date(policy, anchor + datetime.timedelta(days=28))[
            "cycle_week_type"
        ]
        == "normal"
    )


def test_cycle_anchor_change_is_not_retroactive(client_and_db):
    client, _db = client_and_db
    today = datetime.date.today()
    if today.day == 1:
        pytest.skip("No earlier day exists in the current month.")

    past_day = today.replace(day=1)
    before = _history_day(client, past_day)

    new_anchor = today + datetime.timedelta(days=21)
    response = client.put(
        "/api/v1/profile/cycle",
        json={"anchor_date": new_anchor.isoformat()},
        headers={"X-User-ID": "1"},
    )

    assert response.status_code == 200
    policy = response.json()["policy"]
    assert policy["anchor_date"] == monday_of_week(new_anchor).isoformat()
    assert policy["effective_from"] == today.isoformat()

    after_past = _history_day(client, past_day)
    after_today = _history_day(client, today)
    assert after_past["cycle_policy_id"] == before["cycle_policy_id"]
    assert after_past["cycle_week_type"] == before["cycle_week_type"]
    assert after_today["cycle_policy_effective_from"] == today.isoformat()


@pytest.mark.asyncio
async def test_bot_fail_command_creates_notodo_log(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        db.add(User(id=1, username="Gabriel", chat_id="111"))
        db.add(NoTodo(user_id=1, title="Snooze"))
        db.commit()

        monkeypatch.setattr("src.bot.listener.SessionLocal", lambda: db)
        monkeypatch.setattr("src.bot.listener.TELEGRAM_GROUP_ID", "")

        from src.bot.listener import route_command

        update = MagicMock()
        update.message = MagicMock()
        update.message.text = "/fail snooze"
        update.effective_chat.id = 111
        update.message.from_user = MagicMock(username="Gabriel", id=111)
        update.message.reply_text = AsyncMock()

        await route_command(update, MagicMock())

        log = db.query(NoTodoLog).filter_by(user_id=1).one()
        assert log.date == datetime.date.today()
        assert log.title_snapshot == "Snooze"
    finally:
        db.close()
