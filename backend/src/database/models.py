import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    JSON,
    UniqueConstraint,
    Float,
)
from sqlalchemy.orm import relationship
from src.database.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True)
    chat_id = Column(String, nullable=True, unique=True, index=True)
    xp = Column(Integer, default=0)
    level = Column(Integer, default=1)
    gold = Column(Integer, default=0)  # Total accumulated gold
    created_at = Column(DateTime, default=datetime.datetime.now)
    pinned_substeps = Column(JSON, nullable=True, default=list)
    pinned_softskills = Column(JSON, nullable=True, default=list)
    pinned_goals = Column(JSON, nullable=True, default=list)
    password_hash = Column(Text, nullable=True)
    password_salt = Column(String, nullable=True)
    password_changed_at = Column(DateTime, nullable=True)
    is_admin = Column(Boolean, default=False, nullable=False)

    # Google Calendar & Tasks Integration columns
    google_refresh_token = Column(Text, nullable=True)
    google_access_token = Column(Text, nullable=True)
    google_token_expiry = Column(DateTime, nullable=True)
    google_calendar_id = Column(String, nullable=True)
    google_tasks_list_id = Column(String, nullable=True)

    logs = relationship("HabitLog", back_populates="user", cascade="all, delete-orphan")
    scores = relationship(
        "DailyScore", back_populates="user", cascade="all, delete-orphan"
    )
    streaks = relationship(
        "Streak", back_populates="user", cascade="all, delete-orphan"
    )
    todos = relationship("Todo", back_populates="user", cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan")
    substeps = relationship(
        "SubStep", back_populates="user", cascade="all, delete-orphan"
    )
    perfect_day_templates = relationship(
        "PerfectDayTemplate", back_populates="user", cascade="all, delete-orphan"
    )
    habits = relationship("Habit", back_populates="user", cascade="all, delete-orphan")
    notodos = relationship(
        "NoTodo", back_populates="user", cascade="all, delete-orphan"
    )
    notodo_logs = relationship(
        "NoTodoLog", back_populates="user", cascade="all, delete-orphan"
    )
    day_cycle_policies = relationship(
        "DayCyclePolicy", back_populates="user", cascade="all, delete-orphan"
    )
    rewards = relationship(
        "Reward", back_populates="user", cascade="all, delete-orphan"
    )
    biological_zones = relationship(
        "BiologicalZone", back_populates="user", cascade="all, delete-orphan"
    )
    agenda_placements = relationship(
        "DailyAgendaPlacement", back_populates="user", cascade="all, delete-orphan"
    )
    auth_sessions = relationship(
        "AuthSession", back_populates="user", cascade="all, delete-orphan"
    )


class AuthDevice(Base):
    __tablename__ = "auth_devices"

    id = Column(Integer, primary_key=True, index=True)
    device_token_hash = Column(String(64), nullable=False, unique=True, index=True)
    display_name = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending", index=True)
    user_agent = Column(Text, nullable=True)
    created_ip = Column(String, nullable=True)
    first_seen_at = Column(DateTime, default=datetime.datetime.now, nullable=False)
    last_seen_at = Column(DateTime, default=datetime.datetime.now, nullable=False)
    approved_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    approved_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_token_hash = Column(String(64), nullable=False, unique=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_id = Column(
        Integer,
        ForeignKey("auth_devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, default=datetime.datetime.now, nullable=False)
    last_seen_at = Column(DateTime, default=datetime.datetime.now, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    revoked_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="auth_sessions")
    device = relationship("AuthDevice")


class Habit(Base):
    __tablename__ = "habits"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uix_user_habit_name"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    type = Column(String, nullable=False)  # "binary" or "quantitative"
    frequency = Column(
        String, default="daily"
    )  # "daily", "monthly", "custom", "specific_days"
    scheduled_days = Column(
        String, default="0,1,2,3,4,5,6"
    )  # Comma-separated Mon-Sun (0=Sun, 1=Mon, ..., 6=Sat)
    reminder_time = Column(String, nullable=True)  # "HH:MM"
    is_private = Column(Boolean, default=False)
    is_reportable = Column(Boolean, default=True)
    is_mandatory = Column(Boolean, default=False)
    daily_cap = Column(Integer, nullable=True)  # Cap on points for quantitative habits
    daily_target = Column(
        Integer, nullable=True
    )  # Cible de répétitions/jour (affichage X/N) ; None = 1
    unit = Column(String, nullable=True)  # Unit e.g. "min", "km"
    is_active = Column(Boolean, default=True)
    deactivated_at = Column(DateTime, nullable=True)
    effort_type = Column(
        String, nullable=True
    )  # "musculaire", "cerveau", "emotionnel_social", "creatif_divergent", "repos"
    effort_duration = Column(Float, default=1.0, nullable=False)
    source_type = Column(String, nullable=True, default="manual")
    source_ref = Column(String, nullable=True)
    auto_managed = Column(Boolean, default=False, nullable=False)
    archived_at = Column(DateTime, nullable=True)
    agenda_duration_minutes = Column(Integer, nullable=True)
    agenda_placeable = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.now)

    user = relationship("User", back_populates="habits")
    logs = relationship(
        "HabitLog", back_populates="habit", cascade="all, delete-orphan"
    )
    agenda_placements = relationship(
        "DailyAgendaPlacement", back_populates="habit", cascade="all, delete-orphan"
    )


class HabitLog(Base):
    __tablename__ = "habit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    habit_id = Column(
        Integer, ForeignKey("habits.id", ondelete="CASCADE"), nullable=False
    )
    timestamp = Column(DateTime, default=datetime.datetime.now)
    log_type = Column(String, nullable=False)  # "done", "skip", "log"
    amount = Column(Integer, nullable=True)  # For quantitative logs
    unit = Column(String, nullable=True)  # For quantitative logs e.g. "min", "km"
    reason = Column(String, nullable=True)  # Reason for skips

    user = relationship("User", back_populates="logs")
    habit = relationship("Habit", back_populates="logs")


class PerfectDayTemplate(Base):
    __tablename__ = "perfect_day_templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    template_name = Column(String, nullable=False)  # "rest", "regular", "hustle"
    focus_hours = Column(Float, default=6.0, nullable=False)
    ceilings_json = Column(JSON, nullable=True)
    min_rest_hours = Column(Float, default=8.0, nullable=False)
    agenda_json = Column(JSON, nullable=True)

    user = relationship("User", back_populates="perfect_day_templates")


class BiologicalZone(Base):
    __tablename__ = "biological_zones"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    zone_name = Column(String, nullable=False)
    zone_type = Column(String, nullable=False)
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=False)
    color = Column(String, nullable=True)
    display_order = Column(Integer, default=0, nullable=False)

    user = relationship("User", back_populates="biological_zones")


class DailyAgendaPlacement(Base):
    __tablename__ = "daily_agenda_placements"
    __table_args__ = (
        UniqueConstraint("user_id", "date", "habit_id", name="uix_daily_agenda_slot"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date = Column(Date, nullable=False, index=True)
    habit_id = Column(
        Integer,
        ForeignKey("habits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_time = Column(String, nullable=True)
    duration_minutes = Column(Integer, nullable=False)
    status = Column(String, default="planned", nullable=False)
    actual_minutes = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(
        DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now
    )

    user = relationship("User", back_populates="agenda_placements")
    habit = relationship("Habit", back_populates="agenda_placements")


class DailyScore(Base):
    __tablename__ = "daily_scores"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    date = Column(Date, nullable=False, index=True)
    status = Column(String, default="Failed")  # "Failed", "Acceptable", "Perfect"
    template_used = Column(
        String, nullable=False
    )  # "week", "weekend", "recup", "malade"

    user = relationship("User", back_populates="scores")


class Streak(Base):
    __tablename__ = "streaks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    streak_type = Column(
        String, nullable=False
    )  # "Acceptable", "Perfect", or "habit:[habit_id]"
    current_streak = Column(Integer, default=0)
    max_streak = Column(Integer, default=0)
    last_incremented = Column(Date, nullable=True)

    user = relationship("User", back_populates="streaks")


class Todo(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String, nullable=False)
    xp_reward = Column(Integer, default=10)  # Custom up to 40 XP
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.now)
    completed_at = Column(DateTime, nullable=True)
    do_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)

    # Google API references
    google_event_id = Column(String, nullable=True)  # Calendar event, from do_date
    google_task_id = Column(String, nullable=True)  # Google Task (cochable), from due_date

    user = relationship("User", back_populates="todos")


class NoTodo(Base):
    __tablename__ = "notodos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.now)
    failed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="notodos")
    logs = relationship("NoTodoLog", back_populates="notodo", passive_deletes=True)


class NoTodoLog(Base):
    __tablename__ = "notodo_logs"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "notodo_id",
            "date",
            name="uix_notodo_log_user_rule_date",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notodo_id = Column(
        Integer,
        ForeignKey("notodos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title_snapshot = Column(String, nullable=False)
    date = Column(Date, nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.now, nullable=False)

    user = relationship("User", back_populates="notodo_logs")
    notodo = relationship("NoTodo", back_populates="logs")


class DayCyclePolicy(Base):
    __tablename__ = "day_cycle_policies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    anchor_date = Column(Date, nullable=False, index=True)
    effective_from = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.now, nullable=False)

    user = relationship("User", back_populates="day_cycle_policies")


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)
    do_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)

    user = relationship("User", back_populates="goals")
    substep_links = relationship(
        "GoalSubStepLink", back_populates="goal", cascade="all, delete-orphan"
    )


