#!/bin/bash

# ==============================================================================
# Kgents Machine-to-Machine (M2M) End-to-End Test Script
#
# This script tests the non-user-facing authentication and authorization flow:
# 1. Logs in as the admin user.
# 2. Creates a new Role ('test_tool_creator') and Permission ('tools:create').
# 3. Assigns the permission to the role.
# 4. Creates a new Application Client (our "machine").
# 5. Assigns the new role to the client.
# 6. Uses the client's credentials to get a secure M2M access token.
# 7. Uses the M2M token to create a new tool.
#
# Prerequisites:
#   - Docker containers must be running.
#   - `jq` must be installed.
# ==============================================================================

set -e

# --- Configuration ---
AUTH_SERVICE_URL="http://localhost:8001/api/v1"
TOOL_SERVICE_URL="http://localhost:8003/api/v1/tools/"

# Admin credentials from your bootstrap process
ADMIN_EMAIL="admin@admin.com"
ADMIN_PASSWORD="admin"

# --- Helper Functions ---
info() {
  echo "[INFO] $1"
}

success() {
  echo "✅ [SUCCESS] $1"
}

error() {
  echo "❌ [ERROR] $1" >&2
  exit 1
}

# --- Prerequisite Check ---
if ! command -v jq &> /dev/null; then
  error "'jq' is not installed."
fi

# --- Step 1: Login as Admin ---
info "Logging in as admin user: $ADMIN_EMAIL..."
LOGIN_RESPONSE=$(curl -s -X POST "$AUTH_SERVICE_URL/auth/users/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$ADMIN_EMAIL\", \"password\": \"$ADMIN_PASSWORD\"}")

if ! echo "$LOGIN_RESPONSE" | jq -e '.access_token' > /dev/null; then
  error "Admin login failed. Is the auth_service running and bootstrapped? Response: $LOGIN_RESPONSE"
fi
ADMIN_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')
success "Admin login successful."
echo "--------------------------------------------------"

# --- Step 2: Create a 'tool_creator' Role ---
ROLE_NAME="test_tool_creator_$(date +%s)"
info "Creating a new role: '$ROLE_NAME'..."

ROLE_RESPONSE=$(curl -s -X POST "$AUTH_SERVICE_URL/admin/roles" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d "{
        \"name\": \"$ROLE_NAME\",
        \"description\": \"A temporary role for M2M testing.\"
      }")

if ! echo "$ROLE_RESPONSE" | jq -e '.id' > /dev/null; then
  error "Failed to create role. Response: $ROLE_RESPONSE"
fi
ROLE_ID=$(echo "$ROLE_RESPONSE" | jq -r '.id')
success "Role '$ROLE_NAME' created with ID: $ROLE_ID"
echo "--------------------------------------------------"

# --- Step 3: Assign 'tool:create' Permission to Role ---
# First, get the ID of the 'tool:create' permission which was created during bootstrap
info "Getting ID for 'tool:create' permission..."
PERMISSIONS_RESPONSE=$(curl -s -X GET "$AUTH_SERVICE_URL/admin/permissions" -H "Authorization: Bearer $ADMIN_TOKEN")
PERMISSION_ID=$(echo "$PERMISSIONS_RESPONSE" | jq -r '.items[] | select(.name == "tool:create") | .id')

if [ -z "$PERMISSION_ID" ]; then
  error "Could not find the 'tool:create' permission. Has the auth_service been bootstrapped correctly?"
fi
success "Found 'tool:create' permission with ID: $PERMISSION_ID"

info "Assigning permission to role..."
ASSIGN_RESPONSE=$(curl -s -X POST "$AUTH_SERVICE_URL/admin/roles/$ROLE_ID/permissions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d "{\"permission_id\": \"$PERMISSION_ID\"}")

if ! echo "$ASSIGN_RESPONSE" | jq -e '.role_id' > /dev/null; then
  error "Failed to assign permission. Response: $ASSIGN_RESPONSE"
fi
success "Permission 'tool:create' assigned to role '$ROLE_NAME'."
echo "--------------------------------------------------"

# --- Step 4: Create an App Client and Assign Role ---
CLIENT_NAME="external_agent_system_$(date +%s)"
info "Creating a new App Client: '$CLIENT_NAME'..."

CLIENT_RESPONSE=$(curl -s -X POST "$AUTH_SERVICE_URL/admin/clients" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d "{
        \"client_name\": \"$CLIENT_NAME\",
        \"description\": \"An external system for automated testing.\",
        \"allowed_callback_urls\": [],
        \"assigned_roles\": [\"$ROLE_NAME\"]
      }")

if ! echo "$CLIENT_RESPONSE" | jq -e '.client_id' > /dev/null; then
  error "Failed to create App Client. Response: $CLIENT_RESPONSE"
fi
CLIENT_ID=$(echo "$CLIENT_RESPONSE" | jq -r '.client_id')
CLIENT_SECRET=$(echo "$CLIENT_RESPONSE" | jq -r '.client_secret')
success "App Client created with ID: $CLIENT_ID"
info "IMPORTANT: Client Secret is '$CLIENT_SECRET' (this is only shown once)."
echo "--------------------------------------------------"

# --- Step 5: Get an M2M Token ---
info "Requesting an M2M access token for client '$CLIENT_NAME'..."

M2M_TOKEN_RESPONSE=$(curl -s -X POST "$AUTH_SERVICE_URL/auth/token" \
  -H "Content-Type: application/json" \
  -d "{
        \"grant_type\": \"client_credentials\",
        \"client_id\": \"$CLIENT_ID\",
        \"client_secret\": \"$CLIENT_SECRET\"
      }")

if ! echo "$M2M_TOKEN_RESPONSE" | jq -e '.access_token' > /dev/null; then
  error "Failed to get M2M token. Response: $M2M_TOKEN_RESPONSE"
fi
M2M_TOKEN=$(echo "$M2M_TOKEN_RESPONSE" | jq -r '.access_token')
success "Successfully acquired M2M access token."
echo "--------------------------------------------------"

# --- Step 6: Use the M2M Token to Create a Tool ---
info "Using M2M token to create a tool..."
TOOL_NAME="M2M Test Tool $(date +%s)"

TOOL_RESPONSE=$(curl -s -X POST "$TOOL_SERVICE_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $M2M_TOKEN" \
  -d '{
        "name": "'"$TOOL_NAME"'",
        "description": "This tool was created by an M2M client.",
        "tool_type": "api",
        "implementation": {
            "openapi_spec": { "info": { "title": "M2M API" } }
        },
        "schema": { "input": { "data": "string" } }
      }')

if ! echo "$TOOL_RESPONSE" | jq -e '.id' > /dev/null; then
  error "M2M client failed to create tool. Response: $TOOL_RESPONSE"
fi
TOOL_ID=$(echo "$TOOL_RESPONSE" | jq -r '.id')
success "M2M client successfully created tool '$TOOL_NAME' with ID: $TOOL_ID"
echo "--------------------------------------------------"

echo "🎉 M2M authentication and authorization flow completed successfully!"