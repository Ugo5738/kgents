#!/bin/bash

# ==============================================================================
# Kgents End-to-End Test Script
#
# This script automates the process of:
# 1. Logging in a test user to the auth_service.
# 2. Extracting the JWT access token from the response.
# 3. Using the token to create a new agent in the agent_management_service.
# 4. Using the same token to create a new tool in the tool_registry_service.
#
# Usage:
#   ./run_test_flow.sh
#
# Prerequisites:
#   - Docker containers for all services must be running.
#   - `jq` must be installed for JSON parsing. (brew install jq / apt-get install jq)
# ==============================================================================

# --- Configuration ---
set -e # Exit immediately if a command exits with a non-zero status.

AUTH_SERVICE_URL="http://localhost:8001/api/v1/auth"
AGENT_SERVICE_URL="http://localhost:8002/api/v1/agents/"
TOOL_SERVICE_URL="http://localhost:8003/api/v1/tools/"

# Credentials for the test user
TEST_EMAIL="testuser@example.com"
TEST_PASSWORD="a-very-Secure-password123!"

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
  error "'jq' is not installed. Please install it to parse JSON responses (e.g., 'brew install jq' or 'sudo apt-get install jq')."
fi


# --- Step 0: Setup - Ensure Test User Exists ---
info "Ensuring test user '$TEST_EMAIL' exists..."

# We use curl's -f flag to fail silently if the user already exists (which would return a 409 Conflict).
# The || true ensures that the script doesn't exit if curl fails.
curl -s -f -X POST "$AUTH_SERVICE_URL/users/register" \
  -H "Content-Type: application/json" \
  -d "{
        \"email\": \"$TEST_EMAIL\",
        \"password\": \"$TEST_PASSWORD\",
        \"username\": \"testuser\",
        \"first_name\": \"Test\",
        \"last_name\": \"User\"
      }" || true

success "Setup complete. The test user account is available."
echo "--------------------------------------------------"


# --- Step 1: User Login ---
info "Attempting to log in user: $TEST_EMAIL"

LOGIN_RESPONSE=$(curl -s -v -X POST "$AUTH_SERVICE_URL/users/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$TEST_EMAIL\", \"password\": \"$TEST_PASSWORD\"}")

# Check if the login was successful by looking for an access_token
if ! echo "$LOGIN_RESPONSE" | jq -e '.access_token' > /dev/null; then
  error "Login failed. Response: $LOGIN_RESPONSE"
fi

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')
success "Login successful. Token extracted."
echo "--------------------------------------------------"


# --- Step 2: Create Agent ---
info "Attempting to create a new agent..."

# Generate a unique name for the agent for each run
AGENT_NAME="Live Test Agent $(date +%s)"

AGENT_RESPONSE=$(curl -s -v -X POST "$AGENT_SERVICE_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d "{
        \"name\": \"$AGENT_NAME\",
        \"description\": \"This agent was created by the automated test script.\",
        \"config\": { \"details\": \"some live config here\" },
        \"tags\": [\"live\", \"test\", \"automated\"]
      }")

if ! echo "$AGENT_RESPONSE" | jq -e '.id' > /dev/null; then
  error "Agent creation failed. Response: $AGENT_RESPONSE"
fi

AGENT_ID=$(echo "$AGENT_RESPONSE" | jq -r '.id')
success "Agent '$AGENT_NAME' created successfully with ID: $AGENT_ID"
echo "--------------------------------------------------"


# --- Step 3: Create Tool ---
info "Attempting to create a new tool..."

# Generate a unique name for the tool
TOOL_NAME="Live Weather Tool $(date +%s)"

TOOL_RESPONSE=$(curl -s -v -X POST "$TOOL_SERVICE_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
        "name": "'"$TOOL_NAME"'",
        "description": "A tool to get the weather, created by the automated test script.",
        "tool_type": "api",
        "implementation": {
            "openapi_spec": { "info": { "title": "Live Weather API" } }
        },
        "schema": { "input": { "city": "string" } }
      }')

if ! echo "$TOOL_RESPONSE" | jq -e '.id' > /dev/null; then
  error "Tool creation failed. Response: $TOOL_RESPONSE"
fi

TOOL_ID=$(echo "$TOOL_RESPONSE" | jq -r '.id')
success "Tool '$TOOL_NAME' created successfully with ID: $TOOL_ID"
echo "--------------------------------------------------"

echo "🎉 All steps completed successfully!"