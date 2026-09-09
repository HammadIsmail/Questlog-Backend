"""
Dynamic Schedule Shifter — Phase 5 (PRD §8).

When a user overruns a planned block, this agent slides all subsequent
incomplete schedule blocks forward by the overrun amount without marking
the day as failed.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule import ScheduleItem


async def shift_remaining_blocks(
    db: AsyncSession,
    user_id: uuid.UUID,
    anchor_item_id: uuid.UUID,
    overrun_minutes: int,
) -> List[ScheduleItem]:
    """
    Shift all today's incomplete schedule items that start AFTER the anchor item
    forward by `overrun_minutes`. The anchor item itself is not moved.

    Returns the updated list of shifted items (already flushed, not yet committed).
    """
    if overrun_minutes <= 0:
        return []

    # Load the anchor to get its end_time as a boundary
    anchor_result = await db.execute(
        select(ScheduleItem).where(
            and_(
                ScheduleItem.id == anchor_item_id,
                ScheduleItem.user_id == user_id,
            )
        )
    )
    anchor = anchor_result.scalar_one_or_none()
    if anchor is None:
        return []

    boundary = anchor.end_time  # shift blocks that start at or after anchor's end

    # Load all incomplete items starting at or after the boundary
    result = await db.execute(
        select(ScheduleItem)
        .where(
            and_(
                ScheduleItem.user_id == user_id,
                ScheduleItem.is_completed == False,  # noqa: E712
                ScheduleItem.start_time >= boundary,
            )
        )
        .order_by(ScheduleItem.start_time)
    )
    items = result.scalars().all()

    delta = timedelta(minutes=overrun_minutes)
    shifted: List[ScheduleItem] = []

    for item in items:
        item.start_time = item.start_time + delta
        if item.end_time:
            item.end_time = item.end_time + delta
        shifted.append(item)

    await db.flush()
    return shifted
