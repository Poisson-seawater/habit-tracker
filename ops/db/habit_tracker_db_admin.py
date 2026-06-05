#!/usr/bin/env python3
"""Maintenance helpers for the Habit Tracker SQLite database.

The runtime DB stays under data/ and is ignored by Git. This script creates
backups, performs the Gabriel/PandaCoffey merge, and exports/restores a SQL
snapshot that can be committed safely as an explicit deployment artifact.
"""

from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "data" / "habit_tracker.db"
DEFAULT_SNAPSHOT = ROOT / "ops" / "db" / "habit_tracker_snapshot.sql"
BACKUP_DIR = ROOT / "data" / "backups"


USER_TABLES = [
    "perfect_day_templates",
    "daily_scores",
    "streaks",
    "todos",
    "notodos",
    "goals",
    "substeps",
]


def timestamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def backup_db(db_path: Path) -> Path:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / f"{db_path.stem}-{timestamp()}.db"
    shutil.copy2(db_path, backup_path)
    return backup_path


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_user(conn: sqlite3.Connection, username: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT id, username, chat_id, xp, level, gold FROM users WHERE username = ?",
        (username,),
    ).fetchone()


def normalized(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def merge_rows_by_key(
    conn: sqlite3.Connection,
    table: str,
    key_column: str,
    source_user_id: int,
    target_user_id: int,
) -> None:
    target_keys = {
        normalized(row[key_column])
        for row in conn.execute(
            f"SELECT {key_column} FROM {table} WHERE user_id = ?",
            (target_user_id,),
        )
    }
    for row in conn.execute(
        f"SELECT id, {key_column} FROM {table} WHERE user_id = ?",
        (source_user_id,),
    ).fetchall():
        if normalized(row[key_column]) in target_keys:
            conn.execute(f"DELETE FROM {table} WHERE id = ?", (row["id"],))
        else:
            conn.execute(
                f"UPDATE {table} SET user_id = ? WHERE id = ?",
                (target_user_id, row["id"]),
            )
            target_keys.add(normalized(row[key_column]))


def merge_habits(conn: sqlite3.Connection, source_user_id: int, target_user_id: int) -> None:
    target_habits = {
        normalized(row["name"]): row["id"]
        for row in conn.execute(
            "SELECT id, name FROM habits WHERE user_id = ?",
            (target_user_id,),
        )
    }
    source_habits = conn.execute(
        "SELECT id, name FROM habits WHERE user_id = ?",
        (source_user_id,),
    ).fetchall()

    for habit in source_habits:
        source_habit_id = habit["id"]
        target_habit_id = target_habits.get(normalized(habit["name"]))
        if target_habit_id:
            conn.execute(
                "UPDATE habit_logs SET user_id = ?, habit_id = ? WHERE user_id = ? AND habit_id = ?",
                (target_user_id, target_habit_id, source_user_id, source_habit_id),
            )
            merge_habit_streak(conn, source_user_id, target_user_id, source_habit_id, target_habit_id)
            conn.execute("DELETE FROM habits WHERE id = ?", (source_habit_id,))
        else:
            conn.execute(
                "UPDATE habits SET user_id = ? WHERE id = ?",
                (target_user_id, source_habit_id),
            )
            conn.execute(
                "UPDATE habit_logs SET user_id = ? WHERE user_id = ? AND habit_id = ?",
                (target_user_id, source_user_id, source_habit_id),
            )
            conn.execute(
                "UPDATE streaks SET user_id = ? WHERE user_id = ? AND streak_type = ?",
                (target_user_id, source_user_id, f"habit:{source_habit_id}"),
            )
            target_habits[normalized(habit["name"])] = source_habit_id


def merge_habit_streak(
    conn: sqlite3.Connection,
    source_user_id: int,
    target_user_id: int,
    source_habit_id: int,
    target_habit_id: int,
) -> None:
    source_type = f"habit:{source_habit_id}"
    target_type = f"habit:{target_habit_id}"
    source = conn.execute(
        "SELECT * FROM streaks WHERE user_id = ? AND streak_type = ?",
        (source_user_id, source_type),
    ).fetchone()
    if not source:
        return
    target = conn.execute(
        "SELECT * FROM streaks WHERE user_id = ? AND streak_type = ?",
        (target_user_id, target_type),
    ).fetchone()
    if target:
        conn.execute("DELETE FROM streaks WHERE id = ?", (source["id"],))
    else:
        conn.execute(
            "UPDATE streaks SET user_id = ?, streak_type = ? WHERE id = ?",
            (target_user_id, target_type, source["id"]),
        )


def merge_daily_scores(conn: sqlite3.Connection, source_user_id: int, target_user_id: int) -> None:
    target_dates = {
        row["date"]
        for row in conn.execute(
            "SELECT date FROM daily_scores WHERE user_id = ?",
            (target_user_id,),
        )
    }
    for row in conn.execute(
        "SELECT id, date FROM daily_scores WHERE user_id = ?",
        (source_user_id,),
    ).fetchall():
        if row["date"] in target_dates:
            conn.execute("DELETE FROM daily_scores WHERE id = ?", (row["id"],))
        else:
            conn.execute(
                "UPDATE daily_scores SET user_id = ? WHERE id = ?",
                (target_user_id, row["id"]),
            )
            target_dates.add(row["date"])


def merge_streaks(conn: sqlite3.Connection, source_user_id: int, target_user_id: int) -> None:
    target_types = {
        row["streak_type"]
        for row in conn.execute(
            "SELECT streak_type FROM streaks WHERE user_id = ?",
            (target_user_id,),
        )
    }
    for row in conn.execute(
        "SELECT id, streak_type FROM streaks WHERE user_id = ?",
        (source_user_id,),
    ).fetchall():
        if row["streak_type"] in target_types:
            conn.execute("DELETE FROM streaks WHERE id = ?", (row["id"],))
        else:
            conn.execute(
                "UPDATE streaks SET user_id = ? WHERE id = ?",
                (target_user_id, row["id"]),
            )
            target_types.add(row["streak_type"])


def merge_gabriel_into_panda(
    db_path: Path,
    source_username: str = "Gabriel",
    target_username: str = "PandaCoffey",
    final_username: str = "Gabriel",
    delete_username: str = "Benji",
    no_backup: bool = False,
) -> None:
    if not no_backup:
        print(f"Backup created: {backup_db(db_path)}")

    with connect(db_path) as conn:
        conn.execute("BEGIN")
        source = get_user(conn, source_username)
        target = get_user(conn, target_username)
        if not source:
            raise RuntimeError(f"Source user not found: {source_username}")
        if not target:
            raise RuntimeError(f"Target user not found: {target_username}")

        source_id = source["id"]
        target_id = target["id"]

        conn.execute(
            "UPDATE users SET username = ? WHERE id = ?",
            (f"__merged_{source_username}_{timestamp()}__", source_id),
        )

        merge_habits(conn, source_id, target_id)
        merge_rows_by_key(conn, "perfect_day_templates", "template_name", source_id, target_id)
        merge_daily_scores(conn, source_id, target_id)
        merge_streaks(conn, source_id, target_id)
        merge_rows_by_key(conn, "todos", "title", source_id, target_id)
        merge_rows_by_key(conn, "notodos", "title", source_id, target_id)
        merge_rows_by_key(conn, "goals", "title", source_id, target_id)
        merge_rows_by_key(conn, "substeps", "title", source_id, target_id)

        conn.execute("DELETE FROM users WHERE id = ?", (source_id,))
        conn.execute("UPDATE users SET username = ? WHERE id = ?", (final_username, target_id))

        benji = get_user(conn, delete_username)
        if benji:
            conn.execute("DELETE FROM users WHERE id = ?", (benji["id"],))

        assert_no_orphans(conn)
        conn.commit()
        print(f"Merged {source_username} into {target_username}; canonical user is {final_username}.")
        if benji:
            print(f"Deleted exact user: {delete_username}.")


def assert_no_orphans(conn: sqlite3.Connection) -> None:
    checks = [
        ("habits", "user_id", "users", "id"),
        ("habit_logs", "user_id", "users", "id"),
        ("habit_logs", "habit_id", "habits", "id"),
        ("perfect_day_templates", "user_id", "users", "id"),
        ("daily_scores", "user_id", "users", "id"),
        ("streaks", "user_id", "users", "id"),
        ("todos", "user_id", "users", "id"),
        ("notodos", "user_id", "users", "id"),
        ("goals", "user_id", "users", "id"),
        ("substeps", "user_id", "users", "id"),
        ("goal_substep_links", "goal_id", "goals", "id"),
        ("goal_substep_links", "substep_id", "substeps", "id"),
    ]
    for child, child_col, parent, parent_col in checks:
        count = conn.execute(
            f"""
            SELECT COUNT(*) AS count
            FROM {child} c
            LEFT JOIN {parent} p ON p.{parent_col} = c.{child_col}
            WHERE p.{parent_col} IS NULL
            """
        ).fetchone()["count"]
        if count:
            raise RuntimeError(f"Found {count} orphan rows in {child}.{child_col}")


def export_snapshot(db_path: Path, snapshot_path: Path) -> None:
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as conn, snapshot_path.open("w", encoding="utf-8") as fh:
        fh.write("-- Habit Tracker SQLite snapshot\n")
        fh.write(f"-- Generated at {dt.datetime.now().isoformat(timespec='seconds')}\n")
        fh.write("PRAGMA foreign_keys=OFF;\nBEGIN TRANSACTION;\n")
        for line in conn.iterdump():
            if line in {"BEGIN TRANSACTION;", "COMMIT;"}:
                continue
            fh.write(f"{line}\n")
        fh.write("COMMIT;\nPRAGMA foreign_keys=ON;\n")
    print(f"Snapshot exported: {snapshot_path}")


def restore_snapshot(db_path: Path, snapshot_path: Path, no_backup: bool = False) -> None:
    if not snapshot_path.exists():
        raise FileNotFoundError(f"Snapshot not found: {snapshot_path}")
    if db_path.exists() and not no_backup:
        print(f"Backup created: {backup_db(db_path)}")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    with sqlite3.connect(db_path) as conn, snapshot_path.open("r", encoding="utf-8") as fh:
        conn.row_factory = sqlite3.Row
        conn.executescript(fh.read())
        conn.execute("PRAGMA foreign_keys = ON")
        assert_no_orphans(conn)
    print(f"Snapshot restored into: {db_path}")


def inspect_db(db_path: Path) -> None:
    with connect(db_path) as conn:
        print("USERS")
        for row in conn.execute(
            "SELECT id, username, chat_id, xp, level, gold, created_at FROM users ORDER BY id"
        ):
            print(dict(row))
        print("\nCOUNTS_BY_USER")
        for user in conn.execute("SELECT id, username FROM users ORDER BY id"):
            counts = []
            for table in ["habits", "habit_logs", *USER_TABLES]:
                counts.append(
                    f"{table}="
                    f"{conn.execute(f'SELECT COUNT(*) AS c FROM {table} WHERE user_id = ?', (user['id'],)).fetchone()['c']}"
                )
            print(f"{user['id']} {user['username']}: " + ", ".join(counts))
        assert_no_orphans(conn)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Habit Tracker DB maintenance")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--no-backup", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("inspect")
    sub.add_parser("merge-users")
    sub.add_parser("export-snapshot")
    sub.add_parser("restore-snapshot")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "inspect":
        inspect_db(args.db)
    elif args.command == "merge-users":
        merge_gabriel_into_panda(args.db, no_backup=args.no_backup)
    elif args.command == "export-snapshot":
        export_snapshot(args.db, args.snapshot)
    elif args.command == "restore-snapshot":
        restore_snapshot(args.db, args.snapshot, no_backup=args.no_backup)


if __name__ == "__main__":
    main()
