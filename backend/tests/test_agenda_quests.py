import datetime
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.session import Base, get_db
from src.database.models import (
    DailyAgendaPlacement,
    GoalSubStepLink,
    Habit,
    PerfectDayTemplate,
    SubStep,
    User,
    Goal,
)
from src.main import app

TEST_DB_FILE = "backend/tests/.test_agenda_quests.db"
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
        db.add(
            PerfectDayTemplate(
                user_id=1,
                template_name="regular",
                focus_hours=6.0,
                min_rest_hours=8.0,
                ceilings_json={
                    "musculaire": 2.0,
                    "cerveau": 2.0,
                    "emotionnel_social": 2.0,
                    "creatif_divergent": 2.0,
                    "total": 8.0,
                },
                agenda_json={
                    "schema_version": 2,
                    "segments": [
                        {
                            "id": "admin-1",
                            "kind": "admin",
                            "start": "13:00",
                            "end": "15:00",
                        }
                    ],
                    "default_placements": [],
                },
            )
        )
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


@pytest.fixture
def client():
    return TestClient(app)


def add_habit(**overrides):
    db = TestingSessionLocal()
    try:
        habit = Habit(
            user_id=1,
            name=overrides.pop("name", "Quest"),
            type=overrides.pop("type", "binary"),
            frequency=overrides.pop("frequency", "daily"),
            scheduled_days=overrides.pop("scheduled_days", "0,1,2,3,4,5,6"),
            is_active=overrides.pop("is_active", True),
            effort_type=overrides.pop("effort_type", "cerveau"),
            effort_duration=overrides.pop("effort_duration", 1.0),
            agenda_duration_minutes=overrides.pop("agenda_duration_minutes", 60),
            **overrides,
        )
        db.add(habit)
        db.commit()
        db.refresh(habit)
        return habit.id
    finally:
        db.close()


def test_agenda_schema_fields_exist():
    assert hasattr(Habit, "source_type")
    assert hasattr(Habit, "source_ref")
    assert hasattr(Habit, "auto_managed")
    assert hasattr(Habit, "archived_at")
    assert hasattr(Habit, "agenda_duration_minutes")
    assert hasattr(Habit, "agenda_placeable")
    assert hasattr(DailyAgendaPlacement, "start_time")
    assert hasattr(DailyAgendaPlacement, "duration_minutes")


def test_sunday_quest_is_absent_monday_without_archive(client):
    habit_id = add_habit(name="Sunday admin", scheduled_days="0")

    sunday = client.get("/api/v1/agenda?date=2026-07-05", headers={"X-User-ID": "1"})
    assert sunday.status_code == 200
    assert [q["habit_id"] for q in sunday.json()["unplaced_quests"]] == [habit_id]

    monday = client.get("/api/v1/agenda?date=2026-07-06", headers={"X-User-ID": "1"})
    assert monday.status_code == 200
    assert monday.json()["unplaced_quests"] == []

    habits = client.get("/api/v1/habits", headers={"X-User-ID": "1"}).json()
    sunday_habit = next(h for h in habits if h["id"] == habit_id)
    assert sunday_habit["archived_at"] is None


def test_quest_bank_lists_non_visible_quests_separately_from_archives(client):
    daily_id = add_habit(name="Daily visible")
    sunday_id = add_habit(name="Sunday banked", scheduled_days="0")
    archived_id = add_habit(
        name="Archived explicit",
        archived_at=datetime.datetime(2026, 7, 1, 12, 0, 0),
    )

    response = client.get(
        "/api/v1/habits/bank?date=2026-07-06", headers={"X-User-ID": "1"}
    )
    assert response.status_code == 200
    data = response.json()

    assert data["date"] == "2026-07-06"
    assert data["day_type"] == "regular"
    assert data["visible_quest_ids"] == [daily_id]

    hidden = data["hidden_quests"]
    assert [quest["habit_id"] for quest in hidden] == [sunday_id]
    assert hidden[0]["archived_at"] is None
    assert hidden[0]["visibility"] == "hidden"
    assert hidden[0]["next_visible_date"] == "2026-07-12"
    assert hidden[0]["bank_reasons"][0]["code"] == "not_scheduled"

    archived = data["archived_quests"]
    assert [quest["habit_id"] for quest in archived] == [archived_id]
    assert archived[0]["visibility"] == "archived"
    assert archived[0]["bank_reasons"][0]["code"] == "archived"


