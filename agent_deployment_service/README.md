# Agent Deployment Service

## Overview

The Agent Deployment Service is a core component of the Kgents platform responsible for orchestrating the deployment of AI agents. It takes a published agent version, packages it into a runnable service (e.g., Docker container), and manages its lifecycle across multiple deployment platforms.

> Note: Provisioning is not handled by this service. Agent provisioning (e.g., selecting a Langflow flow) is exclusively owned by the Agent Runtime Service (see `agent_runtime_service/README.md`).

## Key Features

### 🚀 Multi-Platform Deployment
- **Google Cloud Run**: Serverless deployment with automatic scaling
- **Kubernetes**: Full container orchestration support
- **Extensible**: Easy to add new deployment platforms

### 🏗️ Flexible Build Strategies
- **GitHub Actions**: FREE cross-platform builds with excellent Docker buildx support
- **Google Cloud Build**: Fast, integrated builds (~$0.003/build)
- **Separation of Concerns**: Build and deployment strategies are independent

### 📦 Agent Type Support
- **Langflow Agents**: Full support for Langflow-based AI agents
- **Custom Agents**: Deploy your own containerized agents
- **OpenAI Assistants**: Integration with OpenAI Assistant API (planned)

### 🔄 Lifecycle Management
- Real-time deployment status tracking (`pending`, `deploying`, `running`, `failed`, `stopped`)
- Automatic health checks and monitoring
- Graceful shutdown and cleanup
- Deployment rollback capabilities

### 🔐 Security & Authentication
- Secure credential management
- Service account integration
- API key protection
- Environment-specific configurations

## Architecture

The service follows a **strategy pattern** architecture with clean separation between:
- **Build Strategy**: How to build Docker images
- **Deployment Strategy**: Where to deploy containers

This allows maximum flexibility - use free GitHub Actions for builds while deploying to any platform.

## Configuration

### Environment Variables

```bash
# Build Strategy (github_actions or cloud_build)
AGENT_DEPLOYMENT_SERVICE_BUILD_STRATEGY=github_actions

# Deployment Strategy (cloud_run or kubernetes)
AGENT_DEPLOYMENT_SERVICE_DEPLOYMENT_STRATEGY=cloud_run

# GCP Configuration (for Cloud Run deployments)
AGENT_DEPLOYMENT_SERVICE_GCP_PROJECT_ID=your-project-id
AGENT_DEPLOYMENT_SERVICE_GCP_REGION=us-central1

# GitHub Configuration (for GitHub Actions builds)
AGENT_DEPLOYMENT_SERVICE_GITHUB_OWNER=your-github-username
AGENT_DEPLOYMENT_SERVICE_GITHUB_REPO=your-repo-name
AGENT_DEPLOYMENT_SERVICE_GITHUB_TOKEN=ghp_your_token

# Service Configuration
AGENT_DEPLOYMENT_SERVICE_PORT=8001
AGENT_DEPLOYMENT_SERVICE_DATABASE_URL=postgresql://...
```

## API Endpoints

### Core Endpoints
- `POST /deployments/` - Create a new deployment
- `GET /deployments/{deployment_id}` - Get deployment details
- `GET /deployments/` - List all deployments
- `PUT /deployments/{deployment_id}` - Update deployment
- `DELETE /deployments/{deployment_id}` - Stop/delete deployment

### Health & Monitoring
- `GET /health` - Service health check
- `GET /deployments/{deployment_id}/status` - Get deployment status
- `GET /deployments/{deployment_id}/logs` - Get deployment logs

## Database Schema

The service uses PostgreSQL with the following main table:

```sql
deployments:
  - id (UUID)
  - user_id (UUID)
  - agent_id (UUID)
  - agent_version_id (UUID)
  - status (enum: pending|deploying|running|failed|stopped)
  - endpoint_url (string)
  - deployment_metadata (JSONB)
  - build_strategy (enum)
  - deployment_strategy (enum)
  - deploy_real_agent (boolean)
  - error_message (text)
  - timestamps
```

## Setup Instructions

### Local Development with Docker Compose

1. **Configure Environment**
   ```bash
   cp .env.example .env.dev
   # Edit .env.dev with your configuration
   ```

2. **Start Supabase (Database)**
   ```bash
   cd ../
   npx supabase start
   ```

3. **Run Database Migrations**
   ```bash
   docker exec kgents-agent_deployment_service-1 alembic upgrade head
   ```

4. **Start the Service**
   ```bash
   docker compose up agent_deployment_service
   ```

### GitHub Actions Setup (Recommended for Builds)

1. **Run Setup Script**
   ```bash
   ./scripts/setup_github_actions.sh
   ```

2. **Configure Secrets in GitHub**
   - Go to Settings → Secrets → Actions
   - Add required secrets (see docs/GITHUB_ACTIONS_SETUP.md)

3. **Update Configuration**
   ```bash
   AGENT_DEPLOYMENT_SERVICE_BUILD_STRATEGY=github_actions
   ```

### Google Cloud Setup (For Cloud Run Deployments)

1. **Enable Required APIs**
   ```bash
   gcloud services enable run.googleapis.com cloudbuild.googleapis.com
   ```

