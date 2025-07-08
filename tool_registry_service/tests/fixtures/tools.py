"""
Test fixtures for tool and tool category data.

This module provides factory functions for creating test data for tools and tool categories.
"""

import uuid
from typing import Dict, List, Optional

from tool_registry_service.models.tool import Tool, ToolCategory, ToolExecution, ToolType, ExecutionEnvironment


def create_test_category(
    id: Optional[uuid.UUID] = None,
    name: str = "Test Category",
    description: Optional[str] = "Test description",
    display_order: int = 0
) -> ToolCategory:
    """
    Create a test tool category with specified parameters.
    
    Args:
        id: Optional UUID for the category
        name: Category name
        description: Category description
        display_order: Display order for sorting
        
    Returns:
        ToolCategory: Populated tool category instance
    """
    return ToolCategory(
        id=id or uuid.uuid4(),
        name=name,
        description=description,
        display_order=display_order,
        icon="test-icon",
        color="#333333",
    )


def create_test_tool(
    id: Optional[uuid.UUID] = None,
    name: str = "Test Tool",
    description: str = "Test tool description",
    category_id: Optional[uuid.UUID] = None,
    owner_id: Optional[uuid.UUID] = None,
    is_public: bool = False,
    is_approved: bool = False,
    tool_type: ToolType = ToolType.HTTP,
    execution_env: ExecutionEnvironment = ExecutionEnvironment.SANDBOX,
    config: Optional[Dict] = None,
) -> Tool:
    """
    Create a test tool with specified parameters.
    
    Args:
        id: Optional UUID for the tool
        name: Tool name
        description: Tool description
        category_id: Optional category ID
        owner_id: Owner user ID
        is_public: Whether the tool is public
        is_approved: Whether the tool is approved
        tool_type: Tool type (HTTP, PYTHON, etc.)
        execution_env: Execution environment
        config: Tool configuration
        
    Returns:
        Tool: Populated tool instance
    """
    if config is None:
        if tool_type == ToolType.HTTP:
            config = {
                "method": "GET",
                "url": "https://api.example.com/test",
                "headers": {"Content-Type": "application/json"},
            }
        elif tool_type == ToolType.PYTHON:
            config = {
                "code": "def execute(input_data):\n    return {'result': input_data['value'] * 2}"
            }
        elif tool_type == ToolType.JAVASCRIPT:
            config = {
                "code": "function execute(inputData) {\n    return {result: inputData.value * 2};\n}"
            }
        elif tool_type == ToolType.COMMAND:
            config = {
                "command": "echo ${input}",
                "shell": True,
            }
    
    return Tool(
        id=id or uuid.uuid4(),
        name=name,
        slug=name.lower().replace(" ", "-"),
        description=description,
        category_id=category_id,
        owner_id=owner_id or uuid.uuid4(),
        is_public=is_public,
        is_approved=is_approved,
        is_active=True,
        tool_type=tool_type,
        execution_env=execution_env,
        config=config,
        input_schema={"type": "object", "properties": {"value": {"type": "number"}}},
        output_schema={"type": "object", "properties": {"result": {"type": "number"}}},
        authentication_config=None,
        metadata={"tags": ["test", "fixture"]},
    )


def create_test_execution(
    id: Optional[uuid.UUID] = None,
    tool_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
    status: str = "completed",
    inputs: Optional[Dict] = None,
    outputs: Optional[Dict] = None,
    error: Optional[str] = None,
) -> ToolExecution:
    """
    Create a test tool execution record.
    
    Args:
        id: Optional UUID for the execution
        tool_id: Tool ID
        user_id: User ID
        status: Execution status
        inputs: Input data
        outputs: Output data
        error: Error message if any
        
    Returns:
        ToolExecution: Populated tool execution instance
    """
    return ToolExecution(
        id=id or uuid.uuid4(),
        tool_id=tool_id or uuid.uuid4(),
        user_id=user_id or uuid.uuid4(),
        status=status,
        inputs=inputs or {"value": 5},
        outputs=outputs or {"result": 10},
        error=error,
        execution_time_ms=150,
        metadata={"source": "test"},
    )
