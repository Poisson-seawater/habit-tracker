import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.session import Base, get_db
from src.database.models import BiologicalZone, User
from src.database.seed import seed_default_biological_zones
from src.main import app

TEST_DB_FILE = "backend/tests/.test_biological_zones.db"
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
def setup_test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        db.add(User(id=1, username="Gabriel", chat_id="111", xp=0, level=1, gold=100))
        db.commit()
    finally:
        db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db_file():
    yield
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass


client = TestClient(app)


def test_biological_zone_model_fields_exist():
    assert hasattr(BiologicalZone, "zone_name")
    assert hasattr(BiologicalZone, "zone_type")
    assert hasattr(BiologicalZone, "start_time")
    assert hasattr(BiologicalZone, "end_time")
    assert hasattr(BiologicalZone, "color")
    assert hasattr(BiologicalZone, "display_order")
    assert hasattr(User, "biological_zones")


def test_default_biological_zone_seed_creates_expected_zones():
    db = TestingSessionLocal()
    try:
        seed_default_biological_zones(db)
        db.commit()
        zones = (
            db.query(BiologicalZone)
            .filter_by(user_id=1)
            .order_by(BiologicalZone.display_order.asc())
            .all()
        )
    finally:
        db.close()

    assert len(zones) == 5
    assert [(z.zone_name, z.zone_type, z.start_time, z.end_time) for z in zones] == [
        ("Sommeil", "sleep", "23:00", "07:00"),
        ("Focus Profond Matin", "deep_focus", "08:00", "12:00"),
        ("Repos / Dejeuner", "rest", "12:00", "13:00"),
        ("Pic Physique", "physical_peak", "14:00", "17:00"),
        ("Zone Creative", "creative", "20:00", "22:00"),
    ]


def test_get_biological_zones_seeds_defaults_for_user_without_zones():
    response = client.get("/api/v1/biological-zones", headers={"X-User-ID": "1"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    assert {zone["zone_type"] for zone in data} == {
        "sleep",
        "deep_focus",
        "rest",
        "physical_peak",
        "creative",
    }


def test_biological_zones_crud_operations():
    create_payload = {
        "zone_name": "Focus court",
        "zone_type": "deep_focus",
        "start_time": "08:00",
        "end_time": "10:00",
        "display_order": 1,
    }
    create_response = client.post(
        "/api/v1/biological-zones",
        json=create_payload,
        headers={"X-User-ID": "1"},
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["zone_name"] == "Focus court"
    assert created["zone_type"] == "deep_focus"

    list_response = client.get(
        "/api/v1/biological-zones",
        headers={"X-User-ID": "1"},
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    update_response = client.put(
        f"/api/v1/biological-zones/{created['id']}",
        json={"zone_name": "Focus allonge", "end_time": "11:00"},
        headers={"X-User-ID": "1"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["zone_name"] == "Focus allonge"
    assert update_response.json()["end_time"] == "11:00"

    delete_response = client.delete(
        f"/api/v1/biological-zones/{created['id']}",
        headers={"X-User-ID": "1"},
    )
    assert delete_response.status_code == 200
    assert delete_response.json() == {"status": "deleted", "id": created["id"]}

    list_response = client.get(
        "/api/v1/biological-zones",
        headers={"X-User-ID": "1"},
    )
    assert len(list_response.json()) == 5


def test_overlap_detection_rejects_overlapping_zone():
    response = client.post(
        "/api/v1/biological-zones",
        json={
            "zone_name": "Focus matin",
            "zone_type": "deep_focus",
            "start_time": "08:00",
            "end_time": "12:00",
        },
        headers={"X-User-ID": "1"},
    )
    assert response.status_code == 201

    overlap_response = client.post(
        "/api/v1/biological-zones",
        json={
            "zone_name": "Chevauchement",
            "zone_type": "rest",
            "start_time": "09:00",
            "end_time": "11:00",
        },
        headers={"X-User-ID": "1"},
    )
    assert overlap_response.status_code == 422
    overlap_data = overlap_response.json()
    assert "Focus matin" in overlap_data["detail"]
    assert overlap_data["code"] == "biological_zone_overlap"
    assert overlap_data["suggestion"] == {
        "start_time": "12:00",
        "end_time": "14:00",
    }


def test_overlap_suggestion_stops_at_midnight_without_wrapping():
    response = client.post(
        "/api/v1/biological-zones",
        json={
            "zone_name": "Long bloc",
            "zone_type": "deep_focus",
            "start_time": "08:00",
            "end_time": "23:00",
        },
        headers={"X-User-ID": "1"},
    )
    assert response.status_code == 201

    overlap_response = client.post(
        "/api/v1/biological-zones",
        json={
            "zone_name": "Sans place",
            "zone_type": "rest",
            "start_time": "09:00",
            "end_time": "11:00",
        },
        headers={"X-User-ID": "1"},
    )
    data = overlap_response.json()
    assert overlap_response.status_code == 422
    assert data["suggestion"] is None
    assert "Aucun creneau libre" in data["suggestion_message"]


def test_overlap_suggestion_can_end_at_midnight():
    response = client.post(
        "/api/v1/biological-zones",
        json={
            "zone_name": "Soiree",
            "zone_type": "social",
            "start_time": "20:00",
            "end_time": "22:00",
        },
        headers={"X-User-ID": "1"},
    )
    assert response.status_code == 201

    overlap_response = client.post(
        "/api/v1/biological-zones",
        json={
            "zone_name": "Fin de journee",
            "zone_type": "creative",
            "start_time": "21:00",
            "end_time": "23:00",
        },
        headers={"X-User-ID": "1"},
    )
    assert overlap_response.json()["suggestion"] == {
        "start_time": "22:00",
        "end_time": "00:00",
    }


def test_overnight_zone_accepts_adjacent_ranges_and_rejects_wrapped_overlap():
    sleep_response = client.post(
        "/api/v1/biological-zones",
        json={
            "zone_name": "Sommeil",
            "zone_type": "sleep",
            "start_time": "23:00",
            "end_time": "07:00",
        },
        headers={"X-User-ID": "1"},
    )
    assert sleep_response.status_code == 201

    adjacent_response = client.post(
        "/api/v1/biological-zones",
        json={
            "zone_name": "Reveil",
            "zone_type": "rest",
            "start_time": "07:00",
            "end_time": "08:00",
        },
        headers={"X-User-ID": "1"},
    )
    assert adjacent_response.status_code == 201

    overlap_response = client.post(
        "/api/v1/biological-zones",
        json={
            "zone_name": "Mauvaise transition",
            "zone_type": "creative",
            "start_time": "22:30",
            "end_time": "23:30",
        },
        headers={"X-User-ID": "1"},
    )
    assert overlap_response.status_code == 422


def test_invalid_zone_type_rejected():
    response = client.post(
        "/api/v1/biological-zones",
        json={
            "zone_name": "Invalide",
            "zone_type": "cerveau",
            "start_time": "08:00",
            "end_time": "09:00",
        },
        headers={"X-User-ID": "1"},
    )
    assert response.status_code == 422