2. **Set Up Authentication**
   
   **For Production**: Use Workload Identity
   ```bash
   # Create service account
   gcloud iam service-accounts create agent-deployment-sa
   
   # Grant permissions
   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="serviceAccount:agent-deployment-sa@PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/run.admin"
   ```
   
   **For Local Development**:
   ```bash
   # Authenticate locally
   gcloud auth application-default login
   
   # Mount credentials in docker-compose.dev.yml
   volumes:
     - ~/.config/gcloud:/root/.config/gcloud:ro
   ```

## Deployment Workflows

### Deploy a Langflow Agent

```python
# Example: Deploy a Langflow agent
POST /deployments/
{
  "agent_id": "uuid",
  "agent_version_id": "uuid",
  "deploy_real_agent": true,
  "build_strategy": "github_actions",
  "deployment_strategy": "cloud_run"
}
```

### Monitor Deployment

```python
# Check deployment status
GET /deployments/{deployment_id}/status

# Response
{
  "status": "running",
  "endpoint_url": "https://agent-xyz.run.app",
  "deployed_at": "2024-01-15T10:30:00Z"
}
```

## Post-Deploy Verification (Langflow Runtime)

Use these steps to validate a deployed Langflow runtime (Cloud Run) and run a simple flow.

### Service readiness

- GET `${LANGFLOW_URL}/health` → expect `{ "status": "ok" }`
- GET `${LANGFLOW_URL}/api/v1/version` → expect Langflow version (e.g., `1.0.0a42`)
- `${LANGFLOW_URL}/openapi.json` and `${LANGFLOW_URL}/docs` should be accessible

```bash
# Example (set to your Cloud Run URL)
LANGFLOW_URL="https://your-cloud-run-url.run.app"

curl -sS "$LANGFLOW_URL/health"
curl -sS "$LANGFLOW_URL/api/v1/version"
```

### Authentication

If `LANGFLOW_AUTO_LOGIN=True` (useful for dev/test), you can mint a Bearer token:

```bash
TOKEN=$(curl -sS "$LANGFLOW_URL/api/v1/auto_login" | jq -r .access_token)
echo "$TOKEN" | head -c 16; echo
```

List flows using the Bearer token:

```bash
curl -sS -H "Authorization: Bearer $TOKEN" \
  "$LANGFLOW_URL/api/v1/flows/"
```

Create an API key (copy the unmasked key from the response):

```bash
curl -sS -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"ci-run"}' \
  "$LANGFLOW_URL/api/v1/api_key/"
```

Run a flow using the API key (replace FLOW_ID and API_KEY):

```bash
FLOW_ID="00000000-0000-0000-0000-000000000000"   # replace with a real flow ID
API_KEY="paste-your-api-key"

curl -sS -X POST \
  "$LANGFLOW_URL/api/v1/run/$FLOW_ID?stream=false" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{
        "input_value": "Hello",
        "input_type": "chat",
        "output_type": "chat"
      }'
```

Notes:
- If the flows list is empty, create or upload a flow via `POST /api/v1/flows/` or `POST /api/v1/flows/upload/`.
- The flows API paths typically include a trailing slash (e.g., `/api/v1/flows/`).

### CI/CD smoke tests (recommended)

Run after each deploy to Cloud Run:

```bash
set -euo pipefail
LANGFLOW_URL="https://your-cloud-run-url.run.app"

curl -fsS "$LANGFLOW_URL/health" >/dev/null
curl -fsS "$LANGFLOW_URL/api/v1/version" | jq -e '.version | length > 0' >/dev/null
```

### Artifact Registry verification

If a deploy fails with "image not found" or to manually confirm the image exists in GAR, run:

```bash
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/kgents/kgents-images \
  --include-tags \
  --filter="package:agent-runtime-<deployment_id>"

gcloud artifacts docker images describe \
  us-central1-docker.pkg.dev/kgents/kgents-images/agent-runtime-<deployment_id>:latest \
  --project kgents \
  --location us-central1
```

### Security

- Disable `LANGFLOW_AUTO_LOGIN` in production; manage users and API keys explicitly.
- Never expose Langflow without auth; prefer a gateway and per-environment API keys.
- Ensure the container listens on port `8080` for Cloud Run.

## Troubleshooting

### Common Issues

1. **Black Formatter Error**
   - Solution: Disabled in alembic.ini post-write hooks

2. **Container Architecture Mismatch**
   - Problem: ARM64 builds fail on Cloud Run (requires AMD64)
   - Solution: Use GitHub Actions for cross-platform builds

3. **Authentication Errors**
   - Ensure gcloud is authenticated: `gcloud auth list`
   - Check service account permissions

4. **Database Connection Issues**
   - Verify DATABASE_URL is correct
   - Check if migrations have been run

## Development Best Practices

1. **Strategy Pattern**: Keep build and deployment strategies separate
2. **Error Handling**: Always handle deployment failures gracefully
3. **Logging**: Use structured logging for better observability
4. **Testing**: Test with deploy_real_agent=false first
5. **Security**: Never commit credentials; use environment variables

## Contributing

See the main Kgents CONTRIBUTING.md for guidelines.

## License

Part of the Kgents platform - see LICENSE file for details.
