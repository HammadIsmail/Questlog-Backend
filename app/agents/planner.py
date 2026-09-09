"""
Planner Agent — generates a daily schedule from goals using an LLM.

Input: goals, durations, priorities, available time, existing schedule
Output: List of ScheduleItem records validated with Pydantic before storage.
Supports Groq and OpenAI via unified LLM service.
"""
import uuid
from datetime import datetime, timezone, date, timedelta
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.goal import Goal
from app.models.schedule import ScheduleItem
from app.schemas.schedule import GenerateScheduleRequest
from app.services.llm_service import complete_json, is_llm_available


async def generate_ai_schedule(
    db: AsyncSession,
    user_id: uuid.UUID,
    request: GenerateScheduleRequest,
) -> List[ScheduleItem]:
    """Use an LLM to create a daily schedule. Falls back to deterministic ordering if no AI key."""
    target_date = (request.date or datetime.now(timezone.utc)).date() if isinstance(
        request.date, datetime
    ) else (request.date or date.today())

    goals_result = await db.execute(
        select(Goal).where(
            and_(
                Goal.user_id == user_id,
                Goal.status.in_(["pending", "in_progress"]),
            )
        ).order_by(Goal.created_at)
    )
    goals = goals_result.scalars().all()

    if not goals:
        return []

    # Try AI generation if an LLM key is configured
    if is_llm_available():
        try:
            return await _ai_generate(db, user_id, goals, target_date, request)
        except Exception:
            pass  # Fall back to deterministic

    # Deterministic fallback: priority sort + pack from 9 AM
    return await _deterministic_schedule(db, user_id, goals, target_date)


async def _deterministic_schedule(
    db: AsyncSession,
    user_id: uuid.UUID,
    goals: list,
    target_date: date,
) -> List[ScheduleItem]:
    """Deterministic scheduler — priority-ordered, starts at 9 AM."""
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_goals = sorted(goals, key=lambda g: priority_order.get(g.priority, 99))

    items = []
    current_time = datetime(target_date.year, target_date.month, target_date.day, 9, 0, 0, tzinfo=timezone.utc)

    for goal in sorted_goals:
        duration = goal.target_duration_seconds or 3600  # default 1h
        end_time = current_time + timedelta(seconds=duration)

        item = ScheduleItem(
            user_id=user_id,
            goal_id=goal.id,
            title=goal.title,
            start_time=current_time,
            end_time=end_time,
            source="ai",
            reason=f"Scheduled based on {goal.priority} priority.",
        )
        db.add(item)
        items.append(item)
        current_time = end_time + timedelta(minutes=15)  # 15-min break

    await db.flush()
    return items


async def _ai_generate(
    db: AsyncSession,
    user_id: uuid.UUID,
    goals: list,
    target_date: date,
    request: GenerateScheduleRequest,
) -> List[ScheduleItem]:
    """LLM-powered schedule generation using Groq or OpenAI."""
    goals_text = "\n".join(
        f"- {g.title} ({g.priority} priority, {(g.target_duration_seconds or 3600) // 60} min)"
        for g in goals
    )

    system_prompt = """You are an expert AI tactical scheduler. Given a list of goals for today,
create a realistic daily schedule starting around 09:00.
Return ONLY valid JSON with this exact structure:
{
  "schedule": [
    {"title": "...", "start": "09:00", "end": "10:00", "goal_title": "...", "reason": "..."}
  ]
}
Include 15-minute breaks between deep work blocks. Schedule high-priority items in the morning.
"""
    user_msg = f"Today is {target_date}. Schedule these goals:\n{goals_text}"
    if request.notes:
        user_msg += f"\n\nAdditional context: {request.notes}"

    content = await complete_json(system_prompt, user_msg)
    if not content or "schedule" not in content:
        return await _deterministic_schedule(db, user_id, goals, target_date)

    schedule_data = content.get("schedule", [])
    goal_map = {g.title: g for g in goals}
    items = []

    for entry in schedule_data:
        try:
            start_h, start_m = map(int, entry["start"].split(":"))
            end_h, end_m = map(int, entry["end"].split(":"))
            start_dt = datetime(target_date.year, target_date.month, target_date.day, start_h, start_m, tzinfo=timezone.utc)
            end_dt = datetime(target_date.year, target_date.month, target_date.day, end_h, end_m, tzinfo=timezone.utc)

            matched_goal = goal_map.get(entry.get("goal_title", entry["title"]))
            item = ScheduleItem(
                user_id=user_id,
                goal_id=matched_goal.id if matched_goal else None,
                title=entry["title"],
                start_time=start_dt,
                end_time=end_dt,
                source="ai",
                reason=entry.get("reason", "AI-scheduled"),
            )
            db.add(item)
            items.append(item)
        except Exception:
            continue

    if not items:
        return await _deterministic_schedule(db, user_id, goals, target_date)

    await db.flush()
    return items
