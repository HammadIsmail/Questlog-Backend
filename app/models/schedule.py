import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ScheduleItem(Base):
    __tablename__ = "schedule_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    goal_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("goals.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, active, completed, skipped
    source: Mapped[str] = mapped_column(String(20), default="manual")  # manual, ai
    reason: Mapped[Optional[str]] = mapped_column(Text)  # AI reason for placement
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now()
    )
