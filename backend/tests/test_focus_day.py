import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.models import (
    DailyScore,
    Goal,
    GoalSubStepLink,
    Habit,
    HabitDailyProgress,
    SubStep,
    Todo,
    User,
)
from src.database.session import Base, get_db
from src.main import app
from src.services import focus_service, softskill_service


@pytest.fixture
def focus_client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False)
    with session_factory() as db:
        db.add(User(id=1, username="gabriel", chat_id="111", xp=0, level=1, gold=0))
        db.commit()

    def override_db():
        with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    try:
        yield TestClient(app), session_factory
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def test_goal_quest_stays_out_of_perfect_day_and_must_agenda(focus_client):
    client, factory = focus_client
    headers = {"X-User-ID": "1"}
    goal = client.post(
        "/api/v1/goals", json={"title": "Contrat"}, headers=headers
    ).json()["goal"]
    client.put(
        "/api/v1/profile/pins", json={"pinned_goals": [goal["id"]]}, headers=headers
    )
    quest = next(
        habit
        for habit in client.get("/api/v1/habits", headers=headers).json()
        if habit["focus_goal_id"] == goal["id"]
    )
    habit_id = quest["id"]
    assert quest["name"] == "Contrat"
    assert quest["focus_due_today"] is True
    agenda = client.get("/api/v1/agenda", headers=headers).json()
    assert habit_id not in {
        item["habit_id"] for item in agenda["placed_quests"] + agenda["unplaced_quests"]
    }
    with factory() as db:
        score = (
            db.query(DailyScore)
            .filter_by(user_id=1, date=datetime.date.today())
            .first()
        )
        assert score.status == "NoMust"
    logged = client.post(
        "/api/v1/logs", json={"habit_id": habit_id, "log_type": "done"}, headers=headers
    )
    assert logged.status_code == 200
    assert logged.json()["daily_score_status"] == "NoMust"
    assert (
        client.post(f"/api/v1/habits/{habit_id}/fail", headers=headers).status_code
        == 409
    )


def test_todo_controls_linked_goal_lifecycle(focus_client):
    client, factory = focus_client
    headers = {"X-User-ID": "1"}
    created = client.post(
        "/api/v1/todos",
        json={"title": "Livrer le contrat", "create_linked_goal": True},
        headers=headers,
    )
    assert created.status_code == 201
    todo_id = created.json()["todo"]["id"]
    goal = next(
        goal
        for goal in client.get("/api/v1/goals", headers=headers).json()
        if goal["source_todo_id"] == todo_id
    )
    assert (
        client.delete(f"/api/v1/goals/{goal['id']}", headers=headers).status_code == 409
    )
    assert (
        client.put(
            f"/api/v1/goals/{goal['id']}", json={"title": "Autre"}, headers=headers
        ).status_code
        == 409
    )
    assert (
        client.put(
            f"/api/v1/todos/{todo_id}", json={"title": "Livrer V2"}, headers=headers
        ).status_code
        == 200
    )
    assert (
        next(
            item
            for item in client.get("/api/v1/goals", headers=headers).json()
            if item["id"] == goal["id"]
        )["title"]
        == "Livrer V2"
    )
    assert (
        client.post(f"/api/v1/todos/{todo_id}/complete", headers=headers).status_code
        == 200
    )
    assert goal["id"] not in {
        item["id"] for item in client.get("/api/v1/goals", headers=headers).json()
    }
    assert (
        goal["id"]
        not in client.get("/api/v1/profile", headers=headers).json()["pinned_goals"]
    )
    with factory() as db:
        assert db.query(Goal).filter_by(id=goal["id"]).one().completed is True
        assert (
            db.query(Habit).filter_by(focus_goal_id=goal["id"]).one().is_active is False
        )
        todo = db.query(Todo).filter_by(id=todo_id).one()
        todo.completed_at = datetime.datetime.now() - datetime.timedelta(days=1)
        xp_after_completion = db.get(User, 1).xp
        db.commit()
    assert client.get("/api/v1/todos", headers=headers).status_code == 200
    with factory() as db:
        assert db.query(Goal).filter_by(id=goal["id"]).first() is None
        assert db.query(Habit).filter_by(focus_goal_id=goal["id"]).first() is None
        assert db.get(User, 1).xp == xp_after_completion


