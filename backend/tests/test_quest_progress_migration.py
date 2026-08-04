from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from src.database import seed


def test_v31_quest_progress_migration_is_idempotent(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy_quest_progress.db"
    test_engine = create_engine(f"sqlite:///{db_path}")
    test_session = sessionmaker(bind=test_engine)

    with test_engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        connection.execute(
            text(
                """
                CREATE TABLE habits (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    agenda_placeable BOOLEAN DEFAULT 1 NOT NULL,
                    day_types TEXT
                )
                """
            )
        )
        connection.execute(text("INSERT INTO users (id) VALUES (1)"))
        connection.execute(text("INSERT INTO habits (id, user_id) VALUES (1, 1)"))

    monkeypatch.setattr(seed, "engine", test_engine)
    monkeypatch.setattr(seed, "SessionLocal", test_session)

    seed._run_migrations()
    seed._run_migrations()

    inspector = inspect(test_engine)
    habit_columns = {column["name"] for column in inspector.get_columns("habits")}
    assert {
        "progress_mode",
        "progress_config_history",
        "checklist_items",
    } <= habit_columns
    assert "habit_daily_progress" in inspector.get_table_names()

    progress_columns = {
        column["name"] for column in inspector.get_columns("habit_daily_progress")
    }
    assert {
        "user_id",
        "habit_id",
        "date",
        "mode_snapshot",
        "unit_snapshot",
        "counter_value",
        "checklist_state",
    } <= progress_columns

    indexes = {index["name"] for index in inspector.get_indexes("habit_daily_progress")}
    assert {
        "ix_habit_daily_progress_user_id",
        "ix_habit_daily_progress_habit_id",
        "ix_habit_daily_progress_date",
    } <= indexes

    with test_engine.connect() as connection:
        mode = connection.execute(
            text("SELECT progress_mode FROM habits WHERE id = 1")
        ).scalar_one()
    assert mode == "standard"
