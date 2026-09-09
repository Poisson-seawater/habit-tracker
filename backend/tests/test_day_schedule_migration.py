import json

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from src.database import seed
from src.services.day_cycle_service import DEFAULT_CHILL_WEEK, DEFAULT_NORMAL_WEEK


def test_v33_day_schedule_migration_is_idempotent(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy_day_schedule.db"
    test_engine = create_engine(f"sqlite:///{db_path}")
    test_session = sessionmaker(bind=test_engine)

    with test_engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        connection.execute(
            text(
                """
                CREATE TABLE day_cycle_policies (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    anchor_date DATE NOT NULL,
                    effective_from DATE NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """
            )
        )
        connection.execute(text("INSERT INTO users (id) VALUES (1)"))
        connection.execute(
            text(
                """
                INSERT INTO day_cycle_policies
                    (id, user_id, anchor_date, effective_from, created_at)
                VALUES
                    (1, 1, '2026-08-03', '2026-08-03', '2026-08-03 08:00:00')
                """
            )
        )

    monkeypatch.setattr(seed, "engine", test_engine)
    monkeypatch.setattr(seed, "SessionLocal", test_session)

    seed._run_migrations()
    seed._run_migrations()

    inspector = inspect(test_engine)
    policy_columns = {
        column["name"] for column in inspector.get_columns("day_cycle_policies")
    }
    assert {"normal_week_json", "chill_week_json"} <= policy_columns
    assert "day_type_overrides" in inspector.get_table_names()

    with test_engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT normal_week_json, chill_week_json "
                "FROM day_cycle_policies WHERE id = 1"
            )
        ).one()
    assert json.loads(row[0]) == DEFAULT_NORMAL_WEEK
    assert json.loads(row[1]) == DEFAULT_CHILL_WEEK