def test_deleting_todo_removes_its_goal_and_quest(focus_client):
    client, factory = focus_client
    headers = {"X-User-ID": "1"}
    created = client.post(
        "/api/v1/todos",
        json={"title": "Contrat", "create_linked_goal": True},
        headers=headers,
    )
    assert created.status_code == 201
    todo_id = created.json()["todo"]["id"]
    with factory() as db:
        goal_id = db.query(Goal).filter_by(source_todo_id=todo_id).one().id
        habit_id = db.query(Habit).filter_by(focus_goal_id=goal_id).one().id
        other = Goal(user_id=1, title="Autre objectif")
        exclusive = SubStep(
            user_id=1, title="Exclusive", gold_reward=0, execution_order=1
        )
        shared = SubStep(user_id=1, title="Shared", gold_reward=0, execution_order=1)
        db.add_all([other, exclusive, shared])
        db.flush()
        db.add_all(
            [
                GoalSubStepLink(
                    goal_id=goal_id, substep_id=exclusive.id, execution_order=1
                ),
                GoalSubStepLink(
                    goal_id=goal_id, substep_id=shared.id, execution_order=1
                ),
                GoalSubStepLink(
                    goal_id=other.id, substep_id=shared.id, execution_order=1
                ),
            ]
        )
        db.commit()
        exclusive_id, shared_id = exclusive.id, shared.id
    deleted = client.delete(f"/api/v1/todos/{todo_id}", headers=headers)
    assert deleted.status_code == 200
    with factory() as db:
        assert db.query(Goal).filter_by(id=goal_id).first() is None
        assert db.query(Habit).filter_by(id=habit_id).first() is None
        assert db.query(SubStep).filter_by(id=exclusive_id).first() is None
        assert db.query(SubStep).filter_by(id=shared_id).first() is not None


def test_unpin_pauses_goal_quest_and_repin_resumes_it(focus_client):
    client, _ = focus_client
    headers = {"X-User-ID": "1"}
    goal_id = client.post(
        "/api/v1/goals", json={"title": "Danse"}, headers=headers
    ).json()["goal"]["id"]
    assert (
        client.put(
            "/api/v1/profile/pins", json={"pinned_goals": [goal_id]}, headers=headers
        ).status_code
        == 200
    )
    habit_id = next(
        habit["id"]
        for habit in client.get("/api/v1/habits", headers=headers).json()
        if habit["focus_goal_id"] == goal_id
    )
    assert (
        client.put(
            "/api/v1/profile/pins", json={"pinned_goals": []}, headers=headers
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/logs",
            json={"habit_id": habit_id, "log_type": "done"},
            headers=headers,
        ).status_code
        == 409
    )
    assert (
        client.put(
            "/api/v1/profile/pins", json={"pinned_goals": [goal_id]}, headers=headers
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/logs",
            json={"habit_id": habit_id, "log_type": "done"},
            headers=headers,
        ).status_code
        == 200
    )


