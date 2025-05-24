from fastapi import APIRouter

router = APIRouter()

@router.get("/health", tags=["agents"])
async def agents_health_check() -> dict:
    """Health check for agents router."""
    return {"status": "agents healthy"} 