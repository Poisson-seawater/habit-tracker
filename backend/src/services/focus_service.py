"""Daily quest roles and links to the Recap's objectives and skills."""

import datetime

from sqlalchemy.orm import Session

from src.database.models import (
    Goal,
    GoalSubStepLink,
    Habit,
    JarWeek,
    Streak,
    SubStep,
    Todo,
    User,
    UserSoftskillProgress,
)
from src.services import quest_tag_service, softskill_service

FOCUS_ROLES = {"must", "goal", "skill"}


def state_on_date(habit: Habit, day: datetime.date) -> dict:
    history = habit.focus_history
    if not history:
        return {"role": habit.focus_role or "must", "enabled": True}
    entries = [
        entry for entry in history if str(entry.get("date", "")) <= day.isoformat()
    ]
    if not entries:
        first = min(history, key=lambda value: str(value["date"]))
        return {"role": "must", "enabled": first["role"] == "must"}
    entry = max(entries, key=lambda value: str(value["date"]))
    return {"role": entry["role"], "enabled": bool(entry.get("enabled", True))}


def set_state(
    habit: Habit,
    *,
    role: str | None = None,
    enabled: bool | None = None,
    day: datetime.date | None = None,
) -> None:
    day = day or datetime.date.today()
    current = state_on_date(habit, day)
    next_role = role or current["role"]
    if next_role not in FOCUS_ROLES:
        raise ValueError("Rôle de quête invalide.")
    next_enabled = current["enabled"] if enabled is None else enabled
    history = list(habit.focus_history or [])
    if not history and habit.created_at and habit.created_at.date() < day:
        history.append(
            {
                "date": habit.created_at.date().isoformat(),
                "role": habit.focus_role or "must",
                "enabled": True,
            }
        )
    history = [entry for entry in history if entry.get("date") != day.isoformat()]
    history.append(
        {"date": day.isoformat(), "role": next_role, "enabled": next_enabled}
    )
    habit.focus_history = sorted(history, key=lambda entry: entry["date"])
    habit.focus_role = next_role


def validate_link(
    db: Session,
    user_id: int,
    role: str,
    goal_id: int | None,
    softskill_id: str | None,
    *,
    excluding_id: int | None = None,
) -> None:
    if role not in FOCUS_ROLES:
        raise ValueError("Rôle de quête invalide.")
    if role == "must":
        if goal_id is not None or softskill_id is not None:
            raise ValueError("Une quête Must ne peut pas avoir de lien de focus.")
        return
    if role == "goal":
        if goal_id is None or softskill_id is not None:
            raise ValueError("Choisissez un seul objectif pour cette quête.")
        goal = db.query(Goal).filter_by(id=goal_id, user_id=user_id).first()
        if not goal or goal.completed:
            raise ValueError("Objectif introuvable ou terminé.")
        existing = db.query(Habit).filter_by(
            user_id=user_id,
            focus_role="goal",
            focus_goal_id=goal_id,
            is_active=True,
            archived_at=None,
        )
    else:
        if not softskill_id or goal_id is not None:
            raise ValueError("Choisissez une seule compétence pour cette quête.")
        skills = softskill_service.load_tree_config().get("skills", [])
        if not any(skill.get("id") == softskill_id for skill in skills):
            raise ValueError("Compétence introuvable.")
        existing = db.query(Habit).filter_by(
            user_id=user_id,
            focus_role="skill",
            focus_softskill_id=softskill_id,
            is_active=True,
            archived_at=None,
        )
    if excluding_id is not None:
        existing = existing.filter(Habit.id != excluding_id)
    if existing.first():
        raise ValueError("Cet item possède déjà une quête active.")


def enabled_for_pins(db: Session, user: User, role: str, goal_id, skill_id) -> bool:
    if role == "must":
        return True
    if role == "goal":
        goal = db.query(Goal).filter_by(id=goal_id, user_id=user.id).first()
        return bool(
            goal and not goal.completed and goal_id in (user.pinned_goals or [])
        )
    progress = (
        db.query(UserSoftskillProgress)
        .filter_by(user_id=user.id, softskill_id=skill_id)
        .first()
    )
    return bool(
        skill_id in (user.pinned_softskills or [])
        and not (progress and progress.completed)
    )


def sync_pin_states(db: Session, user: User) -> None:
    ensure_pinned_quests(db, user)
    habits = db.query(Habit).filter_by(user_id=user.id, is_active=True).all()
    for habit in habits:
        role = habit.focus_role or "must"
        if role == "must":
            continue
        enabled = enabled_for_pins(
            db, user, role, habit.focus_goal_id, habit.focus_softskill_id
        )
        if state_on_date(habit, datetime.date.today())["enabled"] != enabled:
            set_state(habit, enabled=enabled)


def unique_quest_name(db: Session, user_id: int, base: str) -> str:
    name = base.strip()
    candidate = name
    suffix = 2
    while db.query(Habit.id).filter_by(user_id=user_id, name=candidate).first():
        candidate = f"{name} ({suffix})"
        suffix += 1
    return candidate


def create_goal_quest(db: Session, user_id: int, goal: Goal) -> Habit:
    quest = Habit(
        user_id=user_id,
        name=unique_quest_name(db, user_id, f"Travailler sur : {goal.title}"),
        type="binary",
        frequency="daily",
        scheduled_days="0,1,2,3,4,5,6",
        day_types=["rest", "regular", "hustle"],
        is_active=True,
        focus_role="goal",
        focus_goal_id=goal.id,
        focus_history=[
            {"date": datetime.date.today().isoformat(), "role": "goal", "enabled": True}
        ],
    )
    db.add(quest)
    db.flush()
    quest.relationship_root_id = quest.id
    return quest


