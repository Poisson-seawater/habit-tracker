import datetime
import json
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.database.models import (
    DailyAgendaPlacement,
    DailyScore,
    Goal,
    GoalSubStepLink,
    Habit,
    HabitLog,
    PerfectDayTemplate,
    SubStep,
    User,
    Streak,
)
from src.services import softskill_service


EFFORT_TYPES = {
    "musculaire",
    "cerveau",
    "emotionnel_social",
    "creatif_divergent",
    "repos",
}

DAY_TYPES = ("rest", "regular", "hustle")
DAY_TYPE_ALIASES = {
    "normal": "regular",
    "regular": "regular",
    "semaine": "regular",
    "week": "regular",
    "weekend": "regular",
    "repos": "rest",
    "rest": "rest",
    "recovery": "rest",
    "recup": "rest",
    "hustle": "hustle",
    "rush": "hustle",
    "sick": "rest",
    "malade": "rest",
    "default": "regular",
}

EFFORT_CEILING_TYPES = {
    "musculaire",
    "cerveau",
    "emotionnel_social",
    "creatif_divergent",
}

AGENDA_BUFFER_MINUTES = 15

DAY_LABELS = {
    "0": "dimanche",
    "1": "lundi",
    "2": "mardi",
    "3": "mercredi",
    "4": "jeudi",
    "5": "vendredi",
    "6": "samedi",
}

DAY_TYPE_LABELS = {
    "rest": "repos",
    "regular": "regular",
    "hustle": "hustle",
}

DEFAULT_CEILINGS = {
    "rest": {
        "musculaire": 1.0,
        "cerveau": 1.0,
        "emotionnel_social": 1.0,
        "creatif_divergent": 1.0,
        "total": 4.0,
    },
    "regular": {
        "musculaire": 2.0,
        "cerveau": 2.0,
        "emotionnel_social": 2.0,
        "creatif_divergent": 2.0,
        "total": 8.0,
    },
    "hustle": {
        "musculaire": 4.0,
        "cerveau": 4.0,
        "emotionnel_social": 4.0,
        "creatif_divergent": 4.0,
        "total": 10.0,
    },
}

DEFAULT_FOCUS_HOURS = {"rest": 2.0, "regular": 6.0, "hustle": 9.0}
DEFAULT_REST_HOURS = {"rest": 10.0, "regular": 8.0, "hustle": 7.0}

SEGMENT_KIND_MAP = {
    "sleep": "sleep",
    "rest": "rest",
    "relax": "rest",
    "admin": "admin",
    "routine": "admin",
    "intense": "intense",
    "focus": "intense",
}


def day_index_for_date(date_value: datetime.date) -> int:
    """Return the project convention: 0=Sunday, 1=Monday, ..., 6=Saturday."""
    return (date_value.weekday() + 1) % 7


def normalize_day_type(value: Optional[str]) -> str:
    return DAY_TYPE_ALIASES.get(str(value or "regular").lower(), "regular")


def normalize_habit_day_types(value) -> list[str]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            value = [part.strip() for part in value.split(",")]
    if not isinstance(value, (list, tuple, set)):
        return list(DAY_TYPES)

    normalized = []
    for item in value:
        canonical = DAY_TYPE_ALIASES.get(str(item).strip().lower())
        if canonical in DAY_TYPES and canonical not in normalized:
            normalized.append(canonical)
    return normalized or list(DAY_TYPES)


def monthly_anchor_day(
    value: Optional[str], default_date: Optional[datetime.date] = None
) -> int:
    raw = str(value or "").split(",", 1)[0].strip()
    try:
        day = int(raw)
    except ValueError:
        fallback = default_date or datetime.date.today()
        day = fallback.day
    if day < 1:
        fallback = default_date or datetime.date.today()
        day = fallback.day
    return min(day, 30)


def is_monthly_due_on_date(anchor_day: int, date_value: datetime.date) -> bool:
    import calendar

    last_day = calendar.monthrange(date_value.year, date_value.month)[1]
    due_day = min(anchor_day, last_day)
    return date_value.day == due_day


def is_valid_time_string(value: str) -> bool:
    parts = (value or "").split(":")
    if len(parts) != 2:
        return False
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        return False
    return (
        len(parts[0]) == 2
        and len(parts[1]) == 2
        and 0 <= hour <= 23
        and 0 <= minute <= 59
    )


def time_to_minutes(value: str) -> int:
    if value == "24:00":
        return 1440
    if not is_valid_time_string(value):
        raise HTTPException(status_code=422, detail="Heure invalide; attendu HH:MM.")
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


def minutes_to_time(value: int) -> str:
    value = max(0, min(1440, value))
    if value == 1440:
        return "24:00"
    hour = value // 60
    minute = value % 60
    return f"{hour:02d}:{minute:02d}"


