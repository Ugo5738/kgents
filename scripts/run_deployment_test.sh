#!/bin/bash

# ==============================================================================
# Kgents End-to-End Deployment Smoke Test Script
#
# This script automates a full deployment cycle to a live environment (e.g., local Docker + GCP).
# It performs the following actions:
# 1. Authenticates as a test user to get a JWT.
# 2. Creates a new agent definition in the agent_management_service.
# 3. Fetches the initial version ID of the new agent.
# 4. Triggers a deployment in the agent_deployment_service.
# 5. Polls the deployment status until it completes or fails.
# 6. Reports the final status and the public URL if successful.
#
# Prerequisites:
#   - All Kgents services must be running via `docker-compose up`.
#   - `jq` must be installed (`brew install jq` or `sudo apt-get install jq`).
#   - Your local `gcloud` CLI must be authenticated.
#   - Your local Docker must be configured to push to your Artifact Registry.
# ==============================================================================

# --- Configuration ---
# Safer bash options
set -Eeuo pipefail

# Verbosity controls
# Set VERBOSE=1 for verbose curl and more output
# Set TRACE=1 to enable bash xtrace
VERBOSE="${VERBOSE:-0}"
TRACE="${TRACE:-0}"
TAIL_LOGS_ON_ERROR="${TAIL_LOGS_ON_ERROR:-1}"

if [[ "$TRACE" == "1" ]]; then
  set -x
fi

# Service URLs (adjust ports if you changed them in docker-compose)
AUTH_SERVICE_URL="http://localhost:8001/api/v1/auth"
AGENT_MGMT_URL="http://localhost:8002/api/v1/agents"
AGENT_DEPLOY_URL="http://localhost:8004/api/v1/deployments"
AGENT_DEPLOY_HEALTH_LIVE="http://localhost:8004/api/v1/health/liveness"
AGENT_DEPLOY_HEALTH_READY="http://localhost:8004/api/v1/health/readiness"

# Credentials for the test user
TEST_EMAIL="testuser@example.com"
TEST_PASSWORD="a-very-Secure-password123!"

# --- Helper Functions ---
info() { echo -e "\033[34m[INFO] $1\033[0m"; }
warn() { echo -e "\033[33m[WARN] $1\033[0m"; }
success() { echo -e "\033[32m✅ [SUCCESS] $1\033[0m"; }
error() {
  echo -e "\033[31m❌ [ERROR] $1\033[0m" >&2
  if [[ "$TAIL_LOGS_ON_ERROR" == "1" ]]; then
    echo "----- agent_deployment_service logs (tail 200) -----" >&2
    docker compose logs --no-color --tail=200 agent_deployment_service >&2 || true
    echo "----- end logs -----" >&2
  fi
  exit 1
}

