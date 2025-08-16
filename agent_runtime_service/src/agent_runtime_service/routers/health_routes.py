from fastapi import APIRouter

router = APIRouter(tags=["Health"]) 


@router.get("/health")
async def health_check():
    return {"status": "ok"}


@router.get("/internal/health")
async def internal_health():
    return {"status": "ok"}
