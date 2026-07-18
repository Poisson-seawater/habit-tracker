from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from src.database import seed


def test_v28_day_types_migration_is_idempotent_and_backfills(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy_day_types.db"
    test_engine = create_engine(f"sqlite:///{db_path}")
    TestSessionLocal = sessionmaker(bind=test_engine)

    with test_engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE habits (
                    id INTEGER PRIMARY KEY,
                    effort_type TEXT,
                    effort_duration REAL DEFAULT 1.0,
                    source_type TEXT DEFAULT 'manual',
                    source_ref TEXT,
                    auto_managed BOOLEAN DEFAULT 0 NOT NULL,
                    archived_at DATETIME,
                    agenda_duration_minutes INTEGER,
                    agenda_placeable BOOLEAN DEFAULT 1 NOT NULL
                )
                """
            )
        )
        connection.execute(text("INSERT INTO habits (id) VALUES (1)"))

    monkeypatch.setattr(seed, "engine", test_engine)
    monkeypatch.setattr(seed, "SessionLocal", TestSessionLocal)

    seed._run_migrations()
    seed._run_migrations()

    columns = {column["name"] for column in inspect(test_engine).get_columns("habits")}
    assert "day_types" in columns
    with test_engine.connect() as connection:
        value = connection.execute(
            text("SELECT day_types FROM habits WHERE id = 1")
        ).scalar_one()
    assert value == '["rest","regular","hustle"]'
