import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.session import Base, get_db
from src.database.models import (
    User,
    Habit,
    SubStep,
    PerfectDayTemplate,
    DailyScore,
)
from src.main import app

# Setup test DB specifically for perfect day tests
TEST_DB_FILE = "backend/tests/.test_perfect_day.db"
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
        # Seed default user Gabriel
        u = User(id=1, username="Gabriel", chat_id="111", xp=0, level=1, gold=100)
        db.add(u)
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


# T001: Test to verify schema contains the new columns
def test_perfect_day_new_schema_fields():
    # Verify that new fields exist in PerfectDayTemplate
    assert hasattr(PerfectDayTemplate, "focus_hours")
    assert hasattr(PerfectDayTemplate, "ceilings_json")
    assert hasattr(PerfectDayTemplate, "min_rest_hours")

    # Verify that new fields exist in Habit
    assert hasattr(Habit, "effort_type")
    assert hasattr(Habit, "effort_duration")

    # Verify that new fields exist in SubStep
    assert hasattr(SubStep, "effort_type")
    assert hasattr(SubStep, "effort_duration")


# T005: Test GET /api/v1/templates returns rest, regular, hustle templates with defaults
def test_get_templates_default():
    response = client.get("/api/v1/templates", headers={"X-User-ID": "1"})
    assert response.status_code == 200
    data = response.json()

    assert "rest" in data
    assert "regular" in data
    assert "hustle" in data

    # Check default regular settings
    assert data["regular"]["focus_hours"] == 6.0
    assert data["regular"]["min_rest_hours"] == 8.0
    assert data["regular"]["ceilings"]["musculaire"] == 2.0
    assert data["regular"]["ceilings"]["total"] == 8.0


# T005: Test POST /api/v1/templates updates template values
def test_post_template_updates():
    payload = {
        "template_name": "regular",
        "focus_hours": 7.5,
        "min_rest_hours": 7.0,
        "ceilings": {
            "musculaire": 1.5,
            "cerveau": 1.5,
            "emotionnel_social": 1.5,
            "creatif_divergent": 1.5,
        },
    }

    response = client.post(
        "/api/v1/templates", json=payload, headers={"X-User-ID": "1"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify updates are retrieved via GET
    response = client.get("/api/v1/templates", headers={"X-User-ID": "1"})
    assert response.status_code == 200
    data = response.json()
    assert data["regular"]["focus_hours"] == 7.5
    assert data["regular"]["min_rest_hours"] == 7.0
    assert data["regular"]["ceilings"]["musculaire"] == 1.5
    assert data["regular"]["ceilings"]["total"] == 6.0


# T005: Test POST /api/v1/templates with invalid budget (ceilings total > focus_hours)
def test_post_template_updates_invalid_budget():
    payload = {
        "template_name": "regular",
        "focus_hours": 5.0,
        "min_rest_hours": 7.0,
        "ceilings": {
            "musculaire": 2.0,
            "cerveau": 2.0,
            "emotionnel_social": 2.0,
            "creatif_divergent": 2.0,
        },
    }

    response = client.post(
        "/api/v1/templates", json=payload, headers={"X-User-ID": "1"}
    )
    assert response.status_code == 400
    assert "ne peut pas dépasser l'objectif focus" in response.json()["detail"]


# T009: Test POST /api/v1/habits with effort tags
def test_create_habit_with_effort():
    payload = {
        "name": "Exercice de code",
        "type": "binary",
        "effort_type": "cerveau",
        "effort_duration": 1.5,
    }
    response = client.post("/api/v1/habits", json=payload, headers={"X-User-ID": "1"})
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    habit_id = data["id"]

    # Verify via GET
    response = client.get("/api/v1/habits", headers={"X-User-ID": "1"})
    assert response.status_code == 200
    habits = response.json()
    habit = next(h for h in habits if h["id"] == habit_id)
    assert habit["effort_type"] == "cerveau"
    assert habit["effort_duration"] == 1.5


# T009: Test POST /goals/{goal_id}/substeps with effort tags
def test_create_substep_with_effort():
    # Create goal first
    response = client.post(
        "/api/v1/goals",
        json={"title": "Master Python", "description": "Learn python internals"},
        headers={"X-User-ID": "1"},
    )
    assert response.status_code == 201
    goal_id = response.json()["goal"]["id"]

    # Add substep
    payload = {
        "title": "Practice algorithm problems",
        "description": "Solve 5 problems",
        "gold_reward": 10,
        "effort_type": "cerveau",
        "effort_duration": 2.0,
    }
    response = client.post(
        f"/api/v1/goals/{goal_id}/substeps", json=payload, headers={"X-User-ID": "1"}
    )
    assert response.status_code == 201
    substep_id = response.json()["substep"]["id"]

    # Retrieve goal substeps and verify fields
    response = client.get("/api/v1/goals", headers={"X-User-ID": "1"})
    assert response.status_code == 200
    goals = response.json()
    goal = next(g for g in goals if g["id"] == goal_id)
    substep = next(s for s in goal["substeps"] if s["id"] == substep_id)
    assert substep["effort_type"] == "cerveau"
    assert substep["effort_duration"] == 2.0
