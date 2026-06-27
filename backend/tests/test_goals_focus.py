import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.session import Base, get_db
from src.database.models import User, Goal, SubStep, GoalSubStepLink
from src.main import app

TEST_DB_FILE = "backend/tests/.test_goals_focus.db"
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


def test_create_max_20_goals_limit(client):
    # Fetch initial goals, clear any existing just in case
    db = TestingSessionLocal()
    try:
        db.query(GoalSubStepLink).delete()
        db.query(SubStep).delete()
        db.query(Goal).delete()
        # Reset user pinned
        user = db.query(User).filter_by(id=1).first()
        user.pinned_goals = []
        user.pinned_substeps = []
        db.commit()
    finally:
        db.close()

    # 1. Create 20 goals successfully
    for i in range(20):
        response = client.post(
            "/api/v1/goals",
            json={"title": f"Goal {i+1}", "description": f"Desc {i+1}"},
            headers={"X-User-ID": "1"},
        )
        assert response.status_code == 201

    # 2. Try to create the 21st goal (should fail)
    response = client.post(
        "/api/v1/goals",
        json={"title": "Goal 21", "description": "Should fail"},
        headers={"X-User-ID": "1"},
    )
    assert response.status_code == 400
    assert "Limite de 20 objectifs atteinte" in response.json()["detail"]


def test_pin_goals_limit_and_substep_validation(client):
    db = TestingSessionLocal()
    try:
        # Clear database
        db.query(GoalSubStepLink).delete()
        db.query(SubStep).delete()
        db.query(Goal).delete()
        # Reset user
        user = db.query(User).filter_by(id=1).first()
        user.pinned_goals = []
        user.pinned_substeps = []
        db.commit()

        # Create 4 goals and 1 substep for each of the first 2 goals
        goals = []
        for i in range(4):
            g = Goal(user_id=1, title=f"G {i}", description=f"D {i}")
            db.add(g)
            db.flush()
            goals.append(g)

        s1 = SubStep(user_id=1, title="S1", gold_reward=10)
        s2 = SubStep(user_id=1, title="S2", gold_reward=15)
        db.add(s1)
        db.add(s2)
        db.flush()

        db.add(GoalSubStepLink(goal_id=goals[0].id, substep_id=s1.id))
        db.add(GoalSubStepLink(goal_id=goals[1].id, substep_id=s2.id))
        db.commit()

        goal_ids = [g.id for g in goals]
        substep1_id = s1.id
        substep2_id = s2.id
    finally:
        db.close()

    # 1. Try to pin 4 goals (should fail)
    payload = {
        "pinned_goals": [goal_ids[0], goal_ids[1], goal_ids[2], goal_ids[3]],
        "pinned_substeps": [],
    }
    response = client.put(
        "/api/v1/profile/pins", json=payload, headers={"X-User-ID": "1"}
    )
    assert response.status_code == 400
    assert "maximum 3 objectifs" in response.json()["detail"]

    # 2. Pin 2 goals
    payload = {"pinned_goals": [goal_ids[0], goal_ids[2]], "pinned_substeps": []}
    response = client.put(
        "/api/v1/profile/pins", json=payload, headers={"X-User-ID": "1"}
    )
    assert response.status_code == 200

    # 3. Try to complete substep 2 which belongs to goal_ids[1] (not pinned)
    response = client.post(
        f"/api/v1/substeps/{substep2_id}/complete", headers={"X-User-ID": "1"}
    )
    assert response.status_code == 400
    assert "Focus requis" in response.json()["detail"]

    # 4. Complete substep 1 which belongs to goal_ids[0] (pinned)
    response = client.post(
        f"/api/v1/substeps/{substep1_id}/complete", headers={"X-User-ID": "1"}
    )
    assert response.status_code == 200

    # 5. Try to pin substep 2 in pins PUT, it should be filtered out because goal_ids[1] is not pinned
    payload = {
        "pinned_goals": [goal_ids[0], goal_ids[2]],
        "pinned_substeps": [substep2_id],
    }
    response = client.put(
        "/api/v1/profile/pins", json=payload, headers={"X-User-ID": "1"}
    )
    assert response.status_code == 200

    # Verify that pinned_substeps in profile is empty because it got filtered out
    response = client.get("/api/v1/profile", headers={"X-User-ID": "1"})
    assert response.status_code == 200
    assert response.json()["pinned_substeps"] == []
