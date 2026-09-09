from datetime import date
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.session import get_db
from app.models.user import User
from app.models.score import ScoreEvent, DailyScore
from app.schemas.analytics import ScoreEventOut, DailyScoreOut
from app.services.auth_service import get_current_user
from app.services.scoring_service import compute_daily_score

router = APIRouter(prefix="/api/v1/score", tags=["score"])


@router.get("/today", response_model=DailyScoreOut)
async def score_today(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    daily = await compute_daily_score(db, current_user.id, today)
    return DailyScoreOut.model_validate(daily)


@router.get("/events", response_model=List[ScoreEventOut])
async def score_events_today(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    result = await db.execute(
        select(ScoreEvent).where(
            and_(ScoreEvent.user_id == current_user.id, ScoreEvent.date == today)
        ).order_by(ScoreEvent.created_at.desc())
    )
    return [ScoreEventOut.model_validate(e) for e in result.scalars().all()]


@router.get("/history", response_model=List[DailyScoreOut])
async def score_history(
    days: int = 7,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import timedelta
    today = date.today()
    start = today - timedelta(days=days - 1)
    result = await db.execute(
        select(DailyScore).where(
            and_(
                DailyScore.user_id == current_user.id,
                DailyScore.date >= start,
                DailyScore.date <= today,
            )
        ).order_by(DailyScore.date)
    )
    return [DailyScoreOut.model_validate(d) for d in result.scalars().all()]
