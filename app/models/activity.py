import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, DateTime, Integer, Boolean, ForeignKey, func, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
import enum


class ActivitySource(str, enum.Enum):
    desktop = "desktop"
    browser = "browser"


class ActivityCategory(str, enum.Enum):
    coding = "Coding"
    dsa = "DSA"
    study = "Study"
    work = "Work"
    marketing = "Marketing"
    meeting = "Meeting"
    communication = "Communication"
    entertainment = "Entertainment"
    social = "Social"
    gaming = "Gaming"
    break_ = "Break"
    idle = "Idle"
    other = "Other"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="desktop")
    application: Mapped[Optional[str]] = mapped_column(String(255))
    window_title: Mapped[Optional[str]] = mapped_column(String(512))
    domain: Mapped[Optional[str]] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="Other")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    is_productive: Mapped[bool] = mapped_column(Boolean, default=False)
    is_planned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
