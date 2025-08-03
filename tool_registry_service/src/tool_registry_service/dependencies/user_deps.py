from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from shared.schemas.user_schemas import UserTokenData

from ..config import settings
from ..logging_config import logger

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

    try:
        # Decode the JWT. This function checks the signature, expiration,
        # audience, and issuer all at once.
        payload = jwt.decode(
            token,
            settings.USER_JWT_SECRET_KEY,  # The shared secret key
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


def require_admin_user(
    token_data: UserTokenData = Depends(get_current_user_token_data),
) -> UserTokenData:
    """
    Dependency that checks if the current user has the 'admin' role.
    Raises a 403 Forbidden error if the user is not an admin.
    """
    if "admin" not in token_data.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required for this operation.",
        )
    return token_data