def _parse_agenda_json(raw_value) -> dict:
    if raw_value in (None, "", []):
        return {"schema_version": 2, "segments": [], "default_placements": []}
    if isinstance(raw_value, str):
        try:
            raw_value = json.loads(raw_value)
        except ValueError:
            return {"schema_version": 2, "segments": [], "default_placements": []}
    if isinstance(raw_value, dict):
        return {
            "schema_version": 2,
            "segments": list(raw_value.get("segments") or []),
            "default_placements": list(raw_value.get("default_placements") or []),
        }
    if isinstance(raw_value, list):
        segments = []
        for index, block in enumerate(raw_value):
            if not isinstance(block, dict):
                continue
            start = block.get("start")
            end = block.get("end")
            if not start or not end:
                continue
            category = block.get("kind") or block.get("category") or "admin"
            kind = SEGMENT_KIND_MAP.get(category, "admin")
            segments.append(
                {
                    "id": str(block.get("id") or f"segment-{index + 1}"),
                    "kind": kind,
                    "title": block.get("title") or kind.title(),
                    "start": start,
                    "end": end,
                }
            )
        return {"schema_version": 2, "segments": segments, "default_placements": []}
    return {"schema_version": 2, "segments": [], "default_placements": []}


def normalize_agenda_json(raw_value) -> dict:
    normalized = _parse_agenda_json(raw_value)
    segments = []
    for index, segment in enumerate(normalized.get("segments") or []):
        if not isinstance(segment, dict):
            continue
        start = segment.get("start")
        end = segment.get("end")
        if not start or not end:
            continue
        kind = SEGMENT_KIND_MAP.get(segment.get("kind"), "admin")
        segments.append(
            {
                "id": str(segment.get("id") or f"segment-{index + 1}"),
                "kind": kind,
                "title": segment.get("title") or kind.title(),
                "start": start,
                "end": end,
            }
        )

    placements = []
    for placement in normalized.get("default_placements") or []:
        if not isinstance(placement, dict):
            continue
        try:
            habit_id = int(placement.get("habit_id"))
            duration = int(placement.get("duration_minutes") or 0)
        except (TypeError, ValueError):
            continue
        start = placement.get("start") or placement.get("start_time")
        if (
            habit_id <= 0
            or duration <= 0
            or not start
            or not is_valid_time_string(start)
        ):
            continue
        placements.append(
            {
                "habit_id": habit_id,
                "start": start,
                "duration_minutes": duration,
            }
        )

    return {
        "schema_version": 2,
        "segments": sorted(segments, key=lambda item: time_to_minutes(item["start"])),
        "default_placements": sorted(
            placements, key=lambda item: time_to_minutes(item["start"])
        ),
    }


def remove_habit_agenda_references(db: Session, user_id: int, habit_id: int) -> bool:
    changed = False
    deleted_count = (
        db.query(DailyAgendaPlacement)
        .filter(
            DailyAgendaPlacement.user_id == user_id,
            DailyAgendaPlacement.habit_id == habit_id,
        )
        .delete(synchronize_session=False)
    )
    if deleted_count:
        changed = True

    templates = (
        db.query(PerfectDayTemplate)
        .filter(
            PerfectDayTemplate.user_id == user_id,
            PerfectDayTemplate.template_name.in_(DAY_TYPES),
        )
        .all()
    )
    for template in templates:
        agenda_json = normalize_agenda_json(template.agenda_json)
        default_placements = agenda_json.get("default_placements", [])
        kept_placements = [
            placement
            for placement in default_placements
            if int(placement.get("habit_id") or 0) != habit_id
        ]
        if len(kept_placements) == len(default_placements):
            continue
        template.agenda_json = {
            "schema_version": 2,
            "segments": agenda_json.get("segments", []),
            "default_placements": kept_placements,
        }
        changed = True
    return changed


def _softskill_names_by_id() -> dict:
    try:
        config = softskill_service.load_tree_config()
    except Exception:
        return {}
    return {
        str(skill.get("id")): skill.get("name") or str(skill.get("id"))
        for skill in config.get("skills", [])
        if skill.get("id")
    }


def _unique_habit_name(db: Session, user_id: int, base_name: str) -> str:
    existing_names = {
        row[0] for row in db.query(Habit.name).filter(Habit.user_id == user_id).all()
    }
    if base_name not in existing_names:
        return base_name
    suffix = 2
    while f"{base_name} ({suffix})" in existing_names:
        suffix += 1
    return f"{base_name} ({suffix})"


def _find_generated_habit(
    db: Session, user_id: int, source_type: str, source_ref: str
) -> Optional[Habit]:
    return (
        db.query(Habit)
        .filter(
            Habit.user_id == user_id,
            Habit.source_type == source_type,
            Habit.source_ref == source_ref,
        )
        .order_by(Habit.is_active.desc(), Habit.id.desc())
        .first()
    )


