"""
AssemblyAI Voice Service — Manages voice sessions, temporary token generation,
and exposes product tools that the voice agent can invoke (TRD §16).
"""
import logging
import uuid
from typing import Dict, Any, Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.config import settings
from app.models.goal import Goal
from app.models.schedule import ScheduleItem
from datetime import date
from app.services.scoring_service import compute_daily_score
from app.services.analytics_service import get_daily_analytics

logger = logging.getLogger(__name__)


async def get_assemblyai_temp_token(expires_in: int = 3600) -> Optional[str]:
    """
    Generate a temporary, short-lived AssemblyAI token for client-side streaming
    to keep the primary secret key safe on the server (TRD §16).
    """
    if not settings.assemblyai_api_key:
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://streaming.assemblyai.com/v3/token",
                headers={"Authorization": settings.assemblyai_api_key.strip()},
                params={"expires_in_seconds": min(expires_in, 600)},
            )
            if resp.status_code == 200:
                return resp.json().get("token")
            else:
                logger.warning("AssemblyAI token error %s: %s", resp.status_code, resp.text)
    except Exception as e:
        logger.error("Failed to generate AssemblyAI token: %s", e)

    return None


# ──────── PRODUCT TOOLS FOR VOICE AGENT (TRD §16) ────────

VOICE_TOOLS_MANIFEST = [
    {
        "name": "get_today_score",
        "description": "Fetch the user's current productivity score, streak, and deep work time for today.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "get_today_schedule",
        "description": "Fetch the scheduled timeline blocks for today.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "create_goal",
        "description": "Create a new daily quest or goal for the user.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Title of the goal or task"},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "estimated_minutes": {"type": "integer", "description": "Estimated duration in minutes"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "complete_goal",
        "description": "Mark a goal as complete by its title or ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Title of the goal to complete"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "get_daily_insights",
        "description": "Fetch tactical advice and observations about the user's focus and distractions.",
        "parameters": {"type": "object", "properties": {}},
    },
]


async def execute_voice_tool(
    db: AsyncSession,
    user_id: uuid.UUID,
    tool_name: str,
    arguments: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute a product tool invoked by the voice agent and return the result."""
    if tool_name == "get_today_score":
        daily = await compute_daily_score(db, user_id, date.today())
        return {
            "score": daily.score,
            "productive_minutes": daily.productive_seconds // 60,
            "distracting_minutes": daily.distracting_seconds // 60,
            "goals_completed": daily.goals_completed,
            "goals_total": daily.goals_total,
        }

    elif tool_name == "get_today_schedule":
        result = await db.execute(
            select(ScheduleItem)
            .where(ScheduleItem.user_id == user_id)
            .order_by(ScheduleItem.start_time)
        )
        items = result.scalars().all()
        return {
            "schedule": [
                {
                    "title": item.title,
                    "start": item.start_time.strftime("%H:%M"),
                    "end": item.end_time.strftime("%H:%M") if item.end_time else None,
                    "is_completed": item.status == "completed",
                    "status": item.status,
                }
                for item in items
            ]
        }

    elif tool_name == "create_goal":
        title = arguments.get("title", "").strip()
        priority = arguments.get("priority", "medium")
        est_min = arguments.get("estimated_minutes", 30)

        if not title:
            return {"error": "Goal title is required."}

        goal = Goal(
            user_id=user_id,
            title=title,
            priority=priority,
            target_duration_seconds=est_min * 60,
            status="pending",
        )
        db.add(goal)
        await db.commit()
        await db.refresh(goal)
        return {"success": True, "goal_id": str(goal.id), "title": goal.title}

    elif tool_name == "complete_goal":
        title = arguments.get("title", "").strip().lower()
        result = await db.execute(
            select(Goal).where(
                and_(
                    Goal.user_id == user_id,
                    Goal.status != "completed",
                )
            )
        )
        goals = result.scalars().all()
        matched = next((g for g in goals if title in g.title.lower()), None)
        if matched:
            matched.status = "completed"
            await db.commit()
            return {"success": True, "completed_goal": matched.title}
        return {"error": f"No active goal matching '{title}' was found."}

    elif tool_name == "get_daily_insights":
        from app.agents.analytics import get_analytics_insights
        return await get_analytics_insights(db, user_id)

    return {"error": f"Unknown tool: {tool_name}"}
