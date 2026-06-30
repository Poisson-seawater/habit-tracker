import datetime
import json
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator

from src.database.session import get_db
from src.database.models import (
    User,
    Habit,
    HabitLog,
    PerfectDayTemplate,
    BiologicalZone,
    DailyScore,
    Streak,
    Todo,
    Goal,
    SubStep,
    GoalSubStepLink,
    NoTodo,
    UserSoftskillProgress,
    Reward,
    RemoteOperation,
)
from src.database.seed import seed_default_biological_zones
from src.services.score_service import (
    calculate_daily_score,
    update_streaks,
    add_user_xp,
    cleanup_completed_todos,
)
from src.services import agenda_service, softskill_service

router = APIRouter()

# --- Request/Response Pydantic Schemas ---

VALID_BIOLOGICAL_ZONE_TYPES = {
    "deep_focus",
    "physical_peak",
    "creative",
    "rest",
    "social",
    "sleep",
}

BIOLOGICAL_ZONE_TYPE_LABELS = {
    "deep_focus": "Focus profond",
    "physical_peak": "Pic physique",
    "creative": "Creatif",
    "rest": "Repos",
    "social": "Social",
    "sleep": "Sommeil",
}


def _is_valid_time_string(value: str) -> bool:
    parts = value.split(":")
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


class BiologicalZoneBase(BaseModel):
    zone_name: Optional[str] = None
    zone_type: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    color: Optional[str] = None
    display_order: Optional[int] = 0

    @field_validator("zone_name")
    @classmethod
    def validate_zone_name(cls, value):
        if value is not None and not value.strip():
            raise ValueError("Le nom de zone ne peut pas etre vide.")
        return value.strip() if isinstance(value, str) else value

    @field_validator("zone_type")
    @classmethod
    def validate_zone_type(cls, value):
        if value is not None and value not in VALID_BIOLOGICAL_ZONE_TYPES:
            accepted = ", ".join(sorted(VALID_BIOLOGICAL_ZONE_TYPES))
            raise ValueError(f"Type de zone invalide. Valeurs acceptees : {accepted}.")
        return value

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time(cls, value):
        if value is not None and not _is_valid_time_string(value):
            raise ValueError("L'heure doit etre au format HH:MM entre 00:00 et 23:59.")
        return value

    @field_validator("color")
    @classmethod
    def validate_color(cls, value):
        if value in (None, ""):
            return None
        if (
            isinstance(value, str)
            and len(value) == 7
            and value.startswith("#")
            and all(c in "0123456789abcdefABCDEF" for c in value[1:])
        ):
            return value
        raise ValueError("La couleur doit etre un code hexadecimal, ex: #8b5cf6.")

    @field_validator("display_order")
    @classmethod
    def validate_display_order(cls, value):
        if value is not None and value < 0:
            raise ValueError("display_order doit etre positif ou nul.")
        return value


class BiologicalZoneCreate(BiologicalZoneBase):
    zone_name: str
    zone_type: str
    start_time: str
    end_time: str


class BiologicalZoneUpdate(BiologicalZoneBase):
    pass


class LogCreate(BaseModel):
    habit_id: int
    log_type: str  # "done", "skip", "log"
    amount: Optional[int] = None
    reason: Optional[str] = None


class HabitCreate(BaseModel):
    name: str
    type: str  # "binary", "quantitative"
    description: Optional[str] = None
    frequency: Optional[str] = "daily"
    scheduled_days: Optional[str] = "0,1,2,3,4,5,6"
    reminder_time: Optional[str] = None
    is_private: Optional[bool] = False
    is_reportable: Optional[bool] = True
    is_mandatory: Optional[bool] = False
    daily_cap: Optional[int] = None
    daily_target: Optional[int] = None
    unit: Optional[str] = None
    effort_type: Optional[str] = None
    effort_duration: Optional[float] = 1.0
    agenda_duration_minutes: Optional[int] = None


class HabitVersionCreate(BaseModel):
    description: Optional[str] = None
    source_description: Optional[str] = None


class TemplateOverride(BaseModel):
    template_name: str


class TemplateSave(BaseModel):
    template_name: str
    focus_hours: float = 6.0
    min_rest_hours: float = 8.0
    ceilings: Optional[Dict[str, float]] = None
    agenda_json: Optional[Any] = None


class AgendaPlacementUpdate(BaseModel):
    start_time: str
    duration_minutes: Optional[int] = None
    allow_overlap: Optional[bool] = False


class AgendaSaveAsTemplate(BaseModel):
    template_name: str


class TodoCreate(BaseModel):
    title: str
    xp_reward: Optional[int] = Field(10, ge=0, le=40)  # Max 40 XP
    do_date: Optional[datetime.date] = None
    due_date: Optional[datetime.date] = None


class NoTodoCreate(BaseModel):
    title: str


class TelegramWebAppSessionCreate(BaseModel):
    id: int
    username: Optional[str] = None
    first_name: Optional[str] = None


class GoalCreate(BaseModel):
    title: str
    description: Optional[str] = None
    do_date: Optional[datetime.date] = None
    due_date: Optional[datetime.date] = None


class GoalWithSubstepsCreate(GoalCreate):
    substeps: List["SubStepCreate"] = Field(default_factory=list)


class SubStepCreate(BaseModel):
    title: str
    description: Optional[str] = None
    gold_reward: Optional[int] = 50
    execution_order: int = 1
    is_life_lore: Optional[bool] = False
    effort_type: Optional[str] = None
    effort_duration: Optional[float] = 1.0


class SubStepUpdate(BaseModel):
    title: str
    description: Optional[str] = None
    gold_reward: Optional[int] = 50
    execution_order: int = 1
    is_life_lore: Optional[bool] = False
    effort_type: Optional[str] = None
    effort_duration: Optional[float] = 1.0


class SubStepLinkRequest(BaseModel):
    goal_id: int
    substep_id: int
    execution_order: Optional[int] = 1


class SubStepReorderRequest(BaseModel):
    execution_order: int


class SoftskillTestUpdate(BaseModel):
    success_criteria_test: str


class SoftskillCompleteToggle(BaseModel):
    completed: bool


class BranchConfig(BaseModel):
    key: str
    color: str
    pale_color: str
    do_date: Optional[str] = None
    due_date: Optional[str] = None


class BranchUpdate(BaseModel):
    new_key: str
    color: str
    pale_color: str
    do_date: Optional[str] = None
    due_date: Optional[str] = None


class BranchSkillConfig(BaseModel):
    id: str
    name: str
    description: str = ""
    prerequisites: List[str] = Field(default_factory=list)
    related: List[str] = Field(default_factory=list)
    x: Optional[int] = Field(None, ge=0)
    y: Optional[int] = Field(None, ge=0)
    execution_order: int = 1
    success_criteria_test: Optional[str] = ""


class BranchWithSkillsCreate(BranchConfig):
    skills: List[BranchSkillConfig]


class RewardCreate(BaseModel):
    title: str
    description: Optional[str] = None
    gold_cost: int = Field(0, ge=0)
    required_softskill_id: Optional[str] = None
    required_goal_id: Optional[int] = None
    is_one_time: Optional[bool] = False
    category: Optional[str] = "regular"


class RewardUpdate(BaseModel):
    title: str
    description: Optional[str] = None
    gold_cost: int = Field(0, ge=0)
    required_softskill_id: Optional[str] = None
    required_goal_id: Optional[int] = None
    is_one_time: Optional[bool] = False
    category: Optional[str] = "regular"


class SkillConfig(BaseModel):
    id: str
    name: str
    description: str
    branch: str
    prerequisites: List[str] = Field(default_factory=list)
    related: List[str] = Field(default_factory=list)
    x: Optional[int] = Field(None, ge=0)
    y: Optional[int] = Field(None, ge=0)
    execution_order: Optional[int] = 1
    success_criteria_test: Optional[str] = ""


class SkillUpdate(BaseModel):
    name: str
    description: str
    branch: str
    prerequisites: List[str] = Field(default_factory=list)
    related: List[str] = Field(default_factory=list)
    x: Optional[int] = Field(None, ge=0)
    y: Optional[int] = Field(None, ge=0)
    execution_order: Optional[int] = 1
    success_criteria_test: Optional[str] = ""


class PinsUpdate(BaseModel):
    pinned_substeps: Optional[List[int]] = None
    pinned_softskills: Optional[List[str]] = None
    pinned_goals: Optional[List[int]] = None


GoalWithSubstepsCreate.model_rebuild()


# --- Multi-User Dependency ---


def get_current_user_id(
    user_id: Optional[int] = None,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
) -> int:
    """
    Dependency to resolve the current user ID, falling back to Gabriel (ID 1).
    """
    if x_user_id:
        try:
            return int(x_user_id)
        except ValueError:
            pass
    if user_id is not None:
        return user_id
    return 1


def _biological_zone_to_dict(zone: BiologicalZone) -> dict:
    return {
        "id": zone.id,
        "zone_name": zone.zone_name,
        "zone_type": zone.zone_type,
        "start_time": zone.start_time,
        "end_time": zone.end_time,
        "color": zone.color,
        "display_order": zone.display_order,
    }