def test_generated_focus_quests_are_reused_across_unpin_repin(client):
    db = TestingSessionLocal()
    try:
        goal = Goal(id=10, user_id=1, title="Business", description="Build business")
        db.add(goal)
        db.flush()
        substep = SubStep(
            id=100,
            user_id=1,
            title="Market research",
            description="Research the market",
            effort_type="cerveau",
            effort_duration=1.5,
        )
        db.add(substep)
        db.flush()
        db.add(GoalSubStepLink(goal_id=10, substep_id=100, execution_order=1))
        db.commit()
    finally:
        db.close()

    # Pin goal (Top 3) + substep + softskill
    response = client.put(
        "/api/v1/profile/pins",
        json={
            "pinned_goals": [10],
            "pinned_substeps": [100],
            "pinned_softskills": ["python"],
        },
        headers={"X-User-ID": "1"},
    )
    assert response.status_code == 200

    agenda = client.get("/api/v1/agenda?date=2026-07-06", headers={"X-User-ID": "1"})
    assert agenda.status_code == 200
    quests = agenda.json()["unplaced_quests"]
    # Should have a substep quest (not a goal quest) and a softskill quest
    substep_quest = next(q for q in quests if q["source_type"] == "substep")
    skill_quest = next(q for q in quests if q["source_type"] == "softskill")
    assert "goal" not in [q["source_type"] for q in quests]
    original_substep_quest_id = substep_quest["habit_id"]
    original_skill_id = skill_quest["habit_id"]

    # Unpin substep → quest should be auto-archived and absent from agenda
    response = client.put(
        "/api/v1/profile/pins",
        json={
            "pinned_goals": [10],
            "pinned_substeps": [],
            "pinned_softskills": ["python"],
        },
        headers={"X-User-ID": "1"},
    )
    assert response.status_code == 200
    agenda = client.get("/api/v1/agenda?date=2026-07-06", headers={"X-User-ID": "1"})
    assert all(q["source_type"] != "substep" for q in agenda.json()["unplaced_quests"])

    # Verify the quest is archived (not deleted)
    bank = client.get(
        "/api/v1/habits?include_archived=true", headers={"X-User-ID": "1"}
    ).json()
    archived_quest = next(h for h in bank if h["id"] == original_substep_quest_id)
    assert archived_quest["archived_at"] is not None

    # Re-pin substep → same quest should be auto-unarchived
    response = client.put(
        "/api/v1/profile/pins",
        json={
            "pinned_goals": [10],
            "pinned_substeps": [100],
            "pinned_softskills": ["python"],
        },
        headers={"X-User-ID": "1"},
    )
    assert response.status_code == 200
    agenda = client.get("/api/v1/agenda?date=2026-07-06", headers={"X-User-ID": "1"})
    substep_quest_again = next(
        q for q in agenda.json()["unplaced_quests"] if q["source_type"] == "substep"
    )
    assert substep_quest_again["habit_id"] == original_substep_quest_id
    # Softskill quest should also still be reused
    skill_quest_again = next(
        q for q in agenda.json()["unplaced_quests"] if q["source_type"] == "softskill"
    )
    assert skill_quest_again["habit_id"] == original_skill_id


def test_placement_update_rejects_overlap_and_delete_unplaces(client):
    first_id = add_habit(name="Deep work", agenda_duration_minutes=30)
    second_id = add_habit(name="Review", agenda_duration_minutes=30)

    response = client.put(
        f"/api/v1/agenda/2026-07-06/quests/{first_id}/placement",
        json={"start_time": "08:00", "duration_minutes": 30},
        headers={"X-User-ID": "1"},
    )
    assert response.status_code == 200
    assert response.json()["placed_quests"][0]["start_time"] == "08:00"

    overlap = client.put(
        f"/api/v1/agenda/2026-07-06/quests/{second_id}/placement",
        json={"start_time": "08:15", "duration_minutes": 30},
        headers={"X-User-ID": "1"},
    )
    assert overlap.status_code == 200
    shifted = next(
        q for q in overlap.json()["placed_quests"] if q["habit_id"] == second_id
    )
    assert shifted["start_time"] == "08:45"

    invalid_snap = client.put(
        f"/api/v1/agenda/2026-07-06/quests/{first_id}/placement",
        json={"start_time": "08:10", "duration_minutes": 30},
        headers={"X-User-ID": "1"},
    )
    assert invalid_snap.status_code == 422

    removed = client.delete(
        f"/api/v1/agenda/2026-07-06/quests/{first_id}/placement",
        headers={"X-User-ID": "1"},
    )
    assert removed.status_code == 200
    assert [q["habit_id"] for q in removed.json()["placed_quests"]] == [second_id]
    assert {q["habit_id"] for q in removed.json()["unplaced_quests"]} == {
        first_id,
    }


