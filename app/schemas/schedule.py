import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ScheduleItemCreate(BaseModel):
    goal_id: Optional[uuid.UUID] = None
    title: str = Field(..., min_length=1, max_length=512)
    start_time: datetime
    end_time: datetime
    source: str = "manual"
    reason: Optional[str] = None


class ScheduleItemUpdate(BaseModel):
    title: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None
    reason: Optional[str] = None


class ScheduleItemOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    goal_id: Optional[uuid.UUID]
    title: str
    start_time: datetime
    end_time: datetime
    status: str
    source: str
    reason: Optional[str]
    created_at: datetime
    updated_at: datetime


class GenerateScheduleRequest(BaseModel):
    date: Optional[datetime] = None
    goal_ids: Optional[list[uuid.UUID]] = None
    available_hours: Optional[float] = None
    notes: Optional[str] = None
