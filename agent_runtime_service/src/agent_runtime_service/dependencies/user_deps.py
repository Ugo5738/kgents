from __future__ import annotations

from typing import Any, Dict

from fastapi import Depends, Header, HTTPException, Request, status

from shared.security.jwt import AuthError, decode_any, parse_bearer

from ..config import settings


async def get_current_user_token_data(
    request: Request,
    authorization: str | None = Header(default=None),
) -> Dict[str, Any]:
    """Dependency that validates either a USER or M2M JWT and returns its payload.

    Accepts Authorization: Bearer <token> header or `token` query param.
    """
    token = parse_bearer(request.headers, request.query_params)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")

    user_cfg = {
        "secret": settings.USER_JWT_SECRET_KEY,
        "algorithm": settings.USER_JWT_ALGORITHM,
        "issuer": settings.USER_JWT_ISSUER,
        "audience": settings.USER_JWT_AUDIENCE,
    }
    m2m_cfg = {
        "secret": settings.M2M_JWT_SECRET_KEY,
        "algorithm": settings.M2M_JWT_ALGORITHM,
        "issuer": settings.M2M_JWT_ISSUER,
        "audience": settings.M2M_JWT_AUDIENCE,
    }
    try:
        payload = decode_any(token, user_cfg, m2m_cfg)
    except AuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    return payload