def sync_generated_focus_quests(db: Session, user: User) -> bool:
    changed = False
    pinned_substep_ids = [int(sid) for sid in (user.pinned_substeps or [])]
    pinned_substep_refs = {str(sid) for sid in pinned_substep_ids}

    # --- Substep quests: create / unarchive pinned, auto-archive unpinned ---
    if pinned_substep_ids:
        substeps = (
            db.query(SubStep)
            .filter(SubStep.user_id == user.id, SubStep.id.in_(pinned_substep_ids))
            .all()
        )
        for substep in substeps:
            source_ref = str(substep.id)
            existing = _find_generated_habit(db, user.id, "substep", source_ref)
            if existing:
                # Re-pinned: auto-unarchive if it was archived
                if existing.archived_at is not None:
                    existing.archived_at = None
                    if not existing.is_active:
                        existing.is_active = True
                    changed = True
                continue
            db.add(
                Habit(
                    user_id=user.id,
                    name=_unique_habit_name(db, user.id, f"Étape: {substep.title}"),
                    description=substep.description,
                    type="binary",
                    frequency="daily",
                    scheduled_days="0,1,2,3,4,5,6",
                    is_private=False,
                    is_reportable=True,
                    is_mandatory=False,
                    effort_type=substep.effort_type,
                    effort_duration=substep.effort_duration or 1.0,
                    source_type="substep",
                    source_ref=source_ref,
                    auto_managed=True,
                    agenda_duration_minutes=60,
                    is_active=True,
                )
            )
            changed = True

    # Auto-archive substep quests that are no longer pinned
    existing_substep_quests = (
        db.query(Habit)
        .filter(
            Habit.user_id == user.id,
            Habit.source_type == "substep",
            Habit.auto_managed == True,
            Habit.archived_at.is_(None),
        )
        .all()
    )
    now = datetime.datetime.now()
    for habit in existing_substep_quests:
        if str(habit.source_ref or "") not in pinned_substep_refs:
            habit.archived_at = now
            remove_habit_agenda_references(db, user.id, habit.id)
            changed = True

    # --- Softskill quests: create if missing (no auto-archive) ---
    softskill_names = _softskill_names_by_id()
    for skill_id in user.pinned_softskills or []:
        source_ref = str(skill_id)
        if _find_generated_habit(db, user.id, "softskill", source_ref):
            continue
        skill_name = softskill_names.get(source_ref, source_ref)
        db.add(
            Habit(
                user_id=user.id,
                name=_unique_habit_name(db, user.id, f"Competence: {skill_name}"),
                description=f"Quest generated from focused skill: {skill_name}",
                type="binary",
                frequency="daily",
                scheduled_days="0,1,2,3,4,5,6",
                is_private=False,
                is_reportable=True,
                is_mandatory=False,
                effort_type=None,
                effort_duration=1.0,
                source_type="softskill",
                source_ref=source_ref,
                auto_managed=True,
                agenda_duration_minutes=60,
                is_active=True,
            )
        )
        changed = True

    if changed:
        db.flush()
    return changed


def is_habit_eligible_on_date(
    habit: Habit,
    date_value: datetime.date,
    user: User,
    day_type: Optional[str] = None,
) -> bool:
    if not habit.is_active or habit.archived_at is not None:
        return False

    source_type = habit.source_type or "manual"
    # Legacy goal quests are no longer eligible (replaced by substep quests)
    if source_type == "goal":
        return False
    # Substep quests rely on archived_at managed by sync_generated_focus_quests
    if habit.auto_managed or source_type in {"substep", "softskill"}:
        source_ref = str(habit.source_ref or "")
        if source_type == "softskill" and source_ref not in {
            str(skill_id) for skill_id in (user.pinned_softskills or [])
        }:
            return False

    if normalize_day_type(day_type) not in normalize_habit_day_types(habit.day_types):
        return False

    frequency = habit.frequency or "daily"
    if frequency == "monthly":
        return is_monthly_due_on_date(
            monthly_anchor_day(
                habit.scheduled_days,
                habit.created_at.date() if habit.created_at else None,
            ),
            date_value,
        )
    if frequency not in {"daily", "custom", "specific_days"}:
        return False

    day_index = str(day_index_for_date(date_value))
    scheduled_days = {
        value.strip()
        for value in (habit.scheduled_days or "0,1,2,3,4,5,6").split(",")
        if value.strip()
    }
    return day_index in scheduled_days


def _habit_schedule_label(habit: Habit) -> str:
    frequency = habit.frequency or "daily"
    if frequency == "monthly":
        anchor = monthly_anchor_day(
            habit.scheduled_days,
            habit.created_at.date() if habit.created_at else None,
        )
        return f"mensuel le {anchor}"

    scheduled_days = [
        value.strip()
        for value in (habit.scheduled_days or "0,1,2,3,4,5,6").split(",")
        if value.strip()
    ]
    if set(scheduled_days) == set(DAY_LABELS):
        return "tous les jours"
    labels = [DAY_LABELS.get(value, value) for value in scheduled_days]
    return ", ".join(labels) if labels else "planning vide"


