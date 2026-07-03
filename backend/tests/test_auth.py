import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import src.api.routes as routes
from src.database.models import AuthDevice, User
from src.database.session import Base, get_db
from src.main import app


TEST_DB_FILE = "backend/tests/.test_auth.db"
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
def setup(monkeypatch):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    db.add(User(id=1, username="Gabriel", xp=0, level=1, gold=0, is_admin=True))
    db.commit()
    db.close()

    monkeypatch.setattr(routes, "AUTH_BOOTSTRAP_CODE", "setup-code")
    monkeypatch.setattr(routes, "HABIT_API_TOKEN", "api-token")
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)


@pytest.fixture
def client():
    return TestClient(app)


def bootstrap(client):
    response = client.post(
        "/api/v1/auth/bootstrap",
        json={
            "bootstrap_code": "setup-code",
            "password": "correct-password",
            "device_name": "admin laptop",
        },
    )
    assert response.status_code == 200
    return response


def test_bootstrap_creates_password_session_and_approved_device(client):
    bootstrap(client)

    status = client.get("/api/v1/auth/status")
    assert status.status_code == 200
    assert status.json()["authenticated"] is True
    assert status.json()["user"]["username"] == "Gabriel"
    assert status.json()["device_status"] == "approved"

    db = TestingSessionLocal()
    try:
        user = db.query(User).filter_by(username="Gabriel").one()
        assert user.password_hash
        assert user.is_admin is True
        assert db.query(AuthDevice).filter_by(status="approved").count() == 1
    finally:
        db.close()


def test_x_user_id_alone_is_rejected_after_auth_is_configured(client):
    bootstrap(client)

    unauthenticated = TestClient(app)
    response = unauthenticated.get("/api/v1/habits", headers={"X-User-ID": "1"})
    assert response.status_code == 401


def test_machine_token_allows_api_access(client):
    bootstrap(client)

    unauthenticated = TestClient(app)
    response = unauthenticated.get(
        "/api/v1/habits",
        headers={"Authorization": "Bearer api-token", "X-User-ID": "1"},
    )
    assert response.status_code == 200


def test_new_device_is_auto_approved(client):
    bootstrap(client)

    phone = TestClient(app)
    request = phone.post(
        "/api/v1/auth/devices/request", json={"device_name": "phone"}
    )
    assert request.status_code == 200
    assert request.json()["status"] == "approved"

    login = phone.post(
        "/api/v1/auth/login",
        json={"username": "Gabriel", "password": "correct-password"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["username"] == "Gabriel"
