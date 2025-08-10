#!/bin/bash
set -e

echo "🔧 Generating Migration Files for All Services"
echo "============================================="
echo ""

DOCKER_CMD="/usr/local/bin/docker"

# Function to generate migrations for a service
generate_migration() {
    local SERVICE_NAME=$1
    local DB_NAME=$2
    local SERVICE_VAR_PREFIX=$3
    local CONTAINER_NAME="kgents-${SERVICE_NAME}-1"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔧 Generating migration for ${SERVICE_NAME}..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Check if container is running
    if ! $DOCKER_CMD ps | grep -q "${CONTAINER_NAME}"; then
        echo "  ❌ Container ${CONTAINER_NAME} is not running"
        return 1
    fi
    
    # Generate migration using alembic autogenerate
    echo "  → Generating migration from current models..."
    $DOCKER_CMD exec ${CONTAINER_NAME} sh -c "
        cd /app
        export ${SERVICE_VAR_PREFIX}_DATABASE_URL='postgresql+psycopg://postgres:postgres@supabase_db_kgents:5432/${DB_NAME}'
        alembic revision --autogenerate -m 'Initial schema'
    " || {
        echo "  ⚠️ Failed to generate migration for ${SERVICE_NAME}"
        return 1
    }
    
    echo "  ✅ Migration generated successfully!"
    
    # Show generated migration files
    echo "  → Migration files created:"
    ls -la ${SERVICE_NAME}/alembic/versions/*.py 2>/dev/null || echo "    (No files visible on host yet)"
    
    echo ""
}

# Generate migrations for each service
generate_migration "agent_deployment_service" "agent_deployment_dev_db" "AGENT_DEPLOYMENT_SERVICE"
generate_migration "agent_management_service" "agent_management_dev_db" "AGENT_MANAGEMENT_SERVICE"
generate_migration "auth_service" "auth_dev_db" "AUTH_SERVICE"
generate_migration "tool_registry_service" "tool_registry_dev_db" "TOOL_REGISTRY_SERVICE"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Migration generation complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Apply the migrations
echo "Applying migrations to databases..."
echo ""

apply_migration() {
    local SERVICE_NAME=$1
    local DB_NAME=$2
    local SERVICE_VAR_PREFIX=$3
    local CONTAINER_NAME="kgents-${SERVICE_NAME}-1"
    
    echo "  → Applying migration for ${SERVICE_NAME}..."
    $DOCKER_CMD exec ${CONTAINER_NAME} sh -c "
        cd /app
        export ${SERVICE_VAR_PREFIX}_DATABASE_URL='postgresql+psycopg://postgres:postgres@supabase_db_kgents:5432/${DB_NAME}'
        alembic upgrade head
    " && echo "    ✅ Applied" || echo "    ⚠️ Failed to apply"
}

apply_migration "agent_deployment_service" "agent_deployment_dev_db" "AGENT_DEPLOYMENT_SERVICE"
apply_migration "agent_management_service" "agent_management_dev_db" "AGENT_MANAGEMENT_SERVICE"
apply_migration "auth_service" "auth_dev_db" "AUTH_SERVICE"
apply_migration "tool_registry_service" "tool_registry_dev_db" "TOOL_REGISTRY_SERVICE"

echo ""
echo "✅ All migrations generated and applied!"
echo ""
echo "📋 Next Steps:"
echo "1. Restart services to ensure clean state: docker compose restart"
echo "2. Run bootstrap: ./scripts/bootstrap_all_services.sh"
echo "3. Configure GitHub Actions WIF (see docs/GITHUB_ACTIONS_SETUP.md)"
echo "4. Run deployment test: ./scripts/run_deployment_test.sh"
