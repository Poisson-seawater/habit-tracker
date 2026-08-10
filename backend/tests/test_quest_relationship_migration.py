import json

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from src.database import seed


def test_v32_tag_migration_archives_generated_quests_idempotently(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "legacy_quest_relationships.db"
    test_engine = create_engine(f"sqlite:///{db_path}")
    test_session = sessionmaker(bind=test_engine)

    with test_engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    username VARCHAR NOT NULL UNIQUE
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE quest_links (
                    id INTEGER PRIMARY KEY,
                    relationship_root_id INTEGER NOT NULL,
                    kind VARCHAR(32) NOT NULL,
                    ref VARCHAR(100) NOT NULL
                )
                """
            )
        )
        connection.execute(
            text("INSERT INTO users (id, username) VALUES (1, 'Gabriel')")
        )
        connection.execute(
            text(
                """
                CREATE TABLE habits (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    name VARCHAR NOT NULL,
                    effort_type TEXT,
                    effort_duration REAL DEFAULT 1.0,
                    source_type TEXT DEFAULT 'manual',
                    source_ref TEXT,
                    auto_managed BOOLEAN DEFAULT 0 NOT NULL,
                    archived_at DATETIME,
                    agenda_duration_minutes INTEGER,
                    agenda_placeable BOOLEAN DEFAULT 1 NOT NULL,
                    day_types TEXT,
                    progress_mode VARCHAR DEFAULT 'standard' NOT NULL,
                    progress_config_history JSON,
                    checklist_items JSON
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO habits
                    (id, user_id, name, source_type, source_ref, auto_managed,
                     checklist_items)
                VALUES
                    (1, 1, 'routine_matin', 'manual', NULL, 0, '[{"id":"water"}]'),
                    (2, 1, 'Étape 1 - Focus', 'substep', '10', 1, '[{"id":"plan"}]'),
                    (3, 1, 'Étape 2 - Focus', 'substep', '10', 1, '[{"id":"ship"}]')
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE daily_agenda_placements (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    date DATE NOT NULL,
                    habit_id INTEGER NOT NULL,
                    duration_minutes INTEGER NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                "INSERT INTO daily_agenda_placements "
                "(id, user_id, date, habit_id, duration_minutes) "
                "VALUES (1, 1, '2026-08-09', 2, 60)"
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE perfect_day_templates (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    template_name VARCHAR NOT NULL,
                    focus_hours REAL DEFAULT 6.0,
                    ceilings_json TEXT,
                    min_rest_hours REAL DEFAULT 8.0,
                    agenda_json TEXT
                )
                """
            )
        )
        agenda = {
            "schema_version": 2,
            "segments": [],
            "default_placements": [
                {"habit_id": 1, "start": "07:00", "duration_minutes": 60},
                {"habit_id": 2, "start": "08:00", "duration_minutes": 60},
            ],
        }
        connection.execute(
            text(
                "INSERT INTO perfect_day_templates "
                "(id, user_id, template_name, agenda_json) "
                "VALUES (1, 1, 'regular', :agenda)"
            ),
            {"agenda": json.dumps(agenda)},
        )
        connection.execute(
            text(
                """
                CREATE TABLE habit_logs (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    habit_id INTEGER NOT NULL,
                    timestamp DATETIME,
                    log_type VARCHAR NOT NULL,
                    cancelled_at DATETIME,
                    xp_penalty INTEGER DEFAULT 0 NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                "INSERT INTO habit_logs "
                "(id, user_id, habit_id, log_type) VALUES (1, 1, 2, 'done')"
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE habit_daily_progress (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    habit_id INTEGER NOT NULL,
                    date DATE NOT NULL,
                    mode_snapshot VARCHAR NOT NULL,
                    unit_snapshot VARCHAR,
                    counter_value INTEGER DEFAULT 0 NOT NULL,
                    checklist_state JSON,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    UNIQUE (user_id, habit_id, date)
                )
                """
            )
        )
        connection.execute(
            text(
                "INSERT INTO habit_daily_progress "
                "(id, user_id, habit_id, date, mode_snapshot, counter_value, "
                "checklist_state, created_at, updated_at) VALUES "
                "(1, 1, 2, '2026-08-09', 'checklist', 0, "
                "'[\"plan\"]', '2026-08-09 08:00:00', '2026-08-09 08:00:00')"
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE streaks (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    streak_type VARCHAR NOT NULL,
                    current_streak INTEGER DEFAULT 0,
                    max_streak INTEGER DEFAULT 0
                )
                """
            )
        )
        connection.execute(
            text(
                "INSERT INTO streaks "
                "(id, user_id, streak_type, current_streak, max_streak) "
                "VALUES (1, 1, 'habit:2', 14, 21)"
            )
        )

    monkeypatch.setattr(seed, "engine", test_engine)
    monkeypatch.setattr(seed, "SessionLocal", test_session)

    seed._run_migrations()
    seed._run_migrations()

    inspector = inspect(test_engine)
    columns = {column["name"] for column in inspector.get_columns("habits")}
    assert "relationship_root_id" in columns
    assert "quest_tags" in inspector.get_table_names()
    assert "quest_links" not in inspector.get_table_names()

    with test_engine.connect() as connection:
        habits = connection.execute(
            text(
                "SELECT id, relationship_root_id, archived_at, checklist_items "
                "FROM habits ORDER BY id"
            )
        ).fetchall()
        assert habits[0][1] == 1
        assert habits[0][2] is None
        assert habits[1][1] == habits[2][1] == 2
        assert habits[1][2] is not None and habits[2][2] is not None
        assert habits[1][3] == '[{"id":"plan"}]'
        assert (
            connection.execute(text("SELECT COUNT(*) FROM habit_logs")).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                text("SELECT checklist_state FROM habit_daily_progress WHERE id = 1")
            ).scalar_one()
            == '["plan"]'
        )
        assert (
            connection.execute(
                text("SELECT current_streak FROM streaks WHERE id = 1")
            ).scalar_one()
            == 14
        )
        assert (
            connection.execute(
                text("SELECT COUNT(*) FROM daily_agenda_placements")
            ).scalar_one()
            == 0
        )
        migrated_agenda = json.loads(
            connection.execute(
                text("SELECT agenda_json FROM perfect_day_templates WHERE id = 1")
            ).scalar_one()
        )
        assert [item["habit_id"] for item in migrated_agenda["default_placements"]] == [
            1
        ]
