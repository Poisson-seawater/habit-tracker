import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.session import Base, get_db
from src.database.models import User, Goal
from src.main import app

TEST_DB_FILE = "backend/tests/.test_life_lore.db"
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
        # Seed default user Gabriel
        u = User(id=1, username="Gabriel", chat_id="111", xp=0, level=1, gold=100)
        db.add(u)
        # Seed an initial goal
        g = Goal(id=10, user_id=1, title="Devenir Légende", description="Une longue quête")
        db.add(g)
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

@pytest.fixture
def client():
    return TestClient(app)

def test_life_lore_flow(client):
    # 1. Create a subgoal without is_life_lore (defaults to false)
    response = client.post(
        "/api/v1/goals/10/substeps",
        json={
            "title": "Sous-objectif classique",
            "description": "Une étape normale",
            "gold_reward": 50,
            "stats_json": ["force"],
            "execution_order": 1
        },
        headers={"X-User-ID": "1"}
    )
    assert response.status_code == 201
    classic_substep_id = response.json()["substep"]["id"]
    assert response.json()["substep"]["is_life_lore"] is False

    # 2. Create a subgoal with is_life_lore = True
    response = client.post(
        "/api/v1/goals/10/substeps",
        json={
            "title": "Forger Excalibur",
            "description": "Une étape légendaire gravée dans l'histoire de ma vie",
            "gold_reward": 100,
            "stats_json": ["force", "finance"],
            "execution_order": 2,
            "is_life_lore": True
        },
        headers={"X-User-ID": "1"}
    )
    assert response.status_code == 201
    lore_substep_id = response.json()["substep"]["id"]
    assert response.json()["substep"]["is_life_lore"] is True

    # 3. Fetch profile and verify life_lore_today is empty (none completed yet)
    response = client.get("/api/v1/profile", headers={"X-User-ID": "1"})
    assert response.status_code == 200
    data = response.json()
    assert "life_lore_today" in data
    assert len(data["life_lore_today"]) == 0

    # 4. Complete the classic subgoal
    response = client.post(f"/api/v1/substeps/{classic_substep_id}/complete", headers={"X-User-ID": "1"})
    assert response.status_code == 200

    # 5. Complete the life lore subgoal
    response = client.post(f"/api/v1/substeps/{lore_substep_id}/complete", headers={"X-User-ID": "1"})
    assert response.status_code == 200

    # 6. Fetch profile and verify "Forger Excalibur" is in life_lore_today
    response = client.get("/api/v1/profile", headers={"X-User-ID": "1"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["life_lore_today"]) == 1
    assert data["life_lore_today"][0]["id"] == lore_substep_id
    assert data["life_lore_today"][0]["title"] == "Forger Excalibur"

    # 7. Fetch all-time life lore history and verify only the life lore subgoal appears
    response = client.get("/api/v1/profile/life-lore", headers={"X-User-ID": "1"})
    assert response.status_code == 200
    lore_history = response.json()
    assert len(lore_history) == 1
    assert lore_history[0]["id"] == lore_substep_id
    assert lore_history[0]["title"] == "Forger Excalibur"
    assert lore_history[0]["gold_reward"] == 100
    assert "force" in lore_history[0]["stats"]

    # 8. Update classic subgoal to be life lore
    response = client.put(
        f"/api/v1/substeps/{classic_substep_id}",
        json={
            "title": "Sous-objectif classique promu",
            "description": "Devenu légendaire !",
            "gold_reward": 75,
            "stats_json": ["force"],
            "execution_order": 1,
            "is_life_lore": True
        },
        headers={"X-User-ID": "1"}
    )
    assert response.status_code == 200
    assert response.json()["substep"]["is_life_lore"] is True

    # 9. Verify that both appear in all-time history now
    response = client.get("/api/v1/profile/life-lore", headers={"X-User-ID": "1"})
    assert response.status_code == 200
    lore_history = response.json()
    assert len(lore_history) == 2
    titles = [item["title"] for item in lore_history]
    assert "Forger Excalibur" in titles
    assert "Sous-objectif classique promu" in titles
