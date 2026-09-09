"""
Unit tests for the deterministic scoring engine (Phase 7).
Tests verify score rules, event recording, and edge cases.
"""
import uuid
import pytest
import pytest_asyncio
from datetime import date, datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.scoring_service import (
    BASE_SCORE,
    SCORE_RULES,
    compute_daily_score,
    record_score_event,
    award_goal_completion,
)
from app.models.user import User
from app.models.goal import Goal, GoalStatus
from app.models.activity import Activity

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _create_test_user(db: AsyncSession) -> User:
    from app.services.auth_service import hash_password
    user = User(
        email=f"score_test_{uuid.uuid4().hex[:6]}@example.com",
        name="Score Tester",
        password_hash=hash_password("TestPass123!"),
    )
    db.add(user)
    await db.flush()
    return user


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ── Tests ─────────────────────────────────────────────────────────────────────

async def test_base_score_is_50(db_session: AsyncSession):
    """A day with no events should return base score of 50."""
    user = await _create_test_user(db_session)
    daily = await compute_daily_score(db_session, user.id, date.today())
    assert daily.score == BASE_SCORE


async def test_goal_completion_adds_points(db_session: AsyncSession):
    """Completing a normal goal should add 10 points."""
    user = await _create_test_user(db_session)
    event = await record_score_event(
        db_session, user.id, "goal_completed", "Completed task", override_points=None
    )
    assert event.points == SCORE_RULES["goal_completed"]

    daily = await compute_daily_score(db_session, user.id, date.today())
    assert daily.score == BASE_SCORE + SCORE_RULES["goal_completed"]


async def test_high_priority_goal_adds_more_points(db_session: AsyncSession):
    """High-priority goal completion should award more than a normal goal."""
    user = await _create_test_user(db_session)
    goal = Goal(
        user_id=user.id,
        title="Critical Quest",
        priority="critical",
        status=GoalStatus.completed,
        date=_utc_now(),
    )
    db_session.add(goal)
    await db_session.flush()

    event = await award_goal_completion(db_session, user.id, goal)
    assert event.points == SCORE_RULES["high_priority_goal_completed"]
    assert event.points > SCORE_RULES["goal_completed"]


async def test_distraction_penalizes_score(db_session: AsyncSession):
    """A long_unplanned_distraction event should subtract points."""
    user = await _create_test_user(db_session)
    event = await record_score_event(
        db_session, user.id, "long_unplanned_distraction",
        "20+ min on entertainment", override_points=None
    )
    assert event.points < 0
    assert event.points == SCORE_RULES["long_unplanned_distraction"]


async def test_score_capped_at_100(db_session: AsyncSession):
    """Score should never exceed 100 even with many positive events."""
    user = await _create_test_user(db_session)
    for _ in range(20):
        await record_score_event(
            db_session, user.id, "deep_work_session",
            "Deep work", override_points=10
        )
    daily = await compute_daily_score(db_session, user.id, date.today())
    assert daily.score <= 100


async def test_score_floor_at_0(db_session: AsyncSession):
    """Score should never go below 0 even with many penalties."""
    user = await _create_test_user(db_session)
    for _ in range(20):
        await record_score_event(
            db_session, user.id, "long_unplanned_distraction",
            "Distraction", override_points=-10
        )
    daily = await compute_daily_score(db_session, user.id, date.today())
    assert daily.score >= 0


async def test_productive_seconds_aggregated(db_session: AsyncSession):
    """compute_daily_score should correctly aggregate productive seconds."""
    user = await _create_test_user(db_session)
    now = _utc_now()
    act = Activity(
        user_id=user.id,
        application="devenv",
        window_title="VS Code",
        category="Development",
        is_productive=True,
        started_at=now - timedelta(minutes=10),
        ended_at=now,
        duration_seconds=600,
    )
    db_session.add(act)
    await db_session.flush()

    daily = await compute_daily_score(db_session, user.id, date.today())
    assert daily.productive_seconds >= 600
