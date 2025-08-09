# agent_deployment_service/src/agent_deployment_service/routers/deployment_routes.py
"""
API routes for managing agent deployments.

This module defines the FastAPI endpoints for creating, listing, retrieving,
and deleting agent deployment records. All endpoints are protected and require
user authentication.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud import deployments as crud
from ..db import get_db
from ..dependencies.user_deps import get_current_user_id
from ..logging_config import logger
from ..schemas.common import PaginatedResponse
from ..schemas.deployment_schemas import DeploymentCreate, DeploymentResponse
from ..services import orchestration_service

# Initialize the router
router = APIRouter(
    prefix="/deployments",
    tags=["Deployments"],
    dependencies=[Depends(get_current_user_id)],  # Secure all routes in this router
)


@router.post(
    "/",
    response_model=DeploymentResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create a New Agent Deployment",
    description="Accepts a request to deploy a specific version of an agent. This process is asynchronous.",
)
async def create_deployment(
    deployment_data: DeploymentCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Creates a new deployment record and triggers the asynchronous deployment process.

    - **agent_id**: The ID of the agent to deploy.
    - **agent_version_id**: The specific version ID of the agent to deploy.

    The endpoint immediately returns a `pending` deployment record. The actual
    deployment happens in the background.
    """
    # Create the initial deployment record in the database
    deployment = await crud.create_deployment(db, deployment_data, user_id)

    background_tasks.add_task(
        orchestration_service.start_deployment_process, deployment.id
    )

    logger.info(f"Deployment process initiated for deployment ID: {deployment.id}")

    return deployment


@router.get(
    "/",
    response_model=PaginatedResponse[DeploymentResponse],
    summary="List User Deployments",
)
async def list_deployments(
    agent_id: Optional[UUID] = Query(
        None, description="Filter deployments by agent ID."
    ),
    skip: int = Query(0, ge=0, description="Pagination skip."),
    limit: int = Query(100, ge=1, le=200, description="Pagination limit."),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Retrieves a paginated list of deployments owned by the current user.
    """
    deployments, total = await crud.list_deployments(
        db, user_id=user_id, agent_id=agent_id, skip=skip, limit=limit
    )

    pages = (total + limit - 1) // limit if limit > 0 else 0
    page = (skip // limit) + 1 if limit > 0 else 1

    return PaginatedResponse(
        items=deployments,
        total=total,
        page=page,
        size=limit,
        pages=pages,
        has_next=page < pages,
        has_prev=page > 1,
        next_page=page + 1 if page < pages else None,
        prev_page=page - 1 if page > 1 else None,
    )


@router.get(
    "/{deployment_id}",
    response_model=DeploymentResponse,
    summary="Get Deployment Status",
)
async def get_deployment(
    deployment_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Retrieves the details and current status of a specific deployment.
    """
    # The CRUD function handles the ownership check and raises a 404 if not found
    return await crud.get_deployment(db, deployment_id, user_id)


@router.delete(
    "/{deployment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Terminate and Delete a Deployment",
)
async def delete_deployment(
    deployment_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Initiates the termination of a running agent and deletes its deployment record.
    This process is also asynchronous.
    """
    # This CRUD call also serves as an ownership check to ensure the user can delete it
    await crud.get_deployment(db, deployment_id, user_id)

    background_tasks.add_task(
        orchestration_service.start_undeploy_process, deployment_id
    )

    # Delete the record from our database
    await crud.delete_deployment(db, deployment_id, user_id)

    logger.info(f"Termination process initiated for deployment ID: {deployment_id}")

    # Return a 204 No Content response as is standard for DELETE operations
    return
