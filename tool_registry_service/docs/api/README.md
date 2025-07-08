# Tool Registry Service API Documentation

This document provides detailed information about the Tool Registry Service API endpoints, request/response formats, and authentication requirements.

## API Overview

The Tool Registry Service provides a RESTful API for managing and executing tools. All endpoints are prefixed with `/api/v1/`.

### Authentication

All endpoints require authentication via JWT token passed in the `Authorization` header as a bearer token:

```
Authorization: Bearer <your_jwt_token>
```

JWT tokens are validated against the Auth Service. User identity and roles are extracted from the token for authorization.

### Error Handling

All API errors follow a consistent format:

```json
{
  "detail": "Error message description"
}
```

Common HTTP status codes:

- `200 OK`: Request succeeded
- `201 Created`: Resource created successfully
- `204 No Content`: Request succeeded with no content to return
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict (e.g., duplicate name)
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

## API Endpoints

### Health Check

#### GET `/api/v1/health`

Returns the health status of the service.

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2023-06-28T12:34:56Z"
}
```

#### GET `/api/v1/health/db`

Returns the database connection health status.

**Response:**
```json
{
  "status": "ok",
  "latency_ms": 5.2,
  "timestamp": "2023-06-28T12:34:56Z"
}
```

### Tool Categories

#### GET `/api/v1/categories/`

List all tool categories with pagination and filtering.

**Query Parameters:**
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 10, max: 100)
- `name`: Filter by name (optional)

**Response:**
```json
{
  "items": [
    {
      "id": "uuid-string",
      "name": "API Tools",
      "description": "Category description",
      "icon": "api-icon",
      "color": "#336699",
      "display_order": 1,
      "created_at": "2023-06-28T12:34:56Z",
      "updated_at": "2023-06-28T12:34:56Z"
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 10,
  "pages": 1
}
```

#### GET `/api/v1/categories/{category_id}`

Get a specific tool category by ID.

**Response:**
```json
{
  "id": "uuid-string",
  "name": "API Tools",
  "description": "Category description",
  "icon": "api-icon",
  "color": "#336699",
  "display_order": 1,
  "created_at": "2023-06-28T12:34:56Z",
  "updated_at": "2023-06-28T12:34:56Z"
}
```

#### POST `/api/v1/categories/`

Create a new tool category. Requires admin role.

**Request Body:**
```json
{
  "name": "New Category",
  "description": "Category description",
  "icon": "category-icon",
  "color": "#336699",
  "display_order": 2
}
```

**Response:**
```json
{
  "id": "uuid-string",
  "name": "New Category",
  "description": "Category description",
  "icon": "category-icon",
  "color": "#336699",
  "display_order": 2,
  "created_at": "2023-06-28T12:34:56Z",
  "updated_at": "2023-06-28T12:34:56Z"
}
```

#### PATCH `/api/v1/categories/{category_id}`

Update an existing tool category. Requires admin role.

**Request Body:**
```json
{
  "name": "Updated Category",
  "description": "Updated description"
}
```

**Response:**
```json
{
  "id": "uuid-string",
  "name": "Updated Category",
  "description": "Updated description",
  "icon": "category-icon",
  "color": "#336699",
  "display_order": 2,
  "created_at": "2023-06-28T12:34:56Z",
  "updated_at": "2023-06-28T12:34:56Z"
}
```

#### DELETE `/api/v1/categories/{category_id}`

Delete a tool category. Requires admin role.

**Response:** HTTP 204 No Content

### Tools

#### GET `/api/v1/tools/`

List all tools with pagination and filtering.

**Query Parameters:**
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 10, max: 100)
- `name`: Filter by name (optional)
- `category_id`: Filter by category ID (optional)
- `owner_id`: Filter by owner ID (optional)
- `public_only`: Show only public tools (optional, default: false)
- `approved_only`: Show only approved tools (optional, default: false)
- `tool_type`: Filter by tool type (optional)

**Response:**
```json
{
  "items": [
    {
      "id": "uuid-string",
      "name": "Example Tool",
      "slug": "example-tool",
      "description": "Tool description",
      "category_id": "uuid-string",
      "category_name": "API Tools",
      "owner_id": "uuid-string",
      "is_public": true,
      "is_approved": true,
      "is_active": true,
      "tool_type": "http",
      "execution_env": "sandbox",
      "input_schema": {
        "type": "object",
        "properties": {
          "query": {
            "type": "string",
            "description": "Search query"
          }
        },
        "required": ["query"]
      },
      "output_schema": {
        "type": "object",
        "properties": {
          "results": {
            "type": "array",
            "items": {
              "type": "object"
            }
          }
        }
      },
      "created_at": "2023-06-28T12:34:56Z",
      "updated_at": "2023-06-28T12:34:56Z"
    }
  ],
  "total": 25,
  "page": 1,
  "page_size": 10,
  "pages": 3
}
```

#### GET `/api/v1/tools/{tool_id}`

Get a specific tool by ID.

**Response:** Same as tool object in the list response

#### POST `/api/v1/tools/`

Create a new tool.

**Request Body:**
```json
{
  "name": "New Tool",
  "description": "Tool description",
  "category_id": "uuid-string",
  "is_public": false,
  "tool_type": "http",
  "execution_env": "sandbox",
  "config": {
    "method": "GET",
    "url": "https://api.example.com/endpoint",
    "headers": {
      "Content-Type": "application/json"
    }
  },
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query"
      }
    },
    "required": ["query"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "results": {
        "type": "array",
        "items": {
          "type": "object"
        }
      }
    }
  },
  "authentication_config": {
    "type": "api_key",
    "header_name": "X-API-Key"
  },
  "metadata": {
    "tags": ["search", "api"]
  }
}
```

**Response:** Created tool object

#### PATCH `/api/v1/tools/{tool_id}`

Update an existing tool. User must be the owner or have admin role.

**Request Body:**
```json
{
  "name": "Updated Tool Name",
  "description": "Updated description",
  "is_public": true,
  "config": {
    "method": "POST",
    "url": "https://api.example.com/new-endpoint"
  }
}
```

**Response:** Updated tool object

#### DELETE `/api/v1/tools/{tool_id}`

Delete a tool. User must be the owner or have admin role.

**Response:** HTTP 204 No Content

#### POST `/api/v1/tools/{tool_id}/approve`

Approve a tool for public use. Requires admin role.

**Response:** Updated tool object with `is_approved: true`

### Tool Execution

#### POST `/api/v1/execute/{tool_id}`

Execute a tool with provided inputs.

**Request Body:**
```json
{
  "inputs": {
    "query": "search term"
  }
}
```

**Response:**
```json
{
  "execution_id": "uuid-string",
  "status": "pending",
  "started_at": "2023-06-28T12:34:56Z"
}
```

#### GET `/api/v1/execute/status/{execution_id}`

Check the status of a tool execution.

**Response:**
```json
{
  "id": "uuid-string",
  "tool_id": "uuid-string",
  "user_id": "uuid-string",
  "status": "completed",
  "started_at": "2023-06-28T12:34:56Z",
  "completed_at": "2023-06-28T12:34:57Z",
  "execution_time_ms": 120,
  "inputs": {
    "query": "search term"
  },
  "outputs": {
    "results": [
      {"title": "Result 1", "url": "https://example.com/1"},
      {"title": "Result 2", "url": "https://example.com/2"}
    ]
  }
}
```

#### GET `/api/v1/execute/history`

Get the execution history for the authenticated user.

**Query Parameters:**
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 10, max: 100)
- `tool_id`: Filter by tool ID (optional)
- `status`: Filter by status (optional)

**Response:**
```json
{
  "items": [
    {
      "id": "uuid-string",
      "tool_id": "uuid-string",
      "tool_name": "Example Tool",
      "status": "completed",
      "started_at": "2023-06-28T12:34:56Z",
      "completed_at": "2023-06-28T12:34:57Z",
      "execution_time_ms": 120
    }
  ],
  "total": 50,
  "page": 1,
  "page_size": 10,
  "pages": 5
}
```
