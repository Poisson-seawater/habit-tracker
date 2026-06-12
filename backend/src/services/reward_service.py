import logging
import datetime
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException

from src.database.models import User, Reward, Goal, UserSoftskillProgress
from src.services.softskill_service import load_tree_config

logger = logging.getLogger(__name__)

def get_softskill_name(skill_id: str) -> str:
    try:
        config = load_tree_config()
        for s in config.get("skills", []):
            if s.get("id") == skill_id:
                return s.get("name")
    except Exception as e:
        logger.error(f"Error loading softskill name for {skill_id}: {e}")
    return skill_id

def check_reward_lock(db: Session, user_id: int, reward: Reward) -> Tuple[bool, Optional[str]]:
    """
    Checks if a reward is locked.
    Returns (unlocked: bool, lock_reason: Optional[str])
    """
    # 1. Check softskill requirement
    if reward.required_softskill_id:
        # Check if the skill exists in config first. If it does not exist, consider requirement satisfied
        config = load_tree_config()
        skill_exists = any(s.get("id") == reward.required_softskill_id for s in config.get("skills", []))
        if skill_exists:
            progress = (
                db.query(UserSoftskillProgress)
                .filter_by(user_id=user_id, softskill_id=reward.required_softskill_id)
                .first()
            )
            if not progress or not progress.completed:
                skill_name = get_softskill_name(reward.required_softskill_id)
                return False, f"Nécessite la compétence '{skill_name}' complétée."

    # 2. Check goal requirement
    if reward.required_goal_id:
        goal = db.query(Goal).filter_by(id=reward.required_goal_id, user_id=user_id).first()
        if not goal:
            # Goal was deleted (clean cascade logic - though DB should set NULL, just in case)
            return True, None
        if not goal.completed:
            return False, f"Nécessite l'objectif '{goal.title}' complété."

    return True, None

def is_allostasis_available(reward: Reward) -> bool:
    """
    Checks if an allostasis reward is available for purchase in the current period.
    Daily rewards reset at midnight local time, weekly rewards reset Monday midnight local time.
    """
    if reward.category == "regular":
        return True
    if not reward.last_purchased_at:
        return True

    # Treat last_purchased_at as local naive time matching datetime.datetime.now()
    last_purchased = reward.last_purchased_at
    current_time = datetime.datetime.now()

    if reward.category == "allostasis_daily":
        # Available if last purchase was on a previous calendar day
        return last_purchased.date() < current_time.date()

    elif reward.category == "allostasis_weekly":
        # Available if last purchase was in a previous ISO week
        current_year, current_week, _ = current_time.isocalendar()
        last_year, last_week, _ = last_purchased.isocalendar()
        return (last_year, last_week) != (current_year, current_week)

    return True

def purchase_reward(db: Session, user_id: int, reward_id: int) -> dict:
    """
    Executes a purchase of a reward using user gold in an ACID transaction.
    If it is an allostasis reward, the cost is 0 and no gold is deducted.
    """
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    reward = db.query(Reward).filter_by(id=reward_id, user_id=user_id).first()
    if not reward:
        raise HTTPException(status_code=404, detail="Récompense introuvable")

    # 1. Check locks
    unlocked, reason = check_reward_lock(db, user_id, reward)
    if not unlocked:
        raise HTTPException(status_code=400, detail=f"La récompense est verrouillée : {reason}")

    # 2. Check allostasis availability
    if reward.category in ("allostasis_daily", "allostasis_weekly"):
        if not is_allostasis_available(reward):
            raise HTTPException(
                status_code=400,
                detail="Cet item d'allostasie a déjà été validé pour cette période."
            )
    else:
        # 3. Check one-time purchase for regular rewards
        if reward.is_one_time and reward.purchased_count > 0:
            raise HTTPException(status_code=400, detail="Cette récompense unique a déjà été achetée.")

        # 4. Check gold
        if user.gold < reward.gold_cost:
            raise HTTPException(status_code=400, detail="Or insuffisant pour acheter cette récompense.")

        # Deduct gold only for regular rewards
        user.gold -= reward.gold_cost

    # 5. Record purchase
    reward.purchased_count += 1
    reward.last_purchased_at = datetime.datetime.now()

    db.commit()

    return {
        "status": "success",
        "gold_spent": reward.gold_cost if reward.category == "regular" else 0,
        "new_gold": user.gold,
        "purchased_count": reward.purchased_count,
        "last_purchased_at": reward.last_purchased_at.isoformat() if reward.last_purchased_at else None
    }


def get_allostasis_purchases_on_date(db: Session, user_id: int, date: datetime.date) -> list[Reward]:
    """
    Fetches allostasis items (category in ['allostasis_daily', 'allostasis_weekly'])
    that were purchased by a user on a specific date.
    """
    start_dt = datetime.datetime.combine(date, datetime.time.min)
    end_dt = datetime.datetime.combine(date, datetime.time.max)
    
    return (
        db.query(Reward)
        .filter(
            Reward.user_id == user_id,
            Reward.category.in_(["allostasis_daily", "allostasis_weekly"]),
            Reward.last_purchased_at >= start_dt,
            Reward.last_purchased_at <= end_dt
        )
        .all()
    )

