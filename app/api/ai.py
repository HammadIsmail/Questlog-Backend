"""AI chat and insights endpoint. Uses OpenAI function-calling architecture."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    sources: Optional[list] = None


@router.post("/chat", response_model=ChatResponse)
async def ai_chat(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI Coach chat endpoint."""
    from app.agents.coach import get_coach_response
    reply = await get_coach_response(db, current_user.id, data.message)
    return ChatResponse(reply=reply)


@router.post("/insights")
async def ai_insights(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get AI-generated insights from today's data."""
    from app.agents.analytics import get_analytics_insights
    return await get_analytics_insights(db, current_user.id)


@router.post("/plan")
async def ai_plan(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI Planner — generate a daily schedule from goals."""
    from app.schemas.schedule import GenerateScheduleRequest
    from app.agents.planner import generate_ai_schedule
    req = GenerateScheduleRequest(**data)
    items = await generate_ai_schedule(db, current_user.id, req)
    return {"schedule": items}
