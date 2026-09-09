"""
Analytics Agent — converts raw telemetry into actionable insights.
Supports Groq and OpenAI via unified LLM service.
"""
import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analytics_service import get_daily_analytics, get_weekly_analytics
from app.services.llm_service import complete_chat, is_llm_available


async def get_analytics_insights(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Generate AI insights from today's and this week's data."""
    today = date.today()
    daily = await get_daily_analytics(db, user_id, today)
    weekly = await get_weekly_analytics(db, user_id)

    insights = _generate_deterministic_insights(daily, weekly)

    if is_llm_available():
        try:
            ai_insight = await _ai_insights(daily, weekly)
            if ai_insight:
                insights.append(ai_insight)
        except Exception:
            pass

    return {"insights": insights, "date": str(today)}


def _generate_deterministic_insights(daily: dict, weekly: dict) -> list:
    """Generate grounded insights without AI."""
    insights = []

    productive_h = daily["productive_seconds"] / 3600
    distracting_m = daily["distracting_seconds"] / 60
    score = daily["score"]
    goals_rate = daily["goals_completed"] / max(daily["goals_total"], 1)

    if daily.get("best_focus_start"):
        insights.append({
            "type": "focus",
            "text": f"Your strongest focus window today was {daily['best_focus_start']}–{daily['best_focus_end']}.",
            "data": "observed",
        })

    if distracting_m > 30:
        insights.append({
            "type": "distraction",
            "text": f"You spent {int(distracting_m)} minutes on distracting activities today.",
            "data": "observed",
        })

    if productive_h >= 4:
        insights.append({
            "type": "positive",
            "text": f"You achieved {productive_h:.1f} hours of productive work today.",
            "data": "observed",
        })

    if goals_rate < 0.5 and daily["goals_total"] > 0:
        insights.append({
            "type": "goal",
            "text": f"You have completed {daily['goals_completed']}/{daily['goals_total']} goals today. Focus on closing active quests.",
            "data": "observed",
        })

    if weekly.get("average_score", 0) > 0:
        insights.append({
            "type": "trend",
            "text": f"Your 7-day average score is {weekly['average_score']}/100. Strongest day was {weekly.get('strongest_day', 'N/A')}.",
            "data": "observed",
        })

    return insights


async def _ai_insights(daily: dict, weekly: dict) -> dict:
    data_summary = f"""Daily: score={daily['score']}, productive={daily['productive_seconds']//60}m,
distracting={daily['distracting_seconds']//60}m, goals={daily['goals_completed']}/{daily['goals_total']},
top_apps={[a['application'] for a in daily['top_apps'][:3]]}.
Weekly: avg_score={weekly.get('average_score', 0)}, strongest_day={weekly.get('strongest_day', 'N/A')},
completion_rate={weekly.get('goal_completion_rate', 0):.0%}."""

    system_prompt = "Generate one punchy, actionable tactical insight from this productivity data. Be specific and reference numbers. Under 60 words."
    text = await complete_chat(system_prompt, data_summary, temperature=0.6, max_tokens=150)
    if text:
        return {"type": "ai_insight", "text": text, "data": "ai_recommendation"}
    return {}
