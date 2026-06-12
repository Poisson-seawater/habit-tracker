import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.session import Base, get_db
from src.database.models import User
from src.main import app

TEST_DB_FILE = "backend/tests/.test_profile_pins.db"
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

def test_profile_pins_flow(client):
    # 1. Fetch initial profile pins (should be empty lists)
    response = client.get("/api/v1/profile", headers={"X-User-ID": "1"})
    assert response.status_code == 200
    data = response.json()
    assert "pinned_substeps" in data
    assert "pinned_softskills" in data
    assert data["pinned_substeps"] == []
    assert data["pinned_softskills"] == []

    # 2. Update profile pins
    payload = {
        "pinned_substeps": [42, 43],
        "pinned_softskills": ["focus", "lecture"]
    }
    response = client.put("/api/v1/profile/pins", json=payload, headers={"X-User-ID": "1"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["message"] == "Pins updated successfully"

    # 3. Fetch profile pins again and check updated values
    response = client.get("/api/v1/profile", headers={"X-User-ID": "1"})
    assert response.status_code == 200
    data = response.json()
    assert data["pinned_substeps"] == [42, 43]
    assert data["pinned_softskills"] == ["focus", "lecture"]
