import datetime
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import DailyScore, Habit, HabitLog, Streak, User
from src.database.session import Base, get_db
from src.main import app
from src.bot.listener import _render_liste
from src.services.agenda_service import (
    is_habit_eligible_on_date,
    normalize_habit_day_types,
)
from src.services.score_service import calculate_daily_score, update_streaks


TEST_DB_FILE = "backend/tests/.test_habit_day_types.db"
engine = create_engine(
    f"sqlite:///{TEST_DB_FILE}", connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestingSessionLocal() as db:
        db.add(User(id=1, username="Gabriel", xp=0, level=1, gold=0))
        db.commit()
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db_file():
    yield
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)


@pytest.fixture
def client():
    return TestClient(app)


def test_habit_api_defaults_validates_and_updates_day_types(client):
    response = client.post(
        "/api/v1/habits",
        json={"name": "Lecture", "type": "binary"},
        headers={"X-User-ID": "1"},
    )
    assert response.status_code == 201
    habit_id = response.json()["id"]

    habit = client.get("/api/v1/habits", headers={"X-User-ID": "1"}).json()[0]
    assert habit["day_types"] == ["rest", "regular", "hustle"]

    response = client.put(
        f"/api/v1/habits/{habit_id}",
        json={"day_types": ["hustle", "rest"]},
        headers={"X-User-ID": "1"},
    )
    assert response.status_code == 200
    habit = client.get("/api/v1/habits", headers={"X-User-ID": "1"}).json()[0]
    assert habit["day_types"] == ["hustle", "rest"]

    for invalid in ([], ["normal"], ["regular", "vacation"]):
        response = client.put(
            f"/api/v1/habits/{habit_id}",
            json={"day_types": invalid},
            headers={"X-User-ID": "1"},
        )
        assert response.status_code == 400


def test_day_type_filters_agenda_and_perfect_but_manual_log_advances_streak(client):
    date_value = datetime.date(2026, 7, 6)
    timestamp = datetime.datetime.combine(date_value, datetime.time(hour=12))
    with TestingSessionLocal() as db:
        rest_habit = Habit(
            user_id=1,
            name="Repos actif",
            type="binary",
            day_types=["rest"],
            scheduled_days="0,1,2,3,4,5,6",
        )
        hustle_habit = Habit(
            user_id=1,
            name="Travail profond",
            type="binary",
            day_types=["hustle"],
            scheduled_days="0,1,2,3,4,5,6",
        )
        db.add_all([rest_habit, hustle_habit])
        db.flush()
        db.add(
            DailyScore(
                user_id=1, date=date_value, status="Failed", template_used="rest"
            )
        )
        db.add_all(
            [
                HabitLog(
                    user_id=1,
                    habit_id=rest_habit.id,
                    log_type="done",
                    timestamp=timestamp,
                ),
                HabitLog(
                    user_id=1,
                    habit_id=hustle_habit.id,
                    log_type="done",
                    timestamp=timestamp,
                ),
            ]
        )
        db.commit()

        score = calculate_daily_score(db, 1, date_value, template_name="rest")
        assert score.status == "Perfect"
        update_streaks(db, 1, date_value)
        hustle_streak = (
            db.query(Streak).filter_by(streak_type=f"habit:{hustle_habit.id}").one()
        )
        assert hustle_streak.current_streak == 1

    agenda = client.get(
        f"/api/v1/agenda?date={date_value.isoformat()}",
        headers={"X-User-ID": "1"},
    )
    assert agenda.status_code == 200
    visible_names = {
        item["name"]
        for item in agenda.json()["placed_quests"] + agenda.json()["unplaced_quests"]
    }
    assert visible_names == {"Repos actif"}


def test_manual_off_type_api_log_is_allowed_and_visible(client):
    today = datetime.date.today()
    with TestingSessionLocal() as db:
        habit = Habit(
            user_id=1,
            name="Hustle seulement",
            type="binary",
            day_types=["hustle"],
            scheduled_days="0,1,2,3,4,5,6",
        )
        db.add(habit)
        db.flush()
        habit_id = habit.id
        db.add(DailyScore(user_id=1, date=today, status="Failed", template_used="rest"))
        db.commit()

    response = client.post(
        "/api/v1/logs",
        json={"habit_id": habit_id, "log_type": "done"},
        headers={"X-User-ID": "1"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "logged"

    habit = client.get("/api/v1/habits", headers={"X-User-ID": "1"}).json()[0]
    assert habit["today_count"] == 1
    with TestingSessionLocal() as db:
        assert db.query(HabitLog).filter_by(habit_id=habit_id).count() == 1
        assert (
            db.query(Streak)
            .filter_by(streak_type=f"habit:{habit_id}")
            .one()
            .current_streak
            == 1
        )


def test_legacy_day_type_values_fall_back_to_all():
    user = User(id=1, username="Gabriel")
    date_value = datetime.date(2026, 7, 6)
    for value in (None, [], "", "not-json"):
        habit = Habit(
            user_id=1,
            name=f"Legacy {value}",
            type="binary",
            day_types=value,
            scheduled_days="0,1,2,3,4,5,6",
            is_active=True,
        )
        assert normalize_habit_day_types(value) == ["rest", "regular", "hustle"]
        assert is_habit_eligible_on_date(habit, date_value, user, "regular")


def test_habit_version_preserves_day_types(client):
    created = client.post(
        "/api/v1/habits",
        json={"name": "Echecs", "type": "binary", "day_types": ["hustle"]},
        headers={"X-User-ID": "1"},
    ).json()
    version = client.post(
        f"/api/v1/habits/{created['id']}/versions",
        json={},
        headers={"X-User-ID": "1"},
    )
    assert version.status_code == 201
    with TestingSessionLocal() as db:
        new_habit = db.query(Habit).filter_by(id=version.json()["id"]).one()
        assert new_habit.day_types == ["hustle"]


def test_telegram_habit_list_filters_current_day_type():
    today = datetime.date.today()
    with TestingSessionLocal() as db:
        db.add_all(
            [
                DailyScore(
                    user_id=1, date=today, status="Failed", template_used="rest"
                ),
                Habit(
                    user_id=1,
                    name="Repos visible",
                    type="binary",
                    day_types=["rest"],
                    is_active=True,
                ),
                Habit(
                    user_id=1,
                    name="Hustle masque",
                    type="binary",
                    day_types=["hustle"],
                    is_active=True,
                ),
            ]
        )
        db.commit()
        rendered = _render_liste(db, 1, "habit")

    assert "Repos visible" in rendered
    assert "Hustle masque" not in rendered


def test_substep_duration_controls_are_hidden_but_preserved_in_payload():
    repo_root = Path(__file__).resolve().parents[2]
    index_html = (repo_root / "frontend/index.html").read_text()
    app_js = (repo_root / "frontend/js/app.js").read_text()

    assert "Durée d'effort (h)" not in index_html
    assert (
        '<input type="hidden" id="substep-effort-duration" value="1.0">' in index_html
    )
    assert (
        '<input type="hidden" id="edit-substep-effort-duration" value="1.0">'
        in index_html
    )
    assert 'document.getElementById("edit-substep-effort-duration").value' in app_js
