import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.models import (
    DailyScore,
    Habit,
    HabitDailyProgress,
    HabitLog,
    PerfectDayTemplate,
    Streak,
    User,
)
from src.database.session import Base, get_db
from src.main import app
from src.services import quest_progress_service


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

HEADERS = {"X-User-ID": "1"}
TODAY = datetime.date.today()
YESTERDAY = TODAY - datetime.timedelta(days=1)


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
    with TestingSessionLocal() as db:
        db.add_all(
            [
                User(id=1, username="Gabriel", xp=37, level=1, gold=11),
                User(id=2, username="Other", xp=0, level=1, gold=0),
                PerfectDayTemplate(
                    user_id=1,
                    template_name="regular",
                    focus_hours=6,
                    min_rest_hours=8,
                    ceilings_json={},
                    agenda_json={
                        "schema_version": 2,
                        "segments": [],
                        "default_placements": [],
                    },
                ),
            ]
        )
        db.commit()
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client():
    return TestClient(app)


def create_habit(client, **overrides):
    payload = {
        "name": overrides.pop("name", "Quest with progress"),
        "type": overrides.pop("type", "binary"),
        **overrides,
    }
    response = client.post("/api/v1/habits", json=payload, headers=HEADERS)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def listed_habit(client, habit_id):
    response = client.get("/api/v1/habits?include_all_versions=true", headers=HEADERS)
    assert response.status_code == 200
    return next(habit for habit in response.json() if habit["id"] == habit_id)


def agenda_item(client, habit_id, date_value=TODAY):
    response = client.get(
        f"/api/v1/agenda?date={date_value.isoformat()}", headers=HEADERS
    )
    assert response.status_code == 200, response.text
    items = response.json()["placed_quests"] + response.json()["unplaced_quests"]
    return next(item for item in items if item["habit_id"] == habit_id)


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "Unknown", "type": "binary", "progress_mode": "timer"},
        {"name": "No unit", "type": "binary", "progress_mode": "free_counter"},
        {
            "name": "Empty checklist",
            "type": "binary",
            "progress_mode": "checklist",
            "checklist_items": [],
        },
        {
            "name": "Counter plus checklist",
            "type": "binary",
            "progress_mode": "free_counter",
            "unit": "fois",
            "checklist_items": [{"label": "Incompatible"}],
        },
        {
            "name": "Standard plus checklist",
            "type": "binary",
            "progress_mode": "standard",
            "checklist_items": [{"label": "Incompatible"}],
        },
        {
            "name": "Unsafe checklist ID",
            "type": "binary",
            "progress_mode": "checklist",
            "checklist_items": [{"id": "bad/path", "label": "Invalide"}],
        },
    ],
)
def test_progress_mode_validation_rejects_invalid_configuration(client, payload):
    response = client.post("/api/v1/habits", json=payload, headers=HEADERS)
    assert response.status_code in {400, 422}


def test_enriched_modes_force_binary_and_clear_target_and_cap(client):
    habit_id = create_habit(
        client,
        name="Pages lues",
        type="quantitative",
        progress_mode="free_counter",
        unit="pages",
        daily_target=20,
        daily_cap=40,
    )

    habit = listed_habit(client, habit_id)
    assert habit["progress_mode"] == "free_counter"
    assert habit["type"] == "binary"
    assert habit["unit"] == "pages"
    assert habit["daily_target"] is None
    assert habit["daily_cap"] is None
    assert habit["checklist_items"] == []


def test_counter_write_is_absolute_and_has_one_row_per_date(client):
    habit_id = create_habit(
        client, name="Pompes libres", progress_mode="free_counter", unit="répétitions"
    )
    path = f"/api/v1/habits/{habit_id}/counter/{TODAY.isoformat()}"

    first = client.put(path, json={"value": 12}, headers=HEADERS)
    second = client.put(path, json={"value": 4}, headers=HEADERS)
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text

    with TestingSessionLocal() as db:
        rows = db.query(HabitDailyProgress).filter_by(habit_id=habit_id).all()
        assert len(rows) == 1
        assert rows[0].date == TODAY
        assert rows[0].mode_snapshot == "free_counter"
        assert rows[0].unit_snapshot == "répétitions"
        assert rows[0].counter_value == 4

    progress = listed_habit(client, habit_id)["daily_progress"]
    assert progress["counter_value"] == 4


