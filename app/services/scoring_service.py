"""
Deterministic scoring engine.

The AI explains the score, but never owns the calculation.
score = base_score + sum(score_events)
"""
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.score import ScoreEvent, DailyScore
from app.models.goal import Goal, GoalStatus
from app.models.activity import Activity

BASE_SCORE = 50

# Score rules — points delta for each event type
SCORE_RULES = {
    "goal_completed": 10,
    "high_priority_goal_completed": 15,
    "deep_work_session": 5,          # >= 45 min uninterrupted productive
    "planned_productive_achieved": 5,
    "focus_streak_milestone": 5,
    "long_unplanned_distraction": -8,  # >= 20 min distraction in productive block
    "missed_high_priority_goal": -5,
    "repeated_distraction_pattern": -3,
}

PRODUCTIVE_CATEGORIES = {"Coding", "DSA", "Study", "Work", "Marketing"}
DISTRACTION_CATEGORIES = {"Entertainment", "Social", "Gaming"}


async def compute_daily_score(db: AsyncSession, user_id: uuid.UUID, target_date: date) -> DailyScore:
    """Compute or recompute the daily score for a user on a given date."""
    start_dt = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=timezone.utc)
    end_dt = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, tzinfo=timezone.utc)

    # Fetch all activities for the day
    acts_result = await db.execute(
        select(Activity).where(
            and_(
                Activity.user_id == user_id,
                Activity.started_at >= start_dt,
                Activity.started_at <= end_dt,
            )
        ).order_by(Activity.started_at)
    )
    activities = acts_result.scalars().all()

    # Aggregate time by type
    productive_seconds = sum(a.duration_seconds for a in activities if a.is_productive)
    distracting_seconds = sum(
        a.duration_seconds for a in activities
        if a.category in DISTRACTION_CATEGORIES
    )
    idle_seconds = sum(a.duration_seconds for a in activities if a.category == "Idle")

    # Fetch goals for the day
    goals_result = await db.execute(
        select(Goal).where(
            and_(
                Goal.user_id == user_id,
                Goal.date >= start_dt,
                Goal.date <= end_dt,
            )
        )
    )
    goals = goals_result.scalars().all()
    goals_total = len(goals)
    goals_completed = sum(1 for g in goals if g.status == GoalStatus.completed)

    # Fetch existing score events for today
    events_result = await db.execute(
        select(ScoreEvent).where(
            and_(
                ScoreEvent.user_id == user_id,
                ScoreEvent.date == target_date,
            )
        )
    )
    events = events_result.scalars().all()
    event_total = sum(e.points for e in events)

    score = max(0, min(100, BASE_SCORE + event_total))

    # Upsert daily score
    existing_result = await db.execute(
        select(DailyScore).where(
            and_(DailyScore.user_id == user_id, DailyScore.date == target_date)
        )
    )
    daily_score = existing_result.scalar_one_or_none()

    if daily_score is None:
        daily_score = DailyScore(
            user_id=user_id,
            date=target_date,
        )
        db.add(daily_score)

    daily_score.score = score
    daily_score.productive_seconds = productive_seconds
    daily_score.distracting_seconds = distracting_seconds
    daily_score.idle_seconds = idle_seconds
    daily_score.goals_completed = goals_completed
    daily_score.goals_total = goals_total

    await db.flush()
    return daily_score


async def record_score_event(
    db: AsyncSession,
    user_id: uuid.UUID,
    event_type: str,
    reason: str,
    activity_id: Optional[uuid.UUID] = None,
    goal_id: Optional[uuid.UUID] = None,
    override_points: Optional[int] = None,
) -> ScoreEvent:
    """Record a score event and trigger daily score recomputation."""
    points = override_points if override_points is not None else SCORE_RULES.get(event_type, 0)
    today = date.today()

    event = ScoreEvent(
        user_id=user_id,
        date=today,
        event_type=event_type,
        points=points,
        reason=reason,
        activity_id=activity_id,
        goal_id=goal_id,
    )
    db.add(event)
    await db.flush()

    # Recompute daily score
    await compute_daily_score(db, user_id, today)
    return event


async def award_goal_completion(db: AsyncSession, user_id: uuid.UUID, goal: Goal) -> ScoreEvent:
    """Award points for completing a goal."""
    is_high_priority = goal.priority in ("high", "critical")
    event_type = "high_priority_goal_completed" if is_high_priority else "goal_completed"
    reason = f"Completed {'high-priority ' if is_high_priority else ''}goal: {goal.title}"
    return await record_score_event(db, user_id, event_type, reason, goal_id=goal.id)


async def penalize_missed_goal(db: AsyncSession, user_id: uuid.UUID, goal: Goal) -> ScoreEvent:
    """Penalize for missing a high-priority goal."""
    event_type = "missed_high_priority_goal"
    reason = f"Missed high-priority goal: {goal.title}"
    return await record_score_event(db, user_id, event_type, reason, goal_id=goal.id)
