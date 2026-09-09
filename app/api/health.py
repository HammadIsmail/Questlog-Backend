from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("")
async def health():
    return {"status": "ok", "service": "Real-Life Dungeon Master"}
