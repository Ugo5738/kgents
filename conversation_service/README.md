# Conversation Service

Real-time conversation microservice built with FastAPI, async SQLAlchemy, and Alembic. It provides REST APIs for conversations and messages, plus a WebSocket for streaming updates. The service integrates with a Langflow agent runtime (Cloud Run) and uses an M2M credential bootstrap flow to enable secure inter-service communication.

- Language/Framework: Python 3.12, FastAPI, SQLAlchemy 2.x (async), Alembic
- Realtime: WebSocket streaming
- Migrations: Alembic (autogenerate via Docker)
- Config: Pydantic Settings (env-prefixed `CONVERSATION_SERVICE_`)
- Port (dev): 8005 (external) -> 8000 (internal)
- Root path: `/api/v1` (configurable)


## Architecture

- API app: `src/conversation_service/main.py`
- Routers:
  - `src/conversation_service/routers/health_router.py`
  - `src/conversation_service/routers/conversations_router.py`
  - `src/conversation_service/routers/ws_router.py`
- Models: `src/conversation_service/models/{conversation.py,message.py}`
- Schemas: `src/conversation_service/schemas/conversation.py`
- Runtime integration: `src/conversation_service/services/runtime.py`
- DB/Session: `src/conversation_service/db.py`
- Config: `src/conversation_service/config.py`
- Logging and middleware: `src/conversation_service/logging_config.py`
- Migrations: `alembic/` (async env)
- DB manage CLI: `scripts/manage_db.py`

The service stores conversations and messages in Postgres, exposes REST for CRUD, and uses a WebSocket channel per conversation for realtime streaming of assistant responses.


## Key Features

- Conversation and message CRUD
- Background agent run when a user message arrives
- WebSocket streaming of acknowledgements and assistant chunks
- Langflow Cloud Run integration (bearer via `/api/v1/auto_login`)
- Idempotent M2M bootstrap with the auth service, writing client credentials to `.env.dev`


## Configuration

Use `conversation_service/.env.dev` during development. Important variables:

- Service
  - `CONVERSATION_SERVICE_ENVIRONMENT=development`
  - `CONVERSATION_SERVICE_LOGGING_LEVEL=INFO`
  - `CONVERSATION_SERVICE_ROOT_PATH=/api/v1`
  - `CONVERSATION_SERVICE_CORS_ALLOW_ORIGINS=["*"]`
- Database
  - `CONVERSATION_SERVICE_DATABASE_URL=postgresql+psycopg://postgres:postgres@supabase_db_kgents:5432/conversation_dev_db`
- JWT (M2M and User; must align with auth service in your stack)
  - `CONVERSATION_SERVICE_M2M_JWT_SECRET_KEY=...`
  - `CONVERSATION_SERVICE_M2M_JWT_ALGORITHM=HS256`
  - `CONVERSATION_SERVICE_M2M_JWT_ISSUER=...`
  - `CONVERSATION_SERVICE_M2M_JWT_AUDIENCE=authenticated`
  - `CONVERSATION_SERVICE_USER_JWT_SECRET_KEY=...`
  - `CONVERSATION_SERVICE_USER_JWT_ALGORITHM=HS256`
  - `CONVERSATION_SERVICE_USER_JWT_ISSUER=...`
  - `CONVERSATION_SERVICE_USER_JWT_AUDIENCE=authenticated`
- External Runtimes
  - `LANGFLOW_RUNTIME_URL=https://<your-cloud-run-app>`
- Auth bootstrap (for M2M creation)
  - `AUTH_SERVICE_URL=http://auth_service:8000/api/v1`
  - `INITIAL_ADMIN_EMAIL=admin@admin.com`
  - `INITIAL_ADMIN_PASSWORD=admin`
- Populated by bootstrap
  - `CONVERSATION_SERVICE_CLIENT_ID=...`
  - `CONVERSATION_SERVICE_CLIENT_SECRET=...`


## Local Development

- Dev compose: `conversation_service/docker-compose.dev.yml` (exposes 8005)
- Root compose: `docker-compose.yml` includes `conversation_service` by extending the dev compose

Example dev workflow (inside the container):

```bash
# Initialize DB (creates DB, autogenerates initial migration if absent, upgrades, bootstrap M2M)
python scripts/manage_db.py init

# Or recreate from scratch (drop/create DB, reset versions, autogenerate + upgrade, bootstrap)
python scripts/manage_db.py recreate

# Create an explicit migration when models change
python scripts/manage_db.py create-migration -m "add new columns"

# Apply migrations / roll back
python scripts/manage_db.py upgrade
python scripts/manage_db.py downgrade -s 1

# Verify heads/current
python scripts/manage_db.py verify

# Drop just the database (keeps migration files)
python scripts/manage_db.py delete-db
```

Notes
- The bootstrap will create an M2M client against `AUTH_SERVICE_URL` and write credentials back to `.env.dev`.
- Env var updates require recreating the container to take effect in the environment.


## API

All routes are served under the configured root path (default `/api/v1`).

- Health
  - `GET /api/v1/health` → `{ "status": "ok" }`

- Conversations
  - `POST /api/v1/conversations/` → create a conversation
  - `GET /api/v1/conversations/{conversation_id}` → get a conversation
  - `GET /api/v1/conversations/{conversation_id}/messages` → list messages
  - `POST /api/v1/conversations/{conversation_id}/messages` → append a message
    - If `role == "user"`, schedules a background agent flow and immediately sends a WS ack

- WebSocket (JWT required)
  - `ws://localhost:8005/api/v1/ws/conversations/{conversation_id}`
  - Authenticate with one of:
    - Header: `Authorization: Bearer <USER_OR_M2M_JWT>`
    - Query: `?token=<USER_OR_M2M_JWT>`
  - Upon connect, server sends `{ "type": "connected" }`
  - When a message is posted via REST, server sends a JSON ack:
    - `{ "type": "ack", "message_id": "<uuid>", "role": "user|assistant|system" }`
  - During agent run, the server streams JSON messages:

```json
{"type": "info", "message": "langflow_authenticated"}
{"type": "warn", "message": "langflow_auth_failed"}
{"type": "stream", "content": "...chunk..."}
{"type": "complete"}
```


## Data Model (summary)

- Conversation
  - `id: UUID`, `title: Optional[str]`, `owner_id: Optional[UUID]`, `metadata_json: dict`
  - Timestamps from shared base (created_at, updated_at)

- Message
  - `id: UUID`, `conversation_id: UUID`, `role: str in {user,assistant,system}`
  - `content: str`, `metadata_json: dict`, timestamps

See `src/conversation_service/models/` and `schemas/conversation.py` for details.


## Runtime Integration

`services/runtime.py` attempts a real flow execution when Langflow `auto_login` is available by probing common runtime endpoints; when that fails, it falls back to a simulated stream. This will be replaced with a stable, versioned integration once the target API surface is finalized.


## Security

- M2M credentials are created and stored in `.env.dev` by the bootstrap module (`src/conversation_service/bootstrap.py`).
- WebSocket authentication and authorization will be enforced in a follow-up iteration (JWT on connect).
- CORS is configurable; default is permissive in dev.


## Roadmap

- Replace simulated agent run with real Langflow flow execution
- Multi-agent orchestration and MCP/A2A protocol support
- JWT validation on WebSocket connections
- CI/CD integration and production hardening
