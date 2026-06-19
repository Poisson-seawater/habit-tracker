import os
import pytest
import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.session import Base, get_db
from src.database.models import User, Reward
from src.main import app

TEST_DB_FILE = "backend/tests/.test_allostasis_rewards.db"
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
        # Seed default user Gabriel with 100 gold
        u = User(id=1, username="Gabriel", chat_id="111", xp=0, level=1, gold=100)
        db.add(u)
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


class TestAllostasisRewards:

    def test_create_allostasis_reward_zero_cost(self, client):
        # Creating an allostasis reward forces gold cost to 0
        response = client.post(
            "/api/v1/rewards",
            json={
                "title": "25 min TV Show",
                "description": "Watch series",
                "gold_cost": 50,  # Should be forced to 0
                "category": "allostasis_daily",
                "is_one_time": False,
            },
            headers={"X-User-ID": "1"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["reward"]["gold_cost"] == 0
        assert data["reward"]["category"] == "allostasis_daily"

    def test_create_allostasis_reward_capping_limit(self, client):
        # We already created 1 daily item ("25 min TV Show"). Let's create 2 more.
        for i in range(2):
            resp = client.post(
                "/api/v1/rewards",
                json={
                    "title": f"Daily Item {i}",
                    "gold_cost": 0,
                    "category": "allostasis_daily",
                },
                headers={"X-User-ID": "1"},
            )
            assert resp.status_code == 201

        # Attempting to create a 4th daily item should fail
        resp = client.post(
            "/api/v1/rewards",
            json={
                "title": "4th Daily Item",
                "gold_cost": 0,
                "category": "allostasis_daily",
            },
            headers={"X-User-ID": "1"},
        )
        assert resp.status_code == 400
        assert "3 items" in resp.json()["detail"]

        # The same limit (3) applies to allostasis_weekly
        for i in range(3):
            resp = client.post(
                "/api/v1/rewards",
                json={
                    "title": f"Weekly Item {i}",
                    "gold_cost": 0,
                    "category": "allostasis_weekly",
                },
                headers={"X-User-ID": "1"},
            )
            assert resp.status_code == 201

        resp = client.post(
            "/api/v1/rewards",
            json={
                "title": "4th Weekly Item",
                "gold_cost": 0,
                "category": "allostasis_weekly",
            },
            headers={"X-User-ID": "1"},
        )
        assert resp.status_code == 400
        assert "3 items" in resp.json()["detail"]

    def test_purchase_allostasis_reward_free(self, client):
        # Let's verify Gabriel has 100 gold
        profile_resp = client.get("/api/v1/profile", headers={"X-User-ID": "1"})
        assert profile_resp.json()["gold"] == 100

        # Fetch allostasis rewards
        rewards_resp = client.get("/api/v1/rewards", headers={"X-User-ID": "1"})
        rewards = rewards_resp.json()
        daily_item = next(r for r in rewards if r["category"] == "allostasis_daily")

        # Purchase daily item
        purchase_resp = client.post(
            f"/api/v1/rewards/{daily_item['id']}/purchase", headers={"X-User-ID": "1"}
        )
        assert purchase_resp.status_code == 200
        data = purchase_resp.json()
        assert data["status"] == "success"
        assert data["gold_spent"] == 0
        assert data["new_gold"] == 100  # Gold remained 100

        # Fetch reward again to check last_purchased_at is populated and is_available is false
        rewards_resp = client.get("/api/v1/rewards", headers={"X-User-ID": "1"})
        updated_rewards = rewards_resp.json()
        purchased_item = next(r for r in updated_rewards if r["id"] == daily_item["id"])
        assert purchased_item["last_purchased_at"] is not None
        assert purchased_item["is_available"] is False

    def test_purchase_allostasis_reward_limit_same_period(self, client):
        # Fetch the same daily item purchased in the previous test
        rewards_resp = client.get("/api/v1/rewards", headers={"X-User-ID": "1"})
        daily_item = next(
            r
            for r in rewards_resp.json()
            if r["category"] == "allostasis_daily"
            and r["last_purchased_at"] is not None
        )

        # Attempting to purchase it again today must fail
        purchase_resp = client.post(
            f"/api/v1/rewards/{daily_item['id']}/purchase", headers={"X-User-ID": "1"}
        )
        assert purchase_resp.status_code == 400
        assert "déjà été validé" in purchase_resp.json()["detail"]

    def test_allostasis_daily_recap_inclusion(self, client, monkeypatch):
        # Setup mock Bot and token to test recap inclusion
        sent_messages = []

        class MockBot:
            def __init__(self, token):
                self.token = token

            async def send_message(self, chat_id, text, parse_mode=None):
                sent_messages.append(text)

        monkeypatch.setattr("src.bot.scheduler.Bot", MockBot)
        monkeypatch.setattr("src.bot.scheduler.TELEGRAM_BOT_TOKEN", "mock_token")
        monkeypatch.setattr("src.config.TELEGRAM_GROUP_ID", "mock_group_id")

        # Override the database session inside the scheduler to use TestingSessionLocal
        # since it uses SessionLocal by default.
        monkeypatch.setattr("src.bot.scheduler.SessionLocal", TestingSessionLocal)

        # Run daily recap generator
        import asyncio
        from src.bot.scheduler import publish_daily_recap

        asyncio.run(publish_daily_recap())

        # Assert recap generated is sent and includes the validated allostasis item name
        assert len(sent_messages) > 0
        recap_msg = sent_messages[0]
        assert "Allostasie" in recap_msg
        assert "25 min TV Show" in recap_msg