def test_pinned_skill_gets_daily_quest_without_prompt(focus_client, monkeypatch):
    client, factory = focus_client
    headers = {"X-User-ID": "1"}
    monkeypatch.setattr(
        softskill_service,
        "load_tree_config",
        lambda: {"skills": [{"id": "ukulele", "name": "Ukulele"}]},
    )
    pinned = client.put(
        "/api/v1/profile/pins",
        json={"pinned_softskills": ["ukulele"]},
        headers=headers,
    )
    assert pinned.status_code == 200
    quests = [
        habit
        for habit in client.get("/api/v1/habits", headers=headers).json()
        if habit["focus_softskill_id"] == "ukulele"
    ]
    assert len(quests) == 1
    assert quests[0]["focus_due_today"] is True
    with factory() as db:
        quest = db.get(Habit, quests[0]["id"])
        assert quest.frequency == "daily"
        assert quest.scheduled_days == "0,1,2,3,4,5,6"

    assert (
        client.put(
            "/api/v1/profile/pins", json={"pinned_softskills": []}, headers=headers
        ).status_code
        == 200
    )
    assert (
        client.put(
            "/api/v1/profile/pins",
            json={"pinned_softskills": ["ukulele"]},
            headers=headers,
        ).status_code
        == 200
    )
    quests_again = [
        habit
        for habit in client.get("/api/v1/habits", headers=headers).json()
        if habit["focus_softskill_id"] == "ukulele"
    ]
    assert [habit["id"] for habit in quests_again] == [quests[0]["id"]]
    assert quests_again[0]["focus_due_today"] is True


def test_existing_pin_is_backfilled_once(focus_client, monkeypatch):
    _, factory = focus_client
    monkeypatch.setattr(
        softskill_service,
        "load_tree_config",
        lambda: {"skills": [{"id": "ukulele", "name": "Ukulele"}]},
    )
    with factory() as db:
        user = db.get(User, 1)
        user.pinned_softskills = ["ukulele"]
        db.add(
            Habit(
                user_id=1,
                name="Competence: Ukulele",
                type="binary",
                frequency="daily",
                is_active=False,
                archived_at=datetime.datetime.now(),
            )
        )
        db.commit()
    with factory() as db:
        user = db.get(User, 1)
        focus_service.ensure_pinned_quests(db, user)
        focus_service.ensure_pinned_quests(db, user)
        db.commit()
        linked = db.query(Habit).filter_by(focus_softskill_id="ukulele").all()
        assert len(linked) == 1
        assert linked[0].is_active is True


def test_only_old_automatic_goal_names_are_normalized(focus_client):
    _, factory = focus_client
    with factory() as db:
        goal = Goal(user_id=1, title="Devenir Millionnaire")
        custom_goal = Goal(user_id=1, title="Musique")
        db.add_all([goal, custom_goal])
        db.flush()
        old_quest = Habit(
            user_id=1,
            name="Travailler sur : Devenir Millionnaire",
            type="binary",
            frequency="daily",
            is_active=True,
            focus_role="goal",
            focus_goal_id=goal.id,
        )
        custom_quest = Habit(
            user_id=1,
            name="Répéter trente minutes",
            type="binary",
            frequency="daily",
            is_active=True,
            focus_role="goal",
            focus_goal_id=custom_goal.id,
        )
        db.add_all([old_quest, custom_quest])
        db.commit()
        old_id, custom_id = old_quest.id, custom_quest.id

    with factory() as db:
        focus_service.normalize_generated_goal_quest_names(db, db.get(User, 1))
        focus_service.normalize_generated_goal_quest_names(db, db.get(User, 1))
        db.commit()
        assert db.get(Habit, old_id).name == "Devenir Millionnaire"
        assert db.get(Habit, custom_id).name == "Répéter trente minutes"


def test_linked_quest_rejects_checklist_role_change_archive_and_delete(focus_client):
    client, _ = focus_client
    headers = {"X-User-ID": "1"}
    goal_id = client.post(
        "/api/v1/goals", json={"title": "Apprendre"}, headers=headers
    ).json()["goal"]["id"]
    client.put(
        "/api/v1/profile/pins", json={"pinned_goals": [goal_id]}, headers=headers
    )
    quest = next(
        habit
        for habit in client.get("/api/v1/habits", headers=headers).json()
        if habit["focus_goal_id"] == goal_id
    )
    quest_id = quest["id"]

    assert (
        client.put(
            f"/api/v1/habits/{quest_id}",
            json={
                "progress_mode": "checklist",
                "checklist_items": [{"label": "Étape"}],
            },
            headers=headers,
        ).status_code
        == 422
    )
    assert (
        client.put(
            f"/api/v1/habits/{quest_id}", json={"focus_role": "must"}, headers=headers
        ).status_code
        == 409
    )
    assert (
        client.put(
            f"/api/v1/habits/{quest_id}", json={"is_active": False}, headers=headers
        ).status_code
        == 409
    )
    assert (
        client.post(f"/api/v1/habits/{quest_id}/archive", headers=headers).status_code
        == 409
    )
    assert (
        client.delete(f"/api/v1/habits/{quest_id}", headers=headers).status_code == 409
    )
    assert (
        client.post(
            "/api/v1/habits",
            json={
                "name": "Autre quête liée",
                "type": "binary",
                "focus_role": "goal",
                "focus_goal_id": goal_id,
                "progress_mode": "checklist",
                "checklist_items": [{"label": "Étape"}],
            },
            headers=headers,
        ).status_code
        == 422
    )


