import uuid
from datetime import datetime, timezone, date, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.session import get_db
from app.models.user import User
from app.models.schedule import ScheduleItem
from app.schemas.schedule import ScheduleItemCreate, ScheduleItemUpdate, ScheduleItemOut, GenerateScheduleRequest
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/v1/schedule", tags=["schedule"])


@router.get("/today", response_model=List[ScheduleItemOut])
async def get_today_schedule(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    result = await db.execute(
        select(ScheduleItem).where(
            and_(
                ScheduleItem.user_id == current_user.id,
                ScheduleItem.start_time >= start,
                ScheduleItem.start_time < end,
            )
        ).order_by(ScheduleItem.start_time)
    )
    return [ScheduleItemOut.model_validate(s) for s in result.scalars().all()]


@router.post("", response_model=ScheduleItemOut, status_code=status.HTTP_201_CREATED)
async def create_schedule_item(
    data: ScheduleItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = ScheduleItem(user_id=current_user.id, **data.model_dump())
    db.add(item)
    await db.flush()
    return ScheduleItemOut.model_validate(item)


@router.patch("/{item_id}", response_model=ScheduleItemOut)
async def update_schedule_item(
    item_id: uuid.UUID,
    data: ScheduleItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ScheduleItem).where(
            and_(ScheduleItem.id == item_id, ScheduleItem.user_id == current_user.id)
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule item not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(item, field, value)
    await db.flush()
    return ScheduleItemOut.model_validate(item)


@router.post("/generate", response_model=List[ScheduleItemOut])
async def generate_schedule(
    data: GenerateScheduleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI-powered schedule generation. Returns generated schedule items."""
    # Import here to avoid circular deps at module load
    from app.agents.planner import generate_ai_schedule
    items = await generate_ai_schedule(db, current_user.id, data)
    return [ScheduleItemOut.model_validate(i) for i in items]
