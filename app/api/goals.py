import uuid
from datetime import datetime, timezone, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
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
    target_duration = data.target_duration_seconds
    if data.estimated_minutes and data.estimated_minutes > 0:
        target_duration = data.estimated_minutes * 60

    goal_data = data.model_dump(exclude={"estimated_minutes"})
    goal_data["target_duration_seconds"] = target_duration
    goal = Goal(user_id=current_user.id, **goal_data)
    db.add(goal)
    await db.flush()
    return GoalOut.model_validate(goal)


class ConversationPlanRequest(BaseModel):
    text: str
    conversation_history: List[dict] = []   # [{"role": "user"|"assistant", "text": str}]


class ConversationPlanResponse(BaseModel):
    created_goals: List[GoalOut] = []
    updated_goals: List[GoalOut] = []
    deleted_goal_ids: List[uuid.UUID] = []
    assistant_reply: str
    action: str = "chat"  # "created", "ask_clarification", "updated", "deleted", "completed", "chat"


@router.post("/from-conversation", response_model=ConversationPlanResponse)
async def create_goals_from_conversation(
    data: ConversationPlanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Parse user voice/chat input using OpenAI SDK tool calling.
    Directly invokes database CRUD operations (create_quest, update_quest, delete_quest, delete_all_quests, complete_quest).
    """
    from app.services.tool_agent import run_tool_agent

    result = await run_tool_agent(
        user_input=data.text,
        conversation_history=data.conversation_history,
        current_user=current_user,
        db=db,
    )

    return ConversationPlanResponse(
        created_goals=result.get("created_goals", []),
        updated_goals=result.get("updated_goals", []),
        deleted_goal_ids=result.get("deleted_goal_ids", []),
        assistant_reply=result.get("assistant_reply", "Ready for your next quest!"),
        action=result.get("action", "chat"),
    )


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