def _time_to_minutes(time_value: str) -> int:
    hour, minute = time_value.split(":")
    return int(hour) * 60 + int(minute)


def _split_time_range(start_time: str, end_time: str) -> List[tuple[int, int]]:
    start_min = _time_to_minutes(start_time)
    end_min = _time_to_minutes(end_time)
    if start_min == end_min:
        raise HTTPException(
            status_code=422,
            detail="Une zone biologique doit avoir une duree superieure a zero.",
        )
    if end_min > start_min:
        return [(start_min, end_min)]
    return [(start_min, 1440), (0, end_min)]


def _segments_overlap(
    left: tuple[int, int],
    right: tuple[int, int],
) -> bool:
    return left[0] < right[1] and right[0] < left[1]


def _find_overlapping_biological_zone(
    db: Session,
    user_id: int,
    start_time: str,
    end_time: str,
    exclude_zone_id: Optional[int] = None,
) -> Optional[BiologicalZone]:
    target_segments = _split_time_range(start_time, end_time)
    query = db.query(BiologicalZone).filter(BiologicalZone.user_id == user_id)
    if exclude_zone_id is not None:
        query = query.filter(BiologicalZone.id != exclude_zone_id)

    for zone in query.all():
        zone_segments = _split_time_range(zone.start_time, zone.end_time)
        if any(
            _segments_overlap(target, existing)
            for target in target_segments
            for existing in zone_segments
        ):
            return zone
    return None


def _raise_biological_zone_overlap(zone: BiologicalZone):
    raise HTTPException(
        status_code=422,
        detail=(
            f'Ce creneau chevauche la zone "{zone.zone_name}" '
            f"({zone.start_time} - {zone.end_time})."
        ),
    )


# --- Server-side validation helpers ---

VALID_HABIT_TYPES = {"binary", "quantitative"}
VALID_FREQUENCIES = {"daily", "weekly", "monthly", "custom", "specific_days"}


def _split_habit_version_name(name: str) -> tuple[Optional[int], str]:
    cleaned_name = (name or "").strip()
    for prefix in ("Étape ", "Etape "):
        if cleaned_name.startswith(prefix):
            version_part, separator, base_name = cleaned_name[len(prefix) :].partition(
                " - "
            )
            if separator and version_part.isdigit() and base_name.strip():
                return int(version_part), base_name.strip()
    return None, cleaned_name


def _build_habit_version_name(version_index: int, base_name: str) -> str:
    return f"Étape {version_index} - {base_name}"


def _habit_version_history(user_habits: List[Habit], base_name: str) -> list[dict]:
    history = []
    for habit in user_habits:
        version_index, candidate_base_name = _split_habit_version_name(habit.name)
        if candidate_base_name != base_name:
            continue
        history.append(
            {
                "id": habit.id,
                "name": habit.name,
                "description": habit.description,
                "is_active": habit.is_active,
                "version_index": version_index or 1,
            }
        )
    return sorted(
        history,
        key=lambda item: (item["version_index"], item["id"]),
    )


def _latest_visible_habit_versions(habits: List[Habit]) -> List[Habit]:
    parsed_by_id = {}
    versioned_bases = set()

    for habit in habits:
        version_index, base_name = _split_habit_version_name(habit.name)
        parsed_by_id[habit.id] = (version_index, base_name)
        if version_index is not None:
            versioned_bases.add(base_name)

    passthrough_ids = set()
    latest_by_base = {}

    for habit in habits:
        version_index, base_name = parsed_by_id[habit.id]
        if version_index is None and base_name not in versioned_bases:
            passthrough_ids.add(habit.id)
            continue

        effective_version_index = version_index or 1
        current = latest_by_base.get(base_name)
        if current is None or (effective_version_index, habit.id) > (
            current[0],
            current[1].id,
        ):
            latest_by_base[base_name] = (effective_version_index, habit)

    visible_ids = passthrough_ids | {
        habit.id for _version_index, habit in latest_by_base.values()
    }
    return [habit for habit in habits if habit.id in visible_ids]


def validate_habit_payload(payload: "HabitCreate"):
    if payload.type not in VALID_HABIT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid habit type '{payload.type}'. Valid types: {', '.join(sorted(VALID_HABIT_TYPES))}",
        )
    if payload.frequency is not None and payload.frequency not in VALID_FREQUENCIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid frequency '{payload.frequency}'. Valid: {', '.join(sorted(VALID_FREQUENCIES))}",
        )
    if payload.type == "quantitative" and not payload.unit:
        raise HTTPException(
            status_code=400, detail="A quantitative habit requires a 'unit'."
        )


# --- Users & Profile Route ---


@router.get("/capabilities")
def get_capabilities():
    return {
        "protocol_version": 1,
        "idempotency": {
            "header": "Idempotency-Key",
            "recovery_endpoint": "/api/v1/remote-operations/{key}",
        },
        "atomic_operations": [
            "goal_with_substeps",
            "softskill_branch_with_skills",
        ],
    }


