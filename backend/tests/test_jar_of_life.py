import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from src.database.models import Habit, JarWeek, Todo, User
from src.database.session import Base, get_db
from src.main import app
from src.database import seed


WEEK = "2026-09-28"
HEADERS_1 = {"X-User-ID": "1"}
HEADERS_2 = {"X-User-ID": "2"}


@pytest.fixture
def jar_db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'jar.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    with session_factory() as db:
        db.add_all([User(id=1, username="one"), User(id=2, username="two")])
        db.add_all(
            [
                Habit(
                    user_id=1,
                    name="Course",
                    type="binary",
                    frequency="specific_days",
                    scheduled_days="1",
                    day_types=["rest", "regular", "hustle"],
                ),
                Habit(
                    user_id=2,
                    name="Privée",
                    type="binary",
                    frequency="daily",
                ),
                Todo(
                    user_id=1,
                    title="Rendez-vous",
                    do_date=datetime.date(2026, 9, 30),
                ),
                Todo(
                    user_id=1,
                    title="Échéance seule",
                    due_date=datetime.date(2026, 9, 30),
                ),
                Todo(
                    user_id=2,
                    title="Autre utilisateur",
                    do_date=datetime.date(2026, 9, 30),
                ),
            ]
        )
        db.commit()

    app.dependency_overrides[get_db] = override_db
    try:
        yield TestClient(app), session_factory
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def test_week_candidates_follow_schedule_and_work_date(jar_db):
    client, _ = jar_db
    response = client.get(f"/api/v1/jar-of-life/{WEEK}", headers=HEADERS_1)
    assert response.status_code == 200
    assert response.json()["plan"]["available_blocks"] == []
    candidates = response.json()["candidates"]
    assert [(item["title"], item["days"]) for item in candidates] == [
        ("Course", ["2026-09-28"]),
        ("Rendez-vous", ["2026-09-30"]),
    ]


def test_week_plan_persists_per_user_without_touching_actions(jar_db):
    client, session_factory = jar_db
    candidates = client.get(f"/api/v1/jar-of-life/{WEEK}", headers=HEADERS_1).json()[
        "candidates"
    ]
    quest_id = candidates[0]["source_id"]
    plan = {
        "available_blocks": ["0-morning", "2-evening", "6-afternoon"],
        "items": [
            {
                "id": "health",
                "title": "Prendre soin de ma santé",
                "category": "rock",
                "source_type": "habit",
                "source_id": quest_id,
            },
            {"id": "admin", "title": "Administration", "category": "sand"},
        ],
        "placements": {"0-morning": "health", "2-evening": "admin"},
    }
    response = client.put(f"/api/v1/jar-of-life/{WEEK}", json=plan, headers=HEADERS_1)
    assert response.status_code == 200, response.text
    assert response.json()["placements"] == plan["placements"]
    again = client.get(f"/api/v1/jar-of-life/{WEEK}", headers=HEADERS_1)
    assert again.json()["plan"]["items"][0]["title"] == "Prendre soin de ma santé"
    assert (
        client.get(f"/api/v1/jar-of-life/{WEEK}", headers=HEADERS_2).json()["plan"][
            "items"
        ]
        == []
    )
    with session_factory() as db:
        assert db.query(JarWeek).count() == 1
        assert db.query(Habit).filter_by(id=quest_id).one().is_active is True
        assert (
            db.query(Todo).filter_by(user_id=1, title="Rendez-vous").one().is_completed
            is False
        )


def test_invalid_blocks_rocks_and_foreign_source_are_rejected(jar_db):
    client, session_factory = jar_db
    base = {
        "available_blocks": ["0-morning"],
        "items": [{"id": "one", "title": "Focus", "category": "rock"}],
        "placements": {"0-morning": "one"},
    }
    assert (
        client.put(
            "/api/v1/jar-of-life/2026-09-29", json=base, headers=HEADERS_1
        ).status_code
        == 400
    )
    invalid = {**base, "placements": {"0-evening": "one"}}
    assert (
        client.put(
            f"/api/v1/jar-of-life/{WEEK}", json=invalid, headers=HEADERS_1
        ).status_code
        == 422
    )
    invalid = {
        **base,
        "items": [
            {"id": str(index), "title": str(index), "category": "rock"}
            for index in range(4)
        ],
    }
    assert (
        client.put(
            f"/api/v1/jar-of-life/{WEEK}", json=invalid, headers=HEADERS_1
        ).status_code
        == 422
    )
    with session_factory() as db:
        foreign_id = db.query(Habit.id).filter_by(user_id=2).scalar()
    invalid = {
        **base,
        "items": [
            {
                "id": "one",
                "title": "Privée",
                "category": "rock",
                "source_type": "habit",
                "source_id": foreign_id,
            }
        ],
    }
    assert (
        client.put(
            f"/api/v1/jar-of-life/{WEEK}", json=invalid, headers=HEADERS_1
        ).status_code
        == 400
    )


def test_v36_creates_missing_table_idempotently(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'migration.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    JarWeek.__table__.drop(engine)
    monkeypatch.setattr(seed, "engine", engine)
    monkeypatch.setattr(seed, "SessionLocal", sessionmaker(bind=engine))
    seed._run_migrations()
    seed._run_migrations()
    assert "jar_weeks" in inspect(engine).get_table_names()
    assert {"user_id", "week_start", "available_blocks", "items", "placements"} <= {
        column["name"] for column in inspect(engine).get_columns("jar_weeks")
    }
    engine.dispose()
