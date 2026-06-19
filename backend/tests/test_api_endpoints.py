import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.session import Base, get_db
from src.database.models import User, Habit, HabitLog, PerfectDayTemplate, DailyScore, Streak, Goal, SubStep
from src.main import app

TEST_DB_FILE = "backend/tests/.test_habit_tracker_api.db"
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
        
        # Seed V2 PerfectDayTemplates
        t1 = PerfectDayTemplate(
            user_id=1,
            template_name="week",
            thresholds_json={"discipline": 4}
        )
        t2 = PerfectDayTemplate(
            user_id=1,
            template_name="weekend",
            thresholds_json={"sante": 5}
        )
        db.add_all([t1, t2])
        
        # Seed default habits
        h1 = Habit(
            id=1,
            user_id=1,
            name="routine_matin",
            type="binary",
            point_rewards={"discipline": 2},
            is_active=True
        )
        h2 = Habit(
            id=2,
            user_id=1,
            name="lecture",
            type="quantitative",
            unit="min",
            point_rewards={"discipline": 2},
            daily_cap=5,
            is_active=True
        )
        db.add_all([h1, h2])
        db.commit()
    finally:
        db.close()
        
    # Set the override during the execution of this module
    app.dependency_overrides[get_db] = override_get_db
    yield
    
    if get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]
        
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass

client = TestClient(app)

def test_get_profile_endpoint():
    response = client.get("/api/v1/profile")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "Gabriel"
    assert "scores" in data
    assert "stats" in data
    assert "thresholds" in data

def test_get_habits_endpoint():
    response = client.get("/api/v1/habits")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2