def _habit_bank_reasons(
    habit: Habit,
    date_value: datetime.date,
    user: User,
    day_type: str,
) -> list[dict]:
    reasons = []

    if not habit.is_active:
        reasons.append(
            {
                "code": "inactive",
                "label": "Inactive",
                "detail": "La quete est desactivee.",
            }
        )
    if habit.archived_at is not None:
        reasons.append(
            {
                "code": "archived",
                "label": "Archivee",
                "detail": "La quete est explicitement archivee.",
            }
        )
        return reasons

    source_type = habit.source_type or "manual"
    if source_type == "goal":
        reasons.append(
            {
                "code": "legacy_goal",
                "label": "Ancien objectif",
                "detail": "Les anciennes quetes d'objectif sont remplacees par les quetes de sous-etapes.",
            }
        )

    if habit.auto_managed or source_type in {"substep", "softskill"}:
        source_ref = str(habit.source_ref or "")
        if source_type == "softskill" and source_ref not in {
            str(skill_id) for skill_id in (user.pinned_softskills or [])
        }:
            reasons.append(
                {
                    "code": "source_not_pinned",
                    "label": "Skill non epinglee",
                    "detail": "Cette quete de skill reapparait quand la skill est epinglee au Recap.",
                }
            )

    normalized_day_type = normalize_day_type(day_type)
    allowed_day_types = normalize_habit_day_types(habit.day_types)
    if normalized_day_type not in allowed_day_types:
        allowed = ", ".join(
            DAY_TYPE_LABELS.get(value, value) for value in allowed_day_types
        )
        reasons.append(
            {
                "code": "day_type",
                "label": f"Jour {DAY_TYPE_LABELS.get(normalized_day_type, normalized_day_type)}",
                "detail": f"Compatible avec: {allowed}.",
            }
        )

    frequency = habit.frequency or "daily"
    if frequency == "monthly":
        anchor = monthly_anchor_day(
            habit.scheduled_days,
            habit.created_at.date() if habit.created_at else None,
        )
        if not is_monthly_due_on_date(anchor, date_value):
            last_day = calendar.monthrange(date_value.year, date_value.month)[1]
            due_day = min(anchor, last_day)
            reasons.append(
                {
                    "code": "monthly_not_due",
                    "label": f"Mensuel le {due_day}",
                    "detail": f"Cette quete mensuelle est due le {due_day} du mois affiche.",
                }
            )
    elif frequency in {"daily", "custom", "specific_days"}:
        day_index = str(day_index_for_date(date_value))
        scheduled_days = {
            value.strip()
            for value in (habit.scheduled_days or "0,1,2,3,4,5,6").split(",")
            if value.strip()
        }
        if day_index not in scheduled_days:
            reasons.append(
                {
                    "code": "not_scheduled",
                    "label": "Pas ce jour",
                    "detail": f"Planning: {_habit_schedule_label(habit)}.",
                }
            )
    else:
        reasons.append(
            {
                "code": "unsupported_frequency",
                "label": "Frequence ignoree",
                "detail": f"La frequence {frequency} n'est pas visible dans l'agenda.",
            }
        )

    if not reasons:
        reasons.append(
            {
                "code": "not_visible",
                "label": "Hors agenda",
                "detail": "Cette quete n'est pas eligible pour la date affichee.",
            }
        )
    return reasons


def _next_eligible_date(
    db: Session,
    user: User,
    habit: Habit,
    from_date: datetime.date,
    max_days: int = 370,
) -> Optional[datetime.date]:
    for offset in range(1, max_days + 1):
        candidate = from_date + datetime.timedelta(days=offset)
        day_type = resolve_day_type(db, user.id, candidate)
        if is_habit_eligible_on_date(habit, candidate, user, day_type):
            return candidate
    return None


def build_quest_bank_response(
    db: Session, user_id: int, date_value: datetime.date
) -> tuple[dict, bool]:
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    changed = sync_generated_focus_quests(db, user)
    day_type = resolve_day_type(db, user_id, date_value)
    habits = db.query(Habit).filter(Habit.user_id == user_id).order_by(Habit.name).all()
    completions, skipped_ids, failed_ids = _completed_and_skipped_habit_ids(
        db, user_id, date_value, habits
    )

    current_streak_by_habit_id = {}
    habit_ids = [habit.id for habit in habits]
    if habit_ids:
        streak_rows = (
            db.query(Streak)
            .filter(
                Streak.user_id == user_id,
                Streak.streak_type.in_([f"habit:{habit_id}" for habit_id in habit_ids]),
            )
            .all()
        )
        for streak in streak_rows:
            if not streak.streak_type.startswith("habit:"):
                continue
            try:
                habit_id = int(streak.streak_type.split(":", 1)[1])
            except ValueError:
                continue
            current_streak_by_habit_id[habit_id] = streak.current_streak or 0

    visible_quest_ids = []
    hidden_quests = []
    archived_quests = []

    for habit in habits:
        if not habit.is_active:
            continue

        item = habit_to_agenda_item(
            db,
            habit,
            date_value,
            completions,
            skipped_ids,
            failed_ids,
            current_streak_by_habit_id.get(habit.id, 0),
        )

        if habit.archived_at is not None:
            item.update(
                {
                    "visibility": "archived",
                    "bank_reasons": _habit_bank_reasons(
                        habit, date_value, user, day_type
                    ),
                    "next_visible_date": None,
                }
            )
            archived_quests.append(item)
            continue

        if is_habit_eligible_on_date(habit, date_value, user, day_type):
            visible_quest_ids.append(habit.id)
            continue

        next_date = _next_eligible_date(db, user, habit, date_value)
        item.update(
            {
                "visibility": "hidden",
                "bank_reasons": _habit_bank_reasons(habit, date_value, user, day_type),
                "next_visible_date": next_date.isoformat() if next_date else None,
            }
        )
        hidden_quests.append(item)

    hidden_quests.sort(
        key=lambda item: (
            item.get("next_visible_date") is None,
            item.get("next_visible_date") or "",
            item.get("name", "").lower(),
        )
    )
    archived_quests.sort(key=lambda item: item.get("archived_at") or "", reverse=True)

    return (
        {
            "date": date_value.isoformat(),
            "day_type": day_type,
            "visible_quest_ids": visible_quest_ids,
            "visible_count": len(visible_quest_ids),
            "hidden_quests": hidden_quests,
            "hidden_count": len(hidden_quests),
            "archived_quests": archived_quests,
            "archived_count": len(archived_quests),
        },
        changed,
    )