# Curl JSON helper: writes body to BODY and HTTP code to HTTP_CODE
curl_json() {
  local method="$1"; shift
  local url="$1"; shift
  local data="${1:-}"; [[ $# -gt 0 ]] && shift || true
  local tmp
  tmp=$(mktemp)
  local args=(-sS -L -X "$method" "$url" -H "Content-Type: application/json" -o "$tmp" -w "%{http_code}")
  if [[ -n "$data" ]]; then args+=( -d "$data" ); fi
  # Authorization header if AUTH_TOKEN present
  if [[ -n "${AUTH_TOKEN:-}" ]]; then args+=( -H "Authorization: Bearer $AUTH_TOKEN" ); fi
  if [[ "$VERBOSE" == "1" ]]; then args+=( -v ); fi
  local code
  if ! code=$(curl "${args[@]}" 2> >(sed 's/^/[curl] /' >&2)); then
    local rc=$?
    rm -f "$tmp"
    error "curl request failed (exit $rc) for $method $url"
  fi
  BODY=$(cat "$tmp")
  HTTP_CODE="$code"
  rm -f "$tmp"
}

# Tail deployment-specific logs helper
tail_deploy_logs() {
  local id="$1"
  echo "----- deployment logs (Deployment:$id) tail 50 -----"
  docker compose logs --no-color agent_deployment_service | grep -E "\[Deployment:${id}|\[Build:${id}|\[Push:${id}" | tail -n 50 || true
  echo "----- end deployment logs -----"
}

# --- Prerequisite Check ---
if ! command -v jq &> /dev/null; then
  error "'jq' is not installed. Please install it to parse JSON responses."
fi

# --- Preflight: Health checks ---
info "Checking agent_deployment_service health..."
curl_json GET "$AGENT_DEPLOY_HEALTH_LIVE"
if [[ "$HTTP_CODE" != "200" ]]; then
  error "Liveness check failed (HTTP $HTTP_CODE). Body: $BODY"
fi
success "Liveness OK."

curl_json GET "$AGENT_DEPLOY_HEALTH_READY"
if [[ "$HTTP_CODE" != "200" ]]; then
  error "Readiness check failed (HTTP $HTTP_CODE). Body: $BODY"
fi
success "Readiness OK."

# --- Step 1: Authenticate and Get JWT ---
info "Authenticating as user '$TEST_EMAIL' to get a JWT..."
curl_json POST "$AUTH_SERVICE_URL/users/login" "{\"email\": \"$TEST_EMAIL\", \"password\": \"$TEST_PASSWORD\"}"
if [[ "$HTTP_CODE" != "200" ]]; then
  error "Login failed (HTTP $HTTP_CODE). Body: $BODY"
fi
if ! echo "$BODY" | jq -e '.access_token' > /dev/null; then
  error "Login response missing access_token. Body: $BODY"
fi
AUTH_TOKEN=$(echo "$BODY" | jq -r '.access_token')
success "Authentication successful."
echo "--------------------------------------------------"

# --- Step 2: Create a New Agent Definition ---
AGENT_NAME="Cloud Deployed Agent $(date +%s)"
info "Creating agent definition for '$AGENT_NAME'..."

AGENT_CREATE_PAYLOAD=$(cat <<EOF
{
  "name": "$AGENT_NAME",
  "description": "An agent created by the e2e deployment script.",
  "config": {
    "langflow_data": {
      "nodes": [{"id": "test_node"}], 
      "edges": []
    }
  },
  "tags": ["cloud-run", "e2e-test"]
}
EOF
)

curl_json POST "$AGENT_MGMT_URL/" "$AGENT_CREATE_PAYLOAD"
if [[ "$HTTP_CODE" != "201" && "$HTTP_CODE" != "200" && "$HTTP_CODE" != "202" ]]; then
  error "Agent creation failed (HTTP $HTTP_CODE). Body: $BODY"
fi
if ! echo "$BODY" | jq -e '.id' > /dev/null; then
  error "Agent creation response missing id. Body: $BODY"
fi
AGENT_ID=$(echo "$BODY" | jq -r '.id')
success "Agent definition created with ID: $AGENT_ID"
echo "--------------------------------------------------"

# --- Step 3: Get the Initial Agent Version ID ---
info "Fetching the latest version ID for agent '$AGENT_ID'..."
curl_json GET "$AGENT_MGMT_URL/$AGENT_ID/versions/latest"
if [[ "$HTTP_CODE" != "200" ]]; then
  error "Failed to fetch agent version (HTTP $HTTP_CODE). Body: $BODY"
fi
if ! echo "$BODY" | jq -e '.id' > /dev/null; then
  error "Latest version response missing id. Body: $BODY"
fi
AGENT_VERSION_ID=$(echo "$BODY" | jq -r '.id')
success "Found agent version ID: $AGENT_VERSION_ID"
echo "--------------------------------------------------"

# --- Step 4: Trigger the Deployment ---
info "Sending deployment request to agent_deployment_service..."
DEPLOY_PAYLOAD=$(cat <<EOF
{
  "agent_id": "$AGENT_ID",
  "agent_version_id": "$AGENT_VERSION_ID"
}
EOF
)

curl_json POST "$AGENT_DEPLOY_URL/" "$DEPLOY_PAYLOAD"
if [[ "$HTTP_CODE" != "202" && "$HTTP_CODE" != "201" && "$HTTP_CODE" != "200" ]]; then
  error "Deployment trigger failed (HTTP $HTTP_CODE). Body: $BODY"
fi
if ! echo "$BODY" | jq -e '.id' > /dev/null; then
  error "Deployment trigger response missing id. Body: $BODY"
fi
DEPLOYMENT_ID=$(echo "$BODY" | jq -r '.id')
success "Deployment request accepted. Tracking Deployment ID: $DEPLOYMENT_ID"
echo "--------------------------------------------------"

# --- Step 5: Poll for Deployment Status ---
info "Monitoring deployment status... (This may take a few minutes)"
MAX_RETRIES=30 # 30 retries * 10 seconds = 5 minutes timeout
RETRY_INTERVAL=10 # seconds

for (( i=1; i<=$MAX_RETRIES; i++ )); do
  curl_json GET "$AGENT_DEPLOY_URL/$DEPLOYMENT_ID"
  if [[ "$HTTP_CODE" != "200" ]]; then
    warn "Status check HTTP $HTTP_CODE. Body: $BODY"
  fi
  STATUS=$(echo "$BODY" | jq -r '.status // empty')
  info "Attempt $i/$MAX_RETRIES: Current status is '${STATUS:-unknown}'."

  if [[ "$STATUS" == "running" ]]; then
    ENDPOINT_URL=$(echo "$BODY" | jq -r '.endpoint_url // empty')
    success "Deployment completed successfully!"
    if [[ -n "$ENDPOINT_URL" && "$ENDPOINT_URL" != "null" ]]; then
      echo -e "\033[32m🚀 Your agent is live at: $ENDPOINT_URL\033[0m"
    fi
    tail_deploy_logs "$DEPLOYMENT_ID"
    exit 0
  elif [[ "$STATUS" == "failed" ]]; then
    ERROR_MSG=$(echo "$BODY" | jq -r '.error_message // "unknown error"')
    tail_deploy_logs "$DEPLOYMENT_ID"
    error "Deployment failed! Reason: $ERROR_MSG"
  fi

  # Show recent deployment logs during polling
  tail_deploy_logs "$DEPLOYMENT_ID"
  sleep $RETRY_INTERVAL
done

tail_deploy_logs "$DEPLOYMENT_ID"
error "Deployment timed out after $MAX_RETRIES attempts."