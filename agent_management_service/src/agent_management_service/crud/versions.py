from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from agent_management_service.models import Agent, AgentVersion
from agent_management_service.schemas.agent_version import (
    AgentVersionCreate,
    AgentVersionUpdate,
)


async def create_agent_version(
    db: AsyncSession, version_data: AgentVersionCreate, user_id: UUID
) -> AgentVersion:
    """
    Create a new version for an agent.

    Args:
        db: Database session
        version_data: Version data to create
        user_id: ID of the user creating the version

    Returns:
        Newly created version

    Raises:
        HTTPException: If agent not found or user doesn't own the agent
    """
    # Verify agent exists and is owned by the user
    result = await db.execute(
        select(Agent).where(
            and_(Agent.id == version_data.agent_id, Agent.user_id == user_id)
        )
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {version_data.agent_id} not found",
        )

    # Determine version number if not provided
    version_number = version_data.version_number
    if version_number is None:
        # Find the latest version number
        result = await db.execute(
            select(func.max(AgentVersion.version_number)).where(
                AgentVersion.agent_id == version_data.agent_id
            )
        )
        latest_version = result.scalar_one_or_none() or 0
        version_number = latest_version + 1

    # Create the new version
    version = AgentVersion(
        agent_id=version_data.agent_id,
        version_number=version_number,
        config_snapshot=version_data.config_snapshot,
        change_summary=version_data.change_summary,
        user_id=user_id,
    )

    db.add(version)
    await db.commit()
    await db.refresh(version)

    return version


async def get_agent_version(
    db: AsyncSession,
    version_id: UUID,
    user_id: UUID,
    bypass_ownership_check: bool = False,
) -> AgentVersion:
    """
    Get a specific version by ID, ensuring user ownership.

    Args:
        db: Database session
        version_id: ID of the version to retrieve
        user_id: ID of the requesting user
        If bypass_ownership_check is True, it will fetch the version regardless of the user_id.

    Returns:
        Version if found

    Raises:
        HTTPException: If version not found or user doesn't own the agent
    """
    query = select(AgentVersion).where(AgentVersion.id == version_id)

    # Only check for user ownership if the flag is False
    if not bypass_ownership_check:
        query = query.join(Agent).where(Agent.user_id == user_id)

    result = await db.execute(query)
    version = result.scalar_one_or_none()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent version with ID {version_id} not found",
        )

    return version


async def get_latest_agent_version(
    db: AsyncSession, agent_id: UUID, user_id: UUID
) -> Optional[AgentVersion]:
    """
    Get the latest version for an agent.

    Args:
        db: Database session
        agent_id: ID of the agent
        user_id: ID of the requesting user

    Returns:
        Latest version if found, None otherwise

    Raises:
        HTTPException: If agent not found or user doesn't own the agent
    """
    # Verify agent exists and is owned by the user
    result = await db.execute(
        select(Agent).where(and_(Agent.id == agent_id, Agent.user_id == user_id))
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found",
        )

    # Get the latest version
    result = await db.execute(
        select(AgentVersion)
        .where(AgentVersion.agent_id == agent_id)
        .order_by(AgentVersion.version_number.desc())
        .limit(1)
    )
    version = result.scalar_one_or_none()

    return version


async def get_agent_versions(
    db: AsyncSession, agent_id: UUID, user_id: UUID, skip: int = 0, limit: int = 100
) -> Tuple[List[AgentVersion], int]:
    """
    Get a paginated list of versions for an agent.

    Args:
        db: Database session
        agent_id: ID of the agent
        user_id: ID of the requesting user
        skip: Number of items to skip (for pagination)
        limit: Maximum number of items to return (for pagination)

    Returns:
        Tuple containing list of versions and total count

    Raises:
        HTTPException: If agent not found or user doesn't own the agent
    """
    # Verify agent exists and is owned by the user
    result = await db.execute(
        select(Agent).where(and_(Agent.id == agent_id, Agent.user_id == user_id))
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found",
        )

    # Base query for versions
    query = select(AgentVersion).where(AgentVersion.agent_id == agent_id)

    # Get total count for pagination
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply sorting and pagination
    query = query.order_by(AgentVersion.version_number.desc()).offset(skip).limit(limit)

    # Execute query
    result = await db.execute(query)
    versions = result.scalars().all()

    return versions, total


async def update_agent_version(
    db: AsyncSession, version_id: UUID, version_data: AgentVersionUpdate, user_id: UUID
) -> AgentVersion:
    """
    Update an agent version.

    Note: This only allows updating metadata like change_summary, not the config_snapshot
    which should be immutable for auditing purposes.

    Args:
        db: Database session
        version_id: ID of the version to update
        version_data: Version data to update
        user_id: ID of the requesting user

    Returns:
        Updated version

    Raises:
        HTTPException: If version not found or user doesn't own the agent
    """
    version = await get_agent_version(db, version_id, user_id)

    # Update allowed fields
    if version_data.change_summary is not None:
        version.change_summary = version_data.change_summary

    await db.commit()
    await db.refresh(version)

    return version
