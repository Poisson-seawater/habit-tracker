import datetime
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import src.api.routes as routes
from src.database.models import (
    DailyScore,
    Habit,
    HabitLog,
    NoTodo,
    NoTodoLog,
    Streak,
    User,
)
from src.database.session import Base, get_db
from src.main import app
from src.services.daily_log_service import rebuild_streak_projections


TEST_DB_FILE = "backend/tests/.test_yesterday_corrections.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"


@pytest.fixture
def client_and_db(monkeypatch):
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(routes, "AUTH_BOOTSTRAP_CODE", "")
    monkeypatch.setattr(routes, "HABIT_API_TOKEN", "")
    app.dependency_overrides[get_db] = override_get_db
    db = testing_session()
    today = datetime.date.today()
    db.add(
        User(
            id=1,
            username="Gabriel",
            chat_id="111",
            level=10,
            xp=0,
            gold=0,
            created_at=datetime.datetime.combine(
                today - datetime.timedelta(days=10), datetime.time(hour=8)
            ),
        )
    )
    db.add(
        Habit(
            id=1,
            user_id=1,
            name="Routine",
            type="binary",
            frequency="daily",
            scheduled_days="0,1,2,3,4,5,6",
            day_types=["rest", "regular", "hustle"],
            is_active=True,
            created_at=datetime.datetime.combine(
                today - datetime.timedelta(days=10), datetime.time(hour=8)
            ),
        )
    )
    db.commit()
    try:
        yield TestClient(app), db
    finally:
        db.close()
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
        if os.path.exists(TEST_DB_FILE):
            os.remove(TEST_DB_FILE)


def _at(date_value, hour=9):
    return datetime.datetime.combine(date_value, datetime.time(hour=hour))


