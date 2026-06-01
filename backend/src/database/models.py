import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date, ForeignKey, JSON
from sqlalchemy.orm import relationship
from src.database.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True)
    chat_id = Column(String, nullable=True, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    logs = relationship("HabitLog", back_populates="user", cascade="all, delete-orphan")
    scores = relationship("DailyScore", back_populates="user", cascade="all, delete-orphan")
    streaks = relationship("Streak", back_populates="user", cascade="all, delete-orphan")


class Habit(Base):
    __tablename__ = "habits"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
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

    logs = relationship("HabitLog", back_populates="habit", cascade="all, delete-orphan")


class HabitLog(Base):
    __tablename__ = "habit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    habit_id = Column(Integer, ForeignKey("habits.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    log_type = Column(String, nullable=False)  # "done", "skip", "log"
    amount = Column(Integer, nullable=True)  # For quantitative logs
    unit = Column(String, nullable=True)  # For quantitative logs e.g. "min", "km"
    reason = Column(String, nullable=True)  # Reason for skips

    user = relationship("User", back_populates="logs")
    habit = relationship("Habit", back_populates="logs")


class DayTemplate(Base):
    __tablename__ = "day_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)  # e.g., "Semaine", "Weekend", "Récupération", "Malade"
    acceptable_thresholds = Column(JSON, nullable=False)  # e.g., {"discipline": 5, "force": 10}
    perfect_thresholds = Column(JSON, nullable=False)  # e.g., {"discipline": 8, "force": 20}

    scores = relationship("DailyScore", back_populates="active_template")


class DailyScore(Base):
    __tablename__ = "daily_scores"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    status = Column(String, default="Failed")  # "Failed", "Acceptable", "Perfect"
    active_template_id = Column(Integer, ForeignKey("day_templates.id"), nullable=False)
    actual_stats = Column(JSON, nullable=False)  # e.g., {"discipline": 6, "force": 12}

    user = relationship("User", back_populates="scores")
    active_template = relationship("DayTemplate", back_populates="scores")


class Streak(Base):
    __tablename__ = "streaks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    streak_type = Column(String, nullable=False)  # "Acceptable", "Perfect", or "habit:[habit_id]"
    current_streak = Column(Integer, default=0)
    max_streak = Column(Integer, default=0)
    last_incremented = Column(Date, nullable=True)

    user = relationship("User", back_populates="streaks")
