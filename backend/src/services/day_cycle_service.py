import datetime

from sqlalchemy.orm import Session

from src.database.models import DayCyclePolicy, User


NORMAL_RECOMMENDATION = {
    "label": "Semaine normale",
    "hustle": "2-3",
    "hustle_min": 2,
    "hustle_max": 3,
    "rest": "1",
    "rest_min": 1,
    "rest_max": 1,
}

CHILL_RECOMMENDATION = {
    "label": "Semaine chill",
    "hustle": "1-2",
    "hustle_min": 1,
    "hustle_max": 2,
    "rest": "2",
    "rest_min": 2,
    "rest_max": 2,
}


def monday_of_week(date_value: datetime.date) -> datetime.date:
    return date_value - datetime.timedelta(days=date_value.weekday())


def user_install_date(user: User) -> datetime.date:
    if user.created_at:
        return user.created_at.date()
    return datetime.date.today()


def ensure_default_cycle_policy(db: Session, user: User) -> DayCyclePolicy:
    existing = (
        db.query(DayCyclePolicy)
        .filter(DayCyclePolicy.user_id == user.id)
        .order_by(
            DayCyclePolicy.effective_from.asc(),
            DayCyclePolicy.created_at.asc(),
            DayCyclePolicy.id.asc(),
        )
        .first()
    )
    if existing:
        return existing

    install_date = user_install_date(user)
    policy = DayCyclePolicy(
        user_id=user.id,
        anchor_date=monday_of_week(install_date),
        effective_from=install_date,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def get_cycle_policies(db: Session, user_id: int) -> list[DayCyclePolicy]:
    return (
        db.query(DayCyclePolicy)
        .filter(DayCyclePolicy.user_id == user_id)
        .order_by(
            DayCyclePolicy.effective_from.asc(),
            DayCyclePolicy.created_at.asc(),
            DayCyclePolicy.id.asc(),
        )
        .all()
    )


def resolve_cycle_policy(
    policies: list[DayCyclePolicy], date_value: datetime.date
) -> DayCyclePolicy:
    if not policies:
        raise ValueError("No cycle policies available.")

    selected = policies[0]
    for policy in policies:
        if policy.effective_from <= date_value:
            selected = policy
        else:
            break
    return selected


def cycle_info_for_date(
    policy: DayCyclePolicy, date_value: datetime.date
) -> dict:
    week_start = monday_of_week(date_value)
    weeks_since_anchor = (week_start - policy.anchor_date).days // 7
    cycle_index = weeks_since_anchor % 4
    week_type = "chill" if cycle_index == 3 else "normal"
    recommendation = (
        CHILL_RECOMMENDATION if week_type == "chill" else NORMAL_RECOMMENDATION
    )
    return {
        "cycle_week_type": week_type,
        "cycle_recommendation": recommendation,
        "cycle_week_start": week_start,
        "cycle_week_index": cycle_index + 1,
        "cycle_policy_id": policy.id,
        "cycle_policy_anchor_date": policy.anchor_date,
        "cycle_policy_effective_from": policy.effective_from,
    }


def active_cycle_payload(policy: DayCyclePolicy, date_value: datetime.date) -> dict:
    info = cycle_info_for_date(policy, date_value)
    return {
        "id": policy.id,
        "anchor_date": policy.anchor_date.isoformat(),
        "effective_from": policy.effective_from.isoformat(),
        "created_at": policy.created_at.isoformat() if policy.created_at else None,
        "today": date_value.isoformat(),
        "normalized_week_start": monday_of_week(policy.anchor_date).isoformat(),
        "cycle_week_type": info["cycle_week_type"],
        "cycle_recommendation": info["cycle_recommendation"],
        "cycle_week_start": info["cycle_week_start"].isoformat(),
        "cycle_week_index": info["cycle_week_index"],
    }
