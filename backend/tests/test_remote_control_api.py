import json
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Goal, RemoteOperation, Todo, User
from src.database.session import Base, get_db
from src.main import app
from src.services import softskill_service


TEST_DB_FILE = "backend/tests/.test_remote_control.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"
engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup(monkeypatch, tmp_path):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    db.add(User(id=1, username="Gabriel", xp=0, level=1, gold=100))
    db.commit()
    db.close()

    config_path = tmp_path / "softskills_tree.json"
    config_path.write_text(
        json.dumps(
            {
                "branches": {
                    "communication": {
                        "color": "#111111",
                        "pale_color": "#eeeeee",
                    }
                },
                "skills": [],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        softskill_service, "_get_config_path", lambda: str(config_path)
    )
    softskill_service._tree_config = None
    monkeypatch.setattr(
        "src.api.idempotency.SessionLocal", TestingSessionLocal
    )
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    softskill_service._tree_config = None
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)


@pytest.fixture
def client():
    return TestClient(app)


def test_capabilities(client):
    response = client.get("/api/v1/capabilities")
    assert response.status_code == 200
    assert response.json()["protocol_version"] == 1


def test_idempotent_write_replays_without_duplicate(client):
    headers = {"X-User-ID": "1", "Idempotency-Key": "todo-1"}
    payload = {"title": "Faire les impôts", "xp_reward": 10}

    first = client.post("/api/v1/todos", json=payload, headers=headers)
    second = client.post("/api/v1/todos", json=payload, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.headers["Idempotency-Replayed"] == "true"
    assert first.json() == second.json()

    db = TestingSessionLocal()
    try:
        assert db.query(Todo).count() == 1
        operation = db.query(RemoteOperation).one()
        assert operation.status == "completed"
    finally:
        db.close()


def test_idempotency_key_rejects_different_payload(client):
    headers = {"X-User-ID": "1", "Idempotency-Key": "todo-conflict"}
    client.post(
        "/api/v1/todos",
        json={"title": "Premier"},
        headers=headers,
    )
    response = client.post(
        "/api/v1/todos",
        json={"title": "Deuxième"},
        headers=headers,
    )
    assert response.status_code == 409


def test_operation_can_be_recovered(client):
    headers = {"X-User-ID": "1", "Idempotency-Key": "recover-me"}
    client.post(
        "/api/v1/todos",
        json={"title": "Récupérable"},
        headers=headers,
    )
    response = client.get(
        "/api/v1/remote-operations/recover-me",
        headers={"X-User-ID": "1"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["response"]["todo"]["title"] == "Récupérable"


def test_goal_with_substeps_is_created_together(client):
    response = client.post(
        "/api/v1/goals/with-substeps",
        headers={
            "X-User-ID": "1",
            "Idempotency-Key": "goal-tree-1",
        },
        json={
            "title": "Faire le tour du monde",
            "substeps": [
                {
                    "title": "Obtenir un passeport",
                    "gold_reward": 50,
                    "stats_json": ["discipline"],
                },
                {
                    "title": "Créer un budget",
                    "gold_reward": 75,
                    "stats_json": ["finance"],
                },
            ],
        },
    )
    assert response.status_code == 201
    assert len(response.json()["goal"]["substeps"]) == 2

    db = TestingSessionLocal()
    try:
        goal = db.query(Goal).one()
        assert len(goal.substep_links) == 2
    finally:
        db.close()


def test_goal_with_invalid_substep_creates_nothing(client):
    response = client.post(
        "/api/v1/goals/with-substeps",
        headers={"X-User-ID": "1"},
        json={
            "title": "Objectif invalide",
            "substeps": [
                {
                    "title": "Étape",
                    "gold_reward": 10,
                    "stats_json": ["stat_inconnue"],
                }
            ],
        },
    )
    assert response.status_code == 400
    db = TestingSessionLocal()
    try:
        assert db.query(Goal).count() == 0
    finally:
        db.close()


def test_branch_with_skills_is_atomic(client):
    payload = {
        "key": "bon_vivant",
        "color": "#8b5cf6",
        "pale_color": "#ddd6fe",
        "skills": [
            {
                "id": "karaoke",
                "name": "Karaoké",
                "description": "",
            },
            {
                "id": "danse",
                "name": "Danse",
                "description": "",
            },
            {
                "id": "ukulele",
                "name": "Ukulélé",
                "description": "",
            },
        ],
    }
    response = client.post(
        "/api/v1/softskills/branches-with-skills", json=payload
    )
    assert response.status_code == 201
    tree = client.get(
        "/api/v1/softskills", headers={"X-User-ID": "1"}
    ).json()
    assert "bon_vivant" in tree["branches"]
    assert {skill["id"] for skill in tree["skills"]} == {
        "karaoke",
        "danse",
        "ukulele",
    }
    positions = [(skill["x"], skill["y"]) for skill in tree["skills"]]
    assert all(x > 0 and y > 0 for x, y in positions)
    assert len(set(positions)) == 3

    failed = client.post(
        "/api/v1/softskills/branches-with-skills",
        json={
            **payload,
            "key": "autre",
            "skills": [
                {
                    "id": "karaoke",
                    "name": "Doublon",
                    "description": "",
                }
            ],
        },
    )
    assert failed.status_code == 400
    tree_after = client.get(
        "/api/v1/softskills", headers={"X-User-ID": "1"}
    ).json()
    assert "autre" not in tree_after["branches"]


def test_persistent_softskill_config_is_bootstrapped(monkeypatch, tmp_path):
    packaged = tmp_path / "packaged.json"
    packaged.write_text(
        '{"branches":{"base":{"color":"#000","pale_color":"#fff"}},"skills":[]}',
        encoding="utf-8",
    )
    persistent = tmp_path / "data" / "softskills_tree.json"
    monkeypatch.setattr(
        softskill_service,
        "_get_packaged_config_path",
        lambda: str(packaged),
    )

    softskill_service._ensure_config_file(str(persistent))

    assert persistent.exists()
    assert json.loads(persistent.read_text(encoding="utf-8"))["branches"] == {
        "base": {"color": "#000", "pale_color": "#fff"}
    }
