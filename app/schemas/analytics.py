import uuid
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class ScoreEventOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    date: date
    event_type: str
    points: int
    reason: str
    activity_id: Optional[uuid.UUID]
    goal_id: Optional[uuid.UUID]
    created_at: datetime


class DailyScoreOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    date: date
    score: int
    productive_seconds: int
    distracting_seconds: int
    idle_seconds: int
    goals_completed: int
    goals_total: int


class DailyAnalytics(BaseModel):
    date: date
    score: int
    productive_seconds: int
    distracting_seconds: int
    idle_seconds: int
    goals_completed: int
    goals_total: int
    top_apps: List[Dict[str, Any]]
    top_websites: List[Dict[str, Any]]
    category_breakdown: Dict[str, int]
    score_events: List[ScoreEventOut]
    best_focus_start: Optional[str]
    best_focus_end: Optional[str]


class WeeklyAnalytics(BaseModel):
    week_start: date
    week_end: date
    average_score: float
    total_productive_seconds: int
    goal_completion_rate: float
    daily_scores: List[DailyScoreOut]
    category_breakdown: Dict[str, int]
    strongest_day: Optional[str]
    weakest_day: Optional[str]


class AppUsage(BaseModel):
    application: str
    total_seconds: int
    category: str
    is_productive: bool


class WebsiteUsage(BaseModel):
    domain: str
    total_seconds: int
    category: str
    is_productive: bool
