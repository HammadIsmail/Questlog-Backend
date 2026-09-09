"""Activity service — handles ingestion, classification, and retrieval."""
import uuid
from datetime import datetime, timezone, date
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc

from app.models.activity import Activity
from app.schemas.activity import ActivityCreate
from app.services.classification import classify


async def create_activity(
    db: AsyncSession, user_id: uuid.UUID, data: ActivityCreate
) -> Activity:
    """Create a single activity record with auto-classification if not provided."""
    category = data.category
    is_productive = data.is_productive

    # Auto-classify if category is "Other" (not user-overridden)
    if category == "Other":
        classified_cat, classified_prod = classify(
            app_name=data.application,
            domain=data.domain,
            source=data.source,
        )
        category = classified_cat
        is_productive = classified_prod

    activity = Activity(
        user_id=user_id,
        source=data.source,
        application=data.application,
        window_title=data.window_title,
        domain=data.domain,
        category=category,
        started_at=data.started_at,
        ended_at=data.ended_at,
        duration_seconds=data.duration_seconds,
        is_productive=is_productive,
        is_planned=data.is_planned,
    )
    db.add(activity)
    await db.flush()
    return activity


async def create_activities_batch(
    db: AsyncSession, user_id: uuid.UUID, activities: List[ActivityCreate]
) -> List[Activity]:
    """Batch ingest activities."""
    results = []
    for act_data in activities:
        act = await create_activity(db, user_id, act_data)
        results.append(act)
    return results


async def get_activities_today(
    db: AsyncSession, user_id: uuid.UUID
) -> List[Activity]:
    today = date.today()
    start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    end = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=timezone.utc)
    result = await db.execute(
        select(Activity).where(
            and_(
                Activity.user_id == user_id,
                Activity.started_at >= start,
                Activity.started_at <= end,
            )
        ).order_by(Activity.started_at)
    )
    return result.scalars().all()


async def get_activities(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 100,
    offset: int = 0,
    category: Optional[str] = None,
    source: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> List[Activity]:
    q = select(Activity).where(Activity.user_id == user_id)
    if category:
        q = q.where(Activity.category == category)
    if source:
        q = q.where(Activity.source == source)
    if date_from:
        q = q.where(Activity.started_at >= date_from)
    if date_to:
        q = q.where(Activity.started_at <= date_to)
    q = q.order_by(desc(Activity.started_at)).limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


async def delete_activity(
    db: AsyncSession, activity_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    result = await db.execute(
        select(Activity).where(
            and_(Activity.id == activity_id, Activity.user_id == user_id)
        )
    )
    activity = result.scalar_one_or_none()
    if activity is None:
        return False
    await db.delete(activity)
    return True
