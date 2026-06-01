import datetime
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

from src.database.session import get_db
from src.database.models import User, Habit, HabitLog, PerfectDayTemplate, DailyScore, Streak, Todo, Goal, SubStep, GoalSubStepLink, SubStepDependency
from src.services.score_service import calculate_daily_score, update_streaks, add_user_xp, ALL_12_STATS, DEFAULT_THRESHOLDS

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

class GoalCreate(BaseModel):
    title: str
    description: Optional[str] = None

class SubStepCreate(BaseModel):
    title: str
    gold_reward: Optional[int] = 50
    stats_json: List[str] = []
    blocked_by_ids: Optional[List[int]] = []

class SubStepLinkRequest(BaseModel):
    goal_id: int
    substep_id: int

class DependencyRequest(BaseModel):
    blocked_by_id: int

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


# --- Profile Route ---

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
            # Find dependencies
            dependencies = db.query(SubStepDependency).filter_by(substep_id=s.id).all()
            blocked_by_ids = [dep.blocked_by_id for dep in dependencies]
            
            # Check if strictly blocked (at least one dependency is not completed)
            is_blocked = False
            for blocker_id in blocked_by_ids:
                blocker = db.query(SubStep).filter_by(id=blocker_id).first()
                if blocker and not blocker.completed:
                    is_blocked = True
                    break
                    
            substeps_list.append({
                "id": s.id,
                "title": s.title,
                "gold_reward": s.gold_reward,
                "completed": s.completed,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "stats": s.stats_json or [],
                "blocked_by_ids": blocked_by_ids,
                "is_blocked": is_blocked
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
        gold_reward=payload.gold_reward,
        stats_json=payload.stats_json
    )
    db.add(substep)
    db.flush()  # Generate substep ID

    # Link to Goal
    link = GoalSubStepLink(goal_id=goal_id, substep_id=substep.id)
    db.add(link)

    # Add Dependencies
    if payload.blocked_by_ids:
        for blocker_id in payload.blocked_by_ids:
            blocker = db.query(SubStep).filter_by(id=blocker_id, user_id=user_id).first()
            if blocker:
                dep = SubStepDependency(substep_id=substep.id, blocked_by_id=blocker.id)
                db.add(dep)

    db.commit()
    db.refresh(substep)
    
    return {
        "status": "success",
        "substep": {
            "id": substep.id,
            "title": substep.title,
            "gold_reward": substep.gold_reward,
            "stats": substep.stats_json
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

@router.post("/substeps/{substep_id}/dependency")
def add_dependency(substep_id: int, payload: DependencyRequest, db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)):
    """
    Add a blocking dependency relation between two substeps.
    """
    substep = db.query(SubStep).filter_by(id=substep_id, user_id=user_id).first()
    blocker = db.query(SubStep).filter_by(id=payload.blocked_by_id, user_id=user_id).first()
    
    if not substep or not blocker:
        raise HTTPException(status_code=404, detail="Substep not found")
        
    existing = db.query(SubStepDependency).filter_by(substep_id=substep.id, blocked_by_id=blocker.id).first()
    if existing:
        return {"status": "already_exists"}
        
    dep = SubStepDependency(substep_id=substep.id, blocked_by_id=blocker.id)
    db.add(dep)
    db.commit()
    return {"status": "success"}

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

    # Strict Block Check
    dependencies = db.query(SubStepDependency).filter_by(substep_id=substep.id).all()
    for dep in dependencies:
        blocker = db.query(SubStep).filter_by(id=dep.blocked_by_id).first()
        if blocker and not blocker.completed:
            raise HTTPException(
                status_code=400,
                detail=f"Cette sous-étape est bloquée par : '{blocker.title}'."
            )

    # Complete substep
    substep.completed = True
    substep.completed_at = datetime.datetime.utcnow()
    
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
            g.completed_at = datetime.datetime.utcnow()
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
def get_daily_stats_potentials(db: Session = Depends(get_db)):
    """
    Calculate potential statistic totals group by day of the week.
    Scheduled days represented by 0 (Sunday) to 6 (Saturday).
    """
    habits = db.query(Habit).filter_by(is_active=True).all()
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
    habit = db.query(Habit).filter_by(id=payload.habit_id, is_active=True).first()
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
    todo.completed_at = datetime.datetime.utcnow()
    
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


# --- History & Habits Listing ---

@router.get("/habits")
def get_habits(db: Session = Depends(get_db)):
    habits = db.query(Habit).filter_by(is_active=True).all()
    result = []
    for h in habits:
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
            "is_active": h.is_active
        })
    return result

@router.post("/habits", status_code=201)
def create_habit(payload: HabitCreate, db: Session = Depends(get_db)):
    existing = db.query(Habit).filter_by(name=payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Habit with name '{payload.name}' already exists.")

    habit = Habit(
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
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=29)
    
    scores = db.query(DailyScore).filter(
        DailyScore.user_id == user_id,
        DailyScore.date >= start_date,
        DailyScore.date <= today
    ).order_by(DailyScore.date.asc()).all()
    
    score_map = {score.date.isoformat(): score.status for score in scores}
    
    history = []
    for i in range(30):
        d = start_date + datetime.timedelta(days=i)
        d_str = d.isoformat()
        status = score_map.get(d_str, "Incomplet")
        
        ui_status = "failed"
        if status == "Perfect":
            ui_status = "perfect"
            
        history.append({
            "date": d_str,
            "status": ui_status,
            "label": d.strftime("%d/%m")
        })
        
    return history
