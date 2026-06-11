import datetime
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

from src.database.session import get_db
from src.database.models import User, Habit, HabitLog, PerfectDayTemplate, DailyScore, Streak, Todo, Goal, SubStep, GoalSubStepLink, NoTodo, UserSoftskillProgress
from src.services.score_service import calculate_daily_score, update_streaks, add_user_xp, ALL_12_STATS, DEFAULT_THRESHOLDS
from src.services import softskill_service

router = APIRouter()

# --- Request/Response Pydantic Schemas ---

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
    point_rewards: Dict[str, int]
    daily_cap: Optional[int] = None
    unit: Optional[str] = None

class TemplateOverride(BaseModel):
    template_name: str

class TemplateSave(BaseModel):
    template_name: str
    thresholds_json: Dict[str, int]

class TodoCreate(BaseModel):
    title: str
    stat_reward_1: Optional[str] = None
    points_reward_1: Optional[int] = 0
    stat_reward_2: Optional[str] = None
    points_reward_2: Optional[int] = 0
    xp_reward: Optional[int] = Field(10, ge=0, le=40)  # Max 40 XP

class NoTodoCreate(BaseModel):
    title: str

class TelegramWebAppSessionCreate(BaseModel):
    id: int
    username: Optional[str] = None
    first_name: Optional[str] = None

class GoalCreate(BaseModel):
    title: str
    description: Optional[str] = None

class SubStepCreate(BaseModel):
    title: str
    description: Optional[str] = None
    gold_reward: Optional[int] = 50
    stats_json: List[str] = []
    execution_order: int = 1

class SubStepUpdate(BaseModel):
    title: str
    description: Optional[str] = None
    gold_reward: Optional[int] = 50
    stats_json: List[str] = []
    execution_order: int = 1

class SubStepLinkRequest(BaseModel):
    goal_id: int
    substep_id: int


class SoftskillTestUpdate(BaseModel):
    success_criteria_test: str


class SoftskillCompleteToggle(BaseModel):
    completed: bool


class BranchConfig(BaseModel):
    key: str
    color: str
    pale_color: str


class BranchUpdate(BaseModel):
    new_key: str
    color: str
    pale_color: str


class SkillConfig(BaseModel):
    id: str
    name: str
    description: str
    branch: str
    prerequisites: List[str] = []
    related: List[str] = []
    x: Optional[int] = 0
    y: Optional[int] = 0
    order: Optional[int] = 1


class SkillUpdate(BaseModel):
    name: str
    description: str
    branch: str
    prerequisites: List[str] = []
    related: List[str] = []
    x: Optional[int] = 0
    y: Optional[int] = 0
    order: Optional[int] = 1


# --- Multi-User Dependency ---

def get_current_user_id(user_id: Optional[int] = None, x_user_id: Optional[str] = Header(None, alias="X-User-ID")) -> int:
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


# --- Server-side validation helpers ---

VALID_HABIT_TYPES = {"binary", "quantitative"}
VALID_FREQUENCIES = {"daily", "weekly", "custom"}


def _validate_stat_name(stat_name: Optional[str]):
    """Reject a stat name that is not one of the 12 canonical stats. None is allowed."""
    if stat_name and stat_name not in ALL_12_STATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown stat '{stat_name}'. Valid stats: {', '.join(ALL_12_STATS)}"
        )


def validate_todo_payload(payload: "TodoCreate"):
    _validate_stat_name(payload.stat_reward_1)
    _validate_stat_name(payload.stat_reward_2)


