from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..logging_config import logger
from ..models import Agent, AgentVersion
from ..models.agent import AgentStatus
from ..schemas.agent import AgentCreate, AgentUpdate
from ..schemas.langflow_schemas import LangflowFlow


async def create_agent(
    db: AsyncSession, agent_data: AgentCreate, user_id: UUID
) -> Agent:
    """
    Create a new agent with initial configuration.

    Args:
        db: Database session
        agent_data: Agent data to create
        user_id: ID of the user creating the agent

    Returns:
        Newly created agent
    """
    # Create agent
    agent = Agent(
        name=agent_data.name,
        description=agent_data.description,
        config=agent_data.config,
        status=agent_data.status,
        tags=agent_data.tags,
        user_id=user_id,
    )

    # Add and flush to get ID assigned
    db.add(agent)
    await db.flush()

    # Create initial version for this agent
    version = AgentVersion(
        agent_id=agent.id,
        version_number=1,  # First version
        config_snapshot=agent_data.config,
        user_id=user_id,
        change_summary="Initial version",
    )
    db.add(version)

    # Set the active version if the agent is published
    if agent.status == AgentStatus.PUBLISHED:
        agent.active_version_id = version.id

    # Commit transaction
    await db.commit()
    await db.refresh(agent)

    return agent


async def get_agent(
    db: AsyncSession, agent_id: UUID, user_id: UUID, with_versions: bool = False
) -> Optional[Agent]:
    """
    Get an agent by ID, ensuring the requesting user owns it.

    Args:
        db: Database session
        agent_id: ID of the agent to retrieve
        user_id: ID of the requesting user
        with_versions: Whether to load version history

    Returns:
        Agent if found and owned by the user, None otherwise

    Raises:
        HTTPException: If agent is not found
    """
    query = select(Agent).where(and_(Agent.id == agent_id, Agent.user_id == user_id))

    if with_versions:
        query = query.options(
            # Load all versions relationship
            selectinload(Agent.versions)
        )

    result = await db.execute(query)
    agent = result.unique().scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found",
        )

    return agent


async def get_agent_by_name(
    db: AsyncSession, name: str, user_id: UUID
) -> Optional[Agent]:
    """
    Get an agent by name, ensuring the requesting user owns it.

    Args:
        db: Database session
        name: Name of the agent to retrieve
        user_id: ID of the requesting user

    Returns:
        Agent if found and owned by the user, None otherwise
    """
    result = await db.execute(
        select(Agent).where(and_(Agent.name == name, Agent.user_id == user_id))
    )
    return result.scalar_one_or_none()


async def get_agents(
    db: AsyncSession,
    user_id: UUID,
    skip: int = 0,
    limit: int = 100,
    status: Optional[AgentStatus] = None,
) -> Tuple[List[Agent], int]:
    """
    Get a page of agents owned by the user, with optional status filter.

    Args:
        db: Database session
        user_id: ID of the requesting user
        skip: Number of items to skip (for pagination)
        limit: Maximum number of items to return (for pagination)
        status: Optional filter by agent status

    Returns:
        Tuple containing list of agents and total count
    """
    # Build the base query for agents owned by this user
    query = select(Agent).where(Agent.user_id == user_id)

    # Apply status filter if provided
    if status:
        query = query.where(Agent.status == status)

    # Get total count for pagination
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply pagination
    query = query.order_by(Agent.updated_at.desc()).offset(skip).limit(limit)

    # Execute query
    result = await db.execute(query)
    agents = result.scalars().all()

    return agents, total


async def update_agent(
    db: AsyncSession,
    agent_id: UUID,
    agent_data: AgentUpdate,
    user_id: UUID,
    create_version: bool = True,
) -> Agent:
    """
    Update an agent and optionally create a new version.

    Args:
        db: Database session
        agent_id: ID of the agent to update
        agent_data: Updated agent data
        user_id: ID of the requesting user
        create_version: Whether to create a new version (default: True)

    Returns:
        Updated agent

    Raises:
        HTTPException: If agent is not found or if configuration is updated
                      for a published agent without creating a new version
    """
    # Get agent, ensuring ownership
    agent = await get_agent(db, agent_id, user_id)

    # Make a copy of the current config before updates
    previous_config = agent.config.copy()
    has_config_changed = False

    # Update agent attributes
    if agent_data.name is not None:
        agent.name = agent_data.name

    if agent_data.description is not None:
        agent.description = agent_data.description

    if agent_data.tags is not None:
        agent.tags = agent_data.tags

    if agent_data.config is not None:
        agent.config = agent_data.config
        has_config_changed = True

    if agent_data.status is not None:
        agent.status = agent_data.status

    # If config changed and create_version is True, create a new version
    if has_config_changed and create_version:
        # Find the latest version number
        result = await db.execute(
            select(func.max(AgentVersion.version_number)).where(
                AgentVersion.agent_id == agent_id
            )
        )
        latest_version = result.scalar_one_or_none() or 0

        # Create new version
        version = AgentVersion(
            agent_id=agent.id,
            version_number=latest_version + 1,
            config_snapshot=agent.config,
            user_id=user_id,
            # Default change summary can be updated later
            change_summary=f"Updated configuration (v{latest_version + 1})",
        )
        db.add(version)
        await db.flush()

        # If agent is published, update active version
        if agent.status == AgentStatus.PUBLISHED:
            agent.active_version_id = version.id

    # If config changed but we're not creating a version, prevent this for published agents
    elif (
        has_config_changed
        and not create_version
        and agent.status == AgentStatus.PUBLISHED
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update configuration of published agent without creating a new version",
        )

    # Save changes
    await db.commit()
    await db.refresh(agent)

    return agent


