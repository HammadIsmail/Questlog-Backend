from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import get_current_user
from app.services.analytics_service import get_daily_analytics, get_weekly_analytics

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/today")
async def analytics_today(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    return await get_daily_analytics(db, current_user.id, today)


@router.get("/week")
async def analytics_week(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_weekly_analytics(db, current_user.id)


@router.get("/day")
async def analytics_day(
    target_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    d = target_date or date.today()
    return await get_daily_analytics(db, current_user.id, d)


@router.get("/apps")
async def analytics_apps(
    target_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch top used applications and duration (TRD §6)."""
    d = target_date or date.today()
    data = await get_daily_analytics(db, current_user.id, d)
    return data.get("top_apps", [])


@router.get("/websites")
async def analytics_websites(
    target_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch top visited websites/domains and duration (TRD §6)."""
    d = target_date or date.today()
    data = await get_daily_analytics(db, current_user.id, d)
    return data.get("top_websites", [])

