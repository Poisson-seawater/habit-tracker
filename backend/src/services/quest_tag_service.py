"""Optional quest tags shared by every version of the same quest.

Tags organize quests but never participate in completion, validation, scoring,
XP, streaks, or daily checklist progress.
"""

from typing import Any, Iterable

from sqlalchemy import or_
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from src.database.models import Goal, Habit, QuestTag
from src.services import softskill_service


TAG_KINDS = {"goal", "softskill_branch", "softskill"}


class QuestTagError(ValueError):
    """Raised when a quest tag references an invalid catalog entry."""


def _dedupe(values: Iterable[Any]) -> list[Any]:
    return list(dict.fromkeys(values))


def _softskill_branches() -> dict[str, dict]:
    config = softskill_service.load_tree_config()
    return {
        str(key): dict(value or {}) for key, value in config.get("branches", {}).items()
    }


def _goal_map(db: Session, user_id: int, goal_ids: set[int]) -> dict[int, Goal]:
    if not goal_ids:
        return {}
    return {
        goal.id: goal
        for goal in db.query(Goal)
        .filter(Goal.user_id == user_id, Goal.id.in_(goal_ids))
        .all()
    }


def normalize_tags(db: Session, user_id: int, payload: Any) -> list[tuple[str, str]]:
    """Validate and canonicalize one complete tag replacement."""
    normalized = []
    goal_ids = set()
    for raw_tag in payload or []:
        if hasattr(raw_tag, "model_dump"):
            raw_tag = raw_tag.model_dump()
        kind = str(raw_tag.get("kind") or "").strip()
        ref = str(raw_tag.get("ref") or "").strip()
        if kind not in TAG_KINDS:
            raise QuestTagError(f"Unknown quest tag kind '{kind}'.")
        if not ref:
            raise QuestTagError("Quest tag references cannot be empty.")
        if kind == "goal":
            try:
                goal_id = int(ref)
            except ValueError as exc:
                raise QuestTagError(f"Invalid goal tag reference '{ref}'.") from exc
            if goal_id <= 0:
                raise QuestTagError(f"Invalid goal tag reference '{ref}'.")
            ref = str(goal_id)
            goal_ids.add(goal_id)
        normalized.append((kind, ref))

    found_goals = _goal_map(db, user_id, goal_ids)
    missing_goal_ids = sorted(goal_ids - set(found_goals))
    if missing_goal_ids:
        raise QuestTagError(
            f"Unknown goal IDs for this user: {', '.join(map(str, missing_goal_ids))}."
        )

    branch_refs = {ref for kind, ref in normalized if kind == "softskill_branch"}
    if branch_refs:
        branches = _softskill_branches()
        missing_branches = sorted(branch_refs - set(branches))
        if missing_branches:
            raise QuestTagError(
                f"Unknown softskill branches: {', '.join(missing_branches)}."
            )

    skill_refs = {ref for kind, ref in normalized if kind == "softskill"}
    if skill_refs:
        skills = {
            skill["id"]
            for skill in softskill_service.load_tree_config().get("skills", [])
        }
        missing_skills = sorted(skill_refs - skills)
        if missing_skills:
            raise QuestTagError(f"Unknown softskills: {', '.join(missing_skills)}.")

    return _dedupe(normalized)


def ensure_relationship_root(db: Session, habit: Habit) -> int:
    if habit.id is None:
        db.flush()
    if habit.relationship_root_id is None:
        habit.relationship_root_id = habit.id
        db.flush()
    return int(habit.relationship_root_id)


def required_tags_for_roots(
    db: Session, user_id: int, root_ids: set[int]
) -> dict[int, set[tuple[str, str]]]:
    """Derive locks from valid focus links across the entire version group."""
    required = {root_id: set() for root_id in root_ids}
    if not root_ids:
        return required
    links = (
        db.query(Habit)
        .filter(
            Habit.user_id == user_id,
            Habit.focus_role.in_(("goal", "skill")),
            or_(Habit.relationship_root_id.in_(root_ids), Habit.id.in_(root_ids)),
        )
        .all()
    )
    goals = _goal_map(db, user_id, {h.focus_goal_id for h in links if h.focus_goal_id})
    skills = (
        {s["id"] for s in softskill_service.load_tree_config().get("skills", [])}
        if any(h.focus_role == "skill" for h in links)
        else set()
    )
    for habit in links:
        root_id = int(habit.relationship_root_id or habit.id)
        if root_id not in required:
            continue
        if habit.focus_role == "goal" and habit.focus_goal_id in goals:
            required[root_id].add(("goal", str(habit.focus_goal_id)))
        elif habit.focus_role == "skill" and habit.focus_softskill_id in skills:
            required[root_id].add(("softskill", habit.focus_softskill_id))
    return required


def ensure_required_tags(db: Session, user_id: int, habit: Habit) -> None:
    root_id = ensure_relationship_root(db, habit)
    db.flush()
    _insert_required_tags(db, required_tags_for_roots(db, user_id, {root_id}))


