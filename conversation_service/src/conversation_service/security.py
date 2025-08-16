from __future__ import annotations

from typing import Optional

from fastapi import WebSocket

from shared.security.jwt import AuthError, decode_any, parse_bearer

from .config import settings
from .logging_config import logger


def extract_bearer_token_from_ws(websocket: WebSocket) -> Optional[str]:
    """Extract Bearer token from Authorization header or `token` query param."""
    return parse_bearer(websocket.headers, websocket.query_params)


def decode_any_jwt(token: str) -> dict:
    """Try validating as a USER token first, then M2M using shared helpers."""
    try:
        return decode_any(
            token,
            user_cfg={
                "secret": settings.USER_JWT_SECRET_KEY,
                "algorithm": settings.USER_JWT_ALGORITHM,
                "issuer": settings.USER_JWT_ISSUER,
                "audience": settings.USER_JWT_AUDIENCE,
            },
            m2m_cfg={
                "secret": settings.M2M_JWT_SECRET_KEY,
                "algorithm": settings.M2M_JWT_ALGORITHM,
                "issuer": settings.M2M_JWT_ISSUER,
                "audience": settings.M2M_JWT_AUDIENCE,
            },
        )
    except AuthError as user_err:
        logger.debug("JWT validation failed: %s", user_err)
        raise
