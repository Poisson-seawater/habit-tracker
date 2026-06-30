import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.session import Base, get_db
from src.database.models import (
    DailyAgendaPlacement,
    Habit,
    PerfectDayTemplate,
    User,
    Goal,
)
from src.main import app

TEST_DB_FILE = "backend/tests/.test_agenda_quests.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
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

    db = TestingSessionLocal()
    try:
        db.add(User(id=1, username="Gabriel", chat_id="111", xp=0, level=1, gold=100))
        db.add(
            PerfectDayTemplate(
                user_id=1,
                template_name="regular",
                focus_hours=6.0,
                min_rest_hours=8.0,
                ceilings_json={
                    "musculaire": 2.0,
                    "cerveau": 2.0,
                    "emotionnel_social": 2.0,
                    "creatif_divergent": 2.0,
                    "total": 8.0,
                },
                agenda_json={
                    "schema_version": 2,
                    "segments": [
                        {
                            "id": "admin-1",
                            "kind": "admin",
                            "start": "13:00",
                            "end": "15:00",
                        }
                    ],
                    "default_placements": [],
                },
            )
        )
        db.commit()
    finally:
        db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db_file():
    yield
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass


@pytest.fixture
def client():
    return TestClient(app)


def add_habit(**overrides):
    db = TestingSessionLocal()
    try:
        habit = Habit(
            user_id=1,
            name=overrides.pop("name", "Quest"),
            type=overrides.pop("type", "binary"),
            frequency=overrides.pop("frequency", "daily"),
            scheduled_days=overrides.pop("scheduled_days", "0,1,2,3,4,5,6"),
            is_active=overrides.pop("is_active", True),
            effort_type=overrides.pop("effort_type", "cerveau"),
            effort_duration=overrides.pop("effort_duration", 1.0),
            agenda_duration_minutes=overrides.pop("agenda_duration_minutes", 60),
            **overrides,
        )
        db.add(habit)
        db.commit()
        db.refresh(habit)
        return habit.id
    finally:
        db.close()


def test_agenda_schema_fields_exist():
    assert hasattr(Habit, "source_type")
    assert hasattr(Habit, "source_ref")
    assert hasattr(Habit, "auto_managed")
    assert hasattr(Habit, "archived_at")
    assert hasattr(Habit, "agenda_duration_minutes")
    assert hasattr(DailyAgendaPlacement, "start_time")
    assert hasattr(DailyAgendaPlacement, "duration_minutes")


def test_sunday_quest_is_absent_monday_without_archive(client):
    habit_id = add_habit(name="Sunday admin", scheduled_days="0")

    sunday = client.get("/api/v1/agenda?date=2026-07-05", headers={"X-User-ID": "1"})
    assert sunday.status_code == 200
    assert [q["habit_id"] for q in sunday.json()["unplaced_quests"]] == [habit_id]

    monday = client.get("/api/v1/agenda?date=2026-07-06", headers={"X-User-ID": "1"})
    assert monday.status_code == 200
    assert monday.json()["unplaced_quests"] == []

    habits = client.get("/api/v1/habits", headers={"X-User-ID": "1"}).json()
    sunday_habit = next(h for h in habits if h["id"] == habit_id)
    assert sunday_habit["archived_at"] is None


def test_generated_focus_quests_are_reused_across_unpin_repin(client):
    db = TestingSessionLocal()
    try:
        db.add(Goal(id=10, user_id=1, title="Business", description="Build business"))
        db.commit()
    finally:
        db.close()

    response = client.put(
        "/api/v1/profile/pins",
        json={"pinned_goals": [10], "pinned_softskills": ["python"]},
        headers={"X-User-ID": "1"},
    )
    assert response.status_code == 200

    agenda = client.get("/api/v1/agenda?date=2026-07-06", headers={"X-User-ID": "1"})
    assert agenda.status_code == 200
    quests = agenda.json()["unplaced_quests"]
    goal_quest = next(q for q in quests if q["source_type"] == "goal")
    skill_quest = next(q for q in quests if q["source_type"] == "softskill")
    assert goal_quest["needs_configuration"] is True
    assert skill_quest["needs_configuration"] is True
    original_skill_id = skill_quest["habit_id"]

    response = client.put(
        "/api/v1/profile/pins",
        json={"pinned_goals": [10], "pinned_softskills": []},
        headers={"X-User-ID": "1"},
    )
    assert response.status_code == 200
    agenda = client.get("/api/v1/agenda?date=2026-07-06", headers={"X-User-ID": "1"})
    assert all(
        q["source_type"] != "softskill" for q in agenda.json()["unplaced_quests"]
    )

    response = client.put(
        "/api/v1/profile/pins",
        json={"pinned_goals": [10], "pinned_softskills": ["python"]},
        headers={"X-User-ID": "1"},
    )
    assert response.status_code == 200
    agenda = client.get("/api/v1/agenda?date=2026-07-06", headers={"X-User-ID": "1"})
    skill_quest_again = next(
        q for q in agenda.json()["unplaced_quests"] if q["source_type"] == "softskill"
    )
    assert skill_quest_again["habit_id"] == original_skill_id