@router.get("/remote-operations/{idempotency_key}")
def get_remote_operation(
    idempotency_key: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    operation = (
        db.query(RemoteOperation)
        .filter_by(user_id=user_id, idempotency_key=idempotency_key)
        .first()
    )
    if not operation:
        raise HTTPException(status_code=404, detail="Remote operation not found.")
    response = None
    if operation.response_body:
        try:
            response = json.loads(operation.response_body)
        except ValueError:
            response = operation.response_body
    return {
        "idempotency_key": operation.idempotency_key,
        "status": operation.status,
        "http_status": operation.http_status,
        "method": operation.method,
        "path": operation.path,
        "response": response,
        "created_at": operation.created_at.isoformat(),
        "updated_at": operation.updated_at.isoformat(),
    }


@router.get("/users")
def get_users(db: Session = Depends(get_db)):
    """
    Fetch all users for the login/profile selection screen.
    """
    users = db.query(User).all()
    return [{"id": u.id, "username": u.username} for u in users]


@router.post("/telegram-webapp/session")
def create_telegram_webapp_session(
    payload: TelegramWebAppSessionCreate, db: Session = Depends(get_db)
):
    """
    Prototype Telegram Mini App session resolver.
    Uses Telegram-provided client data to select or create a local user.
    """
    telegram_chat_id = str(payload.id)
    display_name = payload.username or payload.first_name or f"telegram_{payload.id}"

    user = db.query(User).filter_by(chat_id=telegram_chat_id).first()
    if not user and payload.username:
        user = db.query(User).filter_by(username=payload.username).first()

    if not user:
        user = User(
            username=display_name, chat_id=telegram_chat_id, xp=0, level=1, gold=0
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif user.chat_id != telegram_chat_id:
        user.chat_id = telegram_chat_id
        db.commit()
        db.refresh(user)

    return {"id": user.id, "username": user.username}


@router.get("/profile")
def get_profile(
    db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    """
    Fetch the user's profile status, level, active daily template, and RPG economy state.
    """
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    today = datetime.date.today()
    # Ensure a DailyScore exists for today
    score = db.query(DailyScore).filter_by(user_id=user.id, date=today).first()
    if not score:
        score = calculate_daily_score(db, user_id=user.id, date=today)

    # Get today's completed habit IDs
    start_dt = datetime.datetime.combine(today, datetime.time.min)
    end_dt = datetime.datetime.combine(today, datetime.time.max)
    logs = (
        db.query(HabitLog)
        .filter(
            HabitLog.user_id == user.id,
            HabitLog.timestamp >= start_dt,
            HabitLog.timestamp <= end_dt,
        )
        .all()
    )
    completed_habit_ids = list(
        set(log.habit_id for log in logs if log.log_type in ["done", "log"])
    )

    # Get today's completed Life Lore subgoals
    life_lore_today = (
        db.query(SubStep)
        .filter(
            SubStep.user_id == user.id,
            SubStep.is_life_lore == True,
            SubStep.completed == True,
            SubStep.completed_at >= start_dt,
            SubStep.completed_at <= end_dt,
        )
        .all()
    )

    return {
        "username": user.username,
        "active_template": score.template_used,
        "completed_habit_ids": completed_habit_ids,
        "scores": {
            "status": score.status,
            "perfect_day_validated": score.status == "Perfect",
        },
        # RPG elements
        "xp": user.xp,
        "level": user.level,
        "gold": user.gold,
        "pinned_substeps": user.pinned_substeps or [],
        "pinned_softskills": user.pinned_softskills or [],
        "pinned_goals": user.pinned_goals or [],
        "life_lore_today": [
            {"id": s.id, "title": s.title, "description": s.description or ""}
            for s in life_lore_today
        ],
    }


@router.get("/profile/life-lore")
def get_user_life_lore(
    db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    """
    Fetch all completed life lore substeps of all time for the user.
    """
    substeps = (
        db.query(SubStep)
        .filter_by(user_id=user_id, is_life_lore=True, completed=True)
        .order_by(SubStep.completed_at.desc())
        .all()
    )
    return [
        {
            "id": s.id,
            "title": s.title,
            "description": s.description or "",
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            "gold_reward": s.gold_reward,
        }
        for s in substeps
    ]


@router.put("/profile/pins")
def update_profile_pins(
    payload: PinsUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Update the user's pinned sub-steps and pinned softskills.
    """
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.pinned_goals is not None:
        if len(payload.pinned_goals) > 3:
            raise HTTPException(
                status_code=400,
                detail="Vous pouvez sélectionner au maximum 3 objectifs prioritaires (Top 3).",
            )
        user.pinned_goals = payload.pinned_goals

        # If pinned_goals is modified but pinned_substeps is not explicitly provided,
        # we still want to filter the existing pinned_substeps to ensure they belong to the new pinned_goals.
        if payload.pinned_substeps is None:
            allowed_substep_ids = set()
            if user.pinned_goals:
                links = (
                    db.query(GoalSubStepLink)
                    .filter(GoalSubStepLink.goal_id.in_(user.pinned_goals))
                    .all()
                )
                for link in links:
                    allowed_substep_ids.add(link.substep_id)
            user.pinned_substeps = [
                sid
                for sid in (user.pinned_substeps or [])
                if sid in allowed_substep_ids
            ]

    # Keep only pinned_substeps that are linked to the pinned_goals
    if payload.pinned_substeps is not None:
        allowed_substep_ids = set()
        current_pinned_goals = user.pinned_goals or []
        if current_pinned_goals:
            links = (
                db.query(GoalSubStepLink)
                .filter(GoalSubStepLink.goal_id.in_(current_pinned_goals))
                .all()
            )
            for link in links:
                allowed_substep_ids.add(link.substep_id)

        user.pinned_substeps = [
            sid for sid in payload.pinned_substeps if sid in allowed_substep_ids
        ]

    if payload.pinned_softskills is not None:
        user.pinned_softskills = payload.pinned_softskills

    agenda_service.sync_generated_focus_quests(db, user)
    db.commit()
    return {"status": "success", "message": "Pins updated successfully"}


@router.get("/status")
def get_status(
    db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    """
    Full day status in a single call — the JSON equivalent of the bot's /status command.
    Exposes the Perfect Day streak and skip reasons, which no other endpoint provides.
    """
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    today = datetime.date.today()
    score = calculate_daily_score(db, user_id=user.id, date=today)

    # Today's logs, grouped by type
    start_dt = datetime.datetime.combine(today, datetime.time.min)
    end_dt = datetime.datetime.combine(today, datetime.time.max)
    today_logs = (
        db.query(HabitLog)
        .filter(
            HabitLog.user_id == user.id,
            HabitLog.timestamp >= start_dt,
            HabitLog.timestamp <= end_dt,
        )
        .all()
    )

    completed = []
    skipped = []
    logged_habit_ids = set()
    for log_entry in today_logs:
        habit = (
            db.query(Habit).filter_by(id=log_entry.habit_id, user_id=user.id).first()
        )
        if not habit:
            continue
        logged_habit_ids.add(habit.id)
        if log_entry.log_type == "done":
            completed.append(
                {
                    "habit_id": habit.id,
                    "name": habit.name,
                    "type": "done",
                    "amount": None,
                    "unit": None,
                }
            )
        elif log_entry.log_type == "log":
            completed.append(
                {
                    "habit_id": habit.id,
                    "name": habit.name,
                    "type": "log",
                    "amount": log_entry.amount,
                    "unit": log_entry.unit,
                }
            )
        elif log_entry.log_type == "skip":
            skipped.append(
                {"habit_id": habit.id, "name": habit.name, "reason": log_entry.reason}
            )

    # Todos completed today
    completed_todos = (
        db.query(Todo)
        .filter(
            Todo.user_id == user.id,
            Todo.is_completed == True,
            Todo.completed_at >= start_dt,
            Todo.completed_at <= end_dt,
        )
        .all()
    )
    completed_todos_out = [
        {"id": t.id, "title": t.title, "xp_reward": t.xp_reward}
        for t in completed_todos
    ]

    # Remaining scheduled habits (not yet logged)
    weekday = today.weekday()
    model_day_idx = (weekday + 1) % 7
    all_habits = (
        db.query(Habit)
        .filter(
            Habit.user_id == user.id,
            Habit.is_active == True,
            Habit.archived_at == None,
        )
        .all()
    )
    remaining = []
    for habit in all_habits:
        scheduled = str(model_day_idx) in [
            day.strip() for day in habit.scheduled_days.split(",")
        ]
        if not scheduled or habit.id in logged_habit_ids:
            continue
        remaining.append({"habit_id": habit.id, "name": habit.name, "type": habit.type})

    # Perfect Day streak
    perf_streak = (
        db.query(Streak).filter_by(user_id=user.id, streak_type="Perfect").first()
    )

    # No-Todos failed today
    failed_notodos = (
        db.query(NoTodo)
        .filter(
            NoTodo.user_id == user.id,
            NoTodo.failed_at >= start_dt,
            NoTodo.failed_at <= end_dt,
        )
        .all()
    )
    failed_notodos_out = [{"id": n.id, "title": n.title} for n in failed_notodos]

    return {
        "username": user.username,
        "template": score.template_used,
        "perfect_day": {
            "status": score.status,
            "validated": score.status == "Perfect",
        },
        "streak": {
            "current": perf_streak.current_streak if perf_streak else 0,
            "max": perf_streak.max_streak if perf_streak else 0,
        },
        "xp": user.xp,
        "level": user.level,
        "gold": user.gold,
        "completed": completed,
        "skipped": skipped,
        "remaining": remaining,
        "completed_todos": completed_todos_out,
        "failed_notodos": failed_notodos_out,
    }


# --- Goals & SubSteps Graph Routes ---


@router.get("/goals")
def get_goals(
    db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    """
    List all goals with their substeps and graph dependencies.
    execution_order is now read from GoalSubStepLink (per-goal ordering).
    Each substep also includes linked_goals: list of other goals it belongs to.
    """
    goals = db.query(Goal).filter_by(user_id=user_id).all()
    result = []

    for g in goals:
        substeps_list = []
        for link in g.substep_links:
            s = link.substep
            # Find all OTHER goals this substep is linked to
            other_goals = []
            for other_link in s.goal_links:
                if other_link.goal_id != g.id:
                    other_goal = other_link.goal
                    other_goals.append({"id": other_goal.id, "title": other_goal.title})
            substeps_list.append(
                {
                    "id": s.id,
                    "title": s.title,
                    "description": s.description or "",
                    "gold_reward": s.gold_reward,
                    "completed": s.completed,
                    "completed_at": (
                        s.completed_at.isoformat() if s.completed_at else None
                    ),
                    "execution_order": link.execution_order,
                    "linked_goals": other_goals,
                    "is_life_lore": s.is_life_lore,
                    "effort_type": s.effort_type,
                    "effort_duration": s.effort_duration,
                }
            )

        result.append(
            {
                "id": g.id,
                "title": g.title,
                "description": g.description,
                "completed": g.completed,
                "completed_at": g.completed_at.isoformat() if g.completed_at else None,
                "do_date": g.do_date.isoformat() if g.do_date else None,
                "due_date": g.due_date.isoformat() if g.due_date else None,
                "substeps": substeps_list,
            }
        )
    return result


@router.post("/goals", status_code=201)
def create_goal(
    payload: GoalCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Create a new goal.
    """
    existing_goals_count = db.query(Goal).filter_by(user_id=user_id).count()
    if existing_goals_count >= 20:
        raise HTTPException(
            status_code=400,
            detail="Limite de 20 objectifs atteinte. Concentrez-vous sur vos objectifs actuels ou supprimez-en.",
        )

    goal = Goal(
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        do_date=payload.do_date,
        due_date=payload.due_date,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return {
        "status": "success",
        "goal": {"id": goal.id, "title": goal.title, "description": goal.description},
    }


@router.post("/goals/with-substeps", status_code=201)
def create_goal_with_substeps(
    payload: GoalWithSubstepsCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    existing_goals_count = db.query(Goal).filter_by(user_id=user_id).count()
    if existing_goals_count >= 20:
        raise HTTPException(
            status_code=400,
            detail="Limite de 20 objectifs atteinte. Concentrez-vous sur vos objectifs actuels ou supprimez-en.",
        )

    goal = Goal(
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        do_date=payload.do_date,
        due_date=payload.due_date,
    )
    db.add(goal)
    db.flush()

    created_substeps = []
    for substep_payload in payload.substeps:
        substep = SubStep(
            user_id=user_id,
            title=substep_payload.title,
            description=substep_payload.description,
            gold_reward=substep_payload.gold_reward,
            execution_order=substep_payload.execution_order,
            is_life_lore=substep_payload.is_life_lore or False,
        )
        db.add(substep)
        db.flush()
        db.add(
            GoalSubStepLink(
                goal_id=goal.id,
                substep_id=substep.id,
                execution_order=substep_payload.execution_order,
            )
        )
        created_substeps.append(
            {
                "id": substep.id,
                "title": substep.title,
                "description": substep.description or "",
                "gold_reward": substep.gold_reward,
                "execution_order": substep.execution_order,
                "is_life_lore": substep.is_life_lore,
            }
        )

    db.commit()
    return {
        "status": "success",
        "goal": {
            "id": goal.id,
            "title": goal.title,
            "description": goal.description,
            "substeps": created_substeps,
        },
    }


@router.delete("/goals/{goal_id}")
def delete_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Delete a goal and its associated goal-substep links.
    """
    goal = db.query(Goal).filter_by(id=goal_id, user_id=user_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    db.delete(goal)
    db.commit()
    return {"status": "success", "message": "Goal deleted successfully"}


@router.put("/goals/{goal_id}")
def update_goal(
    goal_id: int,
    payload: GoalCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Update a goal's title and description.
    """
    goal = db.query(Goal).filter_by(id=goal_id, user_id=user_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    goal.title = payload.title
    goal.description = payload.description
    goal.do_date = payload.do_date
    goal.due_date = payload.due_date
    db.commit()
    db.refresh(goal)
    return {
        "status": "success",
        "goal": {
            "id": goal.id,
            "title": goal.title,
            "description": goal.description,
            "do_date": goal.do_date.isoformat() if goal.do_date else None,
            "due_date": goal.due_date.isoformat() if goal.due_date else None,
        },
    }


@router.post("/goals/{goal_id}/substeps", status_code=201)
def create_substep(
    goal_id: int,
    payload: SubStepCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Create a new substep and associate it with a goal. Optionally define blockers.
    """
    goal = db.query(Goal).filter_by(id=goal_id, user_id=user_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    substep = SubStep(
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        gold_reward=payload.gold_reward,
        execution_order=payload.execution_order,
        is_life_lore=payload.is_life_lore or False,
        effort_type=payload.effort_type,
        effort_duration=payload.effort_duration,
    )
    db.add(substep)
    db.flush()  # Generate substep ID

    # Link to Goal with per-goal execution_order
    link = GoalSubStepLink(
        goal_id=goal_id, substep_id=substep.id, execution_order=payload.execution_order
    )
    db.add(link)

    db.commit()
    db.refresh(substep)

    return {
        "status": "success",
        "substep": {
            "id": substep.id,
            "title": substep.title,
            "description": substep.description or "",
            "gold_reward": substep.gold_reward,
            "execution_order": substep.execution_order,
            "is_life_lore": substep.is_life_lore,
            "effort_type": substep.effort_type,
            "effort_duration": substep.effort_duration,
        },
    }


@router.post("/substeps/link")
def link_substep_to_goal(
    payload: SubStepLinkRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Link an existing substep to another goal (shared substep relation).
    Supports per-goal execution_order.
    """
    goal = db.query(Goal).filter_by(id=payload.goal_id, user_id=user_id).first()
    substep = (
        db.query(SubStep).filter_by(id=payload.substep_id, user_id=user_id).first()
    )

    if not goal or not substep:
        raise HTTPException(status_code=404, detail="Goal or Substep not found")

    existing_link = (
        db.query(GoalSubStepLink)
        .filter_by(goal_id=goal.id, substep_id=substep.id)
        .first()
    )
    if existing_link:
        existing_link.execution_order = payload.execution_order
        db.commit()
        return {"status": "updated"}

    link = GoalSubStepLink(
        goal_id=goal.id, substep_id=substep.id, execution_order=payload.execution_order
    )
    db.add(link)
    db.commit()
    return {"status": "success"}


@router.put("/substeps/{substep_id}")
def update_substep(
    substep_id: int,
    payload: SubStepUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Update a substep's title, description, gold reward, and effort metadata.
    Does not overwrite execution_order on individual goal links.
    """
    substep = db.query(SubStep).filter_by(id=substep_id, user_id=user_id).first()
    if not substep:
        raise HTTPException(status_code=404, detail="Substep not found")

    substep.title = payload.title
    substep.description = payload.description
    substep.gold_reward = payload.gold_reward
    substep.execution_order = payload.execution_order
    substep.is_life_lore = payload.is_life_lore or False
    substep.effort_type = payload.effort_type
    substep.effort_duration = payload.effort_duration

    db.commit()
    db.refresh(substep)

    return {
        "status": "success",
        "substep": {
            "id": substep.id,
            "title": substep.title,
            "description": substep.description or "",
            "gold_reward": substep.gold_reward,
            "execution_order": substep.execution_order,
            "is_life_lore": substep.is_life_lore,
            "effort_type": substep.effort_type,
            "effort_duration": substep.effort_duration,
        },
    }


@router.put("/goals/{goal_id}/substeps/{substep_id}/reorder")
def reorder_substep_in_goal(
    goal_id: int,
    substep_id: int,
    payload: SubStepReorderRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Change the execution_order of a substep within a specific goal only.
    Does NOT affect the substep's order in other goals.
    """
    link = (
        db.query(GoalSubStepLink)
        .join(Goal)
        .filter(
            GoalSubStepLink.goal_id == goal_id,
            GoalSubStepLink.substep_id == substep_id,
            Goal.user_id == user_id,
        )
        .first()
    )
    if not link:
        raise HTTPException(status_code=404, detail="Goal-substep link not found")

    link.execution_order = payload.execution_order
    db.commit()

    return {
        "status": "success",
        "goal_id": goal_id,
        "substep_id": substep_id,
        "execution_order": link.execution_order,
    }


@router.delete("/substeps/{substep_id}")
def delete_substep(
    substep_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Delete a substep manually. Associated links/dependencies will cascade.
    """
    substep = db.query(SubStep).filter_by(id=substep_id, user_id=user_id).first()
    if not substep:
        raise HTTPException(status_code=404, detail="Substep not found")

    db.delete(substep)
    db.commit()
    return {"status": "success", "message": "Substep deleted successfully"}


@router.post("/substeps/{substep_id}/complete")
def complete_substep(
    substep_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Complete a substep manually. Strict Option A validation:
    Cannot complete if any blocker dependency is uncompleted.
    """
    substep = db.query(SubStep).filter_by(id=substep_id, user_id=user_id).first()
    if not substep:
        raise HTTPException(status_code=404, detail="Substep not found")

    user = db.query(User).filter_by(id=user_id).first()
    pinned_goals = user.pinned_goals or []
    linked_goal_ids = [link.goal_id for link in substep.goal_links]
    is_validable = any(gid in pinned_goals for gid in linked_goal_ids)
    if not is_validable:
        raise HTTPException(
            status_code=400,
            detail="Focus requis : cette étape n'appartient à aucun de vos objectifs prioritaires (Top 3).",
        )

    if substep.completed:
        return {"status": "already_completed", "gold": user.gold}

    # Complete substep
    substep.completed = True
    substep.completed_at = datetime.datetime.now()

    # Award customizable gold reward
    user = db.query(User).filter_by(id=user_id).first()
    user.gold += substep.gold_reward

    # Auto check Goals completeness
    completed_goals = []
    all_goals = db.query(Goal).filter_by(user_id=user_id, completed=False).all()
    for g in all_goals:
        # If all substeps linked to this goal are completed
        all_linked_complete = True
        if not g.substep_links:
            all_linked_complete = False
        for link in g.substep_links:
            if not link.substep.completed:
                all_linked_complete = False
                break
        if all_linked_complete:
            g.completed = True
            g.completed_at = datetime.datetime.now()
            completed_goals.append(g.title)

    db.commit()

    return {
        "status": "success",
        "gold_awarded": substep.gold_reward,
        "new_gold": user.gold,
        "completed_goals": completed_goals,
    }


# --- Perfect Day Templates & Summation Routes ---


@router.get("/templates")
def get_templates(
    db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    """
    Get custom template configurations.
    """
    templates = db.query(PerfectDayTemplate).filter_by(user_id=user_id).all()
    result = {}
    for t in templates:
        result[t.template_name] = {
            "focus_hours": t.focus_hours,
            "min_rest_hours": t.min_rest_hours,
            "ceilings": t.ceilings_json
            or {
                "musculaire": (
                    1.0
                    if t.template_name == "rest"
                    else (4.0 if t.template_name == "hustle" else 2.0)
                ),
                "cerveau": (
                    1.0
                    if t.template_name == "rest"
                    else (4.0 if t.template_name == "hustle" else 2.0)
                ),
                "emotionnel_social": (
                    1.0
                    if t.template_name == "rest"
                    else (4.0 if t.template_name == "hustle" else 2.0)
                ),
                "creatif_divergent": (
                    1.0
                    if t.template_name == "rest"
                    else (4.0 if t.template_name == "hustle" else 2.0)
                ),
                "total": (
                    4.0
                    if t.template_name == "rest"
                    else (10.0 if t.template_name == "hustle" else 8.0)
                ),
            },
            "agenda_json": t.agenda_json or [],
        }

    default_agendas = {
        "rest": [
            {
                "id": 2,
                "title": "Méditation / Relaxation",
                "start": "09:00",
                "end": "10:00",
                "category": "relax",
            },
            {
                "id": 3,
                "title": "Marche & Étirements",
                "start": "12:00",
                "end": "13:00",
                "category": "routine",
            },
            {
                "id": 4,
                "title": "Lecture & Repos mental",
                "start": "14:00",
                "end": "17:00",
                "category": "relax",
            },
        ],
        "regular": [
            {
                "id": 2,
                "title": "Routine matinale & Cardio",
                "start": "07:00",
                "end": "08:00",
                "category": "routine",
            },
            {
                "id": 3,
                "title": "Focus Deep Work (Projet principal)",
                "start": "08:30",
                "end": "12:00",
                "category": "focus",
            },
            {
                "id": 4,
                "title": "Gestion administrative / Travail",
                "start": "13:00",
                "end": "15:00",
                "category": "focus",
            },
            {
                "id": 5,
                "title": "Entraînement physique",
                "start": "17:30",
                "end": "19:00",
                "category": "routine",
            },
            {
                "id": 6,
                "title": "Détente / Social",
                "start": "19:00",
                "end": "22:00",
                "category": "relax",
            },
        ],
        "hustle": [
            {
                "id": 2,
                "title": "Cardio & Routine active",
                "start": "06:00",
                "end": "07:00",
                "category": "routine",
            },
            {
                "id": 3,
                "title": "Deep Work",
                "start": "07:30",
                "end": "12:00",
                "category": "focus",
            },
            {
                "id": 4,
                "title": "Focus Code / Projet",
                "start": "13:00",
                "end": "18:00",
                "category": "focus",
            },
            {
                "id": 5,
                "title": "Musculation / Sport",
                "start": "18:30",
                "end": "20:00",
                "category": "routine",
            },
            {
                "id": 6,
                "title": "Veille / Apprentissage",
                "start": "20:00",
                "end": "22:30",
                "category": "focus",
            },
        ],
    }

    # Fill in missing templates with defaults
    for name in ["rest", "regular", "hustle"]:
        if name not in result:
            default_ceilings = {
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
            }[name]
            result[name] = {
                "focus_hours": (
                    2.0 if name == "rest" else (9.0 if name == "hustle" else 6.0)
                ),
                "min_rest_hours": (
                    10.0 if name == "rest" else (7.0 if name == "hustle" else 8.0)
                ),
                "ceilings": default_ceilings,
                "agenda_json": default_agendas[name],
            }

    return result


@router.post("/templates")
def save_template(
    payload: TemplateSave,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Save custom template configurations.
    """
    if payload.ceilings:
        musculaire = payload.ceilings.get("musculaire", 0.0)
        cerveau = payload.ceilings.get("cerveau", 0.0)
        emotionnel_social = payload.ceilings.get("emotionnel_social", 0.0)
        creatif_divergent = payload.ceilings.get("creatif_divergent", 0.0)

        calculated_total = musculaire + cerveau + emotionnel_social + creatif_divergent
        payload.ceilings["total"] = calculated_total

        if calculated_total > payload.focus_hours:
            raise HTTPException(
                status_code=400,
                detail=f"Le total des plafonds ({calculated_total}h) ne peut pas dépasser l'objectif focus ({payload.focus_hours}h).",
            )

    template = (
        db.query(PerfectDayTemplate)
        .filter_by(user_id=user_id, template_name=payload.template_name)
        .first()
    )
    if not template:
        template = PerfectDayTemplate(
            user_id=user_id,
            template_name=payload.template_name,
            focus_hours=payload.focus_hours,
            min_rest_hours=payload.min_rest_hours,
            ceilings_json=payload.ceilings,
            agenda_json=payload.agenda_json,
        )
        db.add(template)
    else:
        template.focus_hours = payload.focus_hours
        template.min_rest_hours = payload.min_rest_hours
        template.ceilings_json = payload.ceilings
        if payload.agenda_json is not None:
            template.agenda_json = payload.agenda_json

    db.commit()
    return {"status": "success", "template_name": payload.template_name}


# --- Manual Quest Agenda ---


@router.get("/agenda")
def get_agenda(
    date: Optional[datetime.date] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    agenda_date = date or datetime.date.today()
    response, changed = agenda_service.build_agenda_response(
        db, user_id=user_id, date_value=agenda_date
    )
    if changed:
        db.commit()
    return response


@router.put("/agenda/{date}/quests/{habit_id}/placement")
def put_agenda_placement(
    date: datetime.date,
    habit_id: int,
    payload: AgendaPlacementUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return agenda_service.update_placement(
        db,
        user_id=user_id,
        date_value=date,
        habit_id=habit_id,
        start_time=payload.start_time,
        duration_minutes=payload.duration_minutes,
        allow_overlap=bool(payload.allow_overlap),
    )


@router.delete("/agenda/{date}/quests/{habit_id}/placement")
def delete_agenda_placement(
    date: datetime.date,
    habit_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return agenda_service.clear_placement(
        db, user_id=user_id, date_value=date, habit_id=habit_id
    )


@router.post("/agenda/{date}/save-as-template")
def save_agenda_disposition(
    date: datetime.date,
    payload: AgendaSaveAsTemplate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return agenda_service.save_agenda_as_template(
        db,
        user_id=user_id,
        date_value=date,
        template_name=payload.template_name,
    )


@router.get("/biological-zones")
def get_biological_zones(
    db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    zones = (
        db.query(BiologicalZone)
        .filter(BiologicalZone.user_id == user_id)
        .order_by(BiologicalZone.start_time.asc(), BiologicalZone.display_order.asc())
        .all()
    )
    if not zones:
        seed_default_biological_zones(db, user_id=user_id)
        db.commit()
        zones = (
            db.query(BiologicalZone)
            .filter(BiologicalZone.user_id == user_id)
            .order_by(
                BiologicalZone.start_time.asc(), BiologicalZone.display_order.asc()
            )
            .all()
        )
    return [_biological_zone_to_dict(zone) for zone in zones]


@router.post("/biological-zones", status_code=201)
def create_biological_zone(
    payload: BiologicalZoneCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    overlap = _find_overlapping_biological_zone(
        db,
        user_id,
        payload.start_time,
        payload.end_time,
    )
    if overlap:
        _raise_biological_zone_overlap(overlap)

    zone = BiologicalZone(
        user_id=user_id,
        zone_name=payload.zone_name,
        zone_type=payload.zone_type,
        start_time=payload.start_time,
        end_time=payload.end_time,
        color=payload.color,
        display_order=payload.display_order or 0,
    )
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return _biological_zone_to_dict(zone)


@router.put("/biological-zones/{zone_id}")
def update_biological_zone(
    zone_id: int,
    payload: BiologicalZoneUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    zone = (
        db.query(BiologicalZone)
        .filter(BiologicalZone.id == zone_id, BiologicalZone.user_id == user_id)
        .first()
    )
    if not zone:
        raise HTTPException(status_code=404, detail="Zone introuvable.")

    updates = payload.model_dump(exclude_unset=True)
    next_start = updates.get("start_time", zone.start_time)
    next_end = updates.get("end_time", zone.end_time)
    overlap = _find_overlapping_biological_zone(
        db,
        user_id,
        next_start,
        next_end,
        exclude_zone_id=zone_id,
    )
    if overlap:
        _raise_biological_zone_overlap(overlap)

    for field, value in updates.items():
        if field == "display_order" and value is None:
            value = 0
        setattr(zone, field, value)

    db.commit()
    db.refresh(zone)
    return _biological_zone_to_dict(zone)


@router.delete("/biological-zones/{zone_id}")
def delete_biological_zone(
    zone_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    zone = (
        db.query(BiologicalZone)
        .filter(BiologicalZone.id == zone_id, BiologicalZone.user_id == user_id)
        .first()
    )
    if not zone:
        raise HTTPException(status_code=404, detail="Zone introuvable.")

    db.delete(zone)
    db.commit()
    return {"status": "deleted", "id": zone_id}


# --- Log habits ---


@router.post("/logs")
def create_log(
    payload: LogCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Submit an ephemeral habit log.
    """
    habit = (
        db.query(Habit)
        .filter_by(id=payload.habit_id, user_id=user_id, is_active=True)
        .first()
    )
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found or inactive")

    if habit.type == "quantitative":
        if payload.log_type == "log" and payload.amount is None:
            raise HTTPException(
                status_code=400, detail="Amount is required for quantitative habit logs"
            )
    elif habit.type == "binary":
        if payload.log_type != "done" and payload.log_type != "skip":
            raise HTTPException(
                status_code=400, detail="Binary habit logs must be 'done' or 'skip'"
            )

    today = datetime.date.today()
    has_target = habit.daily_target is not None and habit.daily_target > 1
    if habit.type == "binary" and payload.log_type == "done" and not has_target:
        start_dt = datetime.datetime.combine(today, datetime.time.min)
        end_dt = datetime.datetime.combine(today, datetime.time.max)
        existing = (
            db.query(HabitLog)
            .filter(
                HabitLog.user_id == user_id,
                HabitLog.habit_id == habit.id,
                HabitLog.log_type == "done",
                HabitLog.timestamp >= start_dt,
                HabitLog.timestamp <= end_dt,
            )
            .first()
        )
        if existing:
            return {
                "log_id": existing.id,
                "status": "already_logged",
            }

    log = HabitLog(
        user_id=user_id,
        habit_id=habit.id,
        log_type=payload.log_type,
        amount=payload.amount,
        unit=habit.unit if habit.type == "quantitative" else None,
        reason=payload.reason,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    # Recalculate daily Perfect Day state (no direct XP awarded for habit logs).
    score = calculate_daily_score(db, user_id=user_id, date=today)
    update_streaks(db, user_id=user_id, date=today)

    return {
        "log_id": log.id,
        "status": "logged",
        "daily_score_status": score.status,
    }


# --- Switch Template ---


@router.post("/profile/template")
def change_profile_template(
    payload: TemplateOverride,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Override the day's active score template and recalculate.
    """
    t_name = payload.template_name.lower()
    t_map = {
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
    matched_name = t_map.get(t_name, "regular")

    today = datetime.date.today()
    score = calculate_daily_score(
        db, user_id=user_id, date=today, template_name=matched_name
    )
    update_streaks(db, user_id=user_id, date=today)

    return {
        "status": "updated",
        "active_template": score.template_used,
        "daily_score_status": score.status,
    }


# --- Todos / Primes with Custom XP ---


@router.get("/todos")
def get_todos(
    db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    """
    List all bounties (todos) for the calling user.
    """
    cleanup_completed_todos(db, user_id)
    todos = (
        db.query(Todo)
        .filter_by(user_id=user_id, is_completed=False)
        .order_by(Todo.created_at.desc())
        .all()
    )
    return [
        {
            "id": t.id,
            "title": t.title,
            "xp_reward": t.xp_reward,
            "is_completed": t.is_completed,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "do_date": t.do_date.isoformat() if t.do_date else None,
            "due_date": t.due_date.isoformat() if t.due_date else None,
        }
        for t in todos
    ]


@router.post("/todos", status_code=201)
def create_todo(
    payload: TodoCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Create a custom todo (bounty). Max XP is 40.
    """
    todo = Todo(
        user_id=user_id,
        title=payload.title,
        xp_reward=payload.xp_reward,
        is_completed=False,
        do_date=payload.do_date,
        due_date=payload.due_date,
    )
    db.add(todo)
    db.commit()
    return {
        "status": "success",
        "todo": {
            "id": todo.id,
            "title": todo.title,
            "xp_reward": todo.xp_reward,
            "is_completed": todo.is_completed,
        },
    }


@router.post("/todos/{todo_id}/complete")
def complete_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Complete a todo and award its custom XP.
    """
    cleanup_completed_todos(db, user_id)
    todo = db.query(Todo).filter_by(id=todo_id, user_id=user_id).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Bounty not found")

    if todo.is_completed:
        raise HTTPException(status_code=400, detail="Bounty already completed")

    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    todo.is_completed = True
    todo.completed_at = datetime.datetime.now()

    # Award permanent XP
    levels_gained = add_user_xp(user, todo.xp_reward)

    # Recalculate daily scores after changing today's task state.
    today = datetime.date.today()
    calculate_daily_score(db, user_id=user_id, date=today)
    update_streaks(db, user_id=user_id, date=today)

    db.commit()

    return {
        "status": "success",
        "xp_rewarded": todo.xp_reward,
        "levels_gained": levels_gained,
        "new_level": user.level,
        "new_xp": user.xp,
    }


# --- No-Todos ---


@router.get("/notodos")
def get_notodos(
    db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    """
    List all No-Todos for the calling user.
    """
    notodos = (
        db.query(NoTodo)
        .filter_by(user_id=user_id)
        .order_by(NoTodo.created_at.desc())
        .all()
    )
    today = datetime.date.today()
    return [
        {
            "id": n.id,
            "title": n.title,
            "failed_today": n.failed_at is not None and n.failed_at.date() == today,
            "created_at": n.created_at.isoformat() if n.created_at else None,
            "failed_at": n.failed_at.isoformat() if n.failed_at else None,
        }
        for n in notodos
    ]


@router.post("/notodos", status_code=201)
def create_notodo(
    payload: NoTodoCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Create a No-Todo rule.
    """
    notodo = NoTodo(user_id=user_id, title=payload.title)
    db.add(notodo)
    db.commit()
    return {
        "status": "success",
        "notodo": {"id": notodo.id, "title": notodo.title, "failed_today": False},
    }


@router.post("/notodos/{notodo_id}/fail")
def fail_notodo(
    notodo_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Mark a No-Todo as failed for today.
    """
    notodo = db.query(NoTodo).filter_by(id=notodo_id, user_id=user_id).first()
    if not notodo:
        raise HTTPException(status_code=404, detail="No-Todo not found")

    notodo.failed_at = datetime.datetime.now()
    db.commit()

    return {"status": "success", "message": "No-Todo marked as failed for today."}


@router.delete("/notodos/{notodo_id}")
def delete_notodo(
    notodo_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Delete a No-Todo rule.
    """
    notodo = db.query(NoTodo).filter_by(id=notodo_id, user_id=user_id).first()
    if not notodo:
        raise HTTPException(status_code=404, detail="No-Todo not found")

    db.delete(notodo)
    db.commit()

    return {"status": "success", "message": "No-Todo deleted successfully."}


# --- History & Habits Listing ---


@router.get("/habits")
def get_habits(
    include_archived: bool = False,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    all_user_habits = db.query(Habit).filter_by(user_id=user_id).all()
    active_habits = [
        habit
        for habit in all_user_habits
        if (include_inactive or habit.is_active)
        and (include_archived or habit.archived_at is None)
    ]
    habits = _latest_visible_habit_versions(active_habits)
    today = datetime.date.today()
    week_start = datetime.datetime.combine(
        today - datetime.timedelta(days=today.weekday()), datetime.time.min
    )
    month_start = datetime.datetime.combine(today.replace(day=1), datetime.time.min)

    # Count today's validations per habit (for the "X/N" display on targeted habits)
    day_start = datetime.datetime.combine(today, datetime.time.min)
    day_end = datetime.datetime.combine(today, datetime.time.max)
    today_logs = (
        db.query(HabitLog)
        .filter(
            HabitLog.user_id == user_id,
            HabitLog.log_type.in_(["done", "log"]),
            HabitLog.timestamp >= day_start,
            HabitLog.timestamp <= day_end,
        )
        .all()
    )
    today_count_by_habit = {}
    for log in today_logs:
        today_count_by_habit[log.habit_id] = (
            today_count_by_habit.get(log.habit_id, 0) + 1
        )

    result = []
    for h in habits:
        _version_index, base_name = _split_habit_version_name(h.name)
        version_history = _habit_version_history(all_user_habits, base_name)
        completed_this_period = False
        if h.frequency in ("weekly", "monthly"):
            cutoff = week_start if h.frequency == "weekly" else month_start
            completed_this_period = (
                db.query(HabitLog)
                .filter(
                    HabitLog.habit_id == h.id,
                    HabitLog.user_id == user_id,
                    HabitLog.log_type.in_(["done", "log"]),
                    HabitLog.timestamp >= cutoff,
                )
                .first()
                is not None
            )
        result.append(
            {
                "id": h.id,
                "name": h.name,
                "description": h.description,
                "type": h.type,
                "frequency": h.frequency,
                "scheduled_days": h.scheduled_days,
                "reminder_time": h.reminder_time,
                "is_private": h.is_private,
                "is_reportable": h.is_reportable,
                "is_mandatory": h.is_mandatory,
                "daily_cap": h.daily_cap,
                "daily_target": h.daily_target,
                "unit": h.unit,
                "is_active": h.is_active,
                "completed_this_period": completed_this_period,
                "today_count": today_count_by_habit.get(h.id, 0),
                "effort_type": h.effort_type,
                "effort_duration": h.effort_duration,
                "agenda_duration_minutes": h.agenda_duration_minutes,
                "source_type": h.source_type or "manual",
                "source_ref": h.source_ref,
                "source_label": agenda_service._source_label(db, h),
                "auto_managed": bool(h.auto_managed),
                "archived_at": h.archived_at.isoformat() if h.archived_at else None,
                "version_history": version_history,
            }
        )
    return result


class HabitUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    frequency: Optional[str] = None
    scheduled_days: Optional[str] = None
    unit: Optional[str] = None
    daily_cap: Optional[int] = None
    daily_target: Optional[int] = None
    is_mandatory: Optional[bool] = None
    is_private: Optional[bool] = None
    is_reportable: Optional[bool] = None
    is_active: Optional[bool] = None
    effort_type: Optional[str] = None
    effort_duration: Optional[float] = None
    agenda_duration_minutes: Optional[int] = None


@router.post("/habits/{habit_id}/versions", status_code=201)
def create_habit_version(
    habit_id: int,
    payload: Optional[HabitVersionCreate] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    source = db.query(Habit).filter_by(id=habit_id, user_id=user_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Habit not found.")

    if payload is not None and payload.source_description is not None:
        source.description = payload.source_description

    _source_version_index, base_name = _split_habit_version_name(source.name)
    used_names = set()
    max_version_index = 0
    unversioned_base_habit = None
    version_group_habits = []

    for existing_habit in db.query(Habit).filter_by(user_id=user_id).all():
        used_names.add(existing_habit.name)
        version_index, candidate_base_name = _split_habit_version_name(
            existing_habit.name
        )
        if candidate_base_name != base_name:
            continue
        version_group_habits.append(existing_habit)
        if version_index is None:
            max_version_index = max(max_version_index, 1)
            if existing_habit.name == base_name:
                unversioned_base_habit = existing_habit
        else:
            max_version_index = max(max_version_index, version_index)

    if unversioned_base_habit:
        first_version_name = _build_habit_version_name(1, base_name)
        if first_version_name not in used_names:
            unversioned_base_habit.name = first_version_name
            used_names.add(first_version_name)

    next_version_index = max_version_index + 1
    next_version_name = _build_habit_version_name(next_version_index, base_name)
    while next_version_name in used_names:
        next_version_index += 1
        next_version_name = _build_habit_version_name(next_version_index, base_name)

    version_description = (
        payload.description
        if payload is not None and payload.description is not None
        else source.description
    )

    habit = Habit(
        user_id=user_id,
        name=next_version_name,
        type=source.type,
        description=version_description,
        frequency=source.frequency,
        scheduled_days=source.scheduled_days,
        reminder_time=source.reminder_time,
        is_private=source.is_private,
        is_reportable=source.is_reportable,
        is_mandatory=source.is_mandatory,
        daily_cap=source.daily_cap,
        daily_target=source.daily_target,
        unit=source.unit,
        effort_type=source.effort_type,
        effort_duration=source.effort_duration,
        source_type=source.source_type or "manual",
        source_ref=source.source_ref,
        auto_managed=bool(source.auto_managed),
        archived_at=source.archived_at,
        agenda_duration_minutes=source.agenda_duration_minutes,
        is_active=True,
    )
    db.add(habit)
    db.flush()

    now = datetime.datetime.now()
    for previous_habit in version_group_habits:
        if previous_habit.id == habit.id:
            continue
        if previous_habit.is_active:
            previous_habit.is_active = False
            previous_habit.deactivated_at = now

    source_streak = (
        db.query(Streak)
        .filter_by(user_id=user_id, streak_type=f"habit:{source.id}")
        .first()
    )
    if not source_streak:
        candidate_streaks = []
        for previous_habit in version_group_habits:
            candidate = (
                db.query(Streak)
                .filter_by(user_id=user_id, streak_type=f"habit:{previous_habit.id}")
                .first()
            )
            if candidate:
                candidate_streaks.append(candidate)
        source_streak = max(
            candidate_streaks,
            key=lambda streak: (
                streak.current_streak or 0,
                streak.max_streak or 0,
                streak.last_incremented or datetime.date.min,
            ),
            default=None,
        )

    if source_streak:
        new_streak = (
            db.query(Streak)
            .filter_by(user_id=user_id, streak_type=f"habit:{habit.id}")
            .first()
        )
        if not new_streak:
            new_streak = Streak(user_id=user_id, streak_type=f"habit:{habit.id}")
            db.add(new_streak)
        new_streak.current_streak = source_streak.current_streak
        new_streak.max_streak = source_streak.max_streak
        new_streak.last_incremented = source_streak.last_incremented

    db.commit()
    db.refresh(habit)
    return {
        "id": habit.id,
        "name": habit.name,
        "base_name": base_name,
        "version_index": next_version_index,
        "source_id": source.id,
        "status": "success",
    }


@router.put("/habits/{habit_id}")
def update_habit(
    habit_id: int,
    payload: HabitUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    habit = db.query(Habit).filter_by(id=habit_id, user_id=user_id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found.")

    # Handle active status transition logic
    payload_dict = payload.model_dump(exclude_none=True)
    if (
        "agenda_duration_minutes" in payload_dict
        and payload_dict["agenda_duration_minutes"] <= 0
    ):
        raise HTTPException(
            status_code=400, detail="agenda_duration_minutes must be positive."
        )
    if "is_active" in payload_dict:
        new_active = payload_dict["is_active"]
        if new_active is False and habit.is_active is True:
            habit.deactivated_at = datetime.datetime.now()
        elif new_active is True and habit.is_active is False:
            if habit.deactivated_at:
                freeze_days = (datetime.datetime.now() - habit.deactivated_at).days
                if freeze_days > 14:
                    # Reset streak
                    h_streak = (
                        db.query(Streak)
                        .filter_by(user_id=user_id, streak_type=f"habit:{habit.id}")
                        .first()
                    )
                    if h_streak:
                        h_streak.current_streak = 0
            habit.deactivated_at = None

    for field, value in payload_dict.items():
        setattr(habit, field, value)
    db.commit()
    return {"status": "updated"}


@router.post("/habits/{habit_id}/archive")
def archive_habit(
    habit_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    habit = db.query(Habit).filter_by(id=habit_id, user_id=user_id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found.")
    if habit.archived_at is None:
        habit.archived_at = datetime.datetime.now()
    db.commit()
    return {"status": "archived", "id": habit.id}


@router.post("/habits/{habit_id}/unarchive")
def unarchive_habit(
    habit_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    habit = db.query(Habit).filter_by(id=habit_id, user_id=user_id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found.")
    habit.archived_at = None
    db.commit()
    return {"status": "unarchived", "id": habit.id}


@router.delete("/habits/{habit_id}")
def delete_habit(
    habit_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    habit = db.query(Habit).filter_by(id=habit_id, user_id=user_id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found.")
    habit.is_active = False
    habit.deactivated_at = datetime.datetime.now()
    db.commit()
    return {"status": "deleted"}


@router.get("/habits/{habit_id}/calendar")
def get_habit_calendar(
    habit_id: int,
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    import calendar

    habit = db.query(Habit).filter_by(id=habit_id, user_id=user_id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found.")

    today = datetime.date.today()
    if year is None:
        year = today.year
    if month is None:
        month = today.month

    _, num_days = calendar.monthrange(year, month)

    start_date = datetime.date(year, month, 1)
    end_date = datetime.date(year, month, num_days)

    start_dt = datetime.datetime.combine(start_date, datetime.time.min)
    end_dt = datetime.datetime.combine(end_date, datetime.time.max)

    logs = (
        db.query(HabitLog)
        .filter(
            HabitLog.habit_id == habit_id,
            HabitLog.user_id == user_id,
            HabitLog.timestamp >= start_dt,
            HabitLog.timestamp <= end_dt,
        )
        .all()
    )

    logs_by_day = {}
    for log in logs:
        log_day = log.timestamp.date().day
        logs_by_day.setdefault(log_day, []).append(log)

    days_status = {}

    h_streak = (
        db.query(Streak)
        .filter_by(user_id=user_id, streak_type=f"habit:{habit.id}")
        .first()
    )
    current_streak = h_streak.current_streak if h_streak else 0
    max_streak = h_streak.max_streak if h_streak else 0

    habit_created_date = habit.created_at.date() if habit.created_at else None

    for day in range(1, num_days + 1):
        day_date = datetime.date(year, month, day)

        if day_date > today:
            days_status[day] = "future"
            continue

        if habit_created_date and day_date < habit_created_date:
            days_status[day] = "pre-creation"
            continue

        day_logs = logs_by_day.get(day, [])
        is_done = any(l.log_type in ["done", "log"] for l in day_logs)
        is_skipped = any(l.log_type == "skip" for l in day_logs)

        if is_done:
            days_status[day] = "completed"
        elif is_skipped:
            days_status[day] = "skipped"
        else:
            weekday = day_date.weekday()
            model_day_idx = (weekday + 1) % 7
            is_scheduled = str(model_day_idx) in [
                d.strip() for d in habit.scheduled_days.split(",")
            ]

            if is_scheduled:
                days_status[day] = "missed"
            else:
                days_status[day] = "non-scheduled"

    return {
        "habit_id": habit.id,
        "habit_name": habit.name,
        "year": year,
        "month": month,
        "current_streak": current_streak,
        "max_streak": max_streak,
        "deactivated_at": (
            habit.deactivated_at.isoformat() if habit.deactivated_at else None
        ),
        "days": days_status,
    }


@router.post("/habits", status_code=201)
def create_habit(
    payload: HabitCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    validate_habit_payload(payload)
    existing = db.query(Habit).filter_by(user_id=user_id, name=payload.name).first()
    if existing:
        raise HTTPException(
            status_code=400, detail=f"Habit with name '{payload.name}' already exists."
        )

    habit = Habit(
        user_id=user_id,
        name=payload.name,
        type=payload.type,
        description=payload.description,
        frequency=payload.frequency,
        scheduled_days=payload.scheduled_days,
        reminder_time=payload.reminder_time,
        is_private=payload.is_private,
        is_reportable=payload.is_reportable,
        is_mandatory=payload.is_mandatory,
        daily_cap=payload.daily_cap,
        daily_target=payload.daily_target,
        unit=payload.unit,
        effort_type=payload.effort_type,
        effort_duration=payload.effort_duration,
        source_type="manual",
        source_ref=None,
        auto_managed=False,
        archived_at=None,
        agenda_duration_minutes=(
            payload.agenda_duration_minutes
            if payload.agenda_duration_minutes is not None
            else int((payload.effort_duration or 1.0) * 60)
        ),
        is_active=True,
    )
    db.add(habit)
    db.commit()
    db.refresh(habit)
    return {"id": habit.id, "name": habit.name, "status": "success"}


@router.get("/history")
def get_history(
    db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    import calendar

    today = datetime.date.today()
    _, num_days = calendar.monthrange(today.year, today.month)
    start_date = today.replace(day=1)

    scores = (
        db.query(DailyScore)
        .filter(
            DailyScore.user_id == user_id,
            DailyScore.date >= start_date,
            DailyScore.date <= today,
        )
        .order_by(DailyScore.date.asc())
        .all()
    )

    score_map = {score.date.isoformat(): score.status for score in scores}

    history = []
    for i in range(num_days):
        d = start_date + datetime.timedelta(days=i)
        d_str = d.isoformat()

        ui_status = "future"
        if d <= today:
            status = score_map.get(d_str, "Incomplet")
            ui_status = "failed"
            if status == "Perfect":
                ui_status = "perfect"

        history.append(
            {
                "date": d_str,
                "status": ui_status,
                "label": d.strftime("%d"),
                "weekday": d.weekday(),
            }
        )

    return history


# --- Softskill Progress Tree Routes ---


@router.get("/softskills")
def get_softskills_tree(
    db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    """
    Get the full softskill tree layout merged with the current user's progress.
    """
    return softskill_service.get_tree_with_progress(db, user_id)


@router.post("/softskills/{softskill_id}/test")
def update_softskill_test(
    softskill_id: str,
    payload: SoftskillTestUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Save or update the user's custom success criteria test for a softskill.
    """
    result = softskill_service.update_success_test(
        db, user_id, softskill_id, payload.success_criteria_test
    )
    return {
        "status": "success",
        "message": "Success criteria test updated",
        "data": result,
    }


@router.post("/softskills/{softskill_id}/complete")
def toggle_softskill_completion(
    softskill_id: str,
    payload: SoftskillCompleteToggle,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Manually mark a softskill as completed or uncompleted.
    Validates that prerequisites are met before allowing completion.
    """
    result = softskill_service.toggle_completion(
        db, user_id, softskill_id, payload.completed
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {
        "status": "success",
        "message": "Softskill completion updated",
        "data": result,
    }


@router.post("/softskills/branches", status_code=201)
def api_create_branch(payload: BranchConfig):
    try:
        return softskill_service.create_branch(
            payload.key,
            payload.color,
            payload.pale_color,
            do_date=payload.do_date,
            due_date=payload.due_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/softskills/branches-with-skills", status_code=201)
def api_create_branch_with_skills(payload: BranchWithSkillsCreate):
    try:
        return softskill_service.create_branch_with_skills(
            payload.key,
            payload.color,
            payload.pale_color,
            [skill.model_dump() for skill in payload.skills],
            do_date=payload.do_date,
            due_date=payload.due_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/softskills/branches/{branch_key}")
def api_update_branch(branch_key: str, payload: BranchUpdate):
    try:
        return softskill_service.update_branch(
            branch_key,
            payload.new_key,
            payload.color,
            payload.pale_color,
            do_date=payload.do_date,
            due_date=payload.due_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/softskills/branches/{branch_key}")
def api_delete_branch(branch_key: str, db: Session = Depends(get_db)):
    try:
        return softskill_service.delete_branch(db, branch_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/softskills/skills", status_code=201)
def api_create_skill(payload: SkillConfig):
    try:
        return softskill_service.create_skill(payload.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/softskills/skills/{skill_id}")
def api_update_skill(skill_id: str, payload: SkillUpdate):
    try:
        return softskill_service.update_skill(skill_id, payload.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/softskills/skills/{skill_id}")
def api_delete_skill(skill_id: str, db: Session = Depends(get_db)):
    try:
        return softskill_service.delete_skill(db, skill_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Reward Shop (Boutique) Routes ---


@router.get("/rewards")
def get_rewards(
    db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    """
    Get list of rewards for the user, with lock states calculated dynamically.
    """
    from src.services.reward_service import check_reward_lock, is_allostasis_available

    rewards = db.query(Reward).filter_by(user_id=user_id).all()
    result = []
    for r in rewards:
        unlocked, lock_reason = check_reward_lock(db, user_id, r)
        is_available = (
            is_allostasis_available(r)
            if r.category in ("allostasis_daily", "allostasis_weekly")
            else True
        )
        result.append(
            {
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "gold_cost": r.gold_cost,
                "required_softskill_id": r.required_softskill_id,
                "required_goal_id": r.required_goal_id,
                "is_one_time": r.is_one_time,
                "purchased_count": r.purchased_count,
                "unlocked": unlocked,
                "lock_reason": lock_reason,
                "category": r.category,
                "last_purchased_at": (
                    r.last_purchased_at.isoformat() if r.last_purchased_at else None
                ),
                "is_available": is_available,
            }
        )
    return result


@router.post("/rewards", status_code=201)
def create_reward(
    payload: RewardCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Create a new reward.
    """
    softskill_id = (
        payload.required_softskill_id
        if payload.required_softskill_id and payload.required_softskill_id.strip()
        else None
    )
    goal_id = payload.required_goal_id
    if goal_id:
        goal = db.query(Goal).filter_by(id=goal_id, user_id=user_id).first()
        if not goal:
            raise HTTPException(
                status_code=400, detail="Objectif requis introuvable ou invalide."
            )

    category = payload.category or "regular"
    if category in ("allostasis_daily", "allostasis_weekly"):
        gold_cost = 0
        existing_count = (
            db.query(Reward).filter_by(user_id=user_id, category=category).count()
        )
        if existing_count >= 3:
            raise HTTPException(
                status_code=400,
                detail=f"Limite de 3 items pour la catégorie {category} atteinte.",
            )
    else:
        gold_cost = payload.gold_cost

    reward = Reward(
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        gold_cost=gold_cost,
        required_softskill_id=softskill_id,
        required_goal_id=goal_id,
        is_one_time=payload.is_one_time or False,
        purchased_count=0,
        category=category,
    )
    db.add(reward)
    db.commit()
    db.refresh(reward)
    return {"status": "success", "reward": reward}


@router.put("/rewards/{reward_id}")
def update_reward(
    reward_id: int,
    payload: RewardUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Update an existing reward.
    """
    reward = db.query(Reward).filter_by(id=reward_id, user_id=user_id).first()
    if not reward:
        raise HTTPException(status_code=404, detail="Récompense introuvable.")

    softskill_id = (
        payload.required_softskill_id
        if payload.required_softskill_id and payload.required_softskill_id.strip()
        else None
    )
    goal_id = payload.required_goal_id
    if goal_id:
        goal = db.query(Goal).filter_by(id=goal_id, user_id=user_id).first()
        if not goal:
            raise HTTPException(
                status_code=400, detail="Objectif requis introuvable ou invalide."
            )

    category = payload.category or "regular"
    if category in ("allostasis_daily", "allostasis_weekly"):
        gold_cost = 0
        existing_count = (
            db.query(Reward)
            .filter(
                Reward.user_id == user_id,
                Reward.category == category,
                Reward.id != reward_id,
            )
            .count()
        )
        if existing_count >= 3:
            raise HTTPException(
                status_code=400,
                detail=f"Limite de 3 items pour la catégorie {category} atteinte.",
            )
    else:
        gold_cost = payload.gold_cost

    reward.title = payload.title
    reward.description = payload.description
    reward.gold_cost = gold_cost
    reward.required_softskill_id = softskill_id
    reward.required_goal_id = goal_id
    reward.is_one_time = payload.is_one_time or False
    reward.category = category

    db.commit()
    db.refresh(reward)
    return {"status": "success", "reward": reward}


@router.delete("/rewards/{reward_id}")
def delete_reward(
    reward_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Delete a reward.
    """
    reward = db.query(Reward).filter_by(id=reward_id, user_id=user_id).first()
    if not reward:
        raise HTTPException(status_code=404, detail="Récompense introuvable.")
    db.delete(reward)
    db.commit()
    return {"status": "success", "message": "Reward deleted successfully"}


@router.post("/rewards/{reward_id}/purchase")
def purchase_reward_endpoint(
    reward_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Purchase a reward.
    """
    from src.services.reward_service import purchase_reward

    return purchase_reward(db, user_id, reward_id)