def test_counter_rejects_values_that_cannot_round_trip_through_javascript(client):
    habit_id = create_habit(
        client, name="Compteur borné", progress_mode="free_counter", unit="fois"
    )
    response = client.put(
        f"/api/v1/habits/{habit_id}/counter/{TODAY.isoformat()}",
        json={"value": 9_007_199_254_740_992},
        headers=HEADERS,
    )
    assert response.status_code == 422


def test_checklist_checked_is_idempotent_and_state_resets_by_date(client):
    checklist = [
        {"id": "bottle", "label": "Préparer la bouteille"},
        {"id": "shoes", "label": "Sortir les chaussures"},
    ]
    habit_id = create_habit(
        client,
        name="Préparer la course",
        progress_mode="checklist",
        checklist_items=checklist,
    )
    today_path = (
        f"/api/v1/habits/{habit_id}/checklist/{TODAY.isoformat()}" "/items/bottle"
    )

    first = client.put(today_path, json={"checked": True}, headers=HEADERS)
    repeated = client.put(today_path, json={"checked": True}, headers=HEADERS)
    assert first.status_code == 200, first.text
    assert repeated.status_code == 200, repeated.text

    yesterday_path = (
        f"/api/v1/habits/{habit_id}/checklist/{YESTERDAY.isoformat()}" "/items/shoes"
    )
    yesterday = client.put(yesterday_path, json={"checked": True}, headers=HEADERS)
    assert yesterday.status_code == 200, yesterday.text

    with TestingSessionLocal() as db:
        rows = {
            row.date: row
            for row in db.query(HabitDailyProgress).filter_by(habit_id=habit_id).all()
        }
        assert set(rows) == {TODAY, YESTERDAY}
        assert rows[TODAY].checklist_state == [
            {
                "id": "bottle",
                "label": "Préparer la bouteille",
                "position": 0,
                "checked": True,
            },
            {
                "id": "shoes",
                "label": "Sortir les chaussures",
                "position": 1,
                "checked": False,
            },
        ]
        assert rows[YESTERDAY].checklist_state == [
            {
                "id": "bottle",
                "label": "Préparer la bouteille",
                "position": 0,
                "checked": False,
            },
            {
                "id": "shoes",
                "label": "Sortir les chaussures",
                "position": 1,
                "checked": True,
            },
        ]


def test_progress_rejects_dates_outside_today_yesterday_and_other_owner(client):
    habit_id = create_habit(
        client, name="Compteur protégé", progress_mode="free_counter", unit="fois"
    )
    for date_value in (
        TODAY - datetime.timedelta(days=2),
        TODAY + datetime.timedelta(days=1),
    ):
        response = client.put(
            f"/api/v1/habits/{habit_id}/counter/{date_value.isoformat()}",
            json={"value": 1},
            headers=HEADERS,
        )
        assert response.status_code == 422

    with TestingSessionLocal() as db:
        other_habit = Habit(
            user_id=2,
            name="Not Gabriel's quest",
            type="binary",
            progress_mode="free_counter",
            unit="fois",
            is_active=True,
        )
        db.add(other_habit)
        db.commit()
        db.refresh(other_habit)
        other_habit_id = other_habit.id

    response = client.put(
        f"/api/v1/habits/{other_habit_id}/counter/{TODAY.isoformat()}",
        json={"value": 1},
        headers=HEADERS,
    )
    assert response.status_code == 404


