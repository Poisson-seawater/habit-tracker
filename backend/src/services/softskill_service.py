"""
Softskill Service — Business logic for the Softskill Progress Tree feature.

Handles:
- Loading and caching the static softskills_tree.json configuration.
- Validating that the configuration has no cyclic dependencies.
- Querying and updating user progress on softskills.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from src.database.models import UserSoftskillProgress

logger = logging.getLogger(__name__)

# ---- Configuration Loading & Validation ----

_tree_config: Optional[Dict[str, Any]] = None

LAYOUT_X_ORIGIN = 100
LAYOUT_Y_ORIGIN = 80
LAYOUT_X_STEP = 200
LAYOUT_Y_STEP = 140
LAYOUT_NODE_WIDTH = 100
LAYOUT_NODE_HEIGHT = 112
LAYOUT_HORIZONTAL_PADDING = 40
LAYOUT_VERTICAL_PADDING = 20


def _skill_order(skill: Dict[str, Any]) -> int:
    try:
        return max(1, int(skill.get("execution_order", 1)))
    except (TypeError, ValueError):
        return 1


def _skill_position(skill: Dict[str, Any]) -> Optional[Tuple[int, int]]:
    try:
        x = int(skill.get("x"))
        y = int(skill.get("y"))
    except (TypeError, ValueError):
        return None
    if x <= 0 or y <= 0:
        return None
    return x, y


def _positions_overlap(
    first: Tuple[int, int], second: Tuple[int, int]
) -> bool:
    return (
        abs(first[0] - second[0])
        < LAYOUT_NODE_WIDTH + LAYOUT_HORIZONTAL_PADDING
        and abs(first[1] - second[1])
        < LAYOUT_NODE_HEIGHT + LAYOUT_VERTICAL_PADDING
    )


def _position_is_free(
    position: Tuple[int, int],
    occupied_positions: List[Tuple[int, int]],
) -> bool:
    return all(
        not _positions_overlap(position, occupied)
        for occupied in occupied_positions
    )


def _occupied_positions(
    config: Dict[str, Any],
    exclude_skill_id: Optional[str] = None,
) -> List[Tuple[int, int]]:
    positions = []
    for skill in config.get("skills", []):
        if skill.get("id") == exclude_skill_id:
            continue
        position = _skill_position(skill)
        if position is not None:
            positions.append(position)
    return positions


def _median_x(positions: List[Tuple[int, int]]) -> int:
    values = sorted(position[0] for position in positions)
    return values[len(values) // 2]


def _new_branch_anchor_x(
    occupied_positions: List[Tuple[int, int]],
) -> int:
    if not occupied_positions:
        return LAYOUT_X_ORIGIN
    max_x = max(position[0] for position in occupied_positions)
    steps = ((max_x - LAYOUT_X_ORIGIN) // LAYOUT_X_STEP) + 1
    return LAYOUT_X_ORIGIN + max(1, steps) * LAYOUT_X_STEP


def _branch_anchor_x(
    config: Dict[str, Any],
    skill_data: Dict[str, Any],
    occupied_positions: List[Tuple[int, int]],
    exclude_skill_id: Optional[str] = None,
) -> int:
    branch = skill_data.get("branch")
    prerequisites = set(skill_data.get("prerequisites", []))
    same_branch_prerequisites = []
    branch_positions = []

    for skill in config.get("skills", []):
        if skill.get("id") == exclude_skill_id:
            continue
        position = _skill_position(skill)
        if position is None or position not in occupied_positions:
            continue
        if skill.get("branch") != branch:
            continue
        branch_positions.append(position)
        if skill.get("id") in prerequisites:
            same_branch_prerequisites.append(position)

    if same_branch_prerequisites:
        return _median_x(same_branch_prerequisites)
    if branch_positions:
        return _median_x(branch_positions)
    return _new_branch_anchor_x(occupied_positions)


def allocate_skill_position(
    config: Dict[str, Any],
    skill_data: Dict[str, Any],
    *,
    occupied_positions: Optional[List[Tuple[int, int]]] = None,
    exclude_skill_id: Optional[str] = None,
) -> Tuple[int, int]:
    """Return the nearest free layout slot for a softskill."""
    occupied = (
        list(occupied_positions)
        if occupied_positions is not None
        else _occupied_positions(config, exclude_skill_id)
    )
    base_x = _branch_anchor_x(
        config,
        skill_data,
        occupied,
        exclude_skill_id,
    )
    y = LAYOUT_Y_ORIGIN + (_skill_order(skill_data) - 1) * LAYOUT_Y_STEP

    radius = 0
    while True:
        offsets = [0] if radius == 0 else [radius, -radius]
        for offset in offsets:
            x = base_x + offset * LAYOUT_X_STEP
            if x < LAYOUT_X_ORIGIN:
                continue
            candidate = (x, y)
            if _position_is_free(candidate, occupied):
                return candidate
        radius += 1


def repair_skill_positions(config: Dict[str, Any]) -> bool:
    """Repair missing, zero, or overlapping positions without moving valid nodes."""
    occupied = []
    pending = []
    changed = False

    for skill in config.get("skills", []):
        position = _skill_position(skill)
        if position is not None and _position_is_free(position, occupied):
            occupied.append(position)
        else:
            pending.append(skill)

    for skill in pending:
        x, y = allocate_skill_position(
            config,
            skill,
            occupied_positions=occupied,
            exclude_skill_id=skill.get("id"),
        )
        if skill.get("x") != x or skill.get("y") != y:
            skill["x"] = x
            skill["y"] = y
            changed = True
        occupied.append((x, y))

    return changed


def _get_config_path() -> str:
    """Resolve the path to softskills_tree.json relative to this module."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "data", "softskills_tree.json")