def _insert_required_tags(db: Session, required: dict) -> None:
    for root_id, tags in required.items():
        for kind, ref in sorted(tags):
            db.execute(
                insert(QuestTag)
                .values(relationship_root_id=root_id, kind=kind, ref=ref)
                .on_conflict_do_nothing(
                    index_elements=["relationship_root_id", "kind", "ref"]
                )
            )


def normalize_linked_quests(db: Session, user_id: int) -> None:
    """Repair legacy focus quests without replacing their manual tags or logs."""
    habits = (
        db.query(Habit)
        .filter(Habit.user_id == user_id, Habit.focus_role.in_(("goal", "skill")))
        .all()
    )
    root_ids = set()
    for habit in habits:
        root_ids.add(ensure_relationship_root(db, habit))
        if habit.day_types != ["rest", "regular", "hustle"]:
            habit.day_types = ["rest", "regular", "hustle"]
    db.flush()
    _insert_required_tags(db, required_tags_for_roots(db, user_id, root_ids))


def clear_tags(db: Session, root_id: int) -> None:
    """Lifecycle cleanup for a deleted quest; intentionally bypass focus locks."""
    db.query(QuestTag).filter_by(relationship_root_id=root_id).delete(
        synchronize_session=False
    )


def replace_tags(db: Session, user_id: int, habit: Habit, payload: Any) -> list:
    normalized = normalize_tags(db, user_id, payload)
    root_id = ensure_relationship_root(db, habit)
    db.flush()
    normalized = _dedupe(
        normalized + sorted(required_tags_for_roots(db, user_id, {root_id})[root_id])
    )
    clear_tags(db, root_id)
    for kind, ref in normalized:
        db.add(QuestTag(relationship_root_id=root_id, kind=kind, ref=ref))
    return normalized


def tags_for_habits(
    db: Session, user_id: int, habits: Iterable[Habit]
) -> dict[int, list[dict]]:
    """Resolve tags for many habits with bounded queries."""
    habits = list(habits)
    if not habits:
        return {}

    roots_by_habit_id = {
        habit.id: int(habit.relationship_root_id or habit.id) for habit in habits
    }
    root_ids = set(roots_by_habit_id.values())
    required = required_tags_for_roots(db, user_id, root_ids)
    rows = (
        db.query(QuestTag)
        .filter(QuestTag.relationship_root_id.in_(root_ids))
        .order_by(QuestTag.id)
        .all()
    )
    goal_ids = {
        int(row.ref) for row in rows if row.kind == "goal" and str(row.ref).isdigit()
    }
    goals = _goal_map(db, user_id, goal_ids)
    needs_branches = any(row.kind == "softskill_branch" for row in rows)
    branches = _softskill_branches() if needs_branches else {}
    skills = (
        {
            skill["id"]: skill
            for skill in softskill_service.load_tree_config().get("skills", [])
        }
        if any(row.kind == "softskill" for row in rows)
        else {}
    )
    tags_by_root: dict[int, list[dict]] = {root_id: [] for root_id in root_ids}

    for row in rows:
        if row.kind == "goal":
            goal = goals.get(int(row.ref)) if str(row.ref).isdigit() else None
            item = {
                "kind": row.kind,
                "ref": row.ref,
                "label": goal.title if goal else f"Objectif supprimé ({row.ref})",
            }
            if not goal:
                item["missing"] = True
        elif row.kind == "softskill":
            skill = skills.get(row.ref)
            # Removed skills must not leave an orphan badge on a historical quest.
            if not skill:
                continue
            item = {"kind": row.kind, "ref": row.ref, "label": skill["name"]}
        else:
            branch = branches.get(row.ref)
            item = {
                "kind": row.kind,
                "ref": row.ref,
                "label": row.ref.replace("_", " ").strip().title(),
            }
            if branch and branch.get("color"):
                item["color"] = branch["color"]
            if not branch:
                item["missing"] = True
        item["locked"] = (row.kind, row.ref) in required[row.relationship_root_id]
        tags_by_root[row.relationship_root_id].append(item)

    return {
        habit_id: [dict(item) for item in tags_by_root[root_id]]
        for habit_id, root_id in roots_by_habit_id.items()
    }


def remove_goal_tags(db: Session, goal_id: int) -> None:
    db.query(QuestTag).filter_by(kind="goal", ref=str(goal_id)).delete(
        synchronize_session=False
    )


def remove_skill_tags(db: Session, skill_ids: Iterable[str]) -> None:
    db.query(QuestTag).filter(
        QuestTag.kind == "softskill", QuestTag.ref.in_(list(skill_ids))
    ).delete(synchronize_session=False)


def rename_branch_tags(db: Session, old_key: str, new_key: str) -> None:
    if old_key == new_key:
        return
    rows = db.query(QuestTag).filter_by(kind="softskill_branch", ref=old_key).all()
    for row in rows:
        duplicate = (
            db.query(QuestTag)
            .filter_by(
                relationship_root_id=row.relationship_root_id,
                kind="softskill_branch",
                ref=new_key,
            )
            .first()
        )
        if duplicate:
            db.delete(row)
        else:
            row.ref = new_key


def remove_branch_tags(db: Session, branch_key: str) -> None:
    db.query(QuestTag).filter_by(kind="softskill_branch", ref=branch_key).delete(
        synchronize_session=False
    )
