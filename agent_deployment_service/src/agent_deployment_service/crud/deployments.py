# agent_deployment_service/src/agent_deployment_service/crud/deployments.py
"""
CRUD (Create, Read, Update, Delete) operations for Deployment models.

This module encapsulates all the database interaction logic for deployments,
keeping the API routers clean and focused on handling HTTP requests.
"""

from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_deployment_service.logging_config import logger
from agent_deployment_service.models.deployment import Deployment, DeploymentStatus
from agent_deployment_service.schemas.deployment_schemas import (
    DeploymentCreate,
    DeploymentUpdate,
)


async def create_deployment(
    db: AsyncSession, deployment_data: DeploymentCreate, user_id: UUID
) -> Deployment:
    """
    Creates a new deployment record in the database.

    Args:
        db: The SQLAlchemy async session.
        deployment_data: The Pydantic schema containing data for the new deployment.
        user_id: The ID of the user initiating the deployment.

    Returns:
        The newly created Deployment object.
    """
    logger.info(
        f"Creating new deployment record for agent {deployment_data.agent_id} by user {user_id}"
    )

    new_deployment = Deployment(
        agent_id=deployment_data.agent_id,
        agent_version_id=deployment_data.agent_version_id,
        user_id=user_id,
        status=DeploymentStatus.PENDING,  # Always starts as pending
    )

    db.add(new_deployment)
    await db.commit()
    await db.refresh(new_deployment)

    logger.info(f"Successfully created deployment record with ID: {new_deployment.id}")
    return new_deployment


async def get_deployment(
    db: AsyncSession, deployment_id: UUID, user_id: UUID
) -> Deployment:
    """
    Retrieves a single deployment by its ID, ensuring user ownership.

    Args:
        db: The SQLAlchemy async session.
        deployment_id: The ID of the deployment to retrieve.
        user_id: The ID of the user requesting the deployment.

    Returns:
        The Deployment object if found and owned by the user.

    Raises:
        HTTPException: If the deployment is not found.
    """
    query = select(Deployment).where(
        Deployment.id == deployment_id, Deployment.user_id == user_id
    )
    result = await db.execute(query)
    deployment = result.scalar_one_or_none()

    if not deployment:
        logger.warning(
            f"Deployment with ID {deployment_id} not found for user {user_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment with ID {deployment_id} not found.",
        )

    return deployment


async def list_deployments(
    db: AsyncSession,
    user_id: UUID,
    agent_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
) -> Tuple[List[Deployment], int]:
    """
    Lists deployments for a user, with optional filtering by agent.

    Args:
        db: The SQLAlchemy async session.
        user_id: The ID of the user whose deployments are being listed.
        agent_id: Optional agent ID to filter deployments.
        skip: Number of records to skip for pagination.
        limit: Maximum number of records to return.

    Returns:
        A tuple containing a list of Deployment objects and the total count.
    """
    query_filters = [Deployment.user_id == user_id]
    if agent_id:
        query_filters.append(Deployment.agent_id == agent_id)

    count_query = select(func.count(Deployment.id)).where(and_(*query_filters))
    total_count_result = await db.execute(count_query)
    total = total_count_result.scalar_one()

    items_query = (
        select(Deployment)
        .where(and_(*query_filters))
        .order_by(Deployment.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    items_result = await db.execute(items_query)
    items = items_result.scalars().all()

    return items, total


async def update_deployment(
    db: AsyncSession,
    deployment_id: UUID,
    user_id: UUID,
    update_data: DeploymentUpdate,
) -> Deployment:
    """
    Updates the status and metadata of a deployment.

    Args:
        db: The SQLAlchemy async session.
        deployment_id: The ID of the deployment to update.
        user_id: The ID of the user who owns the deployment (for verification).
        update_data: A Pydantic model with the fields to update.

    Returns:
        The updated Deployment object.
    """
    deployment = await get_deployment(db, deployment_id, user_id)

    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(deployment, key, value)

    if "status" in update_dict and update_dict["status"] != DeploymentStatus.FAILED:
        deployment.error_message = None

    await db.commit()
    await db.refresh(deployment)

    logger.info(f"Updated deployment {deployment.id} with data: {update_dict}")
    return deployment


async def delete_deployment(
    db: AsyncSession, deployment_id: UUID, user_id: UUID
) -> None:
    """
    Deletes a deployment record from the database.

    Args:
        db: The SQLAlchemy async session.
        deployment_id: The ID of the deployment to delete.
        user_id: The ID of the user who owns the deployment.
    """
    deployment = await get_deployment(db, deployment_id, user_id)

    await db.delete(deployment)
    await db.commit()

    logger.info(f"Deleted deployment record with ID: {deployment_id}")
