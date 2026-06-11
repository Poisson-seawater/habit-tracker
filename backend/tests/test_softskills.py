"""
Tests for the Softskill Progress Tree feature.
Covers: service config loading, cycle validation, API routes.
"""

import json
import os
import pytest
import tempfile

from src.services.softskill_service import validate_no_cycles, load_tree_config


@pytest.fixture(autouse=True)
def mock_config_file(monkeypatch, tmp_path):
    """Fixture to mock the softskills config path with a temporary file."""
    temp_config_file = tmp_path / "test_softskills_tree.json"
    initial_config = {
        "branches": {
            "communication": {"color": "#8b5cf6", "pale_color": "#ddd"},
            "leadership": {"color": "#f59e0b", "pale_color": "#eee"}
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
    # Reset cached tree config
    softskill_service._tree_config = None
    yield temp_config_file


# ---- Config Validation Tests ----


class TestCycleValidation:
    """Test the cyclic dependency detection in softskill prerequisite graphs."""

    def test_no_cycles_valid_config(self):
        """A valid DAG should not raise."""
        config = {
            "branches": {},
            "skills": [
                {"id": "a", "prerequisites": []},
                {"id": "b", "prerequisites": ["a"]},
                {"id": "c", "prerequisites": ["a", "b"]},
            ],
        }
        validate_no_cycles(config)  # Should not raise

    def test_cycle_detected(self):
        """A circular dependency should raise ValueError."""
        config = {
            "branches": {},
            "skills": [
                {"id": "a", "prerequisites": ["b"]},
                {"id": "b", "prerequisites": ["a"]},
            ],
        }
        with pytest.raises(ValueError, match="Cyclic dependency"):
            validate_no_cycles(config)

    def test_self_referencing_cycle(self):
        """A skill that depends on itself should raise ValueError."""
        config = {
            "branches": {},
            "skills": [
                {"id": "a", "prerequisites": ["a"]},
            ],
        }
        with pytest.raises(ValueError, match="Cyclic dependency"):
            validate_no_cycles(config)

    def test_empty_config(self):
        """Empty skills list should not raise."""
        config = {"branches": {}, "skills": []}
        validate_no_cycles(config)  # Should not raise

    def test_unknown_prerequisite_warns(self, caplog):
        """A prerequisite pointing to a non-existent skill should log a warning."""
        config = {
            "branches": {},
            "skills": [
                {"id": "a", "prerequisites": ["nonexistent"]},
            ],
        }
        import logging
        with caplog.at_level(logging.WARNING):
            validate_no_cycles(config)
        assert "unknown prerequisite" in caplog.text.lower()


class TestConfigLoading:
    """Test that the static JSON config loads and caches correctly."""

    def test_load_tree_config_returns_dict(self):
        """The loader should return a dict with branches and skills keys."""
        config = load_tree_config(force_reload=True)
        assert isinstance(config, dict)
        assert "branches" in config
        assert "skills" in config

    def test_skills_have_required_fields(self):
        """Each skill should have id, name, branch, x, y, prerequisites."""
        config = load_tree_config(force_reload=True)
        for skill in config["skills"]:
            assert "id" in skill
            assert "name" in skill
            assert "branch" in skill
            assert "x" in skill
            assert "y" in skill
            assert "prerequisites" in skill

    def test_branches_have_colors(self):
        """Each branch should define color and pale_color."""
        config = load_tree_config(force_reload=True)
        for branch_name, branch_data in config["branches"].items():
            assert "color" in branch_data, f"Branch '{branch_name}' missing 'color'"
            assert "pale_color" in branch_data, f"Branch '{branch_name}' missing 'pale_color'"


# ---- Route Tests (using FastAPI TestClient) ----

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.session import Base, get_db
from src.database.models import User
from src.main import app

TEST_DB_FILE = "backend/tests/.test_softskills.db"
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
    # Set the override during the execution of this module
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
    
    # Clean up override so it doesn't leak to other test modules
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


class TestSoftskillRoutes:
    """Integration tests for the /api/v1/softskills endpoints."""

    def test_get_softskills_returns_200(self, client):
        """GET /softskills should return 200 with tree data."""
        response = client.get("/api/v1/softskills", headers={"X-User-ID": "1"})
        assert response.status_code == 200
        data = response.json()
        assert "branches" in data
        assert "skills" in data
        assert isinstance(data["skills"], list)

    def test_get_softskills_skills_have_progress(self, client):
        """Each skill in the response should have a 'progress' sub-object."""
        response = client.get("/api/v1/softskills", headers={"X-User-ID": "1"})
        data = response.json()
        for skill in data["skills"]:
            assert "progress" in skill
            assert "completed" in skill["progress"]
            assert "current_level" in skill["progress"]

    def test_update_success_test(self, client):
        """POST /softskills/{id}/test should save the test sentence."""
        response = client.post(
            "/api/v1/softskills/ecoute/test",
            json={"success_criteria_test": "Écouter 10 personnes sans interrompre"},
            headers={"X-User-ID": "1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["success_criteria_test"] == "Écouter 10 personnes sans interrompre"

    def test_complete_without_prereqs_fails(self, client):
        """Completing a skill with unmet prerequisites should return 400."""
        response = client.post(
            "/api/v1/softskills/orateur/complete",
            json={"completed": True},
            headers={"X-User-ID": "1"},
        )
        assert response.status_code == 400

    def test_complete_with_no_prereqs_succeeds(self, client):
        """Completing a skill with no prerequisites should succeed."""
        response = client.post(
            "/api/v1/softskills/ecoute/complete",
            json={"completed": True},
            headers={"X-User-ID": "1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["completed"] is True
        assert data["data"]["current_level"] == 100

    def test_branch_crud_endpoints(self, client):
        """Test creating, editing, and deleting a branch via API."""
        # 1. Create branch
        response = client.post(
            "/api/v1/softskills/branches",
            json={"key": "testbranch", "color": "#111111", "pale_color": "#222222"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["key"] == "testbranch"
        assert data["color"] == "#111111"

        # 2. Update branch
        response = client.put(
            "/api/v1/softskills/branches/testbranch",
            json={"new_key": "testbranch_new", "color": "#333333", "pale_color": "#444444"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "testbranch_new"
        assert data["color"] == "#333333"

        # 3. Delete branch
        response = client.delete("/api/v1/softskills/branches/testbranch_new")
        assert response.status_code == 200
        assert response.json()["deleted_branch"] == "testbranch_new"

    def test_skill_crud_endpoints(self, client):
        """Test creating, updating, and deleting a skill node."""
        # 1. Create skill with default order
        response = client.post(
            "/api/v1/softskills/skills",
            json={
                "id": "testskill",
                "name": "Test Skill",
                "description": "Description",
                "branch": "communication",
                "prerequisites": ["ecoute"],
                "related": [],
                "x": 300,
                "y": 200
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "testskill"
        assert "ecoute" in data["prerequisites"]
        assert data["order"] == 1  # default value

        # 2. Update skill with cycle (should return 400)
        response = client.put(
            "/api/v1/softskills/skills/ecoute",
            json={
                "name": "Écoute Active",
                "description": "Savoir écouter autrui.",
                "branch": "communication",
                "prerequisites": ["testskill"],
                "related": [],
                "x": 100,
                "y": 100,
                "order": 1
            }
        )
        assert response.status_code == 400

        # 3. Update skill normally, modifying order
        response = client.put(
            "/api/v1/softskills/skills/testskill",
            json={
                "name": "Test Skill Mod",
                "description": "Description Mod",
                "branch": "communication",
                "prerequisites": [],
                "related": [],
                "x": 350,
                "y": 250,
                "order": 3
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Skill Mod"
        assert data["x"] == 350
        assert data["order"] == 3

        # 4. Delete skill
        response = client.delete("/api/v1/softskills/skills/testskill")
        assert response.status_code == 200
        assert response.json()["deleted_skill"] == "testskill"


