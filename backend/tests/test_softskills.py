"""
Tests for the Softskill Progress Tree feature.
Covers: service config loading, cycle validation, API routes.
"""

import json
import os
import pytest
import tempfile

from src.services.softskill_service import (
    _positions_overlap,
    load_tree_config,
    repair_skill_positions,
    validate_no_cycles,
)


@pytest.fixture(autouse=True)
def mock_config_file(monkeypatch, tmp_path):
    """Fixture to mock the softskills config path with a temporary file."""
    temp_config_file = tmp_path / "test_softskills_tree.json"
    initial_config = {
        "branches": {
            "communication": {"color": "#8b5cf6", "pale_color": "#ddd"},
            "leadership": {"color": "#f59e0b", "pale_color": "#eee"},
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
                "y": 100,
            },
            {
                "id": "orateur",
                "name": "Orateur",
                "description": "Savoir parler en public.",
                "branch": "communication",
                "prerequisites": ["ecoute"],
                "related": [],
                "x": 300,
                "y": 100,
            },
        ],
    }
    with open(temp_config_file, "w", encoding="utf-8") as f:
        json.dump(initial_config, f, indent=2)

    from src.services import softskill_service

    monkeypatch.setattr(
        softskill_service, "_get_config_path", lambda: str(temp_config_file)
    )
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
            assert (
                "pale_color" in branch_data
            ), f"Branch '{branch_name}' missing 'pale_color'"

    def test_load_repairs_zero_and_overlapping_positions(self, mock_config_file):
        config = json.loads(mock_config_file.read_text(encoding="utf-8"))
        config["skills"].extend(
            [
                {
                    "id": "zero",
                    "name": "Zero",
                    "description": "",
                    "branch": "leadership",
                    "prerequisites": [],
                    "related": [],
                    "x": 0,
                    "y": 0,
                    "execution_order": 1,
                },
                {
                    "id": "duplicate",
                    "name": "Duplicate",
                    "description": "",
                    "branch": "communication",
                    "prerequisites": [],
                    "related": [],
                    "x": 100,
                    "y": 100,
                    "execution_order": 1,
                },
            ]
        )
        mock_config_file.write_text(
            json.dumps(config, indent=2),
            encoding="utf-8",
        )

        repaired = load_tree_config(force_reload=True)
        positions = {
            skill["id"]: (skill["x"], skill["y"]) for skill in repaired["skills"]
        }

        assert positions["ecoute"] == (100, 100)
        assert positions["zero"] != (0, 0)
        assert positions["duplicate"] != (100, 100)
        all_positions = list(positions.values())
        for index, position in enumerate(all_positions):
            for other in all_positions[index + 1 :]:
                assert not _positions_overlap(position, other)

        persisted = json.loads(mock_config_file.read_text(encoding="utf-8"))
        assert all(skill["x"] > 0 and skill["y"] > 0 for skill in persisted["skills"])

    def test_dynamic_layout_has_no_fifty_skill_limit(self):
        config = {
            "branches": {"growth": {"color": "#123456", "pale_color": "#abcdef"}},
            "skills": [
                {
                    "id": f"skill_{index}",
                    "name": f"Skill {index}",
                    "description": "",
                    "branch": "growth",
                    "prerequisites": [],
                    "related": [],
                    "x": 0,
                    "y": 0,
                    "execution_order": 1,
                }
                for index in range(55)
            ],
        }

        assert repair_skill_positions(config) is True
        positions = [(skill["x"], skill["y"]) for skill in config["skills"]]
        assert len(set(positions)) == 55
        assert all(x > 0 and y > 0 for x, y in positions)


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
        assert (
            data["data"]["success_criteria_test"]
            == "Écouter 10 personnes sans interrompre"
        )

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
            json={"key": "testbranch", "color": "#111111", "pale_color": "#222222"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["key"] == "testbranch"
        assert data["color"] == "#111111"

        # 2. Update branch
        response = client.put(
            "/api/v1/softskills/branches/testbranch",
            json={
                "new_key": "testbranch_new",
                "color": "#333333",
                "pale_color": "#444444",
            },
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
        # Create prerequisite skill in leadership first
        response = client.post(
            "/api/v1/softskills/skills",
            json={
                "id": "leaderskill",
                "name": "Leader Skill",
                "description": "Desc",
                "branch": "leadership",
                "prerequisites": [],
                "related": [],
                "x": 100,
                "y": 100,
            },
        )
        assert response.status_code == 201

        # 1. Create skill with default order and success criteria test
        response = client.post(
            "/api/v1/softskills/skills",
            json={
                "id": "testskill",
                "name": "Test Skill",
                "description": "Description",
                "branch": "communication",
                "prerequisites": ["leaderskill"],
                "related": [],
                "x": 300,
                "y": 200,
                "success_criteria_test": "Valider 5 appels de prospection",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "testskill"
        assert "leaderskill" in data["prerequisites"]
        assert data["execution_order"] == 1  # default value
        assert data["success_criteria_test"] == "Valider 5 appels de prospection"

        # 1b. Check that get_softskills returns the static success criteria test as progress fallback
        response = client.get("/api/v1/softskills", headers={"X-User-ID": "1"})
        assert response.status_code == 200
        tree_data = response.json()
        target_skill = next(
            (s for s in tree_data["skills"] if s["id"] == "testskill"), None
        )
        assert target_skill is not None
        assert (
            target_skill["progress"]["success_criteria_test"]
            == "Valider 5 appels de prospection"
        )

        # 2. Update skill with cycle (should return 400)
        response = client.put(
            "/api/v1/softskills/skills/leaderskill",
            json={
                "name": "Leader Skill Mod",
                "description": "Desc Mod",
                "branch": "leadership",
                "prerequisites": ["testskill"],
                "related": [],
                "x": 100,
                "y": 100,
                "execution_order": 1,
            },
        )
        assert response.status_code == 400

        # 3. Update skill normally, modifying order and success criteria test
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
                "execution_order": 3,
                "success_criteria_test": "Valider 10 appels",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Skill Mod"
        assert data["x"] == 350
        assert data["execution_order"] == 3
        assert data["success_criteria_test"] == "Valider 10 appels"

        # 3b. Verify get_softskills has the updated fallback
        response = client.get("/api/v1/softskills", headers={"X-User-ID": "1"})
        assert response.status_code == 200
        tree_data = response.json()
        target_skill = next(
            (s for s in tree_data["skills"] if s["id"] == "testskill"), None
        )
        assert target_skill is not None
        assert target_skill["progress"]["success_criteria_test"] == "Valider 10 appels"

        # 4. Delete skill
        response = client.delete("/api/v1/softskills/skills/testskill")
        assert response.status_code == 200
        assert response.json()["deleted_skill"] == "testskill"

        response = client.delete("/api/v1/softskills/skills/leaderskill")
        assert response.status_code == 200

    def test_related_skill_same_branch_fails(self, client):
        """Creating or updating a skill to relate it to a skill in the same branch should return 400."""
        # 1. Try to create a skill with a related skill from the same branch ("ecoute" is in "communication")
        response = client.post(
            "/api/v1/softskills/skills",
            json={
                "id": "invalid_rel",
                "name": "Invalid Relation Skill",
                "description": "Description",
                "branch": "communication",
                "prerequisites": [],
                "related": ["ecoute"],
                "x": 300,
                "y": 200,
            },
        )
        assert response.status_code == 400
        assert "same branch" in response.json()["detail"]

        # 2. Try to update a skill to relate it to a skill in the same branch
        # First, create it validly (related to "confiance" which is in "leadership")
        response = client.post(
            "/api/v1/softskills/skills",
            json={
                "id": "valid_then_invalid",
                "name": "Valid Then Invalid",
                "description": "Description",
                "branch": "communication",
                "prerequisites": [],
                "related": ["confiance"],
                "x": 300,
                "y": 200,
            },
        )
        assert response.status_code == 201

        # Now update it to relate to "ecoute" (same branch "communication")
        response = client.put(
            "/api/v1/softskills/skills/valid_then_invalid",
            json={
                "name": "Valid Then Invalid Mod",
                "description": "Description",
                "branch": "communication",
                "prerequisites": [],
                "related": ["ecoute"],
                "x": 300,
                "y": 200,
            },
        )
        assert response.status_code == 400
        assert "same branch" in response.json()["detail"]

        # Cleanup
        client.delete("/api/v1/softskills/skills/valid_then_invalid")

    def test_prerequisite_same_branch_fails(self, client):
        """Creating or updating a skill to have a prerequisite in the same branch should return 400."""
        # 1. Try to create a skill in "communication" with prerequisite in "communication" ("ecoute")
        response = client.post(
            "/api/v1/softskills/skills",
            json={
                "id": "same_branch_prereq",
                "name": "Same Branch Prereq",
                "description": "Description",
                "branch": "communication",
                "prerequisites": ["ecoute"],
                "related": [],
                "x": 300,
                "y": 200,
            },
        )
        assert response.status_code == 400
        assert "same branch" in response.json()["detail"]

    def test_implicit_level_completion_rule(self, client):
        """Unlocking a higher-level skill requires completing all lower-level same-branch skills."""
        # 1. Create a level 2 skill in communication
        response = client.post(
            "/api/v1/softskills/skills",
            json={
                "id": "lvl2_skill",
                "name": "Level 2 Skill",
                "description": "Description",
                "branch": "communication",
                "prerequisites": [],
                "related": [],
                "x": 300,
                "y": 200,
                "execution_order": 2,
            },
        )
        assert response.status_code == 201

        # 2. Try to complete it (lvl 1 skills "ecoute" and "orateur" in communication are not completed yet)
        response = client.post(
            "/api/v1/softskills/lvl2_skill/complete",
            headers={"X-User-ID": "1"},
            json={"completed": True},
        )
        assert response.status_code == 400
        assert "niveau inférieur" in response.json()["detail"]

        # 3. Complete all level 1 skills (orateur depends on ecoute, so we must complete ecoute first)
        response = client.post(
            "/api/v1/softskills/ecoute/complete",
            headers={"X-User-ID": "1"},
            json={"completed": True},
        )
        assert response.status_code == 200

        response = client.post(
            "/api/v1/softskills/orateur/complete",
            headers={"X-User-ID": "1"},
            json={"completed": True},
        )
        assert response.status_code == 200

        # 4. Now completing the level 2 skill should succeed!
        response = client.post(
            "/api/v1/softskills/lvl2_skill/complete",
            headers={"X-User-ID": "1"},
            json={"completed": True},
        )
        assert response.status_code == 200

        # Cleanup
        client.delete("/api/v1/softskills/skills/lvl2_skill")

    def test_skill_coordinates_are_allocated_and_preserved(self, client):
        response = client.post(
            "/api/v1/softskills/skills",
            json={
                "id": "auto_skill",
                "name": "Auto Skill",
                "description": "",
                "branch": "communication",
                "prerequisites": [],
                "related": [],
                "execution_order": 2,
            },
        )
        assert response.status_code == 201
        created = response.json()
        original_position = (created["x"], created["y"])
        assert created["x"] > 0
        assert created["y"] == 220

        response = client.put(
            "/api/v1/softskills/skills/auto_skill",
            json={
                "name": "Auto Skill Renamed",
                "description": "Updated",
                "branch": "communication",
                "prerequisites": [],
                "related": [],
                "execution_order": 2,
            },
        )
        assert response.status_code == 200
        unchanged = response.json()
        assert (unchanged["x"], unchanged["y"]) == original_position

        response = client.put(
            "/api/v1/softskills/skills/auto_skill",
            json={
                "name": "Auto Skill Renamed",
                "description": "Updated",
                "branch": "communication",
                "prerequisites": [],
                "related": [],
                "execution_order": 3,
            },
        )
        assert response.status_code == 200
        repositioned = response.json()
        assert repositioned["y"] == 360
        assert (repositioned["x"], repositioned["y"]) != original_position

        response = client.delete("/api/v1/softskills/skills/auto_skill")
        assert response.status_code == 200
