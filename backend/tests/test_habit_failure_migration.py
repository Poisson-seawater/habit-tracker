from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from src.database import seed


def test_habit_failure_cancellation_migration_is_idempotent(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy_habit_logs.db"
    test_engine = create_engine(f"sqlite:///{db_path}")
    test_session = sessionmaker(bind=test_engine)
    with test_engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE habit_logs (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    habit_id INTEGER NOT NULL,
                    timestamp DATETIME,
                    log_type VARCHAR NOT NULL
                )
                """
            )
        )

    monkeypatch.setattr(seed, "engine", test_engine)
    monkeypatch.setattr(seed, "SessionLocal", test_session)

    seed._run_migrations()
    seed._run_migrations()

    columns = {
        column["name"] for column in inspect(test_engine).get_columns("habit_logs")
    }
    assert "cancelled_at" in columns
    assert "xp_penalty" in columns