def test_progress_is_additive_in_habits_agenda_bank_and_calendar(client):
    habit_id = create_habit(
        client, name="Verres d'eau", progress_mode="free_counter", unit="verres"
    )
    response = client.put(
        f"/api/v1/habits/{habit_id}/counter/{TODAY.isoformat()}",
        json={"value": 6},
        headers=HEADERS,
    )
    assert response.status_code == 200, response.text

    habit = listed_habit(client, habit_id)
    assert habit["progress_mode"] == "free_counter"
    assert habit["checklist_items"] == []
    assert habit["daily_progress"]["counter_value"] == 6

    agenda = agenda_item(client, habit_id)
    assert agenda["progress_mode"] == "free_counter"
    assert agenda["checklist_items"] == []
    assert agenda["daily_progress"]["counter_value"] == 6

    archived = client.post(f"/api/v1/habits/{habit_id}/archive", headers=HEADERS)
    assert archived.status_code == 200
    bank = client.get(f"/api/v1/habits/bank?date={TODAY.isoformat()}", headers=HEADERS)
    assert bank.status_code == 200
    bank_item = next(
        item for item in bank.json()["archived_quests"] if item["habit_id"] == habit_id
    )
    assert bank_item["progress_mode"] == "free_counter"
    assert bank_item["daily_progress"]["counter_value"] == 6

    calendar = client.get(
        f"/api/v1/habits/{habit_id}/calendar?year={TODAY.year}&month={TODAY.month}",
        headers=HEADERS,
    )
    assert calendar.status_code == 200
    assert "days" in calendar.json()
    assert calendar.json()["daily_progress"][str(TODAY.day)]["counter_value"] == 6


def test_auxiliary_progress_does_not_change_logs_score_xp_or_streak(client):
    habit_id = create_habit(
        client, name="Respirations", progress_mode="free_counter", unit="cycles"
    )
    with TestingSessionLocal() as db:
        db.add(
            Streak(
                user_id=1,
                streak_type=f"habit:{habit_id}",
                current_streak=7,
                max_streak=9,
            )
        )
        db.commit()

    response = client.put(
        f"/api/v1/habits/{habit_id}/counter/{TODAY.isoformat()}",
        json={"value": 100},
        headers=HEADERS,
    )
    assert response.status_code == 200, response.text

    with TestingSessionLocal() as db:
        assert db.query(HabitLog).filter_by(habit_id=habit_id).count() == 0
        assert db.query(DailyScore).filter_by(user_id=1, date=TODAY).count() == 0
        user = db.query(User).filter_by(id=1).one()
        streak = (
            db.query(Streak).filter_by(user_id=1, streak_type=f"habit:{habit_id}").one()
        )
        assert (user.xp, user.level, user.gold) == (37, 1, 11)
        assert (streak.current_streak, streak.max_streak) == (7, 9)


def test_explicit_done_is_independent_from_auxiliary_progress(client):
    habit_id = create_habit(
        client, name="Notes écrites", progress_mode="free_counter", unit="notes"
    )
    progress = client.put(
        f"/api/v1/habits/{habit_id}/counter/{TODAY.isoformat()}",
        json={"value": 25},
        headers=HEADERS,
    )
    assert progress.status_code == 200
    assert agenda_item(client, habit_id)["status"] == "planned"

    done = client.post(
        "/api/v1/logs",
        json={"habit_id": habit_id, "log_type": "done"},
        headers=HEADERS,
    )
    assert done.status_code == 200, done.text
    item = agenda_item(client, habit_id)
    assert item["status"] == "done"
    assert item["daily_progress"]["counter_value"] == 25


def test_incomplete_checklist_does_not_block_explicit_done(client):
    habit_id = create_habit(
        client,
        name="Routine partielle",
        progress_mode="checklist",
        checklist_items=[
            {"id": "first", "label": "Première étape"},
            {"id": "second", "label": "Deuxième étape"},
        ],
    )
    checked = client.put(
        f"/api/v1/habits/{habit_id}/checklist/{TODAY.isoformat()}/items/first",
        json={"checked": True},
        headers=HEADERS,
    )
    assert checked.status_code == 200
    assert agenda_item(client, habit_id)["status"] == "planned"

    done = client.post(
        "/api/v1/logs",
        json={"habit_id": habit_id, "log_type": "done"},
        headers=HEADERS,
    )
    assert done.status_code == 200, done.text
    item = agenda_item(client, habit_id)
    assert item["status"] == "done"
    assert [
        entry["checked"] for entry in item["daily_progress"]["checklist_items"]
    ] == [
        True,
        False,
    ]


