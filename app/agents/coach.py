"""
Coach Agent — provides grounded accountability and coaching responses.
Uses real activity data and concrete language (no vague motivational copy).
Supports Groq and OpenAI through the unified LLM service.
"""
import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analytics_service import get_daily_analytics
from app.services.llm_service import complete_chat, is_llm_available


async def get_coach_response(
    db: AsyncSession,
    user_id: uuid.UUID,
    message: str,
) -> str:
    """Generate a coach response using today's actual data."""
    today = date.today()
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
        f"Current status: {score}/100 today.\n"
        f"You've logged {productive_h}h {productive_m}m of productive focus "
        f"and {distracting_m} minutes of distracting activity.\n"
        f"Goals: {goals_done}/{goals_total} completed.\n"
        f"Best focus window: {analytics.get('best_focus_start', 'not yet recorded')}."
    )