def _habit_duration_minutes(habit: Habit) -> int:
    if habit.agenda_duration_minutes and habit.agenda_duration_minutes > 0:
        return int(habit.agenda_duration_minutes)
    effort_duration = (
        habit.effort_duration if habit.effort_duration is not None else 1.0
    )
    return max(15, int(round(float(effort_duration) * 60)))


def _habit_agenda_placeable(habit: Habit) -> bool:
    return bool(habit.agenda_placeable) if habit.agenda_placeable is not None else True


def _source_label(db: Session, habit: Habit) -> Optional[str]:
    source_type = habit.source_type or "manual"
    if source_type == "substep" and habit.source_ref:
        substep = (
            db.query(SubStep)
            .filter(
                SubStep.user_id == habit.user_id,
                SubStep.id == int(habit.source_ref),
            )
            .first()
            if str(habit.source_ref).isdigit()
            else None
        )
        if substep:
            # Find the parent goal for richer context
            link = (
                db.query(GoalSubStepLink)
                .filter(GoalSubStepLink.substep_id == substep.id)
                .first()
            )
            if link and link.goal:
                return f"Étape: {substep.title} (Objectif: {link.goal.title})"
            return f"Étape: {substep.title}"
        return f"Étape: {habit.source_ref}"
    if source_type == "goal" and habit.source_ref:
        goal = (
            db.query(Goal)
            .filter(Goal.user_id == habit.user_id, Goal.id == int(habit.source_ref))
            .first()
            if str(habit.source_ref).isdigit()
            else None
        )
        return f"Objectif: {goal.title}" if goal else f"Objectif: {habit.source_ref}"
    if source_type == "softskill" and habit.source_ref:
        skill_name = _softskill_names_by_id().get(
            str(habit.source_ref), habit.source_ref
        )
        return f"Skill: {skill_name}"
    return None


def habit_to_agenda_item(
    db: Session,
    habit: Habit,
    date_value: datetime.date,
    completions: dict[int, int],
    skipped_habit_ids: set[int],
    failed_habit_ids: set[int],
    current_streak: int = 0,
) -> dict:
    duration_minutes = _habit_duration_minutes(habit)
    needs_configuration = bool(
        habit.auto_managed
        and (
            not habit.effort_type
            or habit.effort_type not in EFFORT_TYPES
            or duration_minutes <= 0
        )
    )
    source_type = habit.source_type or "manual"
    today_count = completions.get(habit.id, 0)
    target = (
        habit.daily_target if (habit.daily_target and habit.daily_target > 1) else 1
    )
    if habit.id in failed_habit_ids:
        status = "failed"
    elif habit.id in skipped_habit_ids:
        status = "skipped"
    elif today_count >= target:
        status = "done"
    else:
        status = "planned"
    return {
        "id": habit.id,
        "habit_id": habit.id,
        "name": habit.name,
        "description": habit.description or "",
        "type": habit.type,
        "frequency": habit.frequency or "daily",
        "scheduled_days": habit.scheduled_days or "0,1,2,3,4,5,6",
        "day_types": normalize_habit_day_types(habit.day_types),
        "effort_type": habit.effort_type,
        "effort_duration": habit.effort_duration,
        "agenda_duration_minutes": duration_minutes,
        "source_type": source_type,
        "source_ref": habit.source_ref,
        "source_label": _source_label(db, habit),
        "auto_managed": bool(habit.auto_managed),
        "archived_at": habit.archived_at.isoformat() if habit.archived_at else None,
        "needs_configuration": needs_configuration,
        "agenda_placeable": _habit_agenda_placeable(habit),
        "status": status,
        "current_streak": current_streak,
        "daily_target": habit.daily_target,
        "today_count": today_count,
        "unit": habit.unit,
    }


