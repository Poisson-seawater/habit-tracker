import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date, ForeignKey, JSON, UniqueConstraint
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

    logs = relationship("HabitLog", back_populates="user", cascade="all, delete-orphan")
    scores = relationship("DailyScore", back_populates="user", cascade="all, delete-orphan")
    streaks = relationship("Streak", back_populates="user", cascade="all, delete-orphan")
    todos = relationship("Todo", back_populates="user", cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan")
    substeps = relationship("SubStep", back_populates="user", cascade="all, delete-orphan")
    perfect_day_templates = relationship("PerfectDayTemplate", back_populates="user", cascade="all, delete-orphan")
    habits = relationship("Habit", back_populates="user", cascade="all, delete-orphan")
    notodos = relationship("NoTodo", back_populates="user", cascade="all, delete-orphan")
    rewards = relationship("Reward", back_populates="user", cascade="all, delete-orphan")


class Habit(Base):
    __tablename__ = "habits"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uix_user_habit_name"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    type = Column(String, nullable=False)  # "binary" or "quantitative"
    frequency = Column(String, default="daily")  # "daily", "weekly", "custom"
    scheduled_days = Column(String, default="0,1,2,3,4,5,6")  # Comma-separated Mon-Sun (0=Sun, 1=Mon, ..., 6=Sat)
    reminder_time = Column(String, nullable=True)  # "HH:MM"
    is_private = Column(Boolean, default=False)
    is_reportable = Column(Boolean, default=True)
    is_mandatory = Column(Boolean, default=False)
    point_rewards = Column(JSON, nullable=False)  # dict mapping stats e.g. {"discipline": 2, "force": 3}
    daily_cap = Column(Integer, nullable=True)  # Cap on points for quantitative habits
    unit = Column(String, nullable=True)  # Unit e.g. "min", "km"
    is_active = Column(Boolean, default=True)
    deactivated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)

    user = relationship("User", back_populates="habits")
    logs = relationship("HabitLog", back_populates="habit", cascade="all, delete-orphan")


class HabitLog(Base):
    __tablename__ = "habit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    habit_id = Column(Integer, ForeignKey("habits.id", ondelete="CASCADE"), nullable=False)
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
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    template_name = Column(String, nullable=False)  # "week", "weekend", "recup", "malade"
    thresholds_json = Column(JSON, nullable=False)  # dict mapping stats e.g. {"force": 16, "mobilité": 4}

    user = relationship("User", back_populates="perfect_day_templates")


class DailyScore(Base):
    __tablename__ = "daily_scores"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    status = Column(String, default="Failed")  # "Failed", "Acceptable", "Perfect"
    template_used = Column(String, nullable=False)  # "week", "weekend", "recup", "malade"
    actual_stats = Column(JSON, nullable=False)  # e.g., {"discipline": 6, "force": 12}

    user = relationship("User", back_populates="scores")


class Streak(Base):
    __tablename__ = "streaks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    streak_type = Column(String, nullable=False)  # "Acceptable", "Perfect", or "habit:[habit_id]"
    current_streak = Column(Integer, default=0)
    max_streak = Column(Integer, default=0)
    last_incremented = Column(Date, nullable=True)

    user = relationship("User", back_populates="streaks")


class Todo(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    stat_reward_1 = Column(String, nullable=True)
    points_reward_1 = Column(Integer, default=0)
    stat_reward_2 = Column(String, nullable=True)
    points_reward_2 = Column(Integer, default=0)
    xp_reward = Column(Integer, default=10)  # Custom up to 40 XP
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.now)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="todos")


class NoTodo(Base):
    __tablename__ = "notodos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.now)
    failed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="notodos")


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now)

    user = relationship("User", back_populates="goals")
    substep_links = relationship("GoalSubStepLink", back_populates="goal", cascade="all, delete-orphan")


class SubStep(Base):
    __tablename__ = "substeps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    gold_reward = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    description = Column(Text, nullable=True)
    stats_json = Column(JSON, nullable=True)  # List of related stats e.g. ["force", "finance"]
    execution_order = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.datetime.now)

    user = relationship("User", back_populates="substeps")
    goal_links = relationship("GoalSubStepLink", back_populates="substep", cascade="all, delete-orphan")

class GoalSubStepLink(Base):
    __tablename__ = "goal_substep_links"

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id", ondelete="CASCADE"), nullable=False)
    substep_id = Column(Integer, ForeignKey("substeps.id", ondelete="CASCADE"), nullable=False)

    goal = relationship("Goal", back_populates="substep_links")
    substep = relationship("SubStep", back_populates="goal_links")


class UserSoftskillProgress(Base):
    __tablename__ = "user_softskill_progress"
    __table_args__ = (UniqueConstraint("user_id", "softskill_id", name="uix_user_softskill"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    softskill_id = Column(String(100), nullable=False)
    success_criteria_test = Column(Text, nullable=True)
    current_level = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    user = relationship("User", backref="softskill_progress")


class Reward(Base):
    __tablename__ = "rewards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    gold_cost = Column(Integer, nullable=False, default=0)
    required_softskill_id = Column(String(100), nullable=True)
    required_goal_id = Column(Integer, ForeignKey("goals.id", ondelete="SET NULL"), nullable=True)
    is_one_time = Column(Boolean, default=False)
    purchased_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.now)
    category = Column(String(50), nullable=False, default="regular")
    last_purchased_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="rewards")
    required_goal = relationship("Goal")