def test_placement_auto_shift_rejects_when_gap_is_too_small(client):
    first_id = add_habit(name="Deep work", agenda_duration_minutes=30)
    second_id = add_habit(name="Review", agenda_duration_minutes=30)
    third_id = add_habit(name="Write", agenda_duration_minutes=30)

    assert (
        client.put(
            f"/api/v1/agenda/2026-07-06/quests/{first_id}/placement",
            json={"start_time": "08:00", "duration_minutes": 30},
            headers={"X-User-ID": "1"},
        ).status_code
        == 200
    )
    assert (
        client.put(
            f"/api/v1/agenda/2026-07-06/quests/{second_id}/placement",
            json={"start_time": "09:00", "duration_minutes": 30},
            headers={"X-User-ID": "1"},
        ).status_code
        == 200
    )

    rejected = client.put(
        f"/api/v1/agenda/2026-07-06/quests/{third_id}/placement",
        json={"start_time": "08:15", "duration_minutes": 30},
        headers={"X-User-ID": "1"},
    )
    assert rejected.status_code == 422
    assert "Aucun creneau libre suffisant" in rejected.json()["detail"]


def test_non_placeable_quest_stays_visible_but_cannot_be_placed(client):
    response = client.post(
        "/api/v1/habits",
        json={
            "name": "Drink water",
            "type": "binary",
            "agenda_placeable": False,
            "agenda_duration_minutes": 15,
        },
        headers={"X-User-ID": "1"},
    )
    assert response.status_code == 201
    habit_id = response.json()["id"]

    habits = client.get("/api/v1/habits", headers={"X-User-ID": "1"}).json()
    created = next(h for h in habits if h["id"] == habit_id)
    assert created["agenda_placeable"] is False

    agenda = client.get("/api/v1/agenda?date=2026-07-06", headers={"X-User-ID": "1"})
    assert agenda.status_code == 200
    item = next(
        q for q in agenda.json()["unplaced_quests"] if q["habit_id"] == habit_id
    )
    assert item["agenda_placeable"] is False
    assert agenda.json()["placed_quests"] == []

    placed = client.put(
        f"/api/v1/agenda/2026-07-06/quests/{habit_id}/placement",
        json={"start_time": "08:00", "duration_minutes": 15},
        headers={"X-User-ID": "1"},
    )
    assert placed.status_code == 422

    updated = client.put(
        f"/api/v1/habits/{habit_id}",
        json={"agenda_placeable": True},
        headers={"X-User-ID": "1"},
    )
    assert updated.status_code == 200

    placed = client.put(
        f"/api/v1/agenda/2026-07-06/quests/{habit_id}/placement",
        json={"start_time": "08:00", "duration_minutes": 15},
        headers={"X-User-ID": "1"},
    )
    assert placed.status_code == 200
    assert [q["habit_id"] for q in placed.json()["placed_quests"]] == [habit_id]


def test_existing_placement_is_ignored_when_quest_becomes_non_placeable(client):
    habit_id = add_habit(name="Floating quest", agenda_duration_minutes=30)
    placed = client.put(
        f"/api/v1/agenda/2026-07-06/quests/{habit_id}/placement",
        json={"start_time": "07:45", "duration_minutes": 30},
        headers={"X-User-ID": "1"},
    )
    assert placed.status_code == 200

    updated = client.put(
        f"/api/v1/habits/{habit_id}",
        json={"agenda_placeable": False},
        headers={"X-User-ID": "1"},
    )
    assert updated.status_code == 200

    agenda = client.get("/api/v1/agenda?date=2026-07-06", headers={"X-User-ID": "1"})
    assert agenda.status_code == 200
    assert agenda.json()["placed_quests"] == []
    item = next(
        q for q in agenda.json()["unplaced_quests"] if q["habit_id"] == habit_id
    )
    assert item["start_time"] is None
    assert item["agenda_placeable"] is False

    saved = client.post(
        "/api/v1/agenda/2026-07-06/save-as-template",
        json={"template_name": "regular"},
        headers={"X-User-ID": "1"},
    )
    assert saved.status_code == 200
    assert saved.json()["default_placements_count"] == 0


