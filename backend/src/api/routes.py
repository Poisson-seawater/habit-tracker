import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
from pydantic import BaseModel

from src.database.session import get_db
from src.database.models import User, Habit, HabitLog, DayTemplate, DailyScore, Streak
from src.services.score_service import calculate_daily_score, update_streaks, ALL_12_STATS

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

# --- API Routes ---

@router.get("/profile")
def get_profile(db: Session = Depends(get_db)):
    """
    Fetch the solo user's stats, level, active daily template, 
    and progress towards daily score thresholds.
    """
    user = db.query(User).filter_by(id=1).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    today = datetime.date.today()
    # Ensure a DailyScore exists for today
    score = db.query(DailyScore).filter_by(user_id=user.id, date=today).first()
    if not score:
        score = calculate_daily_score(db, user_id=user.id, date=today)

    template = db.query(DayTemplate).filter_by(id=score.active_template_id).first()
    if not template:
        # Fallback
        template = db.query(DayTemplate).filter_by(id=1).first()

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
        "active_template": template.name if template else "Semaine",
        "completed_habit_ids": completed_habit_ids,
        "scores": {
            "status": score.status,
            "acceptable_day_validated": score.status in ["Acceptable", "Perfect"],
            "perfect_day_validated": score.status == "Perfect"
        },
        "stats": score.actual_stats,
        "thresholds": {
            "acceptable": template.acceptable_thresholds if template else {},
            "perfect": template.perfect_thresholds if template else {}
        }
    }

@router.get("/habits")
def get_habits(db: Session = Depends(get_db)):
    """
    List all configured and active habits.
    """
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
    """
    Create a new habit configuration.
    """
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
    return {
        "id": habit.id,
        "name": habit.name,
        "status": "success"
    }

@router.get("/streaks")
def get_streaks(db: Session = Depends(get_db)):
    """
    Retrieve current and historical streaks.
    """
    user_id = 1
    streaks = db.query(Streak).filter_by(user_id=user_id).all()
    result = []
    for s in streaks:
        result.append({
            "streak_type": s.streak_type,
            "current_streak": s.current_streak,
            "max_streak": s.max_streak,
            "last_incremented": str(s.last_incremented) if s.last_incremented else None
        })
    return result

@router.post("/logs")
def create_log(payload: LogCreate, db: Session = Depends(get_db)):
    """
    Submit a habit check-in directly from the web dashboard or API client.
    """
    user_id = 1
    habit = db.query(Habit).filter_by(id=payload.habit_id, is_active=True).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found or inactive")

    # Validate quantitative parameters
    if habit.type == "quantitative":
        if payload.log_type == "log" and payload.amount is None:
            raise HTTPException(status_code=400, detail="Amount is required for quantitative habit logs")
    elif habit.type == "binary":
        if payload.log_type != "done" and payload.log_type != "skip":
            raise HTTPException(status_code=400, detail="Binary habit logs must be 'done' or 'skip'")

    # Double logging prevention for binary logs
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
            # Safely merge / ignore double check-in
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

    # Recalculate scores and streaks
    calculate_daily_score(db, user_id=user_id, date=today)
    update_streaks(db, user_id=user_id, date=today)

    return {
        "log_id": log.id,
        "status": "logged",
        "affected_stats": habit.point_rewards
    }

class TemplateOverride(BaseModel):
    template_name: str

@router.post("/profile/template")
def change_profile_template(payload: TemplateOverride, db: Session = Depends(get_db)):
    """
    Override the day's active score template.
    """
    user_id = 1
    # Resolve template case-insensitively
    t_name = payload.template_name.lower()
    
    # Map friendly names
    t_map = {
        "semaine": "Semaine",
        "weekend": "Weekend",
        "recovery": "Récupération",
        "sick": "Malade",
        "malade": "Malade",
        "récupération": "Récupération",
        "recuperation": "Récupération"
    }
    
    matched_name = t_map.get(t_name, payload.template_name)
    
    template = db.query(DayTemplate).filter(DayTemplate.name.collate("NOCASE") == matched_name).first()
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{payload.template_name}' not found")
        
    today = datetime.date.today()
    score = calculate_daily_score(db, user_id=user_id, date=today, template_id=template.id)
    update_streaks(db, user_id=user_id, date=today)
    
    return {
        "status": "updated",
        "active_template": template.name
    }

@router.get("/history")
def get_history(db: Session = Depends(get_db)):
    """
    Fetch the last 30 days of daily scores.
    """
    user_id = 1
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
        
        # Map DB statuses to UI statuses
        ui_status = "failed"
        if status in ["Perfect", "Parfait"]:
            ui_status = "perfect"
        elif status in ["Acceptable"]:
            ui_status = "acceptable"
            
        history.append({
            "date": d_str,
            "status": ui_status,
            "label": d.strftime("%d/%m")
        })
        
    return history
