#!/bin/bash
# create_test_db.sh - Utility to create test databases for Kgents services

# Default connection string for local development
DEFAULT_CONN_STRING="postgresql://postgres:postgres@127.0.0.1:54322/postgres"

# Help text
show_help() {
    echo "Usage: create_test_db.sh [OPTIONS] SERVICE_NAME"
    echo ""
    echo "Create a test database for a Kgents service"
    echo ""
    echo "Options:"
    echo "  -c, --connection   PostgreSQL connection string (default: $DEFAULT_CONN_STRING)"
    echo "  -h, --help         Show this help message"
    echo ""
    echo "Example:"
    echo "  ./create_test_db.sh auth_service"
    echo "  ./create_test_db.sh -c 'postgresql://user:pass@host:port/postgres' agent_service"
    exit 0
}

# Parse command line arguments
CONN_STRING=$DEFAULT_CONN_STRING
SERVICE_NAME=""

while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -c|--connection)
            CONN_STRING="$2"
            shift
            shift
            ;;
        -h|--help)
            show_help
            ;;
        *)
            SERVICE_NAME="$1"
            shift
            ;;
    esac
done

# Validate service name
if [ -z "$SERVICE_NAME" ]; then
    echo "Error: SERVICE_NAME is required"
    show_help
fi

# Convert service name to database name (remove any paths and add _test_db suffix)
DB_NAME="$(basename "$SERVICE_NAME")_test_db"

# Execute database creation
echo "Creating test database: $DB_NAME"
psql "$CONN_STRING" -c "DROP DATABASE IF EXISTS $DB_NAME WITH (FORCE);"
psql "$CONN_STRING" -c "CREATE DATABASE $DB_NAME;"

# Check if the command was successful
if [ $? -eq 0 ]; then
    echo "Success: Test database '$DB_NAME' created"
    echo ""
    echo "Connection string for your .env.test file:"
    echo "DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/$DB_NAME"
else
    echo "Error: Failed to create test database"
    exit 1
fi
