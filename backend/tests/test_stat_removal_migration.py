from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from src.database import seed


def test_v19_stat_column_removal_is_idempotent(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy_stats.db"
    test_engine = create_engine(f"sqlite:///{db_path}")
    TestSessionLocal = sessionmaker(bind=test_engine)

    with test_engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    username VARCHAR NOT NULL UNIQUE
                )
                """
            )
        )
        conn.execute(text("INSERT INTO users (id, username) VALUES (1, 'Gabriel')"))
        conn.execute(
            text(
                """
                CREATE TABLE habits (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    name VARCHAR NOT NULL,
                    point_rewards JSON
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE todos (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    title VARCHAR NOT NULL,
                    stat_reward_1 VARCHAR,
                    points_reward_1 INTEGER,
                    stat_reward_2 VARCHAR,
                    points_reward_2 INTEGER
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE substeps (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    title VARCHAR NOT NULL,
                    stats_json JSON
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE perfect_day_templates (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    template_name VARCHAR NOT NULL,
                    thresholds_json JSON,
                    focus_hours REAL DEFAULT 6.0,
                    ceilings_json TEXT,
                    min_rest_hours REAL DEFAULT 8.0,
                    agenda_json TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE daily_scores (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    date DATE NOT NULL,
                    status VARCHAR,
                    template_used VARCHAR,
                    actual_stats JSON
                )
                """
            )
        )

    monkeypatch.setattr(seed, "engine", test_engine)
    monkeypatch.setattr(seed, "SessionLocal", TestSessionLocal)

    seed._run_migrations()
    seed._run_migrations()

    inspector = inspect(test_engine)
    expected_removed = {
        "habits": {"point_rewards"},
        "todos": {
            "stat_reward_1",
            "points_reward_1",
            "stat_reward_2",
            "points_reward_2",
        },
        "substeps": {"stats_json"},
        "perfect_day_templates": {"thresholds_json"},
        "daily_scores": {"actual_stats"},
    }

    for table_name, removed_columns in expected_removed.items():
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        assert not (columns & removed_columns)
