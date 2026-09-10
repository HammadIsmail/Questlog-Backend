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
    created_goals: List[GoalOut]
    assistant_reply: str


@router.post("/from-conversation", response_model=ConversationPlanResponse)
async def create_goals_from_conversation(
    data: ConversationPlanRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Parse a user speaking naturally about their day and create corresponding goals.
    Supports continuous conversational addition of quests.
    """
    from app.agents.coach import _extract_goals_from_speech
    from app.services.llm_service import complete_json, is_llm_available

    extracted_items = []
    llm_reply = None

    # Build conversation context for the LLM
    history_text = ""
    if data.conversation_history:
        for turn in data.conversation_history[-6:]:  # last 3 exchanges
            role = "You" if turn.get("role") == "user" else "Assistant"
            history_text += f"{role}: {turn.get('text', '')}\n"

    # Try LLM: extract tasks AND generate a human-like response in one call
    if is_llm_available():
        system_prompt = """You are a warm, enthusiastic personal AI planning assistant named Quest Master.
Your job is to help users plan their day by listening to them speak naturally.

BEHAVIOR:
- Respond in a friendly, conversational way — like a helpful human friend, not a robot.
- Acknowledge what you heard in a natural way (e.g. "Got it!", "Nice!", "Sounds good!").
- For each task you detect, confirm it conversationally: mention the title, duration, and priority.
- If the user did NOT specify a priority, assign a sensible default and mention it (e.g. "I'll set that as high priority since it sounds important!").
- End your response with a warm invitation (e.g. "What else are you planning today?", "Anything else to add?").
- Keep your response SHORT (2-4 sentences), natural, and encouraging.
- Never say "JSON", "object", or anything technical.

RETURN FORMAT — a valid JSON with two keys:
{
  "goals": [
    {
      "title": "Concise quest name (e.g. DSA Practice)",
      "estimated_minutes": 60,
      "priority": "high",
      "category": "Coding"
    }
  ],
  "reply": "Your warm, conversational response to the user."
}

If no tasks can be extracted, return an empty goals array and ask the user to clarify.
Priority must be one of: critical, high, medium, low."""

        user_message = f"""
Conversation so far:
{history_text}
User just said: \"{data.text}\"

Extract all tasks and reply conversationally."""

        try:
            parsed = await complete_json(system_prompt, user_message)
            if parsed:
                llm_reply = parsed.get("reply", "").strip()
                if parsed.get("goals") and isinstance(parsed["goals"], list):
                    for g in parsed["goals"]:
                        title = g.get("title", "").strip()
                        mins = int(g.get("estimated_minutes", 30))
                        prio = g.get("priority", "medium").lower()
                        if prio not in ["critical", "high", "medium", "low"]:
                            prio = "medium"
                        cat = g.get("category", "Quest")
                        if title:
                            extracted_items.append((title, mins, prio, cat))
        except Exception:
            pass

    # Fallback: regex-based extraction
    if not extracted_items:
        regex_goals = _extract_goals_from_speech(data.text)
        for title, duration_sec in regex_goals:
            extracted_items.append((title, duration_sec // 60, "high", "Spoken Quest"))

    # Last resort: treat whole phrase as one task
    if not extracted_items and len(data.text.strip()) > 3:
        clean_text = data.text.strip()
        for prefix in ["i want to ", "i need to ", "please add ", "add ", "schedule ", "today i want to "]:
            if clean_text.lower().startswith(prefix):
                clean_text = clean_text[len(prefix):].strip()
        title = " ".join(word.capitalize() for word in clean_text.split())
        extracted_items.append((title, 45, "medium", "Spoken Quest"))

    # Create the goals in the database
    created_records = []
    for title, mins, prio, cat in extracted_items:
        g = Goal(
            user_id=current_user.id,
            title=title,
            category=cat,
            priority=prio,
            target_duration_seconds=mins * 60,
            status="pending",
        )
        db.add(g)
        await db.flush()
        created_records.append(GoalOut.model_validate(g))

    await db.commit()

    # Build reply: prefer the LLM's conversational reply, fallback to a generated one
    if llm_reply:
        reply = llm_reply
    elif created_records:
        priority_labels = {"critical": "🔴 critical", "high": "🟠 high", "medium": "🟡 medium", "low": "🟢 low"}
        confirmations = [
            f"✅ '{g.title}' ({g.estimated_minutes}m, {priority_labels.get(g.priority, g.priority)} priority)"
            for g in created_records
        ]
        reply = (
            f"Got it! I'm adding {len(created_records)} task(s) to your list:\n"
            + "\n".join(confirmations)
            + "\nAnything else you'd like to plan for today?"
        )
    else:
        reply = (
            "Hey, I'm listening! 👂 I didn't catch any specific tasks though. "
            "Try something like: 'I want to do 2 hours of DSA and 1 hour of project work'."
        )

    return ConversationPlanResponse(
        created_goals=created_records,
        assistant_reply=reply,
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
