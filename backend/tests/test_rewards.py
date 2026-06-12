import os
import pytest
import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.session import Base, get_db
from src.database.models import User, Reward, Goal, UserSoftskillProgress
from src.main import app

TEST_DB_FILE = "backend/tests/.test_rewards.db"
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
def mock_config_file(monkeypatch, tmp_path):
    """Fixture to mock the softskills config path with a temporary file."""
    temp_config_file = tmp_path / "test_softskills_tree.json"
    initial_config = {
        "branches": {
            "communication": {"color": "#8b5cf6", "pale_color": "#ddd"}
        },
        "skills": [
            {
                "id": "ecoute",
                "name": "Écoute Active",
                "description": "Savoir écouter autrui.",
                "branch": "communication",
                "prerequisites": [],
                "related": [],
                "x": 100,
                "y": 100
            },
            {
                "id": "orateur",
                "name": "Orateur",
                "description": "Savoir parler en public.",
                "branch": "communication",
                "prerequisites": ["ecoute"],
                "related": [],
                "x": 200,
                "y": 100
            }
        ]
    }
    with open(temp_config_file, "w", encoding="utf-8") as f:
        json.dump(initial_config, f, indent=2)

    from src.services import softskill_service
    monkeypatch.setattr(softskill_service, "_get_config_path", lambda: str(temp_config_file))
    softskill_service._tree_config = None
    yield temp_config_file

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
        
        # Seed goals
        g1 = Goal(id=1, user_id=1, title="Devenir Riche", description="1M$", completed=False)
        g2 = Goal(id=2, user_id=1, title="Devenir Sage", description="Méditer", completed=True)
        db.add_all([g1, g2])
        
        # Seed softskill progress
        sp1 = UserSoftskillProgress(user_id=1, softskill_id="ecoute", completed=True)
        db.add(sp1)
        
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

