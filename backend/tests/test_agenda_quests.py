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


def test_focus_pins_never_generate_quests(client):
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

    before = client.get(
        "/api/v1/habits?include_archived=true&include_all_versions=true",
        headers={"X-User-ID": "1"},
    ).json()

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

    for path in ("/api/v1/agenda?date=2026-07-06", "/api/v1/habits/bank"):
        assert client.get(path, headers={"X-User-ID": "1"}).status_code == 200

    after = client.get(
        "/api/v1/habits?include_archived=true&include_all_versions=true",
        headers={"X-User-ID": "1"},
    ).json()
    assert [habit["id"] for habit in after] == [habit["id"] for habit in before]


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


def test_editing_quest_duration_updates_existing_placement_size(client):
    habit_id = add_habit(name="Lecture", agenda_duration_minutes=60)
    db = TestingSessionLocal()
    try:
        template = (
            db.query(PerfectDayTemplate)
            .filter_by(user_id=1, template_name="regular")
            .first()
        )
        template.agenda_json = {
            **template.agenda_json,
            "default_placements": [
                {"habit_id": habit_id, "start": "10:00", "duration_minutes": 60}
            ],
        }
        db.commit()
    finally:
        db.close()

    placed = client.put(
        f"/api/v1/agenda/2026-07-06/quests/{habit_id}/placement",
        json={"start_time": "08:00", "duration_minutes": 60},
        headers={"X-User-ID": "1"},
    )
    assert placed.status_code == 200
    assert (
        next(q for q in placed.json()["placed_quests"] if q["habit_id"] == habit_id)[
            "duration_minutes"
        ]
        == 60
    )

    updated = client.put(
        f"/api/v1/habits/{habit_id}",
        json={"agenda_duration_minutes": 120, "effort_duration": 2.0},
        headers={"X-User-ID": "1"},
    )
    assert updated.status_code == 200

    agenda = client.get("/api/v1/agenda?date=2026-07-06", headers={"X-User-ID": "1"})
    assert agenda.status_code == 200
    quest = next(q for q in agenda.json()["placed_quests"] if q["habit_id"] == habit_id)
    assert quest["duration_minutes"] == 120
    assert quest["agenda_duration_minutes"] == 120

    template_agenda = client.get(
        "/api/v1/agenda?date=2026-07-07", headers={"X-User-ID": "1"}
    )
    assert template_agenda.status_code == 200
    template_quest = next(
        q for q in template_agenda.json()["placed_quests"] if q["habit_id"] == habit_id
    )
    assert template_quest["duration_minutes"] == 120


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


def test_pin_changes_do_not_archive_manual_quests(client):
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

    quest_id = add_habit(name="Read chapter every day")
    client.put(
        "/api/v1/profile/pins",
        json={"pinned_goals": [30], "pinned_substeps": [200]},
        headers={"X-User-ID": "1"},
    )

    client.put(
        "/api/v1/profile/pins",
        json={"pinned_goals": [30], "pinned_substeps": []},
        headers={"X-User-ID": "1"},
    )

    agenda = client.get("/api/v1/agenda?date=2026-07-06", headers={"X-User-ID": "1"})
    quest = next(
        q for q in agenda.json()["unplaced_quests"] if q["habit_id"] == quest_id
    )
    assert quest["source_type"] == "manual"
    assert quest["archived_at"] is None


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


def _pins(client):
    return client.get("/api/v1/profile", headers={"X-User-ID": "1"}).json()


def test_archiving_quest_never_changes_focus_pins(client):
    quest_id = add_habit(name="Independent quest")
    with TestingSessionLocal() as db:
        db.add(Goal(id=10, user_id=1, title="Business"))
        db.commit()
    client.put(
        "/api/v1/profile/pins",
        json={"pinned_goals": [10], "pinned_softskills": ["python"]},
        headers={"X-User-ID": "1"},
    )
    archived = client.post(
        f"/api/v1/habits/{quest_id}/archive", headers={"X-User-ID": "1"}
    )
    assert archived.status_code == 200
    assert archived.json()["unpinned"] is False

    profile = _pins(client)
    assert profile["pinned_substeps"] == []
    assert profile["pinned_goals"] == [10]
    assert profile["pinned_softskills"] == ["python"]


def test_quest_supports_optional_objective_and_softskill_branch_tags(client):
    with TestingSessionLocal() as db:
        db.add_all(
            [
                Goal(id=40, user_id=1, title="Devenir Millionnaire"),
                Goal(id=41, user_id=1, title="Forme physique"),
            ]
        )
        db.commit()

    created = client.post(
        "/api/v1/habits",
        json={
            "name": "Hustle",
            "type": "binary",
            "tags": [
                {"kind": "goal", "ref": "40"},
                {"kind": "softskill_branch", "ref": "productivite"},
                {"kind": "goal", "ref": "40"},
            ],
        },
        headers={"X-User-ID": "1"},
    )
    assert created.status_code == 201, created.text
    habit_id = created.json()["id"]

    habits = client.get("/api/v1/habits", headers={"X-User-ID": "1"}).json()
    tags = next(h for h in habits if h["id"] == habit_id)["tags"]
    assert [(tag["kind"], tag["ref"]) for tag in tags] == [
        ("goal", "40"),
        ("softskill_branch", "productivite"),
    ]

    agenda = client.get("/api/v1/agenda", headers={"X-User-ID": "1"}).json()
    agenda_tags = next(
        q for q in agenda["unplaced_quests"] if q["habit_id"] == habit_id
    )["tags"]
    assert agenda_tags == tags