def test_save_as_template_reuses_daily_placement_on_future_dates(client):
    habit_id = add_habit(name="Daily code", agenda_duration_minutes=45)
    placed = client.put(
        f"/api/v1/agenda/2026-07-06/quests/{habit_id}/placement",
        json={"start_time": "07:45", "duration_minutes": 45},
        headers={"X-User-ID": "1"},
    )
    assert placed.status_code == 200

    saved = client.post(
        "/api/v1/agenda/2026-07-06/save-as-template",
        json={"template_name": "regular"},
        headers={"X-User-ID": "1"},
    )
    assert saved.status_code == 200
    assert saved.json()["default_placements_count"] == 1

    future = client.get("/api/v1/agenda?date=2026-07-07", headers={"X-User-ID": "1"})
    assert future.status_code == 200
    placed_quest = future.json()["placed_quests"][0]
    assert placed_quest["habit_id"] == habit_id
    assert placed_quest["start_time"] == "07:45"
    assert placed_quest["placement_source"] == "template"


def test_budget_totals_include_unplaced_visible_quests(client):
    add_habit(name="Focus A", effort_type="cerveau", effort_duration=1.5)
    add_habit(name="Focus B", effort_type="cerveau", effort_duration=1.5)

    response = client.get("/api/v1/agenda?date=2026-07-06", headers={"X-User-ID": "1"})
    assert response.status_code == 200
    data = response.json()
    assert data["effort_totals"]["cerveau"] == 3.0
    assert any("cerveau" in warning for warning in data["warnings"])


def test_repos_counts_toward_minimum_rest_budget(client):
    add_habit(name="Nap", effort_type="repos", effort_duration=2.0)

    response = client.get("/api/v1/agenda?date=2026-07-06", headers={"X-User-ID": "1"})
    assert response.status_code == 200
    data = response.json()
    assert data["effort_totals"]["repos"] == 2.0
    assert any("Repos planifie insuffisant" in warning for warning in data["warnings"])


def test_monthly_quest_uses_day_of_month_anchor(client):
    monthly_id = add_habit(
        name="Monthly review",
        frequency="monthly",
        scheduled_days="30",
    )

    due = client.get("/api/v1/agenda?date=2026-07-30", headers={"X-User-ID": "1"})
    assert due.status_code == 200
    assert [q["habit_id"] for q in due.json()["unplaced_quests"]] == [monthly_id]

    not_due = client.get("/api/v1/agenda?date=2026-07-29", headers={"X-User-ID": "1"})
    assert not_due.status_code == 200
    assert not_due.json()["unplaced_quests"] == []


def test_create_monthly_clamps_day_and_weekly_is_rejected(client):
    weekly = client.post(
        "/api/v1/habits",
        json={"name": "Old weekly", "type": "binary", "frequency": "weekly"},
        headers={"X-User-ID": "1"},
    )
    assert weekly.status_code == 400

    monthly = client.post(
        "/api/v1/habits",
        json={
            "name": "Monthly close",
            "type": "binary",
            "frequency": "monthly",
            "scheduled_days": "31",
        },
        headers={"X-User-ID": "1"},
    )
    assert monthly.status_code == 201

    habits = client.get("/api/v1/habits", headers={"X-User-ID": "1"}).json()
    created = next(h for h in habits if h["name"] == "Monthly close")
    assert created["scheduled_days"] == "30"


def test_update_can_clear_effort_type_for_rest_of_the_day(client):
    habit_id = add_habit(name="Clear effort", effort_type="cerveau")

    response = client.put(
        f"/api/v1/habits/{habit_id}",
        json={"effort_type": None},
        headers={"X-User-ID": "1"},
    )
    assert response.status_code == 200

    habits = client.get("/api/v1/habits", headers={"X-User-ID": "1"}).json()
    updated = next(h for h in habits if h["id"] == habit_id)
    assert updated["effort_type"] is None


