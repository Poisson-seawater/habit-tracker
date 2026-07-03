import os
import pytest
import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.session import Base, get_db
from src.database.models import User, Todo
from src.services.google_sync_service import encrypt_token, decrypt_token
from src.main import app

TEST_DB_FILE = "backend/tests/.test_google_sync.db"
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
        # Seed test user
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


class TestGoogleSync:

    def test_encryption_decryption(self):
        secret = "super-secret-oauth-refresh-token-12345"
        encrypted = encrypt_token(secret)
        assert encrypted != secret
        assert len(encrypted) > 0

        decrypted = decrypt_token(encrypted)
        assert decrypted == secret

    def test_google_status_endpoint_initially_disconnected(self, client):
        response = client.get("/api/v1/auth/google/status", headers={"X-User-ID": "1"})
        assert response.status_code == 200
        data = response.json()
        assert data["is_connected"] is False
        assert data["calendar_id"] is None
        assert data["tasks_list_id"] is None

    def test_google_login_endpoint(self, client):
        # Pass user_id as query parameter
        response = client.get(
            "/api/v1/auth/google/login?user_id=1", follow_redirects=False
        )
        assert response.status_code == 307
        location = response.headers.get("location")
        assert "accounts.google.com" in location
        assert "redirect_uri=" in location
        assert "state=1" in location  # user_id is encoded in state

    def test_google_callback_endpoint_success(self, client, monkeypatch):
        # Mock exchange_auth_code inside routes.py
        async def mock_exchange_auth_code(user_id, code, db):
            user = db.query(User).filter(User.id == user_id).first()
            user.google_access_token = encrypt_token("mock_access")
            user.google_refresh_token = encrypt_token("mock_refresh")
            user.google_calendar_id = "mock_calendar_id"
            user.google_tasks_list_id = "mock_tasks_list_id"
            user.google_token_expiry = datetime.datetime.now() + datetime.timedelta(
                seconds=3600
            )
            db.commit()

        monkeypatch.setattr(
            "src.api.routes.exchange_auth_code", mock_exchange_auth_code
        )

        response = client.get(
            "/api/v1/auth/google/callback?code=mockcode&state=1", follow_redirects=False
        )
        assert response.status_code == 307
        assert "google_success=true" in response.headers.get("location")

        # Query status again to confirm connected state
        status_resp = client.get(
            "/api/v1/auth/google/status", headers={"X-User-ID": "1"}
        )
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["is_connected"] is True
        assert data["calendar_id"] == "mock_calendar_id"
        assert data["tasks_list_id"] == "mock_tasks_list_id"

    def test_todo_crud_triggers_sync_calls(self, client, monkeypatch):
        # Patch routes' SessionLocal to point to TestingSessionLocal
        monkeypatch.setattr("src.api.routes.SessionLocal", TestingSessionLocal)

        sync_created_called = []
        sync_updated_called = []
        sync_deleted_called = []
        sync_completed_called = []

        # Mock service synchronization callbacks with exact signature: (user_id, todo_id, db_session_factory)
        async def mock_sync_todo_created(user_id, todo_id, db_session_factory):
            sync_created_called.append(todo_id)
            # Simulate successfully setting Google Event/Task IDs
            db = db_session_factory()
            todo = db.query(Todo).filter(Todo.id == todo_id).first()
            if todo:
                todo.google_event_id = "mock_event_123"
                todo.google_task_id = "mock_task_123"
                db.commit()
            db.close()

        async def mock_sync_todo_updated(user_id, todo_id, db_session_factory):
            sync_updated_called.append(todo_id)

        async def mock_sync_todo_deleted(
            user_id, event_id, task_id, db_session_factory
        ):
            sync_deleted_called.append((event_id, task_id))

        async def mock_sync_todo_completed(user_id, todo_id, db_session_factory):
            sync_completed_called.append(todo_id)

        monkeypatch.setattr("src.api.routes.sync_todo_created", mock_sync_todo_created)
        monkeypatch.setattr("src.api.routes.sync_todo_updated", mock_sync_todo_updated)
        monkeypatch.setattr("src.api.routes.sync_todo_deleted", mock_sync_todo_deleted)
        monkeypatch.setattr(
            "src.api.routes.sync_todo_completed", mock_sync_todo_completed
        )

        # 1. Create a Todo
        create_resp = client.post(
            "/api/v1/todos",
            json={"title": "Google Integration Test Task", "xp_reward": 10},
            headers={"X-User-ID": "1"},
        )
        assert create_resp.status_code == 201
        todo_id = create_resp.json()["todo"]["id"]

        # Background tasks run synchronously in TestClient, so list should be populated
        assert todo_id in sync_created_called

        # 2. Update Todo
        update_resp = client.put(
            f"/api/v1/todos/{todo_id}",
            json={"title": "Updated Google Integration Test Task", "xp_reward": 15},
            headers={"X-User-ID": "1"},
        )
        assert update_resp.status_code == 200
        assert todo_id in sync_updated_called

        # 3. Complete Todo
        complete_resp = client.post(
            f"/api/v1/todos/{todo_id}/complete", headers={"X-User-ID": "1"}
        )
        assert complete_resp.status_code == 200
        assert todo_id in sync_completed_called

        # 4. Delete Todo
        delete_resp = client.delete(
            f"/api/v1/todos/{todo_id}", headers={"X-User-ID": "1"}
        )
        assert delete_resp.status_code == 200
        assert len(sync_deleted_called) > 0
        assert sync_deleted_called[0] == ("mock_event_123", "mock_task_123")

    def test_export_agenda_endpoint(self, client, monkeypatch):
        export_timeline_called = []

        async def mock_export_timeline_task(
            user_id, start_date, end_date, db_session_factory
        ):
            export_timeline_called.append((user_id, start_date, end_date))

        monkeypatch.setattr(
            "src.api.routes.export_timeline_task",
            mock_export_timeline_task,
        )

        response = client.post(
            "/api/v1/agenda/export-google",
            json={"start_date": "2026-07-01", "end_date": "2026-07-07"},
            headers={"X-User-ID": "1"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "queued"
        assert len(export_timeline_called) > 0
        assert export_timeline_called[0][1] == datetime.date(2026, 7, 1)
        assert export_timeline_called[0][2] == datetime.date(2026, 7, 7)

    def test_google_disconnect_endpoint(self, client):
        # Confirm user is currently connected
        status_resp = client.get(
            "/api/v1/auth/google/status", headers={"X-User-ID": "1"}
        )
        assert status_resp.json()["is_connected"] is True

        # Disconnect
        disconnect_resp = client.post(
            "/api/v1/auth/google/disconnect", headers={"X-User-ID": "1"}
        )
        assert disconnect_resp.status_code == 200
        assert disconnect_resp.json()["status"] == "success"

        # Check status is now disconnected
        status_resp = client.get(
            "/api/v1/auth/google/status", headers={"X-User-ID": "1"}
        )
        assert status_resp.json()["is_connected"] is False
        assert status_resp.json()["calendar_id"] is None
        assert status_resp.json()["tasks_list_id"] is None
