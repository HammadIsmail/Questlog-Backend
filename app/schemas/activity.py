import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ActivityCreate(BaseModel):
    source: str = "desktop"
    application: Optional[str] = None
    window_title: Optional[str] = None
    domain: Optional[str] = None
    category: str = "Other"
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: int = Field(ge=0, default=0)
    is_productive: bool = False
    is_planned: bool = False


class ActivityBatchCreate(BaseModel):
    activities: List[ActivityCreate]


class ActivityUpdate(BaseModel):
    category: Optional[str] = None
    is_productive: Optional[bool] = None


class ActivityOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    source: str
    application: Optional[str]
    window_title: Optional[str]
    domain: Optional[str]
    category: str
    started_at: datetime
    ended_at: Optional[datetime]
    duration_seconds: int
    is_productive: bool
    is_planned: bool
    created_at: datetime