def load_tree_config(force_reload: bool = False) -> Dict[str, Any]:
    """
    Load the softskills tree configuration from the static JSON file.
    Caches in memory after first load. Use force_reload=True to re-read.
    """
    global _tree_config
    if _tree_config is not None and not force_reload:
        return _tree_config

    config_path = _get_config_path()
    if not os.path.exists(config_path):
        logger.error("Softskills tree config not found at %s", config_path)
        _tree_config = {"branches": {}, "skills": []}
        return _tree_config

    with open(config_path, "r", encoding="utf-8") as f:
        _tree_config = json.load(f)

    # Validate on load
    validate_no_cycles(_tree_config)
    if repair_skill_positions(_tree_config):
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(_tree_config, f, indent=2, ensure_ascii=False)
    return _tree_config


def validate_no_cycles(config: Dict[str, Any]) -> None:
    """
    Validate that there are no cyclic dependencies in the prerequisite graph.
    Uses DFS cycle detection.
    """
    skills = config.get("skills", [])
    skill_ids = {s["id"] for s in skills}
    adj: Dict[str, List[str]] = {s["id"]: s.get("prerequisites", []) for s in skills}

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {sid: WHITE for sid in skill_ids}

    def dfs(node: str) -> bool:
        color[node] = GRAY
        for prereq in adj.get(node, []):
            if prereq not in color:
                logger.warning(
                    "Softskill '%s' has unknown prerequisite '%s'", node, prereq
                )
                continue
            if color[prereq] == GRAY:
                logger.critical(
                    "CYCLIC DEPENDENCY detected in softskills: %s <-> %s",
                    node,
                    prereq,
                )
                return True
            if color[prereq] == WHITE and dfs(prereq):
                return True
        color[node] = BLACK
        return False

    for sid in skill_ids:
        if color[sid] == WHITE:
            if dfs(sid):
                raise ValueError(
                    f"Cyclic dependency detected in softskills_tree.json involving '{sid}'"
                )

    logger.info("Softskills tree config validated: no cycles found (%d skills)", len(skills))


def save_tree_config(config: Dict[str, Any]) -> None:
    """
    Validate and save the configuration back to softskills_tree.json.
    Updates the cached config.
    """
    global _tree_config
    repair_skill_positions(config)
    validate_no_cycles(config)
    config_path = _get_config_path()
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    _tree_config = config


def create_branch(key: str, color: str, pale_color: str) -> Dict[str, Any]:
    """Create a new branch key and its colors."""
    config = load_tree_config(force_reload=True)
    if "branches" not in config:
        config["branches"] = {}
    if key in config["branches"]:
        raise ValueError(f"Branch '{key}' already exists.")

    config["branches"][key] = {
        "color": color,
        "pale_color": pale_color
    }
    save_tree_config(config)
    return {"key": key, "color": color, "pale_color": pale_color}