def _completed_and_skipped_habit_ids(
    db: Session, user_id: int, date_value: datetime.date, habits: list[Habit] = None
) -> tuple[dict[int, int], set[int], set[int]]:
    start_dt = datetime.datetime.combine(date_value, datetime.time.min)
    end_dt = datetime.datetime.combine(date_value, datetime.time.max)
    logs = (
        db.query(HabitLog)
        .filter(
            HabitLog.user_id == user_id,
            HabitLog.timestamp >= start_dt,
            HabitLog.timestamp <= end_dt,
        )
        .all()
    )
    from collections import Counter

    completions = Counter(
        log.habit_id
        for log in logs
        if log.log_type in {"done", "log"} and log.cancelled_at is None
    )
    skipped = {
        log.habit_id
        for log in logs
        if log.log_type == "skip" and log.cancelled_at is None
    }
    failed = {
        log.habit_id
        for log in logs
        if log.log_type == "failed" and log.cancelled_at is None
    }
    return completions, skipped, failed


def resolve_day_type(db: Session, user_id: int, date_value: datetime.date) -> str:
    score = db.query(DailyScore).filter_by(user_id=user_id, date=date_value).first()
    if not score:
        return "regular"
    return normalize_day_type(score.template_used)


def _template_config(db: Session, user_id: int, template_name: str) -> dict:
    template = (
        db.query(PerfectDayTemplate)
        .filter_by(user_id=user_id, template_name=template_name)
        .first()
    )
    ceilings = dict(DEFAULT_CEILINGS.get(template_name, DEFAULT_CEILINGS["regular"]))
    focus_hours = DEFAULT_FOCUS_HOURS.get(template_name, 6.0)
    min_rest_hours = DEFAULT_REST_HOURS.get(template_name, 8.0)
    agenda_json = {"schema_version": 2, "segments": [], "default_placements": []}

    if template:
        focus_hours = template.focus_hours
        min_rest_hours = template.min_rest_hours
        if template.ceilings_json:
            raw_ceilings = template.ceilings_json
            if isinstance(raw_ceilings, str):
                try:
                    raw_ceilings = json.loads(raw_ceilings)
                except ValueError:
                    raw_ceilings = {}
            ceilings.update(raw_ceilings or {})
        agenda_json = normalize_agenda_json(template.agenda_json)

    if "total" not in ceilings:
        ceilings["total"] = sum(float(ceilings.get(key, 0.0)) for key in EFFORT_TYPES)

    return {
        "template": template,
        "focus_hours": focus_hours,
        "min_rest_hours": min_rest_hours,
        "ceilings": ceilings,
        "agenda_json": agenda_json,
    }


def _effective_placement_range(item: dict) -> Optional[tuple[int, int]]:
    start = item.get("start_time")
    duration = item.get("duration_minutes")
    if not start or not duration:
        return None
    start_min = time_to_minutes(start)
    return (start_min, start_min + int(duration))


