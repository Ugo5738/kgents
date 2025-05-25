from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.core.security import (
    create_access_token,
    decode_access_token,
    get_current_user_id,
)
from app.db.crud_users import authenticate_user, create_user, get_user_by_id
from app.models.user import Token, UserCreate, UserLogin, UserResponse

router = APIRouter()

@router.get("/health", tags=["auth"])
async def auth_health_check() -> dict:
    """Health check for auth router."""
    return {"status": "auth healthy"}

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["auth"],
)
async def register(user_create: UserCreate) -> UserResponse:
    """Register a new user."""
    try:
        user = await create_user(user_create)
        return user
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed; user may already exist",
        )

@router.post(
    "/login",
    response_model=Token,
    tags=["auth"],
)
async def login(
    user_login: UserLogin,
) -> Token:
    """Authenticate user and return a JWT token."""
    user = await authenticate_user(user_login)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    access_token = create_access_token(subject=str(user.id))
    return Token(access_token=access_token)

@router.get(
    "/me",
    response_model=UserResponse,
    tags=["auth"],
)
async def me(
    user_id: int = Depends(get_current_user_id),
) -> UserResponse:
    """Get current authenticated user's info."""
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user 