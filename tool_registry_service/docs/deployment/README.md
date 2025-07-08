# Tool Registry Service Deployment Guide

This document provides instructions for deploying the Tool Registry Service in various environments.

## Deployment Architecture

The Tool Registry Service is designed to be deployed as a containerized microservice within the Kgents platform ecosystem. It communicates with other services through API calls and relies on a PostgreSQL database for persistence.

### Deployment Environments

1. **Development**: Local development environment
2. **Staging**: Pre-production testing environment
3. **Production**: Live production environment

## Prerequisites

- Docker and Docker Compose
- Access to container registry
- PostgreSQL 15+ database
- Network access to other Kgents services (Auth Service)

## Configuration

### Environment Variables

The Tool Registry Service is configured using environment variables. Different configurations are available for different environments:

- `.env.dev`: Development environment
- `.env.test`: Testing environment
- `.env.prod`: Production environment

Key environment variables:

```
# Service Configuration
TOOL_REGISTRY_SERVICE_ENVIRONMENT=production
TOOL_REGISTRY_SERVICE_LOGGING_LEVEL=INFO
TOOL_REGISTRY_SERVICE_ROOT_PATH=/api/v1/tools

# Database Configuration
TOOL_REGISTRY_SERVICE_DATABASE_URL=postgresql+psycopg://user:password@host:port/database

# Supabase Auth Proxy Configuration
TOOL_REGISTRY_SERVICE_SUPABASE_URL=http://auth_service_url:8000
TOOL_REGISTRY_SERVICE_SUPABASE_KEY=your_supabase_key

# CORS Configuration
TOOL_REGISTRY_SERVICE_CORS_ORIGINS=http://localhost:3000,https://app.kgents.ai

# Tool Execution Configuration
TOOL_REGISTRY_SERVICE_ENABLE_HTTP_TOOLS=true
TOOL_REGISTRY_SERVICE_ENABLE_PYTHON_TOOLS=true
TOOL_REGISTRY_SERVICE_ENABLE_JS_TOOLS=true
TOOL_REGISTRY_SERVICE_ENABLE_COMMAND_TOOLS=false
TOOL_REGISTRY_SERVICE_MAX_EXECUTION_TIME=30
```

### Secrets Management

For production deployments, sensitive configuration (API keys, credentials) should be managed using a secrets management solution:

- Kubernetes Secrets
- Docker Secrets
- Cloud provider secret management (AWS Secrets Manager, Google Secret Manager)

## Deployment Methods

### Docker Compose Deployment

For development and simple staging environments:

1. **Configure environment**:
   ```bash
   cp .env.example .env.prod
   # Edit .env.prod with production settings
   ```

2. **Build and start containers**:
   ```bash
   docker-compose -f docker-compose.prod.yml build
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Apply database migrations**:
   ```bash
   # Create database for production if it doesn't exist
   docker-compose -f docker-compose.prod.yml exec tool_registry_service \
     python -m scripts.manage_migrations create-db --env=prod
   
   # Apply migrations to production database
   docker-compose -f docker-compose.prod.yml exec tool_registry_service \
     python -m scripts.manage_migrations upgrade --env=prod
   ```

### Kubernetes Deployment

For production and scalable environments:

1. **Build and push Docker image**:
   ```bash
   docker build -t registry.kgents.ai/tool-registry-service:latest -f Dockerfile.prod .
   docker push registry.kgents.ai/tool-registry-service:latest
   ```

2. **Apply Kubernetes manifests**:
   ```bash
   kubectl apply -f kubernetes/tool-registry-service.yaml
   ```

3. **Apply database migrations**:
   ```bash
   # Create production database if it doesn't exist
   kubectl exec -it $(kubectl get pods -l app=tool-registry-service -o jsonpath="{.items[0].metadata.name}") -- \
     python -m scripts.manage_migrations create-db --env=prod
     
   # Apply migrations to production database
   kubectl exec -it $(kubectl get pods -l app=tool-registry-service -o jsonpath="{.items[0].metadata.name}") -- \
     python -m scripts.manage_migrations upgrade --env=prod
   ```

### Cloud Provider Deployments

#### AWS Deployment

1. **Create ECR repository**:
   ```bash
   aws ecr create-repository --repository-name kgents/tool-registry-service
   ```

2. **Build and push Docker image**:
   ```bash
   aws ecr get-login-password | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.$(aws configure get region).amazonaws.com
   
   docker build -t $(aws sts get-caller-identity --query Account --output text).dkr.ecr.$(aws configure get region).amazonaws.com/kgents/tool-registry-service:latest -f Dockerfile.prod .
   
   docker push $(aws sts get-caller-identity --query Account --output text).dkr.ecr.$(aws configure get region).amazonaws.com/kgents/tool-registry-service:latest
   ```

3. **Deploy to ECS or EKS** according to your infrastructure setup.

## Health Checks and Monitoring

### Health Check Endpoints

The service provides health check endpoints for monitoring:

- `/api/v1/health`: Service health check
- `/api/v1/health/db`: Database connection health check

These endpoints should be configured in your load balancer or container orchestrator for service health monitoring.

### Logging

The service logs to stdout/stderr in JSON format, which can be captured by container logging systems.

Log levels are configurable via the `TOOL_REGISTRY_SERVICE_LOGGING_LEVEL` environment variable.

### Metrics

The service exposes Prometheus metrics at `/metrics` for monitoring:

- HTTP request counts and latencies
- Database query latencies
- Tool execution counts and latencies
- Error rates

## Backup and Restore

### Database Backup

For PostgreSQL database backup:

```bash
# Using pg_dump directly
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -F c -f backup.dump

# Using Docker
docker exec -t postgres_container pg_dump -U $DB_USER -d $DB_NAME -F c > backup.dump
```

### Database Restore

For PostgreSQL database restore:

```bash
# Using pg_restore directly
pg_restore -h $DB_HOST -U $DB_USER -d $DB_NAME -F c backup.dump

# Using Docker
cat backup.dump | docker exec -i postgres_container pg_restore -U $DB_USER -d $DB_NAME
```

## Deployment Checklist

Before deploying to production:

1. ✅ **Database Migrations**: Ensure all migrations are applied
2. ✅ **Environment Variables**: Verify all environment variables are set correctly
3. ✅ **Security**: Ensure secrets are properly managed
4. ✅ **Network**: Verify connectivity to dependencies (Auth Service, database)
5. ✅ **Load Testing**: Perform load testing to ensure performance
6. ✅ **Rollback Plan**: Document rollback procedure in case of issues
7. ✅ **Monitoring**: Set up alerts for service health
8. ✅ **Documentation**: Update API documentation if needed

## Rollback Procedure

If issues are encountered after deployment:

1. **Revert to previous version**:
   ```bash
   # Using Docker Compose
   docker-compose -f docker-compose.prod.yml down
   docker image tag registry.kgents.ai/tool-registry-service:previous registry.kgents.ai/tool-registry-service:latest
   docker-compose -f docker-compose.prod.yml up -d
   
   # Using Kubernetes
   kubectl rollout undo deployment/tool-registry-service
   ```

2. **Rollback database migrations** if necessary:
   ```bash
   # Rollback production database migrations
   python -m scripts.manage_migrations downgrade --env=prod --revision=-1
   ```

3. **Notify stakeholders** about the rollback and issue.
