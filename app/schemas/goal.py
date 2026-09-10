import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, computed_field


class GoalCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    description: Optional[str] = None
    category: str = "Other"
    target_duration_seconds: int = Field(ge=0, default=0)
    estimated_minutes: Optional[int] = None
    priority: str = "medium"
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    date: Optional[datetime] = None


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    target_duration_seconds: Optional[int] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    actual_duration_seconds: Optional[int] = None


class GoalOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: Optional[str]
    category: str
    target_duration_seconds: int
    priority: str
    status: str
    scheduled_start: Optional[datetime]
    scheduled_end: Optional[datetime]
    actual_duration_seconds: int
    date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def estimated_minutes(self) -> int:
        return (self.target_duration_seconds or 0) // 60

    @computed_field
    @property
    def is_completed(self) -> bool:
        return self.status == "completed"