def test_explicit_done_snapshots_untouched_enriched_progress(client):
    checklist_id = create_habit(
        client,
        name="Checklist intacte",
        progress_mode="checklist",
        checklist_items=[{"id": "only", "label": "Étape non cochée"}],
    )
    counter_id = create_habit(
        client,
        name="Compteur intact",
        progress_mode="free_counter",
        unit="fois",
    )

    for habit_id in (checklist_id, counter_id):
        response = client.post(
            "/api/v1/logs",
            json={"habit_id": habit_id, "log_type": "done"},
            headers=HEADERS,
        )
        assert response.status_code == 200, response.text

    with TestingSessionLocal() as db:
        checklist_row = (
            db.query(HabitDailyProgress).filter_by(habit_id=checklist_id).one()
        )
        counter_row = db.query(HabitDailyProgress).filter_by(habit_id=counter_id).one()
        assert checklist_row.checklist_state[0]["checked"] is False
        assert counter_row.counter_value == 0


def test_legacy_quantitative_log_does_not_complete_enriched_mode(client):
    habit_id = create_habit(
        client, name="Ancien compteur", progress_mode="free_counter", unit="fois"
    )
    with TestingSessionLocal() as db:
        db.add(
            HabitLog(
                user_id=1,
                habit_id=habit_id,
                log_type="log",
                amount=99,
                timestamp=datetime.datetime.now(),
            )
        )
        db.commit()

    assert agenda_item(client, habit_id)["status"] == "planned"


def test_standard_history_keeps_log_types_and_target_after_conversion(client):
    habit_id = create_habit(
        client,
        name="Objectif historique",
        type="quantitative",
        unit="pages",
        daily_target=3,
    )
    with TestingSessionLocal() as db:
        habit = db.query(Habit).filter_by(id=habit_id).one()
        habit.created_at = datetime.datetime.combine(
            YESTERDAY - datetime.timedelta(days=7), datetime.time(hour=8)
        )
        habit.progress_config_history = []
        db.add(
            HabitLog(
                user_id=1,
                habit_id=habit_id,
                log_type="log",
                amount=1,
                timestamp=datetime.datetime.combine(YESTERDAY, datetime.time(hour=9)),
            )
        )
        db.commit()

    switched = client.put(
        f"/api/v1/habits/{habit_id}",
        json={"progress_mode": "free_counter", "unit": "pages"},
        headers=HEADERS,
    )
    assert switched.status_code == 200, switched.text
    yesterday_item = agenda_item(client, habit_id, YESTERDAY)
    assert yesterday_item["status"] == "planned"
    assert yesterday_item["daily_progress"]["mode"] == "standard"

    with TestingSessionLocal() as db:
        habit = db.query(Habit).filter_by(id=habit_id).one()
        assert habit.progress_config_history == [
            {
                "effective_from": (YESTERDAY - datetime.timedelta(days=7)).isoformat(),
                "mode": "standard",
                "type": "quantitative",
                "unit": "pages",
                "daily_target": 3,
                "checklist_items": [],
            },
            {
                "effective_from": TODAY.isoformat(),
                "mode": "free_counter",
                "type": "binary",
                "unit": "pages",
                "daily_target": 1,
                "checklist_items": [],
            },
        ]
    for _ in range(2):
        corrected = client.post(
            "/api/v1/logs",
            json={
                "habit_id": habit_id,
                "log_type": "log",
                "amount": 1,
                "target_date": YESTERDAY.isoformat(),
            },
            headers=HEADERS,
        )
        assert corrected.status_code == 200, corrected.text

    completed_yesterday = agenda_item(client, habit_id, YESTERDAY)
    assert completed_yesterday["status"] == "done"
    assert completed_yesterday["daily_target_for_date"] == 3
    assert completed_yesterday["type_for_date"] == "quantitative"


def test_same_day_enriched_edits_do_not_fabricate_yesterday_progress(client):
    habit_id = create_habit(
        client, name="Nouveau compteur", progress_mode="free_counter", unit="fois"
    )
    edited = client.put(
        f"/api/v1/habits/{habit_id}",
        json={"unit": "répétitions"},
        headers=HEADERS,
    )
    assert edited.status_code == 200, edited.text
    with TestingSessionLocal() as db:
        assert db.query(HabitDailyProgress).filter_by(habit_id=habit_id).count() == 0


