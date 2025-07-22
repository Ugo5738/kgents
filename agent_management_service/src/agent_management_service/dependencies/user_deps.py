from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from agent_management_service.config import settings
from agent_management_service.logging_config import logger
from shared.schemas.user_schemas import UserTokenData

# This tells FastAPI where a client *would* go to get a token,
# which is useful for OpenAPI documentation generation.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/users/login")


def get_current_user_token_data(token: str = Depends(oauth2_scheme)) -> UserTokenData:
    """
    A dependency that decodes and validates a JWT locally.
    It returns the token's payload if validation is successful.
    This is the core of our stateless authentication pattern.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decode the JWT. This function checks the signature, expiration,
        # audience, and issuer all at once.
        payload = jwt.decode(
            token,
            settings.M2M_JWT_SECRET_KEY,  # The shared secret key
            algorithms=[settings.M2M_JWT_ALGORITHM],
            audience=settings.M2M_JWT_AUDIENCE,
            issuer=settings.M2M_JWT_ISSUER,
        )

        # Validate the payload's structure using our Pydantic model.
        token_data = UserTokenData.model_validate(payload)
        return token_data

    except JWTError as e:
        logger.warning(f"JWT validation error: {e}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"An unexpected error occurred during token decoding: {e}")
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
    return UUID(token_data.user_id)
