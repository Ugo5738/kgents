import os

import jwt
from fastapi import Header, HTTPException, status

# JWT configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "secret")
ALGORITHM = "HS256"


def create_access_token(subject: str) -> str:
    """
    Create a JWT access token for a given subject.
    """
    payload = {"sub": subject}
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return token


def decode_access_token(token: str) -> str:
    """
    Decode a JWT token and return its subject.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        if subject is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload missing subject"
            )
        return subject
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


def get_current_user_id(authorization: str = Header(...)) -> int:
    """
    FastAPI dependency to extract and validate JWT, returning user ID.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme"
        )
    token = authorization.split(" ")[1]
    subject = decode_access_token(token)
    try:
        return int(subject)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject"
        ) 