def test_round_trip_mode_history_preserves_each_periods_completion_rules():
    first_day = TODAY - datetime.timedelta(days=4)
    habit = Habit(
        id=99,
        user_id=1,
        name="Quête aller-retour",
        type="binary",
        progress_mode="standard",
        daily_target=2,
        progress_config_history=[
            {
                "effective_from": first_day.isoformat(),
                "mode": "standard",
                "type": "quantitative",
                "unit": "pages",
                "daily_target": 3,
                "checklist_items": [],
            },
            {
                "effective_from": (first_day + datetime.timedelta(days=1)).isoformat(),
                "mode": "free_counter",
                "type": "binary",
                "unit": "reps",
                "daily_target": 1,
                "checklist_items": [],
            },
            {
                "effective_from": (first_day + datetime.timedelta(days=2)).isoformat(),
                "mode": "checklist",
                "type": "binary",
                "unit": None,
                "daily_target": 1,
                "checklist_items": [{"id": "step", "label": "Étape", "position": 0}],
            },
            {
                "effective_from": (first_day + datetime.timedelta(days=3)).isoformat(),
                "mode": "standard",
                "type": "binary",
                "unit": "pages",
                "daily_target": 2,
                "checklist_items": [],
            },
        ],
    )

    def logs(day, *types):
        return [
            HabitLog(
                user_id=1,
                habit_id=99,
                log_type=log_type,
                timestamp=datetime.datetime.combine(day, datetime.time(hour=8 + index)),
            )
            for index, log_type in enumerate(types)
        ]

    assert quest_progress_service.completion_target(habit, first_day) == 3
    assert (
        quest_progress_service.completion_count(habit, logs(first_day, "log", "log"))
        == 2
    )
    counter_day = first_day + datetime.timedelta(days=1)
    assert (
        quest_progress_service.completion_count(habit, logs(counter_day, "log", "done"))
        == 1
    )
    checklist_day = first_day + datetime.timedelta(days=2)
    assert (
        quest_progress_service.completion_count(habit, logs(checklist_day, "done")) == 1
    )
    standard_again = first_day + datetime.timedelta(days=3)
    assert quest_progress_service.completion_target(habit, standard_again) == 2
    assert (
        quest_progress_service.completion_count(habit, logs(standard_again, "done"))
        == 1
    )


def test_skipped_and_failed_progress_is_read_only_in_api(client):
    counter_id = create_habit(
        client, name="Compteur passé", progress_mode="free_counter", unit="fois"
    )
    skipped = client.post(
        "/api/v1/logs",
        json={"habit_id": counter_id, "log_type": "skip"},
        headers=HEADERS,
    )
    assert skipped.status_code == 200, skipped.text
    counter_write = client.put(
        f"/api/v1/habits/{counter_id}/counter/{TODAY.isoformat()}",
        json={"value": 2},
        headers=HEADERS,
    )
    assert counter_write.status_code == 409

    checklist_id = create_habit(
        client,
        name="Checklist ratée",
        progress_mode="checklist",
        checklist_items=[{"id": "step", "label": "Une étape"}],
    )
    failed = client.post(f"/api/v1/habits/{checklist_id}/fail", headers=HEADERS)
    assert failed.status_code == 200, failed.text
    checklist_write = client.put(
        f"/api/v1/habits/{checklist_id}/checklist/{TODAY.isoformat()}/items/step",
        json={"checked": True},
        headers=HEADERS,
    )
    assert checklist_write.status_code == 409

    with TestingSessionLocal() as db:
        rows = db.query(HabitDailyProgress).filter(
            HabitDailyProgress.habit_id.in_([counter_id, checklist_id])
        )
        assert rows.count() == 2


def test_checklist_resource_limits_are_enforced(client):
    too_many = client.post(
        "/api/v1/habits",
        json={
            "name": "Checklist énorme",
            "type": "binary",
            "progress_mode": "checklist",
            "checklist_items": [
                {"id": f"step-{index}", "label": "Étape"} for index in range(51)
            ],
        },
        headers=HEADERS,
    )
    assert too_many.status_code == 422

    long_label = client.post(
        "/api/v1/habits",
        json={
            "name": "Longue étape",
            "type": "binary",
            "progress_mode": "checklist",
            "checklist_items": [{"id": "step", "label": "x" * 201}],
        },
        headers=HEADERS,
    )
    assert long_label.status_code == 422


