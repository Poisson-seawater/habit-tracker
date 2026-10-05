import copy
import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import seed
from src.database.models import Goal, Habit, HabitLog, QuestTag, User
from src.database.session import Base, get_db
from src.main import app
from src.services import focus_service, quest_tag_service, softskill_service
from src.services.agenda_service import is_habit_eligible_on_date

HEADERS = {"X-User-ID": "1"}


@pytest.fixture
def linked_client(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    with factory() as db:
        db.add_all([User(id=1, username="gabriel"), User(id=2, username="other")])
        db.commit()
    config = {
        "branches": {"music": {"color": "#abcdef"}, "other": {"color": "#123456"}},
        "skills": [{"id": "ukulele", "name": "Ukulele", "branch": "music"}],
    }
    monkeypatch.setattr(
        softskill_service, "load_tree_config", lambda **kw: copy.deepcopy(config)
    )

    def save_config(value):
        config.clear()
        config.update(copy.deepcopy(value))

    monkeypatch.setattr(softskill_service, "save_tree_config", save_config)

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    try:
        yield TestClient(app), factory, config
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def find_quest(client, habit_id):
    return next(
        h
        for h in client.get(
            "/api/v1/habits?include_inactive=true&include_all_versions=true",
            headers=HEADERS,
        ).json()
        if h["id"] == habit_id
    )


@pytest.mark.parametrize("role", ["goal", "skill"])
def test_skill_pin_and_legacy_goal_keep_locked_tags_without_changing_rpg(
    linked_client, role
):
    client, factory, _ = linked_client
    with factory() as db:
        if role == "goal":
            db.add(Goal(id=10, user_id=1, title="Voyager"))
            db.flush()
            focus_service.create_goal_quest(db, 1, db.get(Goal, 10))
            db.commit()
    pin = (
        {"pinned_goals": [10]} if role == "goal" else {"pinned_softskills": ["ukulele"]}
    )
    assert (
        client.put("/api/v1/profile/pins", json=pin, headers=HEADERS).status_code == 200
    )
    quest = next(
        h
        for h in client.get("/api/v1/habits", headers=HEADERS).json()
        if h["focus_role"] == role
    )
    expected = (
        {"kind": "goal", "ref": "10", "label": "Voyager", "locked": True}
        if role == "goal"
        else {"kind": "softskill", "ref": "ukulele", "label": "Ukulele", "locked": True}
    )
    assert quest["tags"] == [expected]
    assert (
        client.put(
            f"/api/v1/habits/{quest['id']}",
            json={"tags": [], "day_types": ["rest"]},
            headers=HEADERS,
        ).status_code
        == 200
    )
    assert find_quest(client, quest["id"])["tags"] == [expected]
    assert find_quest(client, quest["id"])["day_types"] == ["rest", "regular", "hustle"]
    with factory() as db:
        assert (db.get(User, 1).xp, db.get(User, 1).gold) == (0, 0)
        assert db.query(HabitLog).count() == 0


def test_direct_create_conversion_and_versions_preserve_locked_and_manual_tags(
    linked_client,
):
    client, factory, _ = linked_client
    with factory() as db:
        db.add_all(
            [
                Goal(id=10, user_id=1, title="Voyager"),
                Goal(id=11, user_id=1, title="Lire"),
            ]
        )
        db.commit()
    created = client.post(
        "/api/v1/habits",
        json={
            "name": "Versionnée",
            "type": "binary",
            "tags": [{"kind": "goal", "ref": "11"}],
        },
        headers=HEADERS,
    )
    habit_id = created.json()["id"]
    converted = client.put(
        f"/api/v1/habits/{habit_id}",
        json={"focus_role": "goal", "focus_goal_id": 10, "day_types": ["hustle"]},
        headers=HEADERS,
    )
    assert converted.status_code == 200, converted.text
    tags = find_quest(client, habit_id)["tags"]
    assert {(t["ref"], t["locked"]) for t in tags} == {("10", True), ("11", False)}
    version = client.post(
        f"/api/v1/habits/{habit_id}/versions",
        json={"description": "V2"},
        headers=HEADERS,
    )
    assert version.status_code == 201, version.text
    new_id = version.json()["id"]
    assert find_quest(client, new_id)["tags"] == tags
    assert (
        client.put(
            f"/api/v1/habits/{habit_id}", json={"tags": []}, headers=HEADERS
        ).status_code
        == 200
    )
    assert find_quest(client, new_id)["tags"] == find_quest(client, habit_id)["tags"]
    assert find_quest(client, new_id)["tags"][0]["ref"] == "10"
    direct = client.post(
        "/api/v1/habits",
        json={
            "name": "Pratique",
            "type": "binary",
            "focus_role": "skill",
            "focus_softskill_id": "ukulele",
            "day_types": ["rest"],
        },
        headers=HEADERS,
    )
    assert direct.status_code == 201, direct.text
    assert find_quest(client, direct.json()["id"])["tags"][0]["locked"] is True
    assert find_quest(client, direct.json()["id"])["day_types"] == [
        "rest",
        "regular",
        "hustle",
    ]


def test_legacy_repair_is_idempotent_and_preserves_logs_manual_tags_and_schedule(
    linked_client,
):
    _, factory, _ = linked_client
    with factory() as db:
        db.add(Goal(id=10, user_id=1, title="Voyager"))
        user = db.get(User, 1)
        user.pinned_goals = [10]
        quest = Habit(
            user_id=1,
            name="Ancienne quête",
            type="binary",
            focus_role="goal",
            focus_goal_id=10,
            day_types=["hustle"],
            frequency="specific_days",
            scheduled_days="1",
        )
        db.add(quest)
        db.flush()
        quest.relationship_root_id = quest.id
        db.add(
            QuestTag(
                relationship_root_id=quest.id, kind="softskill_branch", ref="music"
            )
        )
        db.add(HabitLog(user_id=1, habit_id=quest.id, log_type="done"))
        db.commit()
        for _ in range(2):
            quest_tag_service.normalize_linked_quests(db, 1)
            db.commit()
        assert db.query(QuestTag).count() == 2
        assert db.query(HabitLog).count() == 1
        assert quest.scheduled_days == "1"
        monday = datetime.date(2026, 10, 5)
        for day_type in ("rest", "regular", "hustle"):
            assert is_habit_eligible_on_date(quest, monday, user, day_type)
        assert not is_habit_eligible_on_date(
            quest, monday + datetime.timedelta(days=1), user, "rest"
        )


@pytest.mark.parametrize("delete_branch", [False, True])
def test_skill_rename_and_deletion_clean_tags_without_resurrecting_them(
    linked_client, delete_branch
):
    client, factory, config = linked_client
    client.put(
        "/api/v1/profile/pins", json={"pinned_softskills": ["ukulele"]}, headers=HEADERS
    )
    quest = client.get("/api/v1/habits", headers=HEADERS).json()[0]
    config["skills"][0]["name"] = "Ukulélé"
    config["skills"][0]["branch"] = "other"
    assert find_quest(client, quest["id"])["tags"][0]["label"] == "Ukulélé"
    path = (
        "/api/v1/softskills/branches/other"
        if delete_branch
        else "/api/v1/softskills/skills/ukulele"
    )
    assert client.delete(path, headers=HEADERS).status_code == 200
    with factory() as db:
        quest_tag_service.normalize_linked_quests(db, 1)
        db.commit()
        assert db.query(QuestTag).filter_by(kind="softskill").count() == 0
    assert find_quest(client, quest["id"])["tags"] == []


def test_unknown_skill_and_foreign_goal_tags_are_rejected(linked_client):
    client, factory, _ = linked_client
    with factory() as db:
        db.add(Goal(id=20, user_id=2, title="Privé"))
        db.commit()
    for tag in ({"kind": "softskill", "ref": "missing"}, {"kind": "goal", "ref": "20"}):
        response = client.post(
            "/api/v1/habits",
            json={"name": "Invalide", "type": "binary", "tags": [tag]},
            headers=HEADERS,
        )
        assert response.status_code == 422


def test_rules_are_persisted_per_user_with_unicode_limit_and_clear(linked_client):
    client, factory, _ = linked_client
    assert client.get("/api/v1/profile/rules", headers=HEADERS).json() == {"text": ""}
    note = "é🫙\n" * 166 + "éé"
    assert len(note) == 500
    saved = client.put("/api/v1/profile/rules", json={"text": note}, headers=HEADERS)
    assert saved.status_code == 200
    assert client.get("/api/v1/profile/rules", headers=HEADERS).json() == {"text": note}
    assert client.get("/api/v1/profile/rules", headers={"X-User-ID": "2"}).json() == {
        "text": ""
    }
    for invalid in (note + "x", None):
        assert (
            client.put(
                "/api/v1/profile/rules", json={"text": invalid}, headers=HEADERS
            ).status_code
            == 422
        )
    with factory() as db:
        assert db.get(User, 1).rules_text == note
    assert client.put(
        "/api/v1/profile/rules", json={"text": ""}, headers=HEADERS
    ).json() == {"text": ""}


def test_rules_use_existing_authentication_and_missing_user_handling(linked_client):
    client, factory, _ = linked_client
    assert (
        client.get("/api/v1/profile/rules", headers={"X-User-ID": "999"}).status_code
        == 404
    )
    with factory() as db:
        db.get(User, 1).password_hash = "configured"
        db.commit()
    assert client.get("/api/v1/profile/rules").status_code == 401
    assert (
        client.put(
            "/api/v1/profile/rules", json={"text": "test"}, headers=HEADERS
        ).status_code
        == 401
    )


def test_v38_rules_migration_is_idempotent_and_preserves_note(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    factory = sessionmaker(bind=engine)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        connection.execute(text("INSERT INTO users (id) VALUES (1)"))
    monkeypatch.setattr(seed, "engine", engine)
    monkeypatch.setattr(seed, "SessionLocal", factory)
    seed._run_migrations()
    assert "rules_text" in {c["name"] for c in inspect(engine).get_columns("users")}
    with engine.begin() as connection:
        assert (
            connection.execute(text("SELECT rules_text FROM users")).scalar_one() == ""
        )
        connection.execute(text("UPDATE users SET rules_text = 'Conserver'"))
    seed._run_migrations()
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT rules_text FROM users")).scalar_one()
            == "Conserver"
        )
    engine.dispose()
