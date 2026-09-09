import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, DateTime, Integer, ForeignKey, func, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
import enum


class GoalStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    missed = "missed"
    cancelled = "cancelled"


class GoalPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50), default="Other")
    target_duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    scheduled_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    scheduled_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    actual_duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))  # which day this goal belongs to
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now()
    )
