# src/auth_service/crud/profiles.py
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from auth_service.logging_config import logger

from ..models.profile import Profile
from ..schemas.user_schemas import ProfileCreate


async def get_profile_by_user_id(db: AsyncSession, user_id: UUID) -> Profile | None:
    """Retrieves a user profile from the database by user_id."""
    try:
        result = await db.execute(select(Profile).filter(Profile.user_id == user_id))
        return result.scalars().first()
    except SQLAlchemyError as e:
        logger.error(
            f"Database error while fetching profile for user_id {user_id}: {e}",
            exc_info=True,
        )
        return None


async def get_profile_by_username(db: AsyncSession, username: str) -> Profile | None:
    """Retrieves a user profile from the database by username."""
    try:
        result = await db.execute(select(Profile).filter(Profile.username == username))
        return result.scalars().first()
    except SQLAlchemyError as e:
        logger.error(
            f"Database error while fetching profile for username {username}: {e}",
            exc_info=True,
        )
        return None


async def create_profile(db: AsyncSession, profile_in: ProfileCreate) -> Profile | None:
    """Creates a new user profile in the database."""
    try:
        new_profile = Profile(**profile_in.model_dump())
        db.add(new_profile)
        await db.flush()
        await db.refresh(new_profile)
        logger.info(f"Profile created successfully for user_id: {new_profile.user_id}")
        return new_profile
    except SQLAlchemyError as e:
        logger.error(
            f"Database error during profile creation for user_id {profile_in.user_id}: {e}",
            exc_info=True,
        )
        await db.rollback()
        return None


async def get_profile_by_email(db: AsyncSession, email: str) -> Profile | None:
    """Retrieves a user profile from the database by email."""
    try:
        result = await db.execute(select(Profile).filter(Profile.email == email))
        return result.scalars().first()
    except SQLAlchemyError as e:
        logger.error(
            f"Database error while fetching profile for email {email}: {e}",
            exc_info=True,
        )
        return None


async def update_profile(
    db: AsyncSession, profile: Profile, update_data: dict
) -> Profile | None:
    """Updates a user profile in the database."""
    try:
        for key, value in update_data.items():
            if hasattr(profile, key) and value is not None:
                setattr(profile, key, value)

        await db.flush()
        await db.refresh(profile)
        logger.info(f"Profile updated successfully for user_id: {profile.user_id}")
        return profile
    except SQLAlchemyError as e:
        logger.error(
            f"Database error during profile update for user_id {profile.user_id}: {e}",
            exc_info=True,
        )
        await db.rollback()
        return None


async def deactivate_profile(db: AsyncSession, user_id: UUID) -> Profile | None:
    """Deactivates a user profile by setting is_active to False."""
    try:
        profile = await get_profile_by_user_id(db, user_id)
        if not profile:
            return None

        profile.is_active = False
        await db.flush()
        await db.refresh(profile)
        logger.info(f"Profile deactivated successfully for user_id: {profile.user_id}")
        return profile
    except SQLAlchemyError as e:
        logger.error(
            f"Database error during profile deactivation for user_id {user_id}: {e}",
            exc_info=True,
        )
        await db.rollback()
        return None
