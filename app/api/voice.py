"""
Voice Agent API router for AssemblyAI integration.
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import get_current_user
from app.services.voice_service import (
    get_assemblyai_temp_token,
    VOICE_TOOLS_MANIFEST,
    execute_voice_tool,
)

router = APIRouter(prefix="/api/v1/voice", tags=["Voice"])


class ToolExecutionRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = {}


@router.get("/token")
async def get_voice_token(
    current_user: User = Depends(get_current_user),
):
    """Generate a short-lived AssemblyAI token for client audio streaming."""
    token = await get_assemblyai_temp_token()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AssemblyAI API key not configured or token generation failed.",
        )
    return {"token": token}


@router.get("/tools")
async def get_tools_manifest(
    current_user: User = Depends(get_current_user),
):
    """Return product tools manifest for the voice agent."""
    return {"tools": VOICE_TOOLS_MANIFEST}


@router.post("/tool")
async def call_voice_tool(
    req: ToolExecutionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Execute a product tool requested by the voice agent."""
    result = await execute_voice_tool(
        db=db,
        user_id=current_user.id,
        tool_name=req.tool_name,
        arguments=req.arguments,
    )
    return {"result": result}
