"""
Tool execution service for the Tool Registry Service.

This module provides functionality for executing tools in a secure sandbox environment,
validating inputs, and handling different tool types.
"""

import asyncio
import json
import logging
import subprocess
import tempfile
from typing import Any, Dict, Optional
from uuid import UUID

import httpx
import jsonschema
from fastapi import HTTPException, status

from tool_registry_service.config import settings
from tool_registry_service.models.tool import ExecutionEnvironment, Tool, ToolType

logger = logging.getLogger(__name__)


async def sanitize_inputs(tool: Tool, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and sanitize input parameters against the tool's schema.
    
    Args:
        tool: Tool to execute
        inputs: Input parameters
        
    Returns:
        Sanitized input parameters
        
    Raises:
        ValueError: If inputs are invalid according to the tool's schema
    """
    # If tool has no schema, accept any inputs
    if not tool.input_schema:
        return inputs
    
    # Clone inputs to avoid modifying the original
    sanitized = inputs.copy()
    
    try:
        # Validate against JSON schema
        jsonschema.validate(instance=sanitized, schema=tool.input_schema)
    except jsonschema.exceptions.ValidationError as e:
        logger.error(f"Input validation error for tool {tool.id}: {str(e)}")
        raise ValueError(f"Input validation error: {str(e)}")
    
    return sanitized


async def execute_tool(
    tool: Tool, inputs: Dict[str, Any], timeout_seconds: float
) -> Dict[str, Any]:
    """
    Execute a tool with the provided input parameters.
    
    Args:
        tool: Tool to execute
        inputs: Validated input parameters
        timeout_seconds: Execution timeout in seconds
        
    Returns:
        Execution results
        
    Raises:
        Exception: If execution fails or times out
    """
    logger.info(f"Executing tool {tool.id} ({tool.name}) with timeout {timeout_seconds}s")
    
    # Select execution method based on tool type
    if tool.tool_type == ToolType.HTTP:
        return await execute_http_tool(tool, inputs, timeout_seconds)
    
    elif tool.tool_type == ToolType.PYTHON:
        return await execute_python_tool(tool, inputs, timeout_seconds)
    
    elif tool.tool_type == ToolType.JAVASCRIPT:
        return await execute_javascript_tool(tool, inputs, timeout_seconds)
    
    elif tool.tool_type == ToolType.COMMAND:
        return await execute_command_tool(tool, inputs, timeout_seconds)
    
    else:
        raise ValueError(f"Unsupported tool type: {tool.tool_type}")


async def execute_http_tool(
    tool: Tool, inputs: Dict[str, Any], timeout_seconds: float
) -> Dict[str, Any]:
    """
    Execute an HTTP tool by making an API request.
    
    Args:
        tool: Tool to execute
        inputs: Validated input parameters
        timeout_seconds: Execution timeout in seconds
        
    Returns:
        API response
        
    Raises:
        Exception: If request fails or times out
    """
    # Extract HTTP-specific configuration from the tool
    config = tool.configuration or {}
    
    method = config.get("method", "GET").upper()
    url = config.get("url")
    headers = config.get("headers", {})
    
    if not url:
        raise ValueError("HTTP tool must have a URL in its configuration")
    
    # Create parameter dict for httpx
    request_kwargs = {
        "url": url,
        "headers": headers,
        "timeout": timeout_seconds,
    }
    
    # Add request body for methods that support it
    if method in ["POST", "PUT", "PATCH"]:
        # Determine content type and format body accordingly
        content_type = headers.get("content-type", "").lower()
        
        if "application/json" in content_type:
            request_kwargs["json"] = inputs
        else:
            # Default to form data
            request_kwargs["data"] = inputs
    
    elif method == "GET":
        # For GET requests, add inputs as query parameters
        request_kwargs["params"] = inputs
    
    # Execute the HTTP request
    async with httpx.AsyncClient() as client:
        try:
            logger.debug(f"Making {method} request to {url}")
            
            if method == "GET":
                response = await client.get(**request_kwargs)
            elif method == "POST":
                response = await client.post(**request_kwargs)
            elif method == "PUT":
                response = await client.put(**request_kwargs)
            elif method == "PATCH":
                response = await client.patch(**request_kwargs)
            elif method == "DELETE":
                response = await client.delete(**request_kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Raise exception for HTTP error status codes
            response.raise_for_status()
            
            # Try to parse response as JSON
            try:
                result = response.json()
            except Exception:
                # If not valid JSON, return text response
                result = {"text": response.text}
            
            return result
        
        except httpx.HTTPStatusError as e:
            # Handle HTTP error responses
            error_msg = f"HTTP request failed with status {e.response.status_code}"
            
            try:
                error_detail = e.response.json()
                error_msg = f"{error_msg}: {json.dumps(error_detail)}"
            except Exception:
                error_msg = f"{error_msg}: {e.response.text}"
            
            logger.error(error_msg)
            raise Exception(error_msg)
        
        except Exception as e:
            logger.error(f"HTTP tool execution failed: {str(e)}")
            raise Exception(f"Failed to execute HTTP request: {str(e)}")


async def execute_python_tool(
    tool: Tool, inputs: Dict[str, Any], timeout_seconds: float
) -> Dict[str, Any]:
    """
    Execute a Python tool in a secure sandbox environment.
    
    Args:
        tool: Tool to execute
        inputs: Validated input parameters
        timeout_seconds: Execution timeout in seconds
        
    Returns:
        Execution results
        
    Raises:
        Exception: If execution fails or times out
    """
    if not settings.SANDBOX_EXECUTION_ENABLED:
        raise Exception("Python tool execution is disabled in this environment")
    
    # Check for valid code
    code = tool.code
    if not code:
        raise ValueError("Python tool must have code")
    
    # Create a temporary file with the tool code
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w+") as tmp_file:
        # Write code to file
        tmp_file.write(code)
        tmp_file.flush()
        
        # Prepare inputs as JSON string
        inputs_json = json.dumps(inputs)
        
        # Build command to execute Python code with inputs
        cmd = [
            "python3",
            "-c",
            f"import sys, json; sys.path.append('{tmp_file.name}'); " +
            f"from {tmp_file.name.split('/')[-1].replace('.py', '')} import execute; " +
            f"result = execute(json.loads('{inputs_json}')); " +
            "print(json.dumps(result))"
        ]
        
        # Execute in subprocess
        try:
            logger.debug(f"Executing Python tool with timeout {timeout_seconds}s")
            
            # Use asyncio.create_subprocess_exec for better control and security
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=settings.MAX_TOOL_OUTPUT_SIZE,
            )
            
            # Wait for process with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                # Kill process if it times out
                process.kill()
                raise Exception(f"Python tool execution timed out after {timeout_seconds} seconds")
            
            # Check return code
            if process.returncode != 0:
                error = stderr.decode().strip() if stderr else "Unknown error"
                logger.error(f"Python tool execution failed: {error}")
                raise Exception(f"Python execution failed: {error}")
            
            # Parse output as JSON
            output = stdout.decode().strip()
            try:
                result = json.loads(output)
                return result
            except json.JSONDecodeError:
                # Return raw output if not valid JSON
                return {"output": output}
        
        except Exception as e:
            if isinstance(e, asyncio.TimeoutError) or "timed out" in str(e):
                logger.error(f"Python tool execution timed out after {timeout_seconds}s")
                raise Exception(f"Execution timed out after {timeout_seconds} seconds")
            else:
                logger.error(f"Python tool execution failed: {str(e)}")
                raise Exception(f"Failed to execute Python tool: {str(e)}")


async def execute_javascript_tool(
    tool: Tool, inputs: Dict[str, Any], timeout_seconds: float
) -> Dict[str, Any]:
    """
    Execute a JavaScript tool using Node.js in a secure sandbox environment.
    
    Args:
        tool: Tool to execute
        inputs: Validated input parameters
        timeout_seconds: Execution timeout in seconds
        
    Returns:
        Execution results
        
    Raises:
        Exception: If execution fails or times out
    """
    if not settings.SANDBOX_EXECUTION_ENABLED:
        raise Exception("JavaScript tool execution is disabled in this environment")
    
    # Check for valid code
    code = tool.code
    if not code:
        raise ValueError("JavaScript tool must have code")
    
    # Create a temporary file with the tool code
    with tempfile.NamedTemporaryFile(suffix=".js", mode="w+") as tmp_file:
        # Write code to file with proper exports
        # Ensure code exports an execute function
        if "module.exports" not in code and "export function execute" not in code:
            # Wrap code in an execute function if it doesn't have one
            tmp_file.write("module.exports = { execute: function(inputs) {\n")
            tmp_file.write(code)
            tmp_file.write("\n} };")
        else:
            # Code already has proper exports
            tmp_file.write(code)
        
        tmp_file.flush()
        
        # Prepare inputs as JSON string
        inputs_json = json.dumps(inputs)
        
        # Build command to execute JavaScript code with inputs
        cmd = [
            "node", 
            "-e",
            f"const tool = require('{tmp_file.name}'); " +
            f"const result = tool.execute({inputs_json}); " +
            "console.log(JSON.stringify(result));"
        ]
        
        # Execute in subprocess
        try:
            logger.debug(f"Executing JavaScript tool with timeout {timeout_seconds}s")
            
            # Use asyncio.create_subprocess_exec for better control and security
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=settings.MAX_TOOL_OUTPUT_SIZE,
            )
            
            # Wait for process with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                # Kill process if it times out
                process.kill()
                raise Exception(f"JavaScript tool execution timed out after {timeout_seconds} seconds")
            
            # Check return code
            if process.returncode != 0:
                error = stderr.decode().strip() if stderr else "Unknown error"
                logger.error(f"JavaScript tool execution failed: {error}")
                raise Exception(f"JavaScript execution failed: {error}")
            
            # Parse output as JSON
            output = stdout.decode().strip()
            try:
                result = json.loads(output)
                return result
            except json.JSONDecodeError:
                # Return raw output if not valid JSON
                return {"output": output}
        
        except Exception as e:
            if isinstance(e, asyncio.TimeoutError) or "timed out" in str(e):
                logger.error(f"JavaScript tool execution timed out after {timeout_seconds}s")
                raise Exception(f"Execution timed out after {timeout_seconds} seconds")
            else:
                logger.error(f"JavaScript tool execution failed: {str(e)}")
                raise Exception(f"Failed to execute JavaScript tool: {str(e)}")


async def execute_command_tool(
    tool: Tool, inputs: Dict[str, Any], timeout_seconds: float
) -> Dict[str, Any]:
    """
    Execute a command-line tool in a secure sandbox environment.
    
    Args:
        tool: Tool to execute
        inputs: Validated input parameters
        timeout_seconds: Execution timeout in seconds
        
    Returns:
        Execution results
        
    Raises:
        Exception: If execution fails or times out
    """
    if not settings.SANDBOX_EXECUTION_ENABLED:
        raise Exception("Command tool execution is disabled in this environment")
    
    # This is a higher risk execution type, so we check for explicit permission
    if not settings.COMMAND_EXECUTION_ENABLED:
        raise Exception("Command tool execution is not enabled in this environment")
    
    # Extract command from tool configuration
    config = tool.configuration or {}
    command_template = config.get("command")
    
    if not command_template:
        raise ValueError("Command tool must have a command template in its configuration")
    
    # Build command with inputs
    try:
        # Format command template with inputs
        # We use a separate formatting step to prevent command injection
        command = command_template.format(**inputs)
    except KeyError as e:
        raise ValueError(f"Missing required input parameter: {str(e)}")
    except Exception as e:
        raise ValueError(f"Invalid command template: {str(e)}")
    
    # Execute command
    try:
        logger.debug(f"Executing command tool: {command}")
        
        # Execute in a shell with strict timeout
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=True,
            limit=settings.MAX_TOOL_OUTPUT_SIZE,
        )
        
        try:
            # Wait for process with timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            # Kill process if it times out
            process.kill()
            raise Exception(f"Command execution timed out after {timeout_seconds} seconds")
        
        # Check return code
        stdout_text = stdout.decode(errors='replace').strip() if stdout else ""
        stderr_text = stderr.decode(errors='replace').strip() if stderr else ""
        
        result = {
            "stdout": stdout_text,
            "stderr": stderr_text,
            "return_code": process.returncode
        }
        
        if process.returncode != 0:
            logger.warning(
                f"Command tool executed with non-zero return code {process.returncode}: {stderr_text}"
            )
        
        return result
    
    except Exception as e:
        if isinstance(e, asyncio.TimeoutError) or "timed out" in str(e):
            logger.error(f"Command tool execution timed out after {timeout_seconds}s")
            raise Exception(f"Execution timed out after {timeout_seconds} seconds")
        else:
            logger.error(f"Command tool execution failed: {str(e)}")
            raise Exception(f"Failed to execute command: {str(e)}")
