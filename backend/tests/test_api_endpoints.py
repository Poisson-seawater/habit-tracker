import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.session import Base, get_db
from src.database.models import User, Habit, PerfectDayTemplate, DailyScore, Streak, Goal, SubStep
from src.main import app

TEST_DB_FILE = "tests/test_habit_tracker_api.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

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
        
        # Seed V2 PerfectDayTemplates
        t1 = PerfectDayTemplate(
            user_id=1,
            template_name="week",
            thresholds_json={"discipline": 4}
        )
        t2 = PerfectDayTemplate(
            user_id=1,
            template_name="weekend",
            thresholds_json={"repos": 5}
        )
        db.add_all([t1, t2])
        
        # Seed default habits
        h1 = Habit(
            id=1,
            name="routine_matin",
            type="binary",
            point_rewards={"discipline": 2},
            is_active=True
        )
        h2 = Habit(
            id=2,
            name="lecture",
            type="quantitative",
            unit="min",
            point_rewards={"discipline": 2},
            daily_cap=5,
            is_active=True
        )
        db.add_all([h1, h2])
        db.commit()
    finally:
        db.close()
        
    yield
    
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass

client = TestClient(app)

def test_get_profile_endpoint():
    response = client.get("/api/v1/profile")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "Gabriel"
    assert "scores" in data
    assert "stats" in data
    assert "thresholds" in data

def test_get_habits_endpoint():
    response = client.get("/api/v1/habits")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2

def test_post_logs_endpoint():
    response = client.post("/api/v1/logs", json={
        "habit_id": 1,
        "log_type": "done"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "logged"

def test_change_template_success():
    response = client.post("/api/v1/profile/template", json={"template_name": "weekend"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "updated"
    assert data["active_template"] == "weekend"

def test_create_and_complete_todo_endpoints():
    payload = {
        "title": "⚔️ Dompter le Dragon de Fer (Séance Jambes)",
        "xp_reward": 30,
        "stat_reward_1": "discipline",
        "points_reward_1": 5
    }
    response = client.post("/api/v1/todos", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["todo"]["xp_reward"] == 30
    todo_id = data["todo"]["id"]

    response = client.post(f"/api/v1/todos/{todo_id}/complete")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["xp_rewarded"] == 30

def test_goals_and_substeps_crud():
    # 1. Create a Goal
    response = client.post("/api/v1/goals", json={
        "title": "Devenir Millionnaire",
        "description": "Atteindre 1M en actif"
    })
    assert response.status_code == 201
    goal = response.json()["goal"]
    goal_id = goal["id"]

    # 2. Add SubStep
    response = client.post(f"/api/v1/goals/{goal_id}/substeps", json={
        "title": "Trouver un bon avocat",
        "description": "Réseauter pour trouver un expert",
        "gold_reward": 200,
        "stats_json": ["discipline"]
    })
    assert response.status_code == 201
    substep = response.json()["substep"]
    substep_id = substep["id"]
    assert substep["description"] == "Réseauter pour trouver un expert"

    # 3. Retrieve Goals Graphes
    response = client.get("/api/v1/goals")
    assert response.status_code == 200
    goals = response.json()
    assert len(goals) >= 1
    assert goals[-1]["title"] == "Devenir Millionnaire"
    assert goals[-1]["substeps"][0]["title"] == "Trouver un bon avocat"
    assert goals[-1]["substeps"][0]["description"] == "Réseauter pour trouver un expert"

    # 4. Update SubStep
    response = client.put(f"/api/v1/substeps/{substep_id}", json={
        "title": "Trouver un SUPER avocat",
        "description": "Engager le meilleur avocat de la ville",
        "gold_reward": 300,
        "stats_json": ["discipline", "organisation"],
        "blocked_by_ids": []
    })
    assert response.status_code == 200
    substep_updated = response.json()["substep"]
    assert substep_updated["title"] == "Trouver un SUPER avocat"
    assert substep_updated["description"] == "Engager le meilleur avocat de la ville"
    assert substep_updated["gold_reward"] == 300

    # 5. Delete SubStep
    response = client.delete(f"/api/v1/substeps/{substep_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # 6. Update Goal
    response = client.put(f"/api/v1/goals/{goal_id}", json={
        "title": "Devenir Milliardaire",
        "description": "Atteindre 1B en actif"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["goal"]["title"] == "Devenir Milliardaire"

    # 7. Delete Goal
    response = client.delete(f"/api/v1/goals/{goal_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
