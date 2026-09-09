import uuid
from datetime import datetime, date, timezone
from typing import Optional
from sqlalchemy import String, DateTime, Date, Integer, Float, ForeignKey, func, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ScoreEvent(Base):
    """Individual score change events — the audit trail of scoring."""
    __tablename__ = "score_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    activity_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("activities.id", ondelete="SET NULL"))
    goal_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("goals.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class DailyScore(Base):
    """Aggregated daily productivity score."""
    __tablename__ = "daily_scores"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, default=50)
    productive_seconds: Mapped[int] = mapped_column(Integer, default=0)
    distracting_seconds: Mapped[int] = mapped_column(Integer, default=0)
    idle_seconds: Mapped[int] = mapped_column(Integer, default=0)
    goals_completed: Mapped[int] = mapped_column(Integer, default=0)
    goals_total: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now()
    )


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    tracking_enabled: Mapped[bool] = mapped_column(default=True)
    excluded_apps: Mapped[str] = mapped_column(Text, default="[]")  # JSON array
    excluded_domains: Mapped[str] = mapped_column(Text, default="[]")  # JSON array
    notifications_enabled: Mapped[bool] = mapped_column(default=True)
    voice_enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now()
    )
