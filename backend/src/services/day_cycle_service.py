import datetime

from sqlalchemy.orm import Session

from src.database.models import DailyScore, DayCyclePolicy, DayTypeOverride, User


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
    "sick": "rest",
    "malade": "rest",
    "hustle": "hustle",
    "rush": "hustle",
}
WEEKDAY_KEYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)
DEFAULT_NORMAL_WEEK = {
    "monday": "regular",
    "tuesday": "regular",
    "wednesday": "regular",
    "thursday": "regular",
    "friday": "regular",
    "saturday": "hustle",
    "sunday": "rest",
}
DEFAULT_CHILL_WEEK = {
    "monday": "regular",
    "tuesday": "regular",
    "wednesday": "regular",
    "thursday": "regular",
    "friday": "regular",
    "saturday": "regular",
    "sunday": "rest",
}


def monday_of_week(date_value: datetime.date) -> datetime.date:
    return date_value - datetime.timedelta(days=date_value.weekday())


def user_install_date(user: User) -> datetime.date:
    if user.created_at:
        return user.created_at.date()
    return datetime.date.today()


def normalize_week_pattern(value, default: dict[str, str]) -> dict[str, str]:
    if not isinstance(value, dict):
        return dict(default)
    normalized = {}
    for weekday in WEEKDAY_KEYS:
        day_type = str(value.get(weekday) or "").strip().lower()
        normalized[weekday] = day_type if day_type in DAY_TYPES else default[weekday]
    return normalized


def validate_week_pattern(value, field_name: str) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != set(WEEKDAY_KEYS):
        raise ValueError(
            f"{field_name} must contain exactly: {', '.join(WEEKDAY_KEYS)}."
        )
    invalid = {
        str(day_type)
        for day_type in value.values()
        if str(day_type).strip().lower() not in DAY_TYPES
    }
    if invalid:
        raise ValueError(
            f"{field_name} contains invalid day types: {', '.join(sorted(invalid))}."
        )
    return {weekday: str(value[weekday]).strip().lower() for weekday in WEEKDAY_KEYS}


def policy_week_patterns(policy: DayCyclePolicy) -> tuple[dict, dict]:
    return (
        normalize_week_pattern(policy.normal_week_json, DEFAULT_NORMAL_WEEK),
        normalize_week_pattern(policy.chill_week_json, DEFAULT_CHILL_WEEK),
    )


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
        normal_week_json=dict(DEFAULT_NORMAL_WEEK),
        chill_week_json=dict(DEFAULT_CHILL_WEEK),
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


def pending_cycle_policy(
    policies: list[DayCyclePolicy], date_value: datetime.date
) -> DayCyclePolicy | None:
    return next(
        (policy for policy in policies if policy.effective_from > date_value), None
    )


def _week_recommendation(label: str, pattern: dict[str, str]) -> dict:
    hustle_count = sum(day_type == "hustle" for day_type in pattern.values())
    rest_count = sum(day_type == "rest" for day_type in pattern.values())
    return {
        "label": label,
        "hustle": str(hustle_count),
        "hustle_min": hustle_count,
        "hustle_max": hustle_count,
        "rest": str(rest_count),
        "rest_min": rest_count,
        "rest_max": rest_count,
    }


def cycle_info_for_date(policy: DayCyclePolicy, date_value: datetime.date) -> dict:
    week_start = monday_of_week(date_value)
    weeks_since_anchor = (week_start - policy.anchor_date).days // 7
    cycle_index = weeks_since_anchor % 4
    week_type = "chill" if cycle_index == 3 else "normal"
    normal_week, chill_week = policy_week_patterns(policy)
    pattern = chill_week if week_type == "chill" else normal_week
    recommendation = _week_recommendation(
        "Semaine moins intense" if week_type == "chill" else "Semaine normale",
        pattern,
    )
    return {
        "cycle_week_type": week_type,
        "cycle_recommendation": recommendation,
        "cycle_week_start": week_start,
        "cycle_week_index": cycle_index + 1,
        "cycle_policy_id": policy.id,
        "cycle_policy_anchor_date": policy.anchor_date,
        "cycle_policy_effective_from": policy.effective_from,
        "planned_day_type": pattern[WEEKDAY_KEYS[date_value.weekday()]],
    }


def resolve_planned_day_type(
    db: Session, user_id: int, date_value: datetime.date
) -> str:
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        return "regular"
    ensure_default_cycle_policy(db, user)
    policy = resolve_cycle_policy(get_cycle_policies(db, user_id), date_value)
    return cycle_info_for_date(policy, date_value)["planned_day_type"]


def resolve_effective_day_type(
    db: Session, user_id: int, date_value: datetime.date
) -> str:
    today = datetime.date.today()
    if date_value < today:
        score = db.query(DailyScore).filter_by(user_id=user_id, date=date_value).first()
        if score:
            return DAY_TYPE_ALIASES.get(str(score.template_used).lower(), "regular")

    override = (
        db.query(DayTypeOverride).filter_by(user_id=user_id, date=date_value).first()
    )
    if override and override.day_type in DAY_TYPES:
        return override.day_type
    return resolve_planned_day_type(db, user_id, date_value)


def policy_payload(policy: DayCyclePolicy, date_value: datetime.date) -> dict:
    info = cycle_info_for_date(policy, date_value)
    normal_week, chill_week = policy_week_patterns(policy)
    return {
        "id": policy.id,
        "anchor_date": policy.anchor_date.isoformat(),
        "effective_from": policy.effective_from.isoformat(),
        "created_at": policy.created_at.isoformat() if policy.created_at else None,
        "normal_week": normal_week,
        "chill_week": chill_week,
        "cycle_week_type": info["cycle_week_type"],
        "cycle_recommendation": info["cycle_recommendation"],
        "cycle_week_start": info["cycle_week_start"].isoformat(),
        "cycle_week_index": info["cycle_week_index"],
        "planned_day_type": info["planned_day_type"],
    }


def active_cycle_payload(
    policy: DayCyclePolicy,
    date_value: datetime.date,
    pending_policy: DayCyclePolicy | None = None,
) -> dict:
    payload = policy_payload(policy, date_value)
    payload.update(
        {
            "today": date_value.isoformat(),
            "normalized_week_start": monday_of_week(policy.anchor_date).isoformat(),
            "pending_policy": (
                policy_payload(pending_policy, pending_policy.effective_from)
                if pending_policy
                else None
            ),
        }
    )
    return payload