def test_archive_and_unarchive_are_explicit(client):
    habit_id = add_habit(name="Archive me")
    placed = client.put(
        f"/api/v1/agenda/2026-07-06/quests/{habit_id}/placement",
        json={"start_time": "09:00", "duration_minutes": 60},
        headers={"X-User-ID": "1"},
    )
    assert placed.status_code == 200
    assert [q["habit_id"] for q in placed.json()["placed_quests"]] == [habit_id]

    saved = client.post(
        "/api/v1/agenda/2026-07-06/save-as-template",
        json={"template_name": "regular"},
        headers={"X-User-ID": "1"},
    )
    assert saved.status_code == 200

    db = TestingSessionLocal()
    try:
        for template_name in ("rest", "hustle"):
            db.add(
                PerfectDayTemplate(
                    user_id=1,
                    template_name=template_name,
                    agenda_json={
                        "schema_version": 2,
                        "segments": [],
                        "default_placements": [
                            {
                                "habit_id": habit_id,
                                "start": "10:00",
                                "duration_minutes": 60,
                            }
                        ],
                    },
                )
            )
        db.commit()
    finally:
        db.close()

    archived = client.post(
        f"/api/v1/habits/{habit_id}/archive", headers={"X-User-ID": "1"}
    )
    assert archived.status_code == 200
    agenda = client.get("/api/v1/agenda?date=2026-07-06", headers={"X-User-ID": "1"})
    assert agenda.json()["placed_quests"] == []
    assert agenda.json()["unplaced_quests"] == []

    bank = client.get(
        "/api/v1/habits?include_archived=true", headers={"X-User-ID": "1"}
    )
    assert (
        next(h for h in bank.json() if h["id"] == habit_id)["archived_at"] is not None
    )
    db = TestingSessionLocal()
    try:
        assert (
            db.query(DailyAgendaPlacement)
            .filter_by(user_id=1, habit_id=habit_id)
            .count()
            == 0
        )
        templates = (
            db.query(PerfectDayTemplate)
            .filter(PerfectDayTemplate.template_name.in_(["rest", "regular", "hustle"]))
            .all()
        )
        assert {template.template_name for template in templates} == {
            "rest",
            "regular",
            "hustle",
        }
        for template in templates:
            placements = template.agenda_json.get("default_placements", [])
            assert all(placement["habit_id"] != habit_id for placement in placements)
    finally:
        db.close()

    unarchived = client.post(
        f"/api/v1/habits/{habit_id}/unarchive", headers={"X-User-ID": "1"}
    )
    assert unarchived.status_code == 200
    agenda = client.get("/api/v1/agenda?date=2026-07-06", headers={"X-User-ID": "1"})
    assert agenda.json()["placed_quests"] == []
    assert [q["habit_id"] for q in agenda.json()["unplaced_quests"]] == [habit_id]


def test_habits_include_all_versions_keeps_archived_versions_visible(client):
    v1_id = add_habit(name="Étape 1 - Deep work")
    v2_id = add_habit(
        name="Étape 2 - Deep work",
        archived_at=datetime.datetime(2026, 7, 1, 12, 0, 0),
    )

    default_bank = client.get(
        "/api/v1/habits?include_archived=true", headers={"X-User-ID": "1"}
    )
    assert default_bank.status_code == 200
    assert [habit["id"] for habit in default_bank.json()] == [v2_id]

    all_versions = client.get(
        "/api/v1/habits?include_archived=true&include_all_versions=true",
        headers={"X-User-ID": "1"},
    )
    assert all_versions.status_code == 200
    assert [habit["id"] for habit in all_versions.json()] == [v1_id, v2_id]

    active_all_versions = client.get(
        "/api/v1/habits?include_all_versions=true", headers={"X-User-ID": "1"}
    )
    assert active_all_versions.status_code == 200
    assert [habit["id"] for habit in active_all_versions.json()] == [v1_id]


