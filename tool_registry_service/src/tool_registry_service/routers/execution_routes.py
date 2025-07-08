"""
Tool execution routes for the Tool Registry Service.

This module defines FastAPI routes for executing tools in a secure sandbox environment
and tracking execution history.
"""

import logging
import time
import uuid
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from tool_registry_service.config import settings
from tool_registry_service.crud import tools as tool_crud
from tool_registry_service.db import get_db
from tool_registry_service.dependencies.auth import get_current_user_id
from tool_registry_service.models.tool import Tool, ToolExecution
from tool_registry_service.schemas.common import Message
from tool_registry_service.schemas.tool import (
    ToolExecutionRequest,
    ToolExecutionResponse,
)
from tool_registry_service.services.execution_service import (
    execute_tool,
    sanitize_inputs,
)

router = APIRouter(
    prefix="/execute",
    tags=["tool execution"],
    responses={401: {"model": Message}},
)

logger = logging.getLogger(__name__)


@router.post(
    "/{tool_id}",
    response_model=ToolExecutionResponse,
    summary="Execute a tool",
    description="Execute a tool with the provided input parameters",
)
async def execute_tool_handler(
    tool_id: UUID = Path(..., description="Tool ID"),
    execution_request: ToolExecutionRequest = None,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Execute a tool with the provided input parameters.

    This endpoint:
    1. Validates the tool exists and user has access
    2. Validates input parameters against the tool schema
    3. Creates an execution record
    4. Executes the tool in a sandboxed environment
    5. Updates the execution record with results

    Depending on the tool type, execution might happen:
    - Synchronously (for quick tools)
    - Asynchronously as a background task (for longer-running tools)

    Users can only execute tools they own or that are public and approved.
    """
    # Validate execution is enabled
    if not settings.SANDBOX_EXECUTION_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tool execution is currently disabled",
        )

    # Get tool and verify access
    tool = await tool_crud.get_tool(db, tool_id, owner_id=user_id)

    # Additional check: tool must be approved for execution if it's public
    if tool.is_public and not tool.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This tool is not approved for execution yet",
        )

    # Ensure we have valid inputs
    if execution_request is None:
        execution_request = ToolExecutionRequest(inputs={})

    # Sanitize and validate inputs
    try:
        sanitized_inputs = await sanitize_inputs(tool, execution_request.inputs)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid input parameters: {str(e)}",
        )

    # Create execution record
    execution_id = uuid.uuid4()
    execution = ToolExecution(
        id=execution_id,
        tool_id=tool.id,
        user_id=user_id,
        agent_id=execution_request.agent_id,
        inputs=sanitized_inputs,
        success=False,  # Will be updated after execution
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)

    # Set timeout (use request override if provided and within limits)
    timeout_seconds = min(
        execution_request.timeout_seconds or tool.timeout_seconds,
        settings.MAX_TOOL_EXECUTION_TIME_SECONDS,
    )

    # Start timing execution
    start_time = time.time()

    try:
        # Execute the tool
        result = await execute_tool(tool, sanitized_inputs, timeout_seconds)

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Update execution record with success
        execution.outputs = result
        execution.error = None
        execution.success = True
        execution.duration_ms = duration_ms

        await db.commit()
        await db.refresh(execution)

        # Return execution response
        return execution

    except Exception as e:
        # Calculate duration even for failed executions
        duration_ms = int((time.time() - start_time) * 1000)

        # Update execution record with error
        execution.outputs = None
        execution.error = str(e)
        execution.success = False
        execution.duration_ms = duration_ms

        await db.commit()

        # Re-raise as HTTPException
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool execution failed: {str(e)}",
        )


@router.get(
    "/history/{execution_id}",
    response_model=ToolExecutionResponse,
    summary="Get execution result",
    description="Get the result of a previous tool execution",
)
async def get_execution_result(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Get the result of a previous tool execution.

    Users can only view their own execution results.
    """
    # Find execution record
    execution = await db.get(ToolExecution, execution_id)

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution record not found",
        )

    # Check ownership
    if execution.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this execution record",
        )

    return execution