def test_quest_can_remain_tagless_and_tag_update_is_explicit(client):
    with TestingSessionLocal() as db:
        db.add(Goal(id=42, user_id=1, title="Fitness"))
        db.commit()

    created = client.post(
        "/api/v1/habits",
        json={
            "name": "push up today",
            "type": "binary",
            "tags": [{"kind": "goal", "ref": "42"}],
        },
        headers={"X-User-ID": "1"},
    )
    assert created.status_code == 201, created.text
    habit_id = created.json()["id"]

    unchanged = client.put(
        f"/api/v1/habits/{habit_id}",
        json={"description": "Etape 1"},
        headers={"X-User-ID": "1"},
    )
    assert unchanged.status_code == 200
    tags = next(
        h
        for h in client.get("/api/v1/habits", headers={"X-User-ID": "1"}).json()
        if h["id"] == habit_id
    )["tags"]
    assert [(tag["kind"], tag["ref"]) for tag in tags] == [("goal", "42")]

    cleared = client.put(
        f"/api/v1/habits/{habit_id}",
        json={"tags": []},
        headers={"X-User-ID": "1"},
    )
    assert cleared.status_code == 200
    tags = next(
        h
        for h in client.get("/api/v1/habits", headers={"X-User-ID": "1"}).json()
        if h["id"] == habit_id
    )["tags"]
    assert tags == []


def test_quest_tags_are_shared_by_all_quest_levels(client):
    with TestingSessionLocal() as db:
        db.add(Goal(id=43, user_id=1, title="Endurance"))
        db.commit()

    created = client.post(
        "/api/v1/habits",
        json={
            "name": "Pompes",
            "type": "binary",
            "tags": [{"kind": "goal", "ref": "43"}],
        },
        headers={"X-User-ID": "1"},
    )
    v1_id = created.json()["id"]
    versioned = client.post(
        f"/api/v1/habits/{v1_id}/versions",
        json={"description": "Etape 2", "source_description": "Etape 1"},
        headers={"X-User-ID": "1"},
    )
    assert versioned.status_code == 201, versioned.text
    v2_id = versioned.json()["id"]

    versions = client.get(
        "/api/v1/habits?include_inactive=true&include_all_versions=true",
        headers={"X-User-ID": "1"},
    ).json()
    tag_payloads = {
        habit["id"]: habit["tags"]
        for habit in versions
        if habit["id"] in {v1_id, v2_id}
    }
    assert tag_payloads[v1_id] == tag_payloads[v2_id]

    cleared = client.put(
        f"/api/v1/habits/{v2_id}",
        json={"tags": []},
        headers={"X-User-ID": "1"},
    )
    assert cleared.status_code == 200
    versions = client.get(
        "/api/v1/habits?include_inactive=true&include_all_versions=true",
        headers={"X-User-ID": "1"},
    ).json()
    assert all(
        habit["tags"] == [] for habit in versions if habit["id"] in {v1_id, v2_id}
    )


def test_quest_tags_reject_other_user_and_unknown_sources(client):
    with TestingSessionLocal() as db:
        db.add(User(id=2, username="Other", xp=0, level=1, gold=0))
        db.add(Goal(id=90, user_id=2, title="Private goal"))
        db.commit()

    for tags in (
        [{"kind": "goal", "ref": "90"}],
        [{"kind": "softskill_branch", "ref": "missing"}],
    ):
        response = client.post(
            "/api/v1/habits",
            json={
                "name": f"Invalid {tags}",
                "type": "binary",
                "tags": tags,
            },
            headers={"X-User-ID": "1"},
        )
        assert response.status_code == 422


def test_deleting_goal_removes_quest_tag_without_deleting_quest(client):
    with TestingSessionLocal() as db:
        db.add(Goal(id=44, user_id=1, title="Objectif temporaire"))
        db.commit()

    created = client.post(
        "/api/v1/habits",
        json={
            "name": "Quête durable",
            "type": "binary",
            "tags": [{"kind": "goal", "ref": "44"}],
        },
        headers={"X-User-ID": "1"},
    )
    assert created.status_code == 201
    habit_id = created.json()["id"]

    deleted = client.delete("/api/v1/goals/44", headers={"X-User-ID": "1"})
    assert deleted.status_code == 200

    habits = client.get("/api/v1/habits", headers={"X-User-ID": "1"}).json()
    quest = next(habit for habit in habits if habit["id"] == habit_id)
    assert quest["tags"] == []