class SubStep(Base):
    __tablename__ = "substeps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String, nullable=False)
    gold_reward = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    description = Column(Text, nullable=True)
    execution_order = Column(Integer, default=1)
    is_life_lore = Column(Boolean, default=False, nullable=False)
    effort_type = Column(
        String, nullable=True
    )  # "musculaire", "cerveau", "emotionnel_social", "creatif_divergent", "repos"
    effort_duration = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.now)

    user = relationship("User", back_populates="substeps")
    goal_links = relationship(
        "GoalSubStepLink", back_populates="substep", cascade="all, delete-orphan"
    )


class GoalSubStepLink(Base):
    __tablename__ = "goal_substep_links"
    __table_args__ = (
        UniqueConstraint("goal_id", "substep_id", name="uix_goal_substep"),
    )

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(
        Integer, ForeignKey("goals.id", ondelete="CASCADE"), nullable=False
    )
    substep_id = Column(
        Integer, ForeignKey("substeps.id", ondelete="CASCADE"), nullable=False
    )
    execution_order = Column(Integer, default=1)  # Per-goal ordering for this substep

    goal = relationship("Goal", back_populates="substep_links")
    substep = relationship("SubStep", back_populates="goal_links")


class UserSoftskillProgress(Base):
    __tablename__ = "user_softskill_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "softskill_id", name="uix_user_softskill"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    softskill_id = Column(String(100), nullable=False)
    success_criteria_test = Column(Text, nullable=True)
    current_level = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    updated_at = Column(
        DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now
    )

    user = relationship("User", backref="softskill_progress")


class Reward(Base):
    __tablename__ = "rewards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    gold_cost = Column(Integer, nullable=False, default=0)
    required_softskill_id = Column(String(100), nullable=True)
    required_goal_id = Column(
        Integer, ForeignKey("goals.id", ondelete="SET NULL"), nullable=True
    )
    is_one_time = Column(Boolean, default=False)
    purchased_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.now)
    category = Column(String(50), nullable=False, default="regular")
    last_purchased_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="rewards")
    required_goal = relationship("Goal")


class RemoteOperation(Base):
    __tablename__ = "remote_operations"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uix_remote_operation_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    idempotency_key = Column(String(100), nullable=False)
    request_hash = Column(String(64), nullable=False)
    method = Column(String(10), nullable=False)
    path = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="in_progress")
    http_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.now,
        onupdate=datetime.datetime.now,
        nullable=False,
    )