def test_placement_update_rejects_overlap_and_delete_unplaces(client):
    first_id = add_habit(name="Deep work", agenda_duration_minutes=30)
    second_id = add_habit(name="Review", agenda_duration_minutes=30)

    response = client.put(
        f"/api/v1/agenda/2026-07-06/quests/{first_id}/placement",
        json={"start_time": "08:00", "duration_minutes": 30},
        headers={"X-User-ID": "1"},
    )
    assert response.status_code == 200
    assert response.json()["placed_quests"][0]["start_time"] == "08:00"

    overlap = client.put(
        f"/api/v1/agenda/2026-07-06/quests/{second_id}/placement",
        json={"start_time": "08:15", "duration_minutes": 30},
        headers={"X-User-ID": "1"},
    )
    assert overlap.status_code == 422
    assert "Chevauchement" in overlap.json()["detail"]

    invalid_snap = client.put(
        f"/api/v1/agenda/2026-07-06/quests/{second_id}/placement",
        json={"start_time": "08:10", "duration_minutes": 30},
        headers={"X-User-ID": "1"},
    )
    assert invalid_snap.status_code == 422

    removed = client.delete(
        f"/api/v1/agenda/2026-07-06/quests/{first_id}/placement",
        headers={"X-User-ID": "1"},
    )
    assert removed.status_code == 200
    assert removed.json()["placed_quests"] == []
    assert {q["habit_id"] for q in removed.json()["unplaced_quests"]} == {
        first_id,
        second_id,
    }


def test_save_as_template_reuses_daily_placement_on_future_dates(client):
    habit_id = add_habit(name="Daily code", agenda_duration_minutes=45)
    placed = client.put(
        f"/api/v1/agenda/2026-07-06/quests/{habit_id}/placement",
        json={"start_time": "07:45", "duration_minutes": 45},
        headers={"X-User-ID": "1"},
    )
    assert placed.status_code == 200

    saved = client.post(
        "/api/v1/agenda/2026-07-06/save-as-template",
        json={"template_name": "regular"},
        headers={"X-User-ID": "1"},
    )
    assert saved.status_code == 200
    assert saved.json()["default_placements_count"] == 1

    future = client.get("/api/v1/agenda?date=2026-07-07", headers={"X-User-ID": "1"})
    assert future.status_code == 200
    placed_quest = future.json()["placed_quests"][0]
    assert placed_quest["habit_id"] == habit_id
    assert placed_quest["start_time"] == "07:45"
    assert placed_quest["placement_source"] == "template"


def test_budget_totals_include_unplaced_visible_quests(client):
    add_habit(name="Focus A", effort_type="cerveau", effort_duration=1.5)
    add_habit(name="Focus B", effort_type="cerveau", effort_duration=1.5)

    response = client.get("/api/v1/agenda?date=2026-07-06", headers={"X-User-ID": "1"})
    assert response.status_code == 200
    data = response.json()
    assert data["effort_totals"]["cerveau"] == 3.0
    assert any("cerveau" in warning for warning in data["warnings"])


def test_archive_and_unarchive_are_explicit(client):
    habit_id = add_habit(name="Archive me")

    archived = client.post(
        f"/api/v1/habits/{habit_id}/archive", headers={"X-User-ID": "1"}
    )
    assert archived.status_code == 200
    agenda = client.get("/api/v1/agenda?date=2026-07-06", headers={"X-User-ID": "1"})
    assert agenda.json()["unplaced_quests"] == []

    bank = client.get(
        "/api/v1/habits?include_archived=true", headers={"X-User-ID": "1"}
    )
    assert (
        next(h for h in bank.json() if h["id"] == habit_id)["archived_at"] is not None
    )

    unarchived = client.post(
        f"/api/v1/habits/{habit_id}/unarchive", headers={"X-User-ID": "1"}
    )
    assert unarchived.status_code == 200
    agenda = client.get("/api/v1/agenda?date=2026-07-06", headers={"X-User-ID": "1"})
    assert [q["habit_id"] for q in agenda.json()["unplaced_quests"]] == [habit_id]
