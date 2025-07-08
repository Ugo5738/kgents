from .app_client_schemas import AppClientCreatedResponse  # Added
from .app_client_schemas import AppClientCreateRequest  # Added
from .app_client_schemas import AppClientTokenData
from .common_schemas import MessageResponse
from .user_schemas import (
    MagicLinkLoginRequest,
    MagicLinkSentResponse,
    OAuthProvider,
    OAuthRedirectResponse,
    PasswordResetRequest,
    PasswordResetResponse,
    PasswordUpdateRequest,
    PasswordUpdateResponse,
    ProfileBase,
    ProfileCreate,
    ProfileResponse,
    ProfileUpdate,
    SupabaseSession,
    SupabaseUser,
    UserCreate,
    UserLoginRequest,
    UserProfileUpdateRequest,
    UserResponse,
)

__all__ = [
    "MessageResponse",
    "ProfileBase",
    "ProfileCreate",
    "ProfileUpdate",
    "ProfileResponse",
    "UserProfileUpdateRequest",
    "SupabaseUser",
    "SupabaseSession",
    "OAuthProvider",
    "OAuthRedirectResponse",
    "UserLoginRequest",
    "MagicLinkLoginRequest",
    "MagicLinkSentResponse",
    "PasswordResetRequest",
    "PasswordResetResponse",
    "PasswordUpdateRequest",
    "PasswordUpdateResponse",
    "UserCreate",
    "UserResponse",
    "AppClientTokenData",
    "AppClientCreateRequest",  # Added
    "AppClientCreatedResponse",  # Added
]
