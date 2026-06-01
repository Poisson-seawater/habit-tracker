import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.session import Base, get_db
from src.database.models import User, Habit, DayTemplate, DailyScore, Streak
from src.main import app

TEST_DB_FILE = "backend/tests/test_habit_tracker.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"

# Setup test database and override get_db dependency
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
    # Remove old test DB if it exists
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass
        
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    try:
        # Seed default user Gabriel
        u = User(id=1, username="Gabriel", chat_id="111")
        db.add(u)
        
        # Seed default templates
        t1 = DayTemplate(
            id=1,
            name="Semaine",
            acceptable_thresholds={"discipline": 4},
            perfect_thresholds={"discipline": 8}
        )
        t2 = DayTemplate(
            id=2,
            name="Weekend",
            acceptable_thresholds={"repos": 5},
            perfect_thresholds={"repos": 10}
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
    
    # Clean up test DB after tests
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass

client = TestClient(app)

# --- GET/POST endpoints tests ---

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
    assert data[0]["name"] == "routine_matin"
    assert data[0]["type"] == "binary"
    assert data[1]["name"] == "lecture"
    assert data[1]["type"] == "quantitative"

def test_get_streaks_endpoint():
    response = client.get("/api/v1/streaks")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_post_logs_endpoint():
    # Post a completion log for routine_matin (habit 1)
    response = client.post("/api/v1/logs", json={
        "habit_id": 1,
        "log_type": "done"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "logged"
    assert "affected_stats" in data
    assert data["affected_stats"]["discipline"] == 2

# --- Configuration tests ---

def test_create_habit_success():
    payload = {
        "name": "nouvelle_habitude",
        "type": "binary",
        "description": "Une habitude de test",
        "point_rewards": {"discipline": 3},
        "scheduled_days": "0,1,2,3,4,5,6"
    }
    response = client.post("/api/v1/habits", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "nouvelle_habitude"
    assert data["status"] == "success"

def test_create_habit_duplicate():
    payload = {
        "name": "nouvelle_habitude",
        "type": "binary",
        "point_rewards": {"discipline": 3}
    }
    response = client.post("/api/v1/habits", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

def test_change_template_success():
    response = client.post("/api/v1/profile/template", json={"template_name": "Weekend"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "updated"
    assert data["active_template"] == "Weekend"

def test_get_history_endpoint():
    response = client.get("/api/v1/history")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 30
    assert "date" in data[0]
    assert "status" in data[0]
    assert "label" in data[0]