def validate_habit_payload(payload: "HabitCreate"):
    if payload.type not in VALID_HABIT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid habit type '{payload.type}'. Valid types: {', '.join(sorted(VALID_HABIT_TYPES))}"
        )
    if payload.frequency is not None and payload.frequency not in VALID_FREQUENCIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid frequency '{payload.frequency}'. Valid: {', '.join(sorted(VALID_FREQUENCIES))}"
        )
    if not payload.point_rewards:
        raise HTTPException(status_code=400, detail="point_rewards must not be empty.")
    for stat in payload.point_rewards.keys():
        if stat not in ALL_12_STATS:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown stat '{stat}' in point_rewards. Valid stats: {', '.join(ALL_12_STATS)}"
            )
    if payload.type == "quantitative" and not payload.unit:
        raise HTTPException(status_code=400, detail="A quantitative habit requires a 'unit'.")


# --- Users & Profile Route ---

@router.get("/users")
def get_users(db: Session = Depends(get_db)):
    """
    Fetch all users for the login/profile selection screen.
    """
    users = db.query(User).all()
    return [{"id": u.id, "username": u.username} for u in users]

@router.post("/telegram-webapp/session")
def create_telegram_webapp_session(payload: TelegramWebAppSessionCreate, db: Session = Depends(get_db)):
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
        user = User(username=display_name, chat_id=telegram_chat_id, xp=0, level=1, gold=0)
        db.add(user)
        db.commit()
        db.refresh(user)
    elif user.chat_id != telegram_chat_id:
        user.chat_id = telegram_chat_id
        db.commit()
        db.refresh(user)

    return {"id": user.id, "username": user.username}