def test_archived_or_inactive_habit_progress_is_read_only(client):
    archived_id = create_habit(
        client, name="Compteur archivé", progress_mode="free_counter", unit="fois"
    )
    assert (
        client.post(
            f"/api/v1/habits/{archived_id}/archive", headers=HEADERS
        ).status_code
        == 200
    )
    archived_write = client.put(
        f"/api/v1/habits/{archived_id}/counter/{TODAY.isoformat()}",
        json={"value": 1},
        headers=HEADERS,
    )
    assert archived_write.status_code == 404

    inactive_id = create_habit(
        client, name="Compteur inactif", progress_mode="free_counter", unit="fois"
    )
    assert (
        client.delete(f"/api/v1/habits/{inactive_id}", headers=HEADERS).status_code
        == 200
    )
    inactive_write = client.put(
        f"/api/v1/habits/{inactive_id}/counter/{TODAY.isoformat()}",
        json={"value": 1},
        headers=HEADERS,
    )
    assert inactive_write.status_code == 404


def test_calendar_only_exposes_persisted_progress_history(client):
    habit_id = create_habit(
        client, name="Compteur sans saisie", progress_mode="free_counter", unit="fois"
    )
    calendar = client.get(
        f"/api/v1/habits/{habit_id}/calendar?year={TODAY.year}&month={TODAY.month}",
        headers=HEADERS,
    )
    assert calendar.status_code == 200
    assert calendar.json()["daily_progress"] == {}


def test_yesterday_snapshot_keeps_its_mode_after_quest_mode_changes(client):
    habit_id = create_habit(
        client,
        name="Routine évolutive",
        progress_mode="checklist",
        checklist_items=[{"id": "legacy", "label": "Ancienne étape"}],
    )
    yesterday_path = (
        f"/api/v1/habits/{habit_id}/checklist/{YESTERDAY.isoformat()}" "/items/legacy"
    )
    assert (
        client.put(
            yesterday_path,
            json={"checked": True},
            headers=HEADERS,
        ).status_code
        == 200
    )

    switched = client.put(
        f"/api/v1/habits/{habit_id}",
        json={
            "progress_mode": "free_counter",
            "unit": "fois",
            "checklist_items": [],
        },
        headers=HEADERS,
    )
    assert switched.status_code == 200, switched.text

    yesterday_item = agenda_item(client, habit_id, YESTERDAY)
    assert yesterday_item["progress_mode"] == "free_counter"
    assert yesterday_item["daily_progress"]["mode"] == "checklist"
    assert yesterday_item["daily_progress"]["checklist_items"][0]["checked"] is True

    corrected = client.put(
        yesterday_path,
        json={"checked": False},
        headers=HEADERS,
    )
    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["daily_progress"]["checklist_items"][0]["checked"] is False


@pytest.mark.parametrize(
    ("initial_mode", "initial_unit", "initial_items", "next_payload", "write_path"),
    [
        (
            "checklist",
            None,
            [{"id": "old-step", "label": "Ancienne étape"}],
            {"progress_mode": "free_counter", "unit": "fois", "checklist_items": []},
            "checklist/{date}/items/old-step",
        ),
        (
            "free_counter",
            "fois",
            [],
            {
                "progress_mode": "checklist",
                "unit": None,
                "checklist_items": [{"id": "new-step", "label": "Nouvelle étape"}],
            },
            "counter/{date}",
        ),
    ],
)
def test_rowless_yesterday_correction_uses_dated_configuration(
    client, initial_mode, initial_unit, initial_items, next_payload, write_path
):
    habit_id = create_habit(
        client,
        name=f"Transition depuis {initial_mode}",
        progress_mode=initial_mode,
        unit=initial_unit,
        checklist_items=initial_items,
    )
    with TestingSessionLocal() as db:
        habit = db.query(Habit).filter_by(id=habit_id).one()
        habit.created_at = datetime.datetime.combine(YESTERDAY, datetime.time(hour=8))
        history = [dict(entry) for entry in habit.progress_config_history]
        history[0]["effective_from"] = YESTERDAY.isoformat()
        habit.progress_config_history = history
        db.commit()

    switched = client.put(
        f"/api/v1/habits/{habit_id}", json=next_payload, headers=HEADERS
    )
    assert switched.status_code == 200, switched.text
    with TestingSessionLocal() as db:
        assert db.query(HabitDailyProgress).filter_by(habit_id=habit_id).count() == 0

    path = write_path.format(date=YESTERDAY.isoformat())
    payload = {"checked": True} if initial_mode == "checklist" else {"value": 7}
    corrected = client.put(
        f"/api/v1/habits/{habit_id}/{path}", json=payload, headers=HEADERS
    )
    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["daily_progress"]["mode"] == initial_mode