def create_skill_quest(db: Session, user_id: int, skill: dict) -> Habit:
    quest = Habit(
        user_id=user_id,
        name=unique_quest_name(db, user_id, f"Pratiquer : {skill['name']}"),
        type="binary",
        frequency="daily",
        scheduled_days="0,1,2,3,4,5,6",
        day_types=["rest", "regular", "hustle"],
        is_active=True,
        focus_role="skill",
        focus_softskill_id=skill["id"],
        focus_history=[
            {
                "date": datetime.date.today().isoformat(),
                "role": "skill",
                "enabled": True,
            }
        ],
    )
    db.add(quest)
    db.flush()
    quest.relationship_root_id = quest.id
    return quest


def ensure_pinned_quests(db: Session, user: User) -> None:
    """Give every active Recap goal and skill one scheduled quest."""
    goal_ids = set(user.pinned_goals or [])
    if goal_ids:
        goals = (
            db.query(Goal)
            .filter(
                Goal.user_id == user.id, Goal.id.in_(goal_ids), Goal.completed == False
            )
            .all()
        )
        existing_goals = {
            goal_id
            for (goal_id,) in db.query(Habit.focus_goal_id)
            .filter_by(
                user_id=user.id, focus_role="goal", is_active=True, archived_at=None
            )
            .all()
        }
        for goal in goals:
            if goal.id not in existing_goals:
                create_goal_quest(db, user.id, goal)

    skill_ids = set(user.pinned_softskills or [])
    if skill_ids:
        skills = {
            skill["id"]: skill
            for skill in softskill_service.load_tree_config().get("skills", [])
        }
        existing_skills = {
            skill_id
            for (skill_id,) in db.query(Habit.focus_softskill_id)
            .filter_by(
                user_id=user.id, focus_role="skill", is_active=True, archived_at=None
            )
            .all()
        }
        for skill_id in skill_ids - existing_skills:
            skill = skills.get(skill_id)
            if skill and enabled_for_pins(db, user, "skill", None, skill_id):
                create_skill_quest(db, user.id, skill)


def create_linked_goal(
    db: Session, user: User, todo: Todo, *, replace_goal_id: int | None = None
) -> Goal:
    if db.query(Goal.id).filter_by(source_todo_id=todo.id).first():
        raise ValueError("Ce to-do possède déjà un objectif lié.")
    if db.query(Goal.id).filter_by(user_id=user.id).count() >= 20:
        raise ValueError("Limite de 20 objectifs atteinte.")
    pins = list(user.pinned_goals or [])
    if len(pins) >= 3:
        if replace_goal_id not in pins:
            raise ValueError("Choisissez un objectif du Top 3 à remplacer.")
        pins.remove(replace_goal_id)
    goal = Goal(
        user_id=user.id,
        source_todo_id=todo.id,
        title=todo.title,
        do_date=todo.do_date,
        due_date=todo.due_date,
    )
    db.add(goal)
    db.flush()
    create_goal_quest(db, user.id, goal)
    user.pinned_goals = pins + [goal.id]
    sync_pin_states(db, user)
    return goal


def stop_goal_quests(db: Session, user: User, goal: Goal) -> None:
    for habit in (
        db.query(Habit).filter_by(user_id=user.id, focus_goal_id=goal.id).all()
    ):
        if habit.is_active:
            habit.is_active = False
            habit.deactivated_at = datetime.datetime.now()
            set_state(habit, enabled=False)
    user.pinned_goals = [gid for gid in (user.pinned_goals or []) if gid != goal.id]


def remove_linked_goal(db: Session, user: User, todo: Todo) -> None:
    from src.services import agenda_service

    goal = db.query(Goal).filter_by(user_id=user.id, source_todo_id=todo.id).first()
    if not goal:
        return
    user.pinned_goals = [gid for gid in (user.pinned_goals or []) if gid != goal.id]
    user.pinned_substeps = [
        sid
        for sid in (user.pinned_substeps or [])
        if not db.query(GoalSubStepLink.id)
        .filter_by(goal_id=goal.id, substep_id=sid)
        .first()
    ]
    quests = db.query(Habit).filter_by(user_id=user.id, focus_goal_id=goal.id).all()
    quest_ids = {quest.id for quest in quests}
    for quest in quests:
        agenda_service.remove_habit_agenda_references(db, user.id, quest.id)
        if quest.relationship_root_id == quest.id:
            quest_tag_service.replace_tags(db, user.id, quest, [])
        db.query(Streak).filter_by(
            user_id=user.id, streak_type=f"habit:{quest.id}"
        ).delete(synchronize_session=False)
        db.delete(quest)
    for week in db.query(JarWeek).filter_by(user_id=user.id).all():
        items = [
            item
            for item in (week.items or [])
            if not (
                item.get("source_type") == "habit"
                and item.get("source_id") in quest_ids
            )
        ]
        if len(items) != len(week.items or []):
            week.items = items
            week.placements = {
                key: value
                for key, value in (week.placements or {}).items()
                if key in {item["id"] for item in items}
            }
    links = list(goal.substep_links)
    for link in links:
        substep = link.substep
        if len(substep.goal_links) == 1:
            db.delete(substep)
    db.delete(goal)