def test_telegram_webapp_session_resolves_existing_user():
    response = client.post("/api/v1/telegram-webapp/session", json={
        "id": 111,
        "username": "Gabriel",
        "first_name": "Gabriel"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["username"] == "Gabriel"

def test_telegram_webapp_session_does_not_rename_existing_chat_id():
    response = client.post("/api/v1/telegram-webapp/session", json={
        "id": 111,
        "username": "PandaCoffey",
        "first_name": "Gabriel"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["username"] == "Gabriel"

def test_telegram_webapp_session_creates_unknown_user():
    response = client.post("/api/v1/telegram-webapp/session", json={
        "id": 333,
        "first_name": "Alice"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "Alice"
    assert data["id"] > 1

def test_post_logs_endpoint():
    response = client.post("/api/v1/logs", json={
        "habit_id": 1,
        "log_type": "done"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "logged"

def test_change_template_success():
    response = client.post("/api/v1/profile/template", json={"template_name": "weekend"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "updated"
    assert data["active_template"] == "weekend"

def test_create_and_complete_todo_endpoints():
    payload = {
        "title": "⚔️ Dompter le Dragon de Fer (Séance Jambes)",
        "xp_reward": 30,
        "stat_reward_1": "discipline",
        "points_reward_1": 5
    }
    response = client.post("/api/v1/todos", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["todo"]["xp_reward"] == 30
    todo_id = data["todo"]["id"]

    response = client.post(f"/api/v1/todos/{todo_id}/complete")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["xp_rewarded"] == 30

def test_goals_and_substeps_crud():
    # 1. Create a Goal
    response = client.post("/api/v1/goals", json={
        "title": "Devenir Millionnaire",
        "description": "Atteindre 1M en actif"
    })
    assert response.status_code == 201
    goal = response.json()["goal"]
    goal_id = goal["id"]

    # 2. Add SubStep
    response = client.post(f"/api/v1/goals/{goal_id}/substeps", json={
        "title": "Trouver un bon avocat",
        "description": "Réseauter pour trouver un expert",
        "gold_reward": 200,
        "stats_json": ["discipline"]
    })
    assert response.status_code == 201
    substep = response.json()["substep"]
    substep_id = substep["id"]
    assert substep["description"] == "Réseauter pour trouver un expert"

    # 3. Retrieve Goals Graphes
    response = client.get("/api/v1/goals")
    assert response.status_code == 200
    goals = response.json()
    assert len(goals) >= 1
    assert goals[-1]["title"] == "Devenir Millionnaire"
    assert goals[-1]["substeps"][0]["title"] == "Trouver un bon avocat"
    assert goals[-1]["substeps"][0]["description"] == "Réseauter pour trouver un expert"

    # 4. Update SubStep
    response = client.put(f"/api/v1/substeps/{substep_id}", json={
        "title": "Trouver un SUPER avocat",
        "description": "Engager le meilleur avocat de la ville",
        "gold_reward": 300,
        "stats_json": ["discipline"],
        "blocked_by_ids": []
    })
    assert response.status_code == 200
    substep_updated = response.json()["substep"]
    assert substep_updated["title"] == "Trouver un SUPER avocat"
    assert substep_updated["description"] == "Engager le meilleur avocat de la ville"
    assert substep_updated["gold_reward"] == 300

    # 5. Delete SubStep
    response = client.delete(f"/api/v1/substeps/{substep_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # 6. Update Goal
    response = client.put(f"/api/v1/goals/{goal_id}", json={
        "title": "Devenir Milliardaire",
        "description": "Atteindre 1B en actif"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["goal"]["title"] == "Devenir Milliardaire"

    # 7. Delete Goal
    response = client.delete(f"/api/v1/goals/{goal_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"


# --- B1: GET /status (streak + skip reasons) ---

def test_get_status_endpoint():
    # Insert logs directly with a deterministic noon-today timestamp so the test does not
    # depend on the runner's UTC/local offset (the /status window is built from date.today()).
    import datetime
    noon_today = datetime.datetime.combine(datetime.date.today(), datetime.time(12, 0))
    db = TestingSessionLocal()
    try:
        db.add(HabitLog(user_id=1, habit_id=1, log_type="done", timestamp=noon_today))
        db.add(HabitLog(user_id=1, habit_id=2, log_type="skip",
                        reason="Pas le temps aujourd'hui", timestamp=noon_today))
        db.commit()
    finally:
        db.close()

    response = client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()

    # Perfect Day block + streak are exposed (impossible via other endpoints)
    assert data["perfect_day"]["status"] in ["Perfect", "Failed"]
    assert "thresholds" in data["perfect_day"]
    assert "current" in data["streak"]
    assert "max" in data["streak"]

    # The skip is reported with its reason
    skipped = [s for s in data["skipped"] if s["habit_id"] == 2]
    assert len(skipped) == 1
    assert skipped[0]["reason"] == "Pas le temps aujourd'hui"

    # The done habit is reported as completed and is no longer remaining
    completed_ids = [c["habit_id"] for c in data["completed"]]
    assert 1 in completed_ids
    remaining_ids = [r["habit_id"] for r in data["remaining"]]
    assert 1 not in remaining_ids
    assert 2 not in remaining_ids


# --- B3: server-side validation rejects bad data with 400 ---

def test_create_todo_rejects_bad_stat():
    response = client.post("/api/v1/todos", json={
        "title": "Todo avec stat fautive",
        "stat_reward_1": "forcee",  # typo of "force"
        "points_reward_1": 3
    })
    assert response.status_code == 400
    assert "forcee" in response.json()["detail"]

def test_create_habit_rejects_bad_type():
    response = client.post("/api/v1/habits", json={
        "name": "habit_bad_type",
        "type": "boolean",  # invalid
        "point_rewards": {"discipline": 2}
    })
    assert response.status_code == 400

def test_create_habit_rejects_empty_point_rewards():
    response = client.post("/api/v1/habits", json={
        "name": "habit_empty_pr",
        "type": "binary",
        "point_rewards": {}
    })
    assert response.status_code == 400
    assert "point_rewards" in response.json()["detail"]

def test_create_habit_rejects_bad_stat_key():
    response = client.post("/api/v1/habits", json={
        "name": "habit_bad_stat",
        "type": "binary",
        "point_rewards": {"forcee": 2}
    })
    assert response.status_code == 400
    assert "forcee" in response.json()["detail"]

def test_create_habit_quantitative_requires_unit():
    response = client.post("/api/v1/habits", json={
        "name": "habit_no_unit",
        "type": "quantitative",
        "point_rewards": {"forme_physique": 2}
    })
    assert response.status_code == 400
    assert "unit" in response.json()["detail"]

def test_create_habit_valid_still_passes():
    response = client.post("/api/v1/habits", json={
        "name": "pompes",
        "type": "quantitative",
        "unit": "rep",
        "daily_cap": 100,
        "point_rewards": {"forme_physique": 3}
    })
    assert response.status_code == 201
    assert response.json()["status"] == "success"


def test_per_goal_substep_execution_order():
    # 1. Create two goals
    resp_a = client.post("/api/v1/goals", json={"title": "Goal A", "description": "First goal"})
    assert resp_a.status_code == 201
    goal_a_id = resp_a.json()["goal"]["id"]

    resp_b = client.post("/api/v1/goals", json={"title": "Goal B", "description": "Second goal"})
    assert resp_b.status_code == 201
    goal_b_id = resp_b.json()["goal"]["id"]

    # 2. Create SubStep under Goal A with execution_order 2
    resp_s = client.post(f"/api/v1/goals/{goal_a_id}/substeps", json={
        "title": "Shared Substep",
        "description": "To be shared",
        "gold_reward": 100,
        "execution_order": 2
    })
    assert resp_s.status_code == 201
    substep_id = resp_s.json()["substep"]["id"]

    # 3. Link SubStep to Goal B with execution_order 5
    resp_link = client.post("/api/v1/substeps/link", json={
        "goal_id": goal_b_id,
        "substep_id": substep_id,
        "execution_order": 5
    })
    assert resp_link.status_code == 200
    assert resp_link.json()["status"] == "success"

    # 4. Fetch goals and assert orders
    resp_goals = client.get("/api/v1/goals")
    assert resp_goals.status_code == 200
    goals = resp_goals.json()
    
    goal_a = next(g for g in goals if g["id"] == goal_a_id)
    goal_b = next(g for g in goals if g["id"] == goal_b_id)

    assert goal_a["substeps"][0]["id"] == substep_id
    assert goal_a["substeps"][0]["execution_order"] == 2

    assert goal_b["substeps"][0]["id"] == substep_id
    assert goal_b["substeps"][0]["execution_order"] == 5

    # 5. Update substep generally (this should NOT overwrite link execution orders)
    resp_update = client.put(f"/api/v1/substeps/{substep_id}", json={
        "title": "Shared Substep Updated",
        "description": "To be shared",
        "gold_reward": 120,
        "execution_order": 9  # generic/default order
    })
    assert resp_update.status_code == 200

    resp_goals = client.get("/api/v1/goals")
    goals = resp_goals.json()
    goal_a = next(g for g in goals if g["id"] == goal_a_id)
    goal_b = next(g for g in goals if g["id"] == goal_b_id)

    # Confirm execution orders in links are unchanged
    assert goal_a["substeps"][0]["execution_order"] == 2
    assert goal_b["substeps"][0]["execution_order"] == 5

    # 6. Reorder specifically for Goal A to execution_order 4
    resp_reorder = client.put(f"/api/v1/goals/{goal_a_id}/substeps/{substep_id}/reorder", json={
        "execution_order": 4
    })
    assert resp_reorder.status_code == 200

    resp_goals = client.get("/api/v1/goals")
    goals = resp_goals.json()
    goal_a = next(g for g in goals if g["id"] == goal_a_id)
    goal_b = next(g for g in goals if g["id"] == goal_b_id)

    assert goal_a["substeps"][0]["execution_order"] == 4
    assert goal_b["substeps"][0]["execution_order"] == 5


def test_notodo_crud():
    # 1. Create a No-Todo
    response = client.post("/api/v1/notodos", json={
        "title": "Ne pas procrastiner"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["notodo"]["title"] == "Ne pas procrastiner"
    notodo_id = data["notodo"]["id"]

    # 2. Get list of No-Todos
    response = client.get("/api/v1/notodos")
    assert response.status_code == 200
    notodos = response.json()
    assert any(n["id"] == notodo_id for n in notodos)

    # 3. Fail No-Todo
    response = client.post(f"/api/v1/notodos/{notodo_id}/fail")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # 4. Delete No-Todo
    response = client.delete(f"/api/v1/notodos/{notodo_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # 5. Verify deleted No-Todo is gone
    response = client.get("/api/v1/notodos")
    assert response.status_code == 200
    notodos = response.json()
    assert not any(n["id"] == notodo_id for n in notodos)