def test_yesterday_log_recalculates_score_and_preserves_today_projection(client_and_db):
    client, db = client_and_db
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    two_days_ago = today - datetime.timedelta(days=2)
    db.add_all(
        [
            HabitLog(
                user_id=1, habit_id=1, log_type="done", timestamp=_at(two_days_ago)
            ),
            HabitLog(user_id=1, habit_id=1, log_type="done", timestamp=_at(today)),
            DailyScore(
                user_id=1, date=two_days_ago, status="Perfect", template_used="regular"
            ),
            DailyScore(
                user_id=1, date=yesterday, status="Failed", template_used="regular"
            ),
            DailyScore(
                user_id=1, date=today, status="Perfect", template_used="regular"
            ),
            Streak(
                user_id=1,
                streak_type="habit:1",
                current_streak=1,
                max_streak=1,
                last_incremented=today,
            ),
        ]
    )
    db.commit()

    response = client.post(
        "/api/v1/logs",
        headers={"X-User-ID": "1"},
        json={
            "habit_id": 1,
            "log_type": "done",
            "target_date": yesterday.isoformat(),
        },
    )

    assert response.status_code == 200
    assert response.json()["target_date"] == yesterday.isoformat()
    db.expire_all()
    log = (
        db.query(HabitLog)
        .filter(
            HabitLog.timestamp >= _at(yesterday, 0), HabitLog.timestamp < _at(today, 0)
        )
        .one()
    )
    assert log.timestamp.date() == yesterday
    assert (
        db.query(DailyScore).filter_by(user_id=1, date=yesterday).one().status
        == "Perfect"
    )
    streak = db.query(Streak).filter_by(user_id=1, streak_type="habit:1").one()
    assert streak.current_streak == 3
    assert streak.last_incremented == today
    assert db.query(User).filter_by(id=1).one().xp == 5

    duplicate = client.post(
        "/api/v1/logs",
        headers={"X-User-ID": "1"},
        json={
            "habit_id": 1,
            "log_type": "done",
            "target_date": yesterday.isoformat(),
        },
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["status"] == "already_logged"
    db.expire_all()
    assert db.query(User).filter_by(id=1).one().xp == 5


@pytest.mark.parametrize("offset", [-2, 1])
def test_log_date_outside_today_yesterday_is_rejected(client_and_db, offset):
    client, db = client_and_db
    target = datetime.date.today() + datetime.timedelta(days=offset)

    response = client.post(
        "/api/v1/logs",
        headers={"X-User-ID": "1"},
        json={"habit_id": 1, "log_type": "done", "target_date": target.isoformat()},
    )

    assert response.status_code == 422
    assert db.query(HabitLog).count() == 0


def test_yesterday_notodo_failure_is_dated_and_idempotent(client_and_db):
    client, db = client_and_db
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    notodo = NoTodo(user_id=1, title="Snooze")
    db.add(notodo)
    db.commit()

    for _ in range(2):
        response = client.post(
            f"/api/v1/notodos/{notodo.id}/fail",
            headers={"X-User-ID": "1"},
            json={"target_date": yesterday.isoformat()},
        )
        assert response.status_code == 200
        assert response.json()["log"]["date"] == yesterday.isoformat()

    db.expire_all()
    assert (
        db.query(NoTodoLog)
        .filter_by(user_id=1, notodo_id=notodo.id, date=yesterday)
        .count()
        == 1
    )
    listed = client.get(
        f"/api/v1/notodos?target_date={yesterday.isoformat()}",
        headers={"X-User-ID": "1"},
    )
    assert listed.status_code == 200
    assert listed.json()[0]["failed_on_date"] is True
    assert listed.json()[0]["failed_today"] is False


def test_habit_failure_is_idempotent_and_undo_defers_streak_restore(client_and_db):
    client, db = client_and_db
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    db.get(User, 1).xp = 20
    db.add(
        Streak(
            user_id=1,
            streak_type="habit:1",
            current_streak=5,
            max_streak=5,
            last_incremented=yesterday,
        )
    )
    db.commit()

    failed = client.post("/api/v1/habits/1/fail", headers={"X-User-ID": "1"})
    assert failed.status_code == 200
    assert failed.json()["status"] == "failed"
    assert failed.json()["xp_penalty_applied"] == 5
    db.expire_all()
    assert db.get(User, 1).xp == 15
    repeated = client.post("/api/v1/habits/1/fail", headers={"X-User-ID": "1"})
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "already_failed"
    assert repeated.json()["xp_penalty_applied"] == 0
    db.expire_all()
    assert db.get(User, 1).xp == 15
    assert db.query(HabitLog).filter_by(log_type="failed").count() == 1
    assert db.query(Streak).filter_by(streak_type="habit:1").one().current_streak == 0
    agenda = client.get(
        f"/api/v1/agenda?date={today.isoformat()}",
        headers={"X-User-ID": "1"},
    ).json()
    agenda_habit = next(
        item for item in agenda["unplaced_quests"] if item["habit_id"] == 1
    )
    assert agenda_habit["status"] == "failed"

    blocked = client.post(
        "/api/v1/logs",
        headers={"X-User-ID": "1"},
        json={"habit_id": 1, "log_type": "done"},
    )
    assert blocked.status_code == 409

    undone = client.delete("/api/v1/habits/1/fail", headers={"X-User-ID": "1"})
    assert undone.status_code == 200
    assert undone.json()["status"] == "undone"
    assert undone.json()["xp_restored"] == 5
    db.expire_all()
    assert db.get(User, 1).xp == 20
    repeated_undo = client.delete("/api/v1/habits/1/fail", headers={"X-User-ID": "1"})
    assert repeated_undo.json()["status"] == "already_undone"
    assert repeated_undo.json()["xp_restored"] == 0
    db.expire_all()
    assert db.get(User, 1).xp == 20

    completed = client.post(
        "/api/v1/logs",
        headers={"X-User-ID": "1"},
        json={"habit_id": 1, "log_type": "done"},
    )
    assert completed.status_code == 200
    db.expire_all()
    failure = db.query(HabitLog).filter_by(log_type="failed").one()
    assert failure.cancelled_at is not None
    assert db.query(Streak).filter_by(streak_type="habit:1").one().current_streak == 0

    rebuild_streak_projections(db, user_id=1, through_date=today, finalizing=True)
    assert db.query(Streak).filter_by(streak_type="habit:1").one().current_streak == 1


def test_completed_habit_cannot_be_marked_failed(client_and_db):
    client, _ = client_and_db
    completed = client.post(
        "/api/v1/logs",
        headers={"X-User-ID": "1"},
        json={"habit_id": 1, "log_type": "done"},
    )
    assert completed.status_code == 200

    failed = client.post("/api/v1/habits/1/fail", headers={"X-User-ID": "1"})
    assert failed.status_code == 409


def test_dashboard_exposes_yesterday_and_failure_controls():
    repo_root = Path(__file__).resolve().parents[2]
    index_html = (repo_root / "frontend/index.html").read_text()
    app_js = (repo_root / "frontend/js/app.js").read_text()

    assert 'id="agenda-yesterday-btn"' in index_html
    assert 'id="agenda-today-btn"' in index_html
    assert "target_date: targetDate" in app_js
    assert "async function setHabitFailure" in app_js
    assert "failed_on_date" in app_js
