import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.activity import ActivityCreate, ActivityBatchCreate, ActivityOut
from app.services.activity_service import (
    create_activity, create_activities_batch,
    get_activities_today, get_activities, delete_activity
)
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/v1/activities", tags=["activities"])


@router.post("", response_model=ActivityOut, status_code=status.HTTP_201_CREATED)
async def ingest_activity(
    data: ActivityCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_activity(db, current_user.id, data)


@router.post("/batch", response_model=List[ActivityOut], status_code=status.HTTP_201_CREATED)
async def ingest_batch(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import json as _json
    body = await request.json()
    print(f"[DEBUG batch] body keys: {list(body.keys()) if isinstance(body, dict) else type(body)}")
    if isinstance(body, dict) and "activities" in body and body["activities"]:
        print(f"[DEBUG batch] first activity keys: {list(body['activities'][0].keys())}")
    try:
        data = ActivityBatchCreate(**body)
    except Exception as ve:
        print(f"[DEBUG batch] validation error: {ve}")
        raise HTTPException(status_code=422, detail=str(ve))
    return await create_activities_batch(db, current_user.id, data.activities)



@router.get("/today", response_model=List[ActivityOut])
async def list_today(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_activities_today(db, current_user.id)


@router.get("", response_model=List[ActivityOut])
async def list_activities(
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    category: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_activities(
        db, current_user.id, limit, offset, category, source, date_from, date_to
    )


@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_activity(
    activity_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deleted = await delete_activity(db, activity_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")
