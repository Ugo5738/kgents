from __future__ import annotations

from typing import Any, Mapping, Optional

from jose import JWTError, jwt


class AuthError(Exception):
    pass


def parse_bearer(headers: Mapping[str, str], query_params: Optional[Mapping[str, Any]] = None) -> Optional[str]:
    """Parse a Bearer token from HTTP headers or query params.

    - Looks for Authorization: Bearer <token>
    - Falls back to query param `token`
    """
    # headers are case-insensitive in ASGI frameworks but presented as a case-preserving mapping
    auth = headers.get("authorization") or headers.get("Authorization")
    if auth:
        parts = auth.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
    if query_params is not None:
        token = query_params.get("token")  # type: ignore[index]
        if isinstance(token, str) and token:
            return token
    return None


def decode_jwt(
    token: str,
    *,
    secret: str,
    algorithm: str,
    issuer: Optional[str] = None,
    audience: Optional[str] = None,
) -> dict:
    """Decode and verify a JWT with flexible verification flags.

    If issuer or audience are None/empty, their verification is disabled.
    """
    options = {
        "verify_signature": True,
        "verify_exp": True,
        "verify_iss": bool(issuer),
        "verify_aud": bool(audience),
    }
    try:
        return jwt.decode(
            token,
            secret,
            algorithms=[algorithm],
            audience=audience if audience else None,
            issuer=issuer if issuer else None,
            options=options,
        )
    except JWTError as e:
        raise AuthError(str(e))


def decode_any(token: str, user_cfg: dict, m2m_cfg: dict) -> dict:
    """Try validating as USER first, then M2M. Configs should include:
    {secret, algorithm, issuer, audience}
    """
    try:
        return decode_jwt(
            token,
            secret=user_cfg["secret"],
            algorithm=user_cfg["algorithm"],
            issuer=user_cfg.get("issuer"),
            audience=user_cfg.get("audience"),
        )
    except AuthError:
        # try m2m
        return decode_jwt(
            token,
            secret=m2m_cfg["secret"],
            algorithm=m2m_cfg["algorithm"],
            issuer=m2m_cfg.get("issuer"),
            audience=m2m_cfg.get("audience"),
        )