@router.get("/profile")
def get_profile(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """
    Fetch the user's profile status, level, active daily template, RPG attributes,
    and progress towards daily score thresholds.
    """
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    today = datetime.date.today()
    # Ensure a DailyScore exists for today
    score = db.query(DailyScore).filter_by(user_id=user.id, date=today).first()
    if not score:
        score = calculate_daily_score(db, user_id=user.id, date=today)

    # Get custom template thresholds or fallback
    custom_template = db.query(PerfectDayTemplate).filter_by(user_id=user.id, template_name=score.template_used).first()
    thresholds = custom_template.thresholds_json if custom_template else DEFAULT_THRESHOLDS.get(score.template_used, {})

    # Get today's completed habit IDs
    start_dt = datetime.datetime.combine(today, datetime.time.min)
    end_dt = datetime.datetime.combine(today, datetime.time.max)
    logs = db.query(HabitLog).filter(
        HabitLog.user_id == user.id,
        HabitLog.timestamp >= start_dt,
        HabitLog.timestamp <= end_dt
    ).all()
    completed_habit_ids = list(set(log.habit_id for log in logs if log.log_type in ["done", "log"]))

    return {
        "username": user.username,
        "active_template": score.template_used,
        "completed_habit_ids": completed_habit_ids,
        "scores": {
            "status": score.status,
            "perfect_day_validated": score.status == "Perfect"
        },
        "stats": score.actual_stats,
        "thresholds": thresholds,
        # RPG elements
        "xp": user.xp,
        "level": user.level,
        "gold": user.gold
    }


@router.get("/status")
def get_status(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """
    Full day status in a single call — the JSON equivalent of the bot's /status command.
    Exposes the Perfect Day streak and skip reasons, which no other endpoint provides.
    """
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    today = datetime.date.today()
    score = calculate_daily_score(db, user_id=user.id, date=today)

    custom_template = db.query(PerfectDayTemplate).filter_by(user_id=user.id, template_name=score.template_used).first()
    thresholds = custom_template.thresholds_json if custom_template else DEFAULT_THRESHOLDS.get(score.template_used, {})

    # Today's logs, grouped by type
    start_dt = datetime.datetime.combine(today, datetime.time.min)
    end_dt = datetime.datetime.combine(today, datetime.time.max)
    today_logs = db.query(HabitLog).filter(
        HabitLog.user_id == user.id,
        HabitLog.timestamp >= start_dt,
        HabitLog.timestamp <= end_dt
    ).all()

    completed = []
    skipped = []
    logged_habit_ids = set()
    for log_entry in today_logs:
        habit = db.query(Habit).filter_by(id=log_entry.habit_id, user_id=user.id).first()
        if not habit:
            continue
        logged_habit_ids.add(habit.id)
        if log_entry.log_type == "done":
            completed.append({"habit_id": habit.id, "name": habit.name, "type": "done", "amount": None, "unit": None})
        elif log_entry.log_type == "log":
            completed.append({"habit_id": habit.id, "name": habit.name, "type": "log", "amount": log_entry.amount, "unit": log_entry.unit})
        elif log_entry.log_type == "skip":
            skipped.append({"habit_id": habit.id, "name": habit.name, "reason": log_entry.reason})

    # Todos completed today
    completed_todos = db.query(Todo).filter(
        Todo.user_id == user.id,
        Todo.is_completed == True,
        Todo.completed_at >= start_dt,
        Todo.completed_at <= end_dt
    ).all()
    completed_todos_out = [{"id": t.id, "title": t.title, "xp_reward": t.xp_reward} for t in completed_todos]

    # Remaining scheduled habits (not yet logged)
    weekday = today.weekday()
    model_day_idx = (weekday + 1) % 7
    all_habits = db.query(Habit).filter_by(user_id=user.id, is_active=True).all()
    remaining = []
    for habit in all_habits:
        scheduled = str(model_day_idx) in [day.strip() for day in habit.scheduled_days.split(",")]
        if not scheduled or habit.id in logged_habit_ids:
            continue
        remaining.append({"habit_id": habit.id, "name": habit.name, "type": habit.type})

    # Perfect Day streak
    perf_streak = db.query(Streak).filter_by(user_id=user.id, streak_type="Perfect").first()

    # No-Todos failed today
    failed_notodos = db.query(NoTodo).filter(
        NoTodo.user_id == user.id,
        NoTodo.failed_at >= start_dt,
        NoTodo.failed_at <= end_dt
    ).all()
    failed_notodos_out = [{"id": n.id, "title": n.title} for n in failed_notodos]

    return {
        "username": user.username,
        "template": score.template_used,
        "perfect_day": {
            "status": score.status,
            "validated": score.status == "Perfect",
            "thresholds": thresholds,
            "actual": {stat: score.actual_stats.get(stat.lower(), 0) for stat in thresholds},
        },
        "streak": {
            "current": perf_streak.current_streak if perf_streak else 0,
            "max": perf_streak.max_streak if perf_streak else 0,
        },
        "xp": user.xp,
        "level": user.level,
        "gold": user.gold,
        "stats": score.actual_stats,
        "completed": completed,
        "skipped": skipped,
        "remaining": remaining,
        "completed_todos": completed_todos_out,
        "failed_notodos": failed_notodos_out,
    }


# --- Goals & SubSteps Graph Routes ---

@router.get("/goals")
def get_goals(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """
    List all goals with their substeps and graph dependencies.
    """
    goals = db.query(Goal).filter_by(user_id=user_id).all()
    result = []
    
    for g in goals:
        substeps_list = []
        for link in g.substep_links:
            s = link.substep
            substeps_list.append({
                "id": s.id,
                "title": s.title,
                "description": s.description or "",
                "gold_reward": s.gold_reward,
                "completed": s.completed,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "stats": s.stats_json or [],
                "execution_order": s.execution_order
            })
            
        result.append({
            "id": g.id,
            "title": g.title,
            "description": g.description,
            "completed": g.completed,
            "completed_at": g.completed_at.isoformat() if g.completed_at else None,
            "substeps": substeps_list
        })
        
    return result

@router.post("/goals", status_code=201)
def create_goal(payload: GoalCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """
    Create a new goal.
    """
    goal = Goal(
        user_id=user_id,
        title=payload.title,
        description=payload.description
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return {
        "status": "success",
        "goal": {
            "id": goal.id,
            "title": goal.title,
            "description": goal.description
        }
    }

@router.delete("/goals/{goal_id}")
def delete_goal(goal_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
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
def update_goal(goal_id: int, payload: GoalCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """
    Update a goal's title and description.
    """
    goal = db.query(Goal).filter_by(id=goal_id, user_id=user_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
        
    goal.title = payload.title
    goal.description = payload.description
    db.commit()
    db.refresh(goal)
    return {
        "status": "success",
        "goal": {
            "id": goal.id,
            "title": goal.title,
            "description": goal.description
        }
    }

@router.post("/goals/{goal_id}/substeps", status_code=201)
def create_substep(goal_id: int, payload: SubStepCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
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
        stats_json=payload.stats_json,
        execution_order=payload.execution_order
    )
    db.add(substep)
    db.flush()  # Generate substep ID

    # Link to Goal
    link = GoalSubStepLink(goal_id=goal_id, substep_id=substep.id)
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
            "stats": substep.stats_json,
            "execution_order": substep.execution_order
        }
    }

@router.post("/substeps/link")
def link_substep_to_goal(payload: SubStepLinkRequest, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """
    Link an existing substep to another goal (shared substep relation).
    """
    goal = db.query(Goal).filter_by(id=payload.goal_id, user_id=user_id).first()
    substep = db.query(SubStep).filter_by(id=payload.substep_id, user_id=user_id).first()
    
    if not goal or not substep:
        raise HTTPException(status_code=404, detail="Goal or Substep not found")
        
    existing_link = db.query(GoalSubStepLink).filter_by(goal_id=goal.id, substep_id=substep.id).first()
    if existing_link:
        return {"status": "already_linked"}
        
    link = GoalSubStepLink(goal_id=goal.id, substep_id=substep.id)
    db.add(link)
    db.commit()
    return {"status": "success"}



@router.put("/substeps/{substep_id}")
def update_substep(substep_id: int, payload: SubStepUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """
    Update a substep's title, description, gold reward, target stats, and blocker dependencies.
    """
    substep = db.query(SubStep).filter_by(id=substep_id, user_id=user_id).first()
    if not substep:
        raise HTTPException(status_code=404, detail="Substep not found")
        
    substep.title = payload.title
    substep.description = payload.description
    substep.gold_reward = payload.gold_reward
    substep.stats_json = payload.stats_json
    substep.execution_order = payload.execution_order
    

                
    db.commit()
    db.refresh(substep)
    
    return {
        "status": "success",
        "substep": {
            "id": substep.id,
            "title": substep.title,
            "description": substep.description or "",
            "gold_reward": substep.gold_reward,
            "stats": substep.stats_json,
            "execution_order": substep.execution_order
        }
    }

@router.delete("/substeps/{substep_id}")
def delete_substep(substep_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
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
def complete_substep(substep_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """
    Complete a substep manually. Strict Option A validation:
    Cannot complete if any blocker dependency is uncompleted.
    """
    substep = db.query(SubStep).filter_by(id=substep_id, user_id=user_id).first()
    if not substep:
        raise HTTPException(status_code=404, detail="Substep not found")
        
    if substep.completed:
        return {"status": "already_completed", "gold": substep.user.gold}



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
        "completed_goals": completed_goals
    }


# --- Perfect Day Templates & Summation Routes ---

@router.get("/templates")
def get_templates(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """
    Get custom template thresholds configurations.
    """
    templates = db.query(PerfectDayTemplate).filter_by(user_id=user_id).all()
    result = {}
    for t in templates:
        result[t.template_name] = t.thresholds_json
        
    # Fill in missing templates with defaults
    for name, default_vals in DEFAULT_THRESHOLDS.items():
        if name not in result:
            result[name] = default_vals
            
    return result

@router.post("/templates")
def save_template(payload: TemplateSave, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """
    Save custom template thresholds configurations.
    """
    template = db.query(PerfectDayTemplate).filter_by(user_id=user_id, template_name=payload.template_name).first()
    if not template:
        template = PerfectDayTemplate(
            user_id=user_id,
            template_name=payload.template_name,
            thresholds_json=payload.thresholds_json
        )
        db.add(template)
    else:
        template.thresholds_json = payload.thresholds_json
        
    db.commit()
    return {"status": "success", "template_name": payload.template_name}

@router.get("/quests/daily-stats-potentials")
def get_daily_stats_potentials(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """
    Calculate potential statistic totals group by day of the week.
    Scheduled days represented by 0 (Sunday) to 6 (Saturday).
    """
    habits = db.query(Habit).filter_by(user_id=user_id, is_active=True).all()
    day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    potentials = {day: {stat: 0 for stat in ALL_12_STATS} for day in day_names}
    
    for h in habits:
        scheduled_days = [int(d.strip()) for d in h.scheduled_days.split(",") if d.strip().isdigit()]
        for d_idx in scheduled_days:
            if 0 <= d_idx < 7:
                day_name = day_names[d_idx]
                for stat, reward_points in h.point_rewards.items():
                    stat_key = stat.lower()
                    if stat_key in potentials[day_name]:
                        # Sum potential values
                        potentials[day_name][stat_key] += reward_points
                        
    return potentials


# --- Log habits ---

@router.post("/logs")
def create_log(payload: LogCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """
    Submit an ephemeral habit log.
    """
    habit = db.query(Habit).filter_by(id=payload.habit_id, user_id=user_id, is_active=True).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found or inactive")

    if habit.type == "quantitative":
        if payload.log_type == "log" and payload.amount is None:
            raise HTTPException(status_code=400, detail="Amount is required for quantitative habit logs")
    elif habit.type == "binary":
        if payload.log_type != "done" and payload.log_type != "skip":
            raise HTTPException(status_code=400, detail="Binary habit logs must be 'done' or 'skip'")

    today = datetime.date.today()
    if habit.type == "binary" and payload.log_type == "done":
        start_dt = datetime.datetime.combine(today, datetime.time.min)
        end_dt = datetime.datetime.combine(today, datetime.time.max)
        existing = db.query(HabitLog).filter(
            HabitLog.user_id == user_id,
            HabitLog.habit_id == habit.id,
            HabitLog.log_type == "done",
            HabitLog.timestamp >= start_dt,
            HabitLog.timestamp <= end_dt
        ).first()
        if existing:
            return {
                "log_id": existing.id,
                "status": "already_logged",
                "affected_stats": habit.point_rewards
            }

    log = HabitLog(
        user_id=user_id,
        habit_id=habit.id,
        log_type=payload.log_type,
        amount=payload.amount,
        unit=habit.unit if habit.type == "quantitative" else None,
        reason=payload.reason
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    # Recalculate daily stats and save to DailyScore (no direct XP awarded for habits logs in V2!)
    score = calculate_daily_score(db, user_id=user_id, date=today)
    update_streaks(db, user_id=user_id, date=today)

    return {
        "log_id": log.id,
        "status": "logged",
        "affected_stats": habit.point_rewards,
        "daily_score_status": score.status
    }


# --- Switch Template ---

@router.post("/profile/template")
def change_profile_template(payload: TemplateOverride, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """
    Override the day's active score template and recalculate.
    """
    t_name = payload.template_name.lower()
    t_map = {
        "semaine": "week",
        "week": "week",
        "weekend": "weekend",
        "recovery": "recup",
        "recup": "recup",
        "sick": "malade",
        "malade": "malade"
    }
    matched_name = t_map.get(t_name, "week")
    
    today = datetime.date.today()
    score = calculate_daily_score(db, user_id=user_id, date=today, template_name=matched_name)
    update_streaks(db, user_id=user_id, date=today)
    
    return {
        "status": "updated",
        "active_template": score.template_used,
        "daily_score_status": score.status
    }


# --- Todos / Primes with Custom XP and Stats Rewards ---

@router.get("/todos")
def get_todos(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """
    List all bounties (todos) for the calling user.
    """
    todos = db.query(Todo).filter_by(user_id=user_id).order_by(Todo.created_at.desc()).all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "stat_reward_1": t.stat_reward_1,
            "points_reward_1": t.points_reward_1,
            "stat_reward_2": t.stat_reward_2,
            "points_reward_2": t.points_reward_2,
            "xp_reward": t.xp_reward,
            "is_completed": t.is_completed,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None
        }
        for t in todos
    ]

@router.post("/todos", status_code=201)
def create_todo(payload: TodoCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """
    Create a custom todo (bounty). Max XP is 40.
    """
    validate_todo_payload(payload)
    todo = Todo(
        user_id=user_id,
        title=payload.title,
        stat_reward_1=payload.stat_reward_1,
        points_reward_1=payload.points_reward_1,
        stat_reward_2=payload.stat_reward_2,
        points_reward_2=payload.points_reward_2,
        xp_reward=payload.xp_reward,
        is_completed=False
    )
    db.add(todo)
    db.commit()
    return {
        "status": "success",
        "todo": {
            "id": todo.id,
            "title": todo.title,
            "xp_reward": todo.xp_reward,
            "is_completed": todo.is_completed
        }
    }

@router.post("/todos/{todo_id}/complete")
def complete_todo(todo_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """
    Complete a todo and award its custom XP. Add stats points to current daily scores.
    """
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
    
    # Recalculate daily scores to instantly add Todo stats points
    today = datetime.date.today()
    calculate_daily_score(db, user_id=user_id, date=today)
    update_streaks(db, user_id=user_id, date=today)

    db.commit()

    return {
        "status": "success",
        "xp_rewarded": todo.xp_reward,
        "levels_gained": levels_gained,
        "new_level": user.level,
        "new_xp": user.xp
    }


# --- No-Todos ---

@router.get("/notodos")
def get_notodos(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """
    List all No-Todos for the calling user.
    """
    notodos = db.query(NoTodo).filter_by(user_id=user_id).order_by(NoTodo.created_at.desc()).all()
    today = datetime.date.today()
    return [
        {
            "id": n.id,
            "title": n.title,
            "failed_today": n.failed_at is not None and n.failed_at.date() == today,
            "created_at": n.created_at.isoformat() if n.created_at else None,
            "failed_at": n.failed_at.isoformat() if n.failed_at else None
        }
        for n in notodos
    ]

@router.post("/notodos", status_code=201)
def create_notodo(payload: NoTodoCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """
    Create a No-Todo rule.
    """
    notodo = NoTodo(
        user_id=user_id,
        title=payload.title
    )
    db.add(notodo)
    db.commit()
    return {
        "status": "success",
        "notodo": {
            "id": notodo.id,
            "title": notodo.title,
            "failed_today": False
        }
    }

@router.post("/notodos/{notodo_id}/fail")
def fail_notodo(notodo_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """
    Mark a No-Todo as failed for today.
    """
    notodo = db.query(NoTodo).filter_by(id=notodo_id, user_id=user_id).first()
    if not notodo:
        raise HTTPException(status_code=404, detail="No-Todo not found")

    notodo.failed_at = datetime.datetime.now()
    db.commit()

    return {
        "status": "success",
        "message": "No-Todo marked as failed for today."
    }


# --- History & Habits Listing ---

@router.get("/habits")
def get_habits(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    habits = db.query(Habit).filter_by(user_id=user_id, is_active=True).all()
    today = datetime.date.today()
    week_start = datetime.datetime.combine(today - datetime.timedelta(days=today.weekday()), datetime.time.min)
    month_start = datetime.datetime.combine(today.replace(day=1), datetime.time.min)
    result = []
    for h in habits:
        completed_this_period = False
        if h.frequency in ("weekly", "monthly"):
            cutoff = week_start if h.frequency == "weekly" else month_start
            completed_this_period = db.query(HabitLog).filter(
                HabitLog.habit_id == h.id,
                HabitLog.user_id == user_id,
                HabitLog.log_type.in_(["done", "log"]),
                HabitLog.timestamp >= cutoff,
            ).first() is not None
        result.append({
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
            "point_rewards": h.point_rewards,
            "daily_cap": h.daily_cap,
            "unit": h.unit,
            "is_active": h.is_active,
            "completed_this_period": completed_this_period,
        })
    return result

class HabitUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    frequency: Optional[str] = None
    scheduled_days: Optional[str] = None
    unit: Optional[str] = None
    point_rewards: Optional[Dict[str, int]] = None
    daily_cap: Optional[int] = None
    is_mandatory: Optional[bool] = None
    is_private: Optional[bool] = None
    is_reportable: Optional[bool] = None

@router.put("/habits/{habit_id}")
def update_habit(habit_id: int, payload: HabitUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    habit = db.query(Habit).filter_by(id=habit_id, user_id=user_id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found.")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(habit, field, value)
    db.commit()
    return {"status": "updated"}

@router.delete("/habits/{habit_id}")
def delete_habit(habit_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    habit = db.query(Habit).filter_by(id=habit_id, user_id=user_id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found.")
    habit.is_active = False
    db.commit()
    return {"status": "deleted"}

@router.post("/habits", status_code=201)
def create_habit(payload: HabitCreate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    validate_habit_payload(payload)
    existing = db.query(Habit).filter_by(user_id=user_id, name=payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Habit with name '{payload.name}' already exists.")

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
        point_rewards=payload.point_rewards,
        daily_cap=payload.daily_cap,
        unit=payload.unit,
        is_active=True
    )
    db.add(habit)
    db.commit()
    db.refresh(habit)
    return {"id": habit.id, "name": habit.name, "status": "success"}

@router.get("/history")
def get_history(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    import calendar
    today = datetime.date.today()
    _, num_days = calendar.monthrange(today.year, today.month)
    start_date = today.replace(day=1)
    
    scores = db.query(DailyScore).filter(
        DailyScore.user_id == user_id,
        DailyScore.date >= start_date,
        DailyScore.date <= today
    ).order_by(DailyScore.date.asc()).all()
    
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
                
        history.append({
            "date": d_str,
            "status": ui_status,
            "label": d.strftime("%d"),
            "weekday": d.weekday()
        })
        
    return history


# --- Softskill Progress Tree Routes ---

@router.get("/softskills")
def get_softskills_tree(db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """
    Get the full softskill tree layout merged with the current user's progress.
    """
    return softskill_service.get_tree_with_progress(db, user_id)


@router.post("/softskills/{softskill_id}/test")
def update_softskill_test(softskill_id: str, payload: SoftskillTestUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """
    Save or update the user's custom success criteria test for a softskill.
    """
    result = softskill_service.update_success_test(db, user_id, softskill_id, payload.success_criteria_test)
    return {"status": "success", "message": "Success criteria test updated", "data": result}


@router.post("/softskills/{softskill_id}/complete")
def toggle_softskill_completion(softskill_id: str, payload: SoftskillCompleteToggle, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """
    Manually mark a softskill as completed or uncompleted.
    Validates that prerequisites are met before allowing completion.
    """
    result = softskill_service.toggle_completion(db, user_id, softskill_id, payload.completed)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"status": "success", "message": "Softskill completion updated", "data": result}


@router.post("/softskills/branches", status_code=201)
def api_create_branch(payload: BranchConfig):
    try:
        return softskill_service.create_branch(payload.key, payload.color, payload.pale_color)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/softskills/branches/{branch_key}")
def api_update_branch(branch_key: str, payload: BranchUpdate):
    try:
        return softskill_service.update_branch(branch_key, payload.new_key, payload.color, payload.pale_color)
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

