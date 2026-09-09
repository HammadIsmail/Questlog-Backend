"""Analytics service — aggregates activity data into actionable metrics."""
import uuid
from datetime import date, datetime, timezone, timedelta
from typing import Optional, Dict, List, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc

from app.models.activity import Activity
from app.models.score import DailyScore, ScoreEvent
from app.models.goal import Goal
from app.services.scoring_service import compute_daily_score


async def get_daily_analytics(db: AsyncSession, user_id: uuid.UUID, target_date: date) -> Dict[str, Any]:
    start_dt = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=timezone.utc)
    end_dt = start_dt + timedelta(days=1)

    # Activities
    acts_result = await db.execute(
        select(Activity).where(
            and_(
                Activity.user_id == user_id,
                Activity.started_at >= start_dt,
                Activity.started_at < end_dt,
            )
        ).order_by(Activity.started_at)
    )
    activities = acts_result.scalars().all()

    # Daily score (compute fresh)
    daily = await compute_daily_score(db, user_id, target_date)

    # Top apps
    app_time: Dict[str, int] = {}
    for a in activities:
        if a.application and a.source == "desktop":
            app_time[a.application] = app_time.get(a.application, 0) + a.duration_seconds
    top_apps = sorted(
        [{"application": k, "seconds": v} for k, v in app_time.items()],
        key=lambda x: x["seconds"],
        reverse=True,
    )[:10]

    # Top websites
    domain_time: Dict[str, int] = {}
    for a in activities:
        if a.domain and a.source == "browser":
            domain_time[a.domain] = domain_time.get(a.domain, 0) + a.duration_seconds
    top_websites = sorted(
        [{"domain": k, "seconds": v} for k, v in domain_time.items()],
        key=lambda x: x["seconds"],
        reverse=True,
    )[:10]

    # Category breakdown
    cat_time: Dict[str, int] = {}
    for a in activities:
        cat_time[a.category] = cat_time.get(a.category, 0) + a.duration_seconds

    # Score events
    events_result = await db.execute(
        select(ScoreEvent).where(
            and_(ScoreEvent.user_id == user_id, ScoreEvent.date == target_date)
        )
    )
    score_events = events_result.scalars().all()

    # Best focus period (find longest continuous productive block)
    best_start = best_end = None
    max_duration = 0
    block_start = None
    block_duration = 0
    for a in activities:
        if a.is_productive and a.duration_seconds > 0:
            if block_start is None:
                block_start = a.started_at
                block_duration = a.duration_seconds
            else:
                # Check continuity (within 5 minutes gap)
                gap = (a.started_at - (block_start + timedelta(seconds=block_duration))).total_seconds()
                if gap <= 300:
                    block_duration += a.duration_seconds
                else:
                    if block_duration > max_duration:
                        max_duration = block_duration
                        best_start = block_start
                        best_end = block_start + timedelta(seconds=block_duration)
                    block_start = a.started_at
                    block_duration = a.duration_seconds
        else:
            if block_start and block_duration > max_duration:
                max_duration = block_duration
                best_start = block_start
                best_end = block_start + timedelta(seconds=block_duration)
            block_start = None
            block_duration = 0

    return {
        "date": target_date,
        "score": daily.score,
        "productive_seconds": daily.productive_seconds,
        "distracting_seconds": daily.distracting_seconds,
        "idle_seconds": daily.idle_seconds,
        "goals_completed": daily.goals_completed,
        "goals_total": daily.goals_total,
        "top_apps": top_apps,
        "top_websites": top_websites,
        "category_breakdown": cat_time,
        "score_events": score_events,
        "best_focus_start": best_start.strftime("%H:%M") if best_start else None,
        "best_focus_end": best_end.strftime("%H:%M") if best_end else None,
    }


async def get_weekly_analytics(db: AsyncSession, user_id: uuid.UUID) -> Dict[str, Any]:
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    daily_scores_result = await db.execute(
        select(DailyScore).where(
            and_(
                DailyScore.user_id == user_id,
                DailyScore.date >= week_start,
                DailyScore.date <= week_end,
            )
        ).order_by(DailyScore.date)
    )
    daily_scores = daily_scores_result.scalars().all()

    avg_score = sum(d.score for d in daily_scores) / len(daily_scores) if daily_scores else 0
    total_productive = sum(d.productive_seconds for d in daily_scores)
    total_goals = sum(d.goals_total for d in daily_scores)
    completed_goals = sum(d.goals_completed for d in daily_scores)
    completion_rate = completed_goals / total_goals if total_goals > 0 else 0

    strongest = max(daily_scores, key=lambda d: d.score, default=None)
    weakest = min(daily_scores, key=lambda d: d.score, default=None)

    return {
        "week_start": week_start,
        "week_end": week_end,
        "average_score": round(avg_score, 1),
        "total_productive_seconds": total_productive,
        "goal_completion_rate": round(completion_rate, 2),
        "daily_scores": daily_scores,
        "strongest_day": strongest.date.strftime("%A") if strongest else None,
        "weakest_day": weakest.date.strftime("%A") if weakest else None,
        "category_breakdown": {},
    }
