"""
Coach Agent — provides grounded accountability, coaching responses, and direct voice/text schedule generation.
Uses real activity data and concrete language (no vague motivational copy).
Supports Groq and OpenAI through the unified LLM service.
"""
import uuid
import re
from datetime import date, datetime, timezone
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_

from app.models.goal import Goal
from app.models.schedule import ScheduleItem
from app.schemas.schedule import GenerateScheduleRequest
from app.agents.planner import generate_ai_schedule
from app.services.analytics_service import get_daily_analytics
from app.services.llm_service import complete_chat, is_llm_available


def _extract_goals_from_speech(text: str) -> List[tuple[str, int]]:
    """
    Extract goal titles and durations (in seconds) from speech/text like:
    'schedule 2 hours of DSA and 1 hour of project work and 45 minutes of reading'
    """
    goals = []
    # Pattern for "X hours/mins of Y" or "Xh/m Y"
    pattern = r'(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|minutes?|mins?|m)\s*(?:of\s+)?([^,.;]+?)(?=(?:\s+and\s+\d|\s*,\s*\d|\s*;\s*\d|\s*\.|$))'
    matches = re.finditer(pattern, text, re.IGNORECASE)

    for m in matches:
        amount = float(m.group(1))
        unit = m.group(2).lower()
        title = m.group(3).strip()
        
        # Clean title words
        title = re.sub(r'^(to|for|on|my|a|an)\s+', '', title, flags=re.IGNORECASE).strip()
        if not title:
            continue

        if 'h' in unit:
            duration_sec = int(amount * 3600)
        else:
            duration_sec = int(amount * 60)

        # Capitalize nicely
        clean_title = " ".join(word.capitalize() for word in title.split())
        goals.append((clean_title, duration_sec))

    return goals


async def get_coach_response(
    db: AsyncSession,
    user_id: uuid.UUID,
    message: str,
) -> str:
    """Generate a coach response or build schedule from conversation."""
    today = date.today()
    msg_lower = message.lower()

    # ── Check for direct scheduling intents ──
    schedule_keywords = [
        "schedule", "plan my day", "make a list of my schedule", "make list of my schedule",
        "make my schedule", "create schedule", "generate schedule", "add quest", "set schedule",
        "organize my day", "what is my schedule", "plan today"
    ]
    is_scheduling = any(k in msg_lower for k in schedule_keywords)

    if is_scheduling:
        extracted = _extract_goals_from_speech(message)
        if extracted:
            for title, duration in extracted:
                # Add as goal
                new_goal = Goal(
                    user_id=user_id,
                    title=title,
                    category="Spoken Quest",
                    priority="high",
                    target_duration_seconds=duration,
                    status="pending",
                )
                db.add(new_goal)
            await db.flush()

        # Clear existing today schedule items to regenerate cleanly
        now_utc = datetime.now(timezone.utc)
        day_start = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=timezone.utc)
        day_end = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=timezone.utc)
        
        await db.execute(
            delete(ScheduleItem).where(
                and_(
                    ScheduleItem.user_id == user_id,
                    ScheduleItem.start_time >= day_start,
                    ScheduleItem.start_time <= day_end,
                )
            )
        )
        await db.flush()

        # Generate schedule via planner
        req = GenerateScheduleRequest(date=datetime.now(timezone.utc))
        items = await generate_ai_schedule(db, user_id, req)
        await db.commit()

        if items:
            lines = [
                "⚔️ **Dungeon Master's Tactical Schedule**",
                "",
                "By your decree, I have orchestrated your campaign schedule for today:",
                "",
            ]
            for item in items:
                start_str = item.start_time.strftime("%I:%M %p")
                end_str = item.end_time.strftime("%I:%M %p")
                duration_m = int((item.end_time - item.start_time).total_seconds() // 60)
                lines.append(f"• **{start_str} – {end_str}** | {item.title} ({duration_m}m)")

            lines.append("")
            lines.append("⚡ Your tactical itinerary is now synchronized with your Daily Schedule. Step forward and conquer!")
            return "\n".join(lines)
        else:
            return "⚔️ I tried to arrange your schedule, but no active quests or goals were found. Tell me what tasks to schedule!"

    # ── General Coach Analysis ──
    analytics = await get_daily_analytics(db, user_id, today)

    productive_h = analytics["productive_seconds"] // 3600
    productive_m = (analytics["productive_seconds"] % 3600) // 60
    distracting_m = analytics["distracting_seconds"] // 60
    score = analytics["score"]
    goals_done = analytics["goals_completed"]
    goals_total = analytics["goals_total"]

    context = f"""Today's real user data:
- Productivity score: {score}/100
- Productive time: {productive_h}h {productive_m}m
- Distracting time: {distracting_m} minutes
- Goals: {goals_done}/{goals_total} completed
- Best focus: {analytics.get('best_focus_start', 'N/A')} – {analytics.get('best_focus_end', 'N/A')}
- Top activities: {', '.join(a['application'] for a in analytics['top_apps'][:3]) if analytics['top_apps'] else 'none recorded'}
"""

    if not is_llm_available():
        return _template_response(message, analytics)

    system_prompt = """You are a productivity coach and Dungeon Master for a personal productivity tracking app.
You have access to the user's real activity telemetry for today.
Be direct and specific. Reference the actual numbers. Never use motivational fluff.
Avoid phrases like "great job", "unlock your potential", "amazing work".
Keep responses concise (under 150 words).
"""
    user_prompt = f"Context:\n{context}\n\nUser query: {message}"

    ai_reply = await complete_chat(system_prompt, user_prompt, temperature=0.7, max_tokens=250)
    if ai_reply:
        return ai_reply

    return _template_response(message, analytics)


def _template_response(message: str, analytics: dict) -> str:
    """Fallback template-based coach response using real data."""
    score = analytics["score"]
    productive_h = analytics["productive_seconds"] // 3600
    productive_m = (analytics["productive_seconds"] % 3600) // 60
    distracting_m = analytics["distracting_seconds"] // 60
    goals_done = analytics["goals_completed"]
    goals_total = analytics["goals_total"]

    return (
        f"⚔️ **Dungeon Master Telemetry Report**:\n"
        f"• Productivity Score: {score}/100 today.\n"
        f"• Productive Focus: {productive_h}h {productive_m}m\n"
        f"• Distraction Time: {distracting_m} minutes\n"
        f"• Quest Completion: {goals_done}/{goals_total}\n"
        f"• Optimal Window: {analytics.get('best_focus_start', 'pending data')}."
    )