async def delete_agent(db: AsyncSession, agent_id: UUID, user_id: UUID) -> bool:
    """
    Delete an agent and all its versions.

    Args:
        db: Database session
        agent_id: ID of the agent to delete
        user_id: ID of the requesting user

    Returns:
        True if deleted successfully

    Raises:
        HTTPException: If agent is not found
    """
    # Get agent, ensuring ownership
    agent = await get_agent(db, agent_id, user_id)

    # Delete the agent (cascades to versions due to relationship configuration)
    await db.delete(agent)
    await db.commit()

    return True


async def publish_agent(
    db: AsyncSession, agent_id: UUID, user_id: UUID, version_id: Optional[UUID] = None
) -> Agent:
    """
    Publish an agent, making it available for deployment.

    If version_id is provided, that specific version becomes active.
    Otherwise, the latest version is used.

    Args:
        db: Database session
        agent_id: ID of the agent to publish
        user_id: ID of the requesting user
        version_id: Optional specific version to publish

    Returns:
        Updated agent with published status

    Raises:
        HTTPException: If agent or specified version is not found
    """
    # Get agent, ensuring ownership
    agent = await get_agent(db, agent_id, user_id)

    # Handle version selection
    if version_id:
        # Verify the version exists and belongs to this agent
        result = await db.execute(
            select(AgentVersion).where(
                and_(AgentVersion.id == version_id, AgentVersion.agent_id == agent_id)
            )
        )
        version = result.scalar_one_or_none()

        if not version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version with ID {version_id} not found for this agent",
            )

        agent.active_version_id = version.id
    else:
        # Use the latest version
        result = await db.execute(
            select(AgentVersion)
            .where(AgentVersion.agent_id == agent_id)
            .order_by(AgentVersion.version_number.desc())
            .limit(1)
        )
        latest_version = result.scalar_one_or_none()

        if not latest_version:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot publish agent without any versions",
            )

        agent.active_version_id = latest_version.id

    # Update status to PUBLISHED
    agent.status = AgentStatus.PUBLISHED

    # Save changes
    await db.commit()
    await db.refresh(agent)

    return agent


async def archive_agent(db: AsyncSession, agent_id: UUID, user_id: UUID) -> Agent:
    """
    Archive an agent, preventing it from being deployed.

    Args:
        db: Database session
        agent_id: ID of the agent to archive
        user_id: ID of the requesting user

    Returns:
        Updated agent with archived status

    Raises:
        HTTPException: If agent is not found
    """
    # Get agent, ensuring ownership
    agent = await get_agent(db, agent_id, user_id)

    # Update status to ARCHIVED
    agent.status = AgentStatus.ARCHIVED

    # Save changes
    await db.commit()
    await db.refresh(agent)

    return agent


async def import_agent_from_langflow(
    db: AsyncSession,
    flow_data: LangflowFlow,
    user_id: UUID,
    existing_agent_id: Optional[UUID] = None,
    create_version: bool = True,
) -> Agent:
    """
    Handles the business logic of creating or updating an agent from a Langflow flow.
    """
    agent_config = {"langflow_data": flow_data.data, "source": "langflow_import"}

    # --- Case 1: Updating an existing agent ---
    if existing_agent_id:
        try:
            update_data = AgentUpdate(
                name=flow_data.name,
                description=flow_data.description,
                config=agent_config,
            )
            updated_agent = await update_agent(
                db,
                existing_agent_id,
                update_data,
                user_id,
                create_version=create_version,
            )
            logger.info(f"Updated agent {updated_agent.id} from Langflow import.")
            return updated_agent
        except HTTPException as e:
            if e.status_code == 404:  # If agent not found, fall through to create
                pass
            else:
                raise

    # --- Case 2: Creating a new agent ---
    # Check for name conflicts before creating
    existing_by_name = await get_agent_by_name(db, flow_data.name, user_id)
    if existing_by_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent with name '{flow_data.name}' already exists for this user.",
        )

    create_data = AgentCreate(
        name=flow_data.name,
        description=flow_data.description
        or f"Imported from Langflow: {flow_data.name}",
        config=agent_config,
        status=AgentStatus.DRAFT,
    )
    new_agent = await create_agent(db, create_data, user_id)
    logger.info(f"Created new agent {new_agent.id} from Langflow import.")
    return new_agent
