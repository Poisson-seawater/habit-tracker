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
    SubStep,
    Todo,
    User,
)
from src.database.session import Base, get_db
from src.main import app


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
    created = client.post(
        "/api/v1/habits",
        json={
            "name": "Contrat quotidien",
            "type": "binary",
            "focus_role": "goal",
            "focus_goal_id": goal["id"],
        },
        headers=headers,
    )
    assert created.status_code == 201
    habit_id = created.json()["id"]
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
    created = client.post(
        "/api/v1/habits",
        json={
            "name": "Pratiquer Danse",
            "type": "binary",
            "focus_role": "goal",
            "focus_goal_id": goal_id,
        },
        headers=headers,
    )
    assert created.status_code == 201
    habit_id = created.json()["id"]
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