def _ranges_overlap(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left[0] < right[1] and right[0] < left[1]


def _compute_effort(
    quest_items: list[dict], ceilings: dict, min_rest_hours: float
) -> dict:
    totals = {key: 0.0 for key in EFFORT_TYPES}
    warnings = []
    incomplete = []
    for item in quest_items:
        effort_type = item.get("effort_type")
        effort_duration = item.get("effort_duration")
        if effort_type not in EFFORT_TYPES or effort_duration in (None, ""):
            if item.get("needs_configuration"):
                incomplete.append(item["habit_id"])
            continue
        totals[effort_type] += float(effort_duration)

    total = sum(totals[key] for key in EFFORT_CEILING_TYPES)
    totals["total"] = total

    labels = {
        "musculaire": "musculaire",
        "cerveau": "cerveau",
        "emotionnel_social": "social/emotionnel",
        "creatif_divergent": "creatif/divergent",
    }
    for effort_type, label in labels.items():
        ceiling = float(ceilings.get(effort_type, 0.0))
        if totals[effort_type] > ceiling:
            warnings.append(
                f"Budget {label} depasse: {totals[effort_type]:.1f}h / {ceiling:.1f}h."
            )
    total_ceiling = float(
        ceilings.get("total", sum(float(ceilings.get(k, 0)) for k in labels))
    )
    if total > total_ceiling:
        warnings.append(f"Budget total depasse: {total:.1f}h / {total_ceiling:.1f}h.")
    if min_rest_hours > 0 and totals["repos"] < min_rest_hours:
        warnings.append(
            f"Repos planifie insuffisant: {totals['repos']:.1f}h / {float(min_rest_hours):.1f}h minimum."
        )

    return {
        "totals": totals,
        "ceilings": ceilings,
        "warnings": warnings,
        "incomplete_habit_ids": incomplete,
    }


def build_agenda_response(
    db: Session, user_id: int, date_value: datetime.date
) -> tuple[dict, bool]:
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    changed = sync_generated_focus_quests(db, user)

    day_type = resolve_day_type(db, user_id, date_value)
    template_config = _template_config(db, user_id, day_type)
    agenda_json = template_config["agenda_json"]
    habits = db.query(Habit).filter(Habit.user_id == user_id).all()
    completions, skipped_ids, failed_ids = _completed_and_skipped_habit_ids(
        db, user_id, date_value, habits
    )

    eligible_habits = [
        habit
        for habit in habits
        if is_habit_eligible_on_date(habit, date_value, user, day_type)
    ]
    eligible_by_id = {habit.id: habit for habit in eligible_habits}
    current_streak_by_habit_id = {}
    eligible_ids = list(eligible_by_id)
    if eligible_ids:
        streak_rows = (
            db.query(Streak)
            .filter(
                Streak.user_id == user_id,
                Streak.streak_type.in_(
                    [f"habit:{habit_id}" for habit_id in eligible_ids]
                ),
            )
            .all()
        )
        for streak in streak_rows:
            if not streak.streak_type.startswith("habit:"):
                continue
            try:
                habit_id = int(streak.streak_type.split(":", 1)[1])
            except ValueError:
                continue
            current_streak_by_habit_id[habit_id] = streak.current_streak or 0

    placement_rows = (
        db.query(DailyAgendaPlacement)
        .filter(
            DailyAgendaPlacement.user_id == user_id,
            DailyAgendaPlacement.date == date_value,
        )
        .all()
    )
    placement_by_habit_id = {
        placement.habit_id: placement for placement in placement_rows
    }
    default_by_habit_id = {
        int(placement["habit_id"]): placement
        for placement in agenda_json.get("default_placements", [])
    }

    placed_quests = []
    unplaced_quests = []
    all_items = []

    for habit in eligible_habits:
        item = habit_to_agenda_item(
            db,
            habit,
            date_value,
            completions,
            skipped_ids,
            failed_ids,
            current_streak_by_habit_id.get(habit.id, 0),
        )
        placement = placement_by_habit_id.get(habit.id)
        default = default_by_habit_id.get(habit.id)
        placeable = _habit_agenda_placeable(habit)

        if placement and placeable:
            item.update(
                {
                    "placement_id": placement.id,
                    "start_time": placement.start_time,
                    "duration_minutes": placement.duration_minutes,
                    "placement_status": placement.status,
                    "actual_minutes": placement.actual_minutes,
                    "placement_source": "date",
                }
            )
        elif default and placeable:
            item.update(
                {
                    "placement_id": None,
                    "start_time": default["start"],
                    "duration_minutes": default["duration_minutes"],
                    "placement_status": "planned",
                    "actual_minutes": None,
                    "placement_source": "template",
                }
            )
        else:
            item.update(
                {
                    "placement_id": None,
                    "start_time": None,
                    "duration_minutes": item["agenda_duration_minutes"],
                    "placement_status": "planned",
                    "actual_minutes": None,
                    "placement_source": None,
                }
            )

        if item.get("start_time"):
            placed_quests.append(item)
        else:
            unplaced_quests.append(item)
        all_items.append(item)

    effort = _compute_effort(
        all_items,
        template_config["ceilings"],
        template_config["min_rest_hours"],
    )
    placed_quests.sort(key=lambda item: time_to_minutes(item["start_time"]))
    unplaced_quests.sort(key=lambda item: item["name"].lower())

    return (
        {
            "date": date_value.isoformat(),
            "day_type": day_type,
            "segments": agenda_json.get("segments", []),
            "placed_quests": placed_quests,
            "unplaced_quests": unplaced_quests,
            "effort_totals": effort["totals"],
            "ceilings": effort["ceilings"],
            "focus_hours": template_config["focus_hours"],
            "min_rest_hours": template_config["min_rest_hours"],
            "warnings": effort["warnings"],
            "incomplete_habit_ids": effort["incomplete_habit_ids"],
            "eligible_count": len(eligible_by_id),
        },
        changed,
    )


def _validate_placement_time(start_time: str, duration_minutes: int) -> tuple[int, int]:
    start_min = time_to_minutes(start_time)
    if start_min % 15 != 0:
        raise HTTPException(
            status_code=422,
            detail="Le debut doit etre aligne sur une grille de 15 minutes.",
        )
    if duration_minutes <= 0:
        raise HTTPException(status_code=422, detail="La duree doit etre positive.")
    if duration_minutes % 15 != 0:
        raise HTTPException(
            status_code=422,
            detail="La duree doit etre un multiple de 15 minutes.",
        )
    end_min = start_min + duration_minutes
    if end_min > 1440:
        raise HTTPException(
            status_code=422,
            detail="Le placement doit rester dans la journee courante.",
        )
    return start_min, end_min


def _placement_busy_range(item: dict) -> Optional[tuple[int, int]]:
    placement_range = _effective_placement_range(item)
    if not placement_range:
        return None
    return (placement_range[0], placement_range[1] + AGENDA_BUFFER_MINUTES)


def _resolve_auto_shifted_range(
    requested_start: int,
    duration_minutes: int,
    placed_items: list[dict],
) -> tuple[int, int, bool]:
    requested_busy = (
        requested_start,
        requested_start + duration_minutes + AGENDA_BUFFER_MINUTES,
    )
    busy_ranges = []
    for item in placed_items:
        busy_range = _placement_busy_range(item)
        if busy_range:
            busy_ranges.append((busy_range[0], busy_range[1], item))
    busy_ranges.sort(key=lambda value: value[0])

    conflict = None
    for busy_start, busy_end, item in busy_ranges:
        if _ranges_overlap(requested_busy, (busy_start, busy_end)):
            conflict = (busy_start, busy_end, item)
            break

    if not conflict:
        return requested_start, requested_start + duration_minutes, False

    shifted_start = conflict[1]
    shifted_end = shifted_start + duration_minutes
    if shifted_end > 1440:
        raise HTTPException(
            status_code=422,
            detail="Aucun creneau libre suffisant avant 24:00 apres le buffer.",
        )

    shifted_busy_end = shifted_end + AGENDA_BUFFER_MINUTES
    for busy_start, _busy_end, item in busy_ranges:
        if busy_start < shifted_start:
            continue
        if shifted_busy_end > busy_start:
            raise HTTPException(
                status_code=422,
                detail=f"Aucun creneau libre suffisant avant {item['name']} ({item['start_time']}).",
            )
        break

    return shifted_start, shifted_end, True


def update_placement(
    db: Session,
    user_id: int,
    date_value: datetime.date,
    habit_id: int,
    start_time: str,
    duration_minutes: Optional[int] = None,
    allow_overlap: bool = False,
) -> dict:
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    changed = sync_generated_focus_quests(db, user)
    habit = db.query(Habit).filter_by(id=habit_id, user_id=user_id).first()
    day_type = resolve_day_type(db, user_id, date_value)
    if not habit or not is_habit_eligible_on_date(habit, date_value, user, day_type):
        raise HTTPException(status_code=404, detail="Quest not eligible for this date.")
    if not _habit_agenda_placeable(habit):
        raise HTTPException(
            status_code=422,
            detail="Cette quete est configuree hors agenda et ne peut pas etre placee.",
        )

    duration = int(duration_minutes or _habit_duration_minutes(habit))
    target_range = _validate_placement_time(start_time, duration)

    agenda, _ = build_agenda_response(db, user_id, date_value)
    if not allow_overlap:
        placed_without_current = [
            item for item in agenda["placed_quests"] if item["habit_id"] != habit_id
        ]
        shifted_start, shifted_end, _shifted = _resolve_auto_shifted_range(
            target_range[0], duration, placed_without_current
        )
        target_range = (shifted_start, shifted_end)
        start_time = minutes_to_time(shifted_start)

    placement = (
        db.query(DailyAgendaPlacement)
        .filter_by(user_id=user_id, date=date_value, habit_id=habit_id)
        .first()
    )
    now = datetime.datetime.now()
    if not placement:
        placement = DailyAgendaPlacement(
            user_id=user_id,
            date=date_value,
            habit_id=habit_id,
            created_at=now,
        )
        db.add(placement)
    placement.start_time = start_time
    placement.duration_minutes = duration
    placement.status = "planned"
    placement.updated_at = now
    habit.agenda_duration_minutes = duration
    db.commit()

    response, _changed_after = build_agenda_response(db, user_id, date_value)
    if changed:
        db.commit()
    return response


def clear_placement(
    db: Session, user_id: int, date_value: datetime.date, habit_id: int
) -> dict:
    habit = db.query(Habit).filter_by(id=habit_id, user_id=user_id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Quest not found.")
    placement = (
        db.query(DailyAgendaPlacement)
        .filter_by(user_id=user_id, date=date_value, habit_id=habit_id)
        .first()
    )
    now = datetime.datetime.now()
    if not placement:
        placement = DailyAgendaPlacement(
            user_id=user_id,
            date=date_value,
            habit_id=habit_id,
            created_at=now,
        )
        db.add(placement)
    placement.start_time = None
    placement.duration_minutes = _habit_duration_minutes(habit)
    placement.status = "planned"
    placement.updated_at = now
    db.commit()
    response, changed = build_agenda_response(db, user_id, date_value)
    if changed:
        db.commit()
    return response


def save_agenda_as_template(
    db: Session, user_id: int, date_value: datetime.date, template_name: str
) -> dict:
    if template_name not in {"rest", "regular", "hustle"}:
        raise HTTPException(status_code=422, detail="Template invalide.")

    agenda, changed = build_agenda_response(db, user_id, date_value)
    if changed:
        db.commit()

    template_config = _template_config(db, user_id, template_name)
    template = template_config["template"]
    if not template:
        template = PerfectDayTemplate(
            user_id=user_id,
            template_name=template_name,
            focus_hours=DEFAULT_FOCUS_HOURS[template_name],
            min_rest_hours=DEFAULT_REST_HOURS[template_name],
            ceilings_json=DEFAULT_CEILINGS[template_name],
        )
        db.add(template)

    default_placements = []
    for item in agenda["placed_quests"]:
        if item.get("frequency") != "daily":
            continue
        default_placements.append(
            {
                "habit_id": item["habit_id"],
                "start": item["start_time"],
                "duration_minutes": int(item["duration_minutes"]),
            }
        )

    current_agenda_json = normalize_agenda_json(template.agenda_json)
    template.agenda_json = {
        "schema_version": 2,
        "segments": current_agenda_json.get("segments", []),
        "default_placements": sorted(
            default_placements, key=lambda item: time_to_minutes(item["start"])
        ),
    }
    db.commit()
    return {
        "status": "success",
        "template_name": template_name,
        "default_placements_count": len(default_placements),
    }