def test_pinned_goal_alone_does_not_generate_quest(client):
    """Pinning a goal (Top 3) without pinning any substep should NOT create a quest."""
    db = TestingSessionLocal()
    try:
        db.add(Goal(id=20, user_id=1, title="Fitness", description="Get fit"))
        db.commit()
    finally:
        db.close()

    response = client.put(
        "/api/v1/profile/pins",
        json={"pinned_goals": [20]},
        headers={"X-User-ID": "1"},
    )
    assert response.status_code == 200

    agenda = client.get("/api/v1/agenda?date=2026-07-06", headers={"X-User-ID": "1"})
    assert agenda.status_code == 200
    quests = agenda.json()["unplaced_quests"]
    assert all(q["source_type"] not in ("goal", "substep") for q in quests)


def test_unpin_substep_auto_archives_quest(client):
    """Unpinning a substep should auto-archive its generated quest."""
    db = TestingSessionLocal()
    try:
        goal = Goal(id=30, user_id=1, title="Learning", description="Learn things")
        db.add(goal)
        db.flush()
        substep = SubStep(
            id=200,
            user_id=1,
            title="Read chapter 1",
            description="First chapter",
        )
        db.add(substep)
        db.flush()
        db.add(GoalSubStepLink(goal_id=30, substep_id=200, execution_order=1))
        db.commit()
    finally:
        db.close()

    # Pin goal + substep
    client.put(
        "/api/v1/profile/pins",
        json={"pinned_goals": [30], "pinned_substeps": [200]},
        headers={"X-User-ID": "1"},
    )

    # Verify quest exists in agenda
    agenda = client.get("/api/v1/agenda?date=2026-07-06", headers={"X-User-ID": "1"})
    substep_quests = [
        q for q in agenda.json()["unplaced_quests"] if q["source_type"] == "substep"
    ]
    assert len(substep_quests) == 1
    quest_id = substep_quests[0]["habit_id"]

    # Unpin substep (keep goal pinned)
    client.put(
        "/api/v1/profile/pins",
        json={"pinned_goals": [30], "pinned_substeps": []},
        headers={"X-User-ID": "1"},
    )

    # Quest should be absent from agenda
    agenda = client.get("/api/v1/agenda?date=2026-07-06", headers={"X-User-ID": "1"})
    assert all(q["source_type"] != "substep" for q in agenda.json()["unplaced_quests"])

    # Quest should be archived in the bank
    bank = client.get(
        "/api/v1/habits?include_archived=true", headers={"X-User-ID": "1"}
    ).json()
    quest = next(h for h in bank if h["id"] == quest_id)
    assert quest["archived_at"] is not None
    assert quest["source_type"] == "substep"


def test_agenda_quest_done_only_when_target_reached(client):
    import datetime

    # Add a daily habit with daily_target = 2
    habit_id = add_habit(name="Quantitative Habit", daily_target=2, type="binary")
    today_str = datetime.date.today().isoformat()

    # Get agenda - status should be planned, today_count should be 0
    agenda = client.get(
        f"/api/v1/agenda?date={today_str}", headers={"X-User-ID": "1"}
    ).json()
    quest = next(q for q in agenda["unplaced_quests"] if q["habit_id"] == habit_id)
    assert quest["status"] == "planned"
    assert quest["today_count"] == 0
    assert quest["daily_target"] == 2

    # Log once
    response = client.post(
        "/api/v1/logs",
        json={"habit_id": habit_id, "log_type": "done"},
        headers={"X-User-ID": "1"},
    )
    assert response.status_code == 200

    # Get agenda again - status should be planned, today_count should be 1
    agenda = client.get(
        f"/api/v1/agenda?date={today_str}", headers={"X-User-ID": "1"}
    ).json()
    quest = next(q for q in agenda["unplaced_quests"] if q["habit_id"] == habit_id)
    assert quest["status"] == "planned"
    assert quest["today_count"] == 1

    # Log a second time
    response = client.post(
        "/api/v1/logs",
        json={"habit_id": habit_id, "log_type": "done"},
        headers={"X-User-ID": "1"},
    )
    assert response.status_code == 200

    # Get agenda again - status should be done, today_count should be 2
    agenda = client.get(
        f"/api/v1/agenda?date={today_str}", headers={"X-User-ID": "1"}
    ).json()
    quest = next(q for q in agenda["unplaced_quests"] if q["habit_id"] == habit_id)
    assert quest["status"] == "done"
    assert quest["today_count"] == 2