class TestRewardShop:
    
    def test_create_reward_success(self, client):
        response = client.post(
            "/api/v1/rewards",
            json={
                "title": "Une bonne bière",
                "description": "Une IPA bien fraîche",
                "gold_cost": 25,
                "is_one_time": False
            },
            headers={"X-User-ID": "1"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["reward"]["title"] == "Une bonne bière"
        assert data["reward"]["gold_cost"] == 25
        assert data["reward"]["required_softskill_id"] is None

    def test_create_reward_invalid_cost(self, client):
        response = client.post(
            "/api/v1/rewards",
            json={
                "title": "Une bière gratuite ?",
                "gold_cost": -5,
                "is_one_time": False
            },
            headers={"X-User-ID": "1"}
        )
        assert response.status_code == 422

    def test_get_rewards_and_lock_states(self, client):
        # Create rewards with different requirements
        # R1: requires uncompleted Goal 1
        client.post(
            "/api/v1/rewards",
            json={
                "title": "Achat de voiture",
                "gold_cost": 50,
                "required_goal_id": 1,
                "is_one_time": True
            },
            headers={"X-User-ID": "1"}
        )
        # R2: requires completed Goal 2
        client.post(
            "/api/v1/rewards",
            json={
                "title": "Séance de spa",
                "gold_cost": 30,
                "required_goal_id": 2,
                "is_one_time": False
            },
            headers={"X-User-ID": "1"}
        )
        # R3: requires completed Softskill "ecoute"
        client.post(
            "/api/v1/rewards",
            json={
                "title": "Discussion Premium",
                "gold_cost": 10,
                "required_softskill_id": "ecoute",
                "is_one_time": False
            },
            headers={"X-User-ID": "1"}
        )
        # R4: requires uncompleted Softskill "orateur"
        client.post(
            "/api/v1/rewards",
            json={
                "title": "Présentation TedX",
                "gold_cost": 40,
                "required_softskill_id": "orateur",
                "is_one_time": False
            },
            headers={"X-User-ID": "1"}
        )

        response = client.get("/api/v1/rewards", headers={"X-User-ID": "1"})
        assert response.status_code == 200
        rewards = response.json()
        
        # Verify lock statuses
        r_car = next(r for r in rewards if r["title"] == "Achat de voiture")
        assert r_car["unlocked"] is False
        assert "Devenir Riche" in r_car["lock_reason"]

        r_spa = next(r for r in rewards if r["title"] == "Séance de spa")
        assert r_spa["unlocked"] is True
        assert r_spa["lock_reason"] is None

        r_disc = next(r for r in rewards if r["title"] == "Discussion Premium")
        assert r_disc["unlocked"] is True
        assert r_disc["lock_reason"] is None

        r_ted = next(r for r in rewards if r["title"] == "Présentation TedX")
        assert r_ted["unlocked"] is False
        assert "Orateur" in r_ted["lock_reason"]

    def test_purchase_reward_success(self, client):
        # Get active rewards
        response = client.get("/api/v1/rewards", headers={"X-User-ID": "1"})
        rewards = response.json()
        r_spa = next(r for r in rewards if r["title"] == "Séance de spa")

        # Initial gold check: Gabriel should have 100 gold
        profile_resp = client.get("/api/v1/profile", headers={"X-User-ID": "1"})
        assert profile_resp.json()["gold"] == 100

        # Purchase Spa reward (cost = 30)
        purchase_resp = client.post(f"/api/v1/rewards/{r_spa['id']}/purchase", headers={"X-User-ID": "1"})
        assert purchase_resp.status_code == 200
        data = purchase_resp.json()
        assert data["status"] == "success"
        assert data["gold_spent"] == 30
        assert data["new_gold"] == 70

        # Verify profile gold is updated
        profile_resp = client.get("/api/v1/profile", headers={"X-User-ID": "1"})
        assert profile_resp.json()["gold"] == 70

    def test_purchase_locked_reward_fails(self, client):
        response = client.get("/api/v1/rewards", headers={"X-User-ID": "1"})
        rewards = response.json()
        r_car = next(r for r in rewards if r["title"] == "Achat de voiture")

        # Purchase car (locked)
        purchase_resp = client.post(f"/api/v1/rewards/{r_car['id']}/purchase", headers={"X-User-ID": "1"})
        assert purchase_resp.status_code == 400
        assert "verrouillée" in purchase_resp.json()["detail"]

    def test_purchase_insufficient_gold_fails(self, client):
        # Create a reward that costs 200 gold (Gabriel has 70 gold now)
        response = client.post(
            "/api/v1/rewards",
            json={
                "title": "Voyage spatial",
                "gold_cost": 200,
                "is_one_time": False
            },
            headers={"X-User-ID": "1"}
        )
        r_id = response.json()["reward"]["id"]

        purchase_resp = client.post(f"/api/v1/rewards/{r_id}/purchase", headers={"X-User-ID": "1"})
        assert purchase_resp.status_code == 400
        assert "Or insuffisant" in purchase_resp.json()["detail"]

    def test_purchase_one_time_reward_only_once(self, client):
        # Create a one-time reward (cost = 10)
        response = client.post(
            "/api/v1/rewards",
            json={
                "title": "Badge unique",
                "gold_cost": 10,
                "is_one_time": True
            },
            headers={"X-User-ID": "1"}
        )
        r_id = response.json()["reward"]["id"]

        # Purchase once (succeeds)
        p1 = client.post(f"/api/v1/rewards/{r_id}/purchase", headers={"X-User-ID": "1"})
        assert p1.status_code == 200
        assert p1.json()["new_gold"] == 60

        # Purchase twice (fails)
        p2 = client.post(f"/api/v1/rewards/{r_id}/purchase", headers={"X-User-ID": "1"})
        assert p2.status_code == 400
        assert "déjà" in p2.json()["detail"]

    def test_update_reward(self, client):
        response = client.get("/api/v1/rewards", headers={"X-User-ID": "1"})
        rewards = response.json()
        r_spa = next(r for r in rewards if r["title"] == "Séance de spa")

        # Update description and cost
        update_resp = client.put(
            f"/api/v1/rewards/{r_spa['id']}",
            json={
                "title": "Séance de spa de luxe",
                "description": "Avec massage aux pierres chaudes",
                "gold_cost": 50,
                "is_one_time": False,
                "required_softskill_id": None,
                "required_goal_id": None
            },
            headers={"X-User-ID": "1"}
        )
        assert update_resp.status_code == 200
        data = update_resp.json()
        assert data["reward"]["title"] == "Séance de spa de luxe"
        assert data["reward"]["gold_cost"] == 50
        assert data["reward"]["description"] == "Avec massage aux pierres chaudes"

    def test_delete_reward(self, client):
        response = client.get("/api/v1/rewards", headers={"X-User-ID": "1"})
        rewards = response.json()
        r_spa = next(r for r in rewards if r["title"] == "Séance de spa de luxe")

        # Delete
        del_resp = client.delete(f"/api/v1/rewards/{r_spa['id']}", headers={"X-User-ID": "1"})
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "success"

        # Verify not in list
        get_resp = client.get("/api/v1/rewards", headers={"X-User-ID": "1"})
        assert not any(r["title"] == "Séance de spa de luxe" for r in get_resp.json())