def update_branch(old_key: str, new_key: str, color: str, pale_color: str) -> Dict[str, Any]:
    """Update a branch's color and optionally rename its key."""
    config = load_tree_config(force_reload=True)
    if "branches" not in config or old_key not in config["branches"]:
        raise ValueError(f"Branch '{old_key}' does not exist.")

    if old_key != new_key and new_key in config["branches"]:
        raise ValueError(f"Branch '{new_key}' already exists.")

    branch_data = {
        "color": color,
        "pale_color": pale_color
    }

    if old_key != new_key:
        del config["branches"][old_key]
        config["branches"][new_key] = branch_data
        for skill in config.get("skills", []):
            if skill.get("branch") == old_key:
                skill["branch"] = new_key
    else:
        config["branches"][old_key] = branch_data

    save_tree_config(config)
    return {"key": new_key, "color": color, "pale_color": pale_color}


def delete_branch(db: Session, key: str) -> Dict[str, Any]:
    """Delete a branch and all its associated skills and progress."""
    config = load_tree_config(force_reload=True)
    if "branches" not in config or key not in config["branches"]:
        raise ValueError(f"Branch '{key}' does not exist.")

    del config["branches"][key]

    skills_to_delete = [s["id"] for s in config.get("skills", []) if s.get("branch") == key]
    for skill_id in skills_to_delete:
        db.query(UserSoftskillProgress).filter_by(softskill_id=skill_id).delete()
        for s in config.get("skills", []):
            if "prerequisites" in s and skill_id in s["prerequisites"]:
                s["prerequisites"].remove(skill_id)
            if "related" in s and skill_id in s["related"]:
                s["related"].remove(skill_id)

    config["skills"] = [s for s in config.get("skills", []) if s.get("branch") != key]

    db.commit()
    save_tree_config(config)
    return {"deleted_branch": key, "deleted_skills": skills_to_delete}


