from fastapi import APIRouter

router = APIRouter()

@router.get("/health", tags=["nl_agents"])
async def nl_agents_health_check() -> dict:
    """Health check for nl_agents router."""
    return {"status": "nl_agents healthy"} 