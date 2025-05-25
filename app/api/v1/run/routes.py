from fastapi import APIRouter

router = APIRouter()

@router.get("/health", tags=["run"])
async def run_health_check() -> dict:
    """Health check for run router."""
    return {"status": "run healthy"} 