def test_todo_goal_cannot_be_removed_or_replaced(focus_client):
    client, _ = focus_client
    headers = {"X-User-ID": "1"}
    created = client.post(
        "/api/v1/todos",
        json={"title": "Livrer", "create_linked_goal": True},
        headers=headers,
    )
    assert created.status_code == 201
    goal_id = next(
        goal["id"]
        for goal in client.get("/api/v1/goals", headers=headers).json()
        if goal["source_todo_id"] == created.json()["todo"]["id"]
    )
    assert (
        client.put(
            "/api/v1/profile/pins", json={"pinned_goals": []}, headers=headers
        ).status_code
        == 409
    )
    for title in ("Deuxième", "Troisième"):
        new_goal_id = client.post(
            "/api/v1/goals", json={"title": title}, headers=headers
        ).json()["goal"]["id"]
        pins = client.get("/api/v1/profile", headers=headers).json()["pinned_goals"]
        assert (
            client.put(
                "/api/v1/profile/pins",
                json={"pinned_goals": pins + [new_goal_id]},
                headers=headers,
            ).status_code
            == 200
        )
    blocked = client.post(
        "/api/v1/todos",
        json={
            "title": "Nouveau",
            "create_linked_goal": True,
            "replace_pinned_goal_id": goal_id,
        },
        headers=headers,
    )
    assert blocked.status_code == 409


def test_existing_linked_checklist_becomes_simple_without_losing_logs(focus_client):
    client, factory = focus_client
    headers = {"X-User-ID": "1"}
    goal_id = client.post(
        "/api/v1/goals", json={"title": "Automatisation"}, headers=headers
    ).json()["goal"]["id"]
    client.put(
        "/api/v1/profile/pins", json={"pinned_goals": [goal_id]}, headers=headers
    )
    with factory() as db:
        quest = db.query(Habit).filter_by(focus_goal_id=goal_id).one()
        quest.progress_mode = "checklist"
        quest.checklist_items = [{"id": "step-1", "label": "Ancienne étape"}]
        quest.progress_config_history = [
            {
                "effective_from": datetime.date.today().isoformat(),
                "mode": "checklist",
                "type": "binary",
                "unit": None,
                "daily_target": 1,
                "checklist_items": [{"id": "step-1", "label": "Ancienne étape"}],
            }
        ]
        db.flush()
        quest_id = quest.id
        db.add(
            HabitDailyProgress(
                user_id=1,
                habit_id=quest_id,
                date=datetime.date.today(),
                mode_snapshot="checklist",
                checklist_state=[{"id": "step-1", "checked": True}],
            )
        )
        db.commit()
    with factory() as db:
        focus_service.remove_focus_checklists(db, db.get(User, 1))
        db.commit()
        quest = db.get(Habit, quest_id)
        assert quest.progress_mode == "standard"
        assert quest.checklist_items == []
        assert all(
            entry["mode"] != "checklist" for entry in quest.progress_config_history
        )
        assert db.query(HabitDailyProgress).filter_by(habit_id=quest_id).first() is None
    logged = client.post(
        "/api/v1/logs", json={"habit_id": quest_id, "log_type": "done"}, headers=headers
    )
    assert logged.status_code == 200
