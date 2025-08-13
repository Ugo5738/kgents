from __future__ import annotations

from typing import Optional

from fastapi import WebSocket
from jose import JWTError, jwt

from .config import settings
from .logging_config import logger


class AuthError(Exception):
    pass


def extract_bearer_token_from_ws(websocket: WebSocket) -> Optional[str]:
    """Extract Bearer token from Authorization header or `token` query param."""
    # Headers are case-insensitive; FastAPI provides a CIMultiDict-like .headers
    auth = websocket.headers.get("authorization")
    if auth:
        parts = auth.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
    # Fallback to query param `token`
    token = websocket.query_params.get("token")
    if token:
        return token
    return None


def decode_user_jwt(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.USER_JWT_SECRET_KEY,
            algorithms=[settings.USER_JWT_ALGORITHM],
            audience=settings.USER_JWT_AUDIENCE,
            issuer=settings.USER_JWT_ISSUER,
            options={
                "verify_signature": True,
                "verify_aud": True,
                "verify_iss": True,
                "verify_exp": True,
            },
        )
        return payload
    except JWTError as e:
        raise AuthError(f"Invalid USER JWT: {e}")


def decode_m2m_jwt(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.M2M_JWT_SECRET_KEY,
            algorithms=[settings.M2M_JWT_ALGORITHM],
            audience=settings.M2M_JWT_AUDIENCE,
            issuer=settings.M2M_JWT_ISSUER,
            options={
                "verify_signature": True,
                "verify_aud": True,
                "verify_iss": True,
                "verify_exp": True,
            },
        )
        return payload
    except JWTError as e:
        raise AuthError(f"Invalid M2M JWT: {e}")


def decode_any_jwt(token: str) -> dict:
    """Try validating as a USER token first, then M2M."""
    try:
        return decode_user_jwt(token)
    except AuthError as user_err:
        logger.debug("USER JWT validation failed, trying M2M: %s", user_err)
    # Try M2M
    return decode_m2m_jwt(token)
