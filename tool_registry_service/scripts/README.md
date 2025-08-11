# To create a new migration

docker compose run --rm --entrypoint "" tool_registry_service alembic revision --autogenerate -m "Add metadata column to tools"