def test_done_yesterday_does_not_create_auxiliary_row_for_historical_standard_mode(
    client,
):
    habit_id = create_habit(client, name="Standard puis compteur", daily_target=3)
    with TestingSessionLocal() as db:
        habit = db.query(Habit).filter_by(id=habit_id).one()
        habit.created_at = datetime.datetime.combine(YESTERDAY, datetime.time(hour=8))
        history = [dict(entry) for entry in habit.progress_config_history]
        history[0]["effective_from"] = YESTERDAY.isoformat()
        habit.progress_config_history = history
        db.commit()

    switched = client.put(
        f"/api/v1/habits/{habit_id}",
        json={"progress_mode": "free_counter", "unit": "fois"},
        headers=HEADERS,
    )
    assert switched.status_code == 200, switched.text
    for _ in range(3):
        done = client.post(
            "/api/v1/logs",
            json={
                "habit_id": habit_id,
                "log_type": "done",
                "target_date": YESTERDAY.isoformat(),
            },
            headers=HEADERS,
        )
        assert done.status_code == 200, done.text
        assert done.json()["status"] == "logged"
    with TestingSessionLocal() as db:
        assert db.query(HabitDailyProgress).filter_by(habit_id=habit_id).count() == 0
        assert db.query(HabitLog).filter_by(habit_id=habit_id).count() == 3
    assert agenda_item(client, habit_id, YESTERDAY)["status"] == "done"


def test_version_clones_progress_configuration_but_not_daily_state(client):
    checklist = [
        {"id": "outline", "label": "Faire le plan"},
        {"id": "draft", "label": "Écrire le brouillon"},
    ]
    source_id = create_habit(
        client,
        name="Article",
        progress_mode="checklist",
        checklist_items=checklist,
    )
    checked = client.put(
        f"/api/v1/habits/{source_id}/checklist/{TODAY.isoformat()}" "/items/outline",
        json={"checked": True},
        headers=HEADERS,
    )
    assert checked.status_code == 200

    version = client.post(
        f"/api/v1/habits/{source_id}/versions", json={}, headers=HEADERS
    )
    assert version.status_code == 201, version.text
    new_id = version.json()["id"]

    with TestingSessionLocal() as db:
        new_habit = db.query(Habit).filter_by(id=new_id, user_id=1).one()
        assert new_habit.progress_mode == "checklist"
        assert new_habit.checklist_items == [
            {**item, "position": position} for position, item in enumerate(checklist)
        ]
        assert db.query(HabitDailyProgress).filter_by(habit_id=source_id).count() == 1
        assert db.query(HabitDailyProgress).filter_by(habit_id=new_id).count() == 0


def test_frontend_exposes_progress_forms_controls_and_routes():
    repo_root = Path(__file__).resolve().parents[2]
    index_html = (repo_root / "frontend/index.html").read_text(encoding="utf-8")
    app_js = (repo_root / "frontend/js/app.js").read_text(encoding="utf-8")

    assert 'id="new-quest-free-counter"' in index_html
    assert 'id="edit-quest-free-counter"' in index_html
    assert 'id="new-quest-checklist-items"' in index_html
    assert 'id="quest-tracking-drawer"' in index_html
    assert 'id="edit-quest-daily-progress-shell"' in index_html
    assert "/counter/${targetDate}" in app_js
    assert "/checklist/${targetDate}/items/${encodedItemId}" in app_js
    assert 'progress_mode: item.progress_mode || "standard"' in app_js
    assert "progress_mode: getQuestProgressMode(item)" not in app_js
    assert "function questConfigForAgendaItem(item)" in app_js
    assert "function renderEditQuestDailyProgress(habit, agendaItem = null)" in app_js
    assert 'heading.textContent = mode === "checklist" ? "Checklist du jour"' in app_js
    assert "function questProgressButtonLabel(item)" in app_js
    assert 'progressBtn.className = "agenda-small-btn agenda-progress-quest"' in app_js