def create_skill(skill_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new skill node."""
    config = load_tree_config(force_reload=True)
    skills = config.get("skills", [])

    skill_id = skill_data.get("id")
    if not skill_id:
        raise ValueError("Skill ID is required.")

    if any(s["id"] == skill_id for s in skills):
        raise ValueError(f"Skill with ID '{skill_id}' already exists.")

    branch = skill_data.get("branch")
    if branch not in config.get("branches", {}):
        raise ValueError(f"Branch '{branch}' does not exist.")

    new_skill = {
        "id": skill_id,
        "name": skill_data.get("name", ""),
        "description": skill_data.get("description", ""),
        "branch": branch,
        "prerequisites": skill_data.get("prerequisites", []),
        "related": skill_data.get("related", []),
        "execution_order": _skill_order(skill_data),
    }
    requested_position = _skill_position(skill_data)
    occupied = _occupied_positions(config)
    if (
        requested_position is not None
        and _position_is_free(requested_position, occupied)
    ):
        x, y = requested_position
    else:
        x, y = allocate_skill_position(
            config,
            new_skill,
            occupied_positions=occupied,
        )
    new_skill["x"] = x
    new_skill["y"] = y

    skills.append(new_skill)
    config["skills"] = skills

    save_tree_config(config)
    return new_skill


def update_skill(skill_id: str, skill_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update a skill node's details."""
    config = load_tree_config(force_reload=True)
    skills = config.get("skills", [])

    skill_idx = None
    for idx, s in enumerate(skills):
        if s["id"] == skill_id:
            skill_idx = idx
            break

    if skill_idx is None:
        raise ValueError(f"Skill with ID '{skill_id}' does not exist.")

    branch = skill_data.get("branch")
    if branch not in config.get("branches", {}):
        raise ValueError(f"Branch '{branch}' does not exist.")

    current_skill = skills[skill_idx]
    old_branch = current_skill.get("branch")
    old_order = _skill_order(current_skill)
    updated_skill = {
        **current_skill,
        "name": skill_data.get("name", ""),
        "description": skill_data.get("description", ""),
        "branch": branch,
        "prerequisites": skill_data.get("prerequisites", []),
        "related": skill_data.get("related", []),
        "execution_order": _skill_order(skill_data),
    }

    occupied = _occupied_positions(config, exclude_skill_id=skill_id)
    requested_position = _skill_position(skill_data)
    current_position = _skill_position(current_skill)
    structure_changed = (
        branch != old_branch
        or updated_skill["execution_order"] != old_order
    )

    if requested_position is not None:
        if _position_is_free(requested_position, occupied):
            x, y = requested_position
        else:
            x, y = allocate_skill_position(
                config,
                updated_skill,
                occupied_positions=occupied,
                exclude_skill_id=skill_id,
            )
    elif (
        structure_changed
        or current_position is None
        or not _position_is_free(current_position, occupied)
    ):
        x, y = allocate_skill_position(
            config,
            updated_skill,
            occupied_positions=occupied,
            exclude_skill_id=skill_id,
        )
    else:
        x, y = current_position

    updated_skill["x"] = x
    updated_skill["y"] = y
    skills[skill_idx] = updated_skill

    config["skills"] = skills
    save_tree_config(config)
    return skills[skill_idx]


def delete_skill(db: Session, skill_id: str) -> Dict[str, Any]:
    """Delete a skill node and its user progress."""
    config = load_tree_config(force_reload=True)
    skills = config.get("skills", [])

    skill_idx = None
    for idx, s in enumerate(skills):
        if s["id"] == skill_id:
            skill_idx = idx
            break

    if skill_idx is None:
        raise ValueError(f"Skill with ID '{skill_id}' does not exist.")

    db.query(UserSoftskillProgress).filter_by(softskill_id=skill_id).delete()
    db.commit()

    for s in skills:
        if "prerequisites" in s and skill_id in s["prerequisites"]:
            s["prerequisites"].remove(skill_id)
        if "related" in s and skill_id in s["related"]:
            s["related"].remove(skill_id)

    del skills[skill_idx]
    config["skills"] = skills

    save_tree_config(config)
    return {"deleted_skill": skill_id}


# ---- User Progress Queries ----


def get_user_progress(db: Session, user_id: int) -> Dict[str, Dict[str, Any]]:
    """
    Return a dict mapping softskill_id -> progress info for the given user.
    """
    rows = (
        db.query(UserSoftskillProgress)
        .filter(UserSoftskillProgress.user_id == user_id)
        .all()
    )
    result: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        result[row.softskill_id] = {
            "success_criteria_test": row.success_criteria_test,
            "current_level": row.current_level,
            "completed": row.completed,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
    return result


def get_tree_with_progress(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Combine the static tree config with user-specific progress data.
    Returns the full payload for the GET /softskills endpoint.
    """
    config = load_tree_config()
    progress = get_user_progress(db, user_id)

    skills_out = []
    for skill in config.get("skills", []):
        skill_progress = progress.get(skill["id"], {
            "success_criteria_test": None,
            "current_level": 0,
            "completed": False,
            "updated_at": None,
        })
        skills_out.append({**skill, "progress": skill_progress})

    return {
        "branches": config.get("branches", {}),
        "skills": skills_out,
    }


def update_success_test(
    db: Session, user_id: int, softskill_id: str, test_text: str
) -> Dict[str, Any]:
    """
    Create or update the user's custom success criteria test for a softskill.
    """
    row = (
        db.query(UserSoftskillProgress)
        .filter_by(user_id=user_id, softskill_id=softskill_id)
        .first()
    )
    if not row:
        row = UserSoftskillProgress(
            user_id=user_id,
            softskill_id=softskill_id,
            success_criteria_test=test_text,
        )
        db.add(row)
    else:
        row.success_criteria_test = test_text

    db.commit()
    db.refresh(row)
    return {
        "softskill_id": softskill_id,
        "success_criteria_test": row.success_criteria_test,
    }


def toggle_completion(
    db: Session, user_id: int, softskill_id: str, completed: bool
) -> Dict[str, Any]:
    """
    Mark a softskill as completed (or uncompleted).
    Validates that all prerequisites are completed before allowing completion.
    Returns error info if prerequisites are not met.
    """
    config = load_tree_config()
    skill_map = {s["id"]: s for s in config.get("skills", [])}

    skill = skill_map.get(softskill_id)
    if not skill:
        return {"error": f"Unknown softskill '{softskill_id}'."}

    # Check prerequisites if completing
    if completed:
        prereqs = skill.get("prerequisites", [])
        if prereqs:
            progress = get_user_progress(db, user_id)
            for prereq_id in prereqs:
                prereq_progress = progress.get(prereq_id, {})
                if not prereq_progress.get("completed", False):
                    prereq_name = skill_map.get(prereq_id, {}).get("name", prereq_id)
                    return {
                        "error": f"Cannot unlock '{skill['name']}': Prerequisite '{prereq_name}' is not completed."
                    }

    row = (
        db.query(UserSoftskillProgress)
        .filter_by(user_id=user_id, softskill_id=softskill_id)
        .first()
    )
    if not row:
        row = UserSoftskillProgress(
            user_id=user_id,
            softskill_id=softskill_id,
            completed=completed,
            current_level=100 if completed else 0,
        )
        db.add(row)
    else:
        row.completed = completed
        row.current_level = 100 if completed else row.current_level

    db.commit()
    db.refresh(row)
    return {
        "softskill_id": softskill_id,
        "completed": row.completed,
        "current_level": row.current_level,
    }
