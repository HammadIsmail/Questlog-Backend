import uuid
from datetime import datetime, timezone, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.session import get_db
from app.models.user import User
from app.models.goal import Goal, GoalStatus
from app.schemas.goal import GoalCreate, GoalUpdate, GoalOut
from app.services.auth_service import get_current_user
from app.services.scoring_service import award_goal_completion, penalize_missed_goal

router = APIRouter(prefix="/api/v1/goals", tags=["goals"])


@router.post("", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
async def create_goal(
    data: GoalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    goal = Goal(user_id=current_user.id, **data.model_dump())
    db.add(goal)
    await db.flush()
    return GoalOut.model_validate(goal)


@router.get("", response_model=List[GoalOut])
async def list_goals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Goal).where(Goal.user_id == current_user.id).order_by(Goal.created_at.desc())
    )
    return [GoalOut.model_validate(g) for g in result.scalars().all()]


@router.get("/today", response_model=List[GoalOut])
async def list_today_goals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    end = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=timezone.utc)
    result = await db.execute(
        select(Goal).where(
            and_(
                Goal.user_id == current_user.id,
                Goal.date >= start,
                Goal.date <= end,
            )
        ).order_by(Goal.created_at)
    )
    return [GoalOut.model_validate(g) for g in result.scalars().all()]


@router.patch("/{goal_id}", response_model=GoalOut)
async def update_goal(
    goal_id: uuid.UUID,
    data: GoalUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Goal).where(and_(Goal.id == goal_id, Goal.user_id == current_user.id))
    )
    goal = result.scalar_one_or_none()
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(goal, field, value)
    await db.flush()
    return GoalOut.model_validate(goal)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Goal).where(and_(Goal.id == goal_id, Goal.user_id == current_user.id))
    )
    goal = result.scalar_one_or_none()
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    await db.delete(goal)


@router.post("/{goal_id}/complete", response_model=GoalOut)
async def complete_goal(
    goal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Goal).where(and_(Goal.id == goal_id, Goal.user_id == current_user.id))
    )
    goal = result.scalar_one_or_none()
    if goal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

    goal.status = GoalStatus.completed
    await db.flush()

    # Award score points
    await award_goal_completion(db, current_user.id, goal)

    return GoalOut.model_validate(goal)
