from fastapi import APIRouter

router = APIRouter()

@router.get("/health", tags=["tools"])
async def tools_health_check() -> dict:
    """Health check for tools router."""
    return {"status": "tools healthy"} 