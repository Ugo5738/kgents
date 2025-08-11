from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from shared.schemas.user_schemas import UserTokenData

from ..config import settings
from ..logging_config import logger

# This tells FastAPI where a client *would* go to get a token,
# which is useful for OpenAPI documentation generation.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/users/login")


def get_current_user_token_data(token: str = Depends(oauth2_scheme)) -> UserTokenData:
    """
    A dependency that decodes and validates a JWT locally.
    It returns the token's payload if validation is successful.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = None

    # Some clients accidentally pass "Bearer <JWT>" as the token value, which results
    # in "Authorization: Bearer Bearer <JWT>". OAuth2PasswordBearer will then provide
    # a token string like "Bearer <JWT>", which breaks JWT decoding ("Not enough segments").
    # Be tolerant by stripping common prefixes and surrounding quotes.
    if isinstance(token, str):
        raw = token.strip()
        # Remove surrounding quotes if present
        if (raw.startswith("\"") and raw.endswith("\"")) or (
            raw.startswith("'") and raw.endswith("'")
        ):
            raw = raw[1:-1].strip()
        # Strip an accidental leading "Bearer "
        if raw.lower().startswith("bearer "):
            raw = raw.split(" ", 1)[1].strip()
        token = raw

    try:
        # Decode the JWT. This function checks the signature, expiration,
        # audience, and issuer all at once.
        payload = jwt.decode(
            token,
            settings.USER_JWT_SECRET_KEY,
            algorithms=[settings.USER_JWT_ALGORITHM],
            audience=settings.USER_JWT_AUDIENCE,
            issuer=settings.USER_JWT_ISSUER,
        )
    except JWTError as e:
        logger.warning(
            f"Failed to validate as a user token: {e}. Trying M2M validation..."
        )
        # If it fails, we don't immediately raise. We'll try the M2M secret next.
        pass

    # Step 2: If user validation failed, try to validate as an M2M token
    if payload is None:
        try:
            payload = jwt.decode(
                token,
                settings.M2M_JWT_SECRET_KEY,
                algorithms=[settings.M2M_JWT_ALGORITHM],
                audience=settings.M2M_JWT_AUDIENCE,
                issuer=settings.M2M_JWT_ISSUER,
            )
        except JWTError as e:
            logger.error(
                f"Failed to validate as M2M token after user validation failed: {e}"
            )
            # If both fail, the token is truly invalid.
            raise credentials_exception

    # Step 3: If we have a valid payload, parse it with our shared schema
    try:
        token_data = UserTokenData.model_validate(payload)
        return token_data
    except Exception as e:
        logger.error(f"Token payload failed Pydantic validation: {e}")
        raise credentials_exception


def get_current_user_id(
    token_data: UserTokenData = Depends(get_current_user_token_data),
) -> UUID:
    """
    A simple dependency that relies on get_current_user_token_data
    to get the validated payload, and then extracts just the user_id.

    Routes that only need the user's ID can depend on this for simplicity.
    """
    if not token_data.user_id:
        raise HTTPException(status_code=400, detail="User ID (sub) missing from token")
    return token_data.user_id
