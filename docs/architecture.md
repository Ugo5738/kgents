# Architecture & Deployment Overview

This document captures our service architecture, starting as a monorepo/multi-module app with a clear path to splitting into standalone microservice repos and deploying via containers and Kubernetes.

## 1. Monorepo First

- All services live together under `app/` (auth, agents, tools, NL agents, run).
- Shared code (models, DB client, utils) is imported directly, simplifying local dev and CI.

## 2. Containerization

- Each service folder produces its own Docker image:
  ```bash
  docker build -f app/api/v1/auth/Dockerfile -t myorg/user-service:latest .
  docker build -f app/api/v1/agents/Dockerfile -t myorg/agent-service:latest .
  ```
- Locally, orchestrate with `docker-compose.yml` to run all services side-by-side.

## 3. Kubernetes Deployment

- Deploy each image as a separate **Deployment** and **Service** in a Kubernetes cluster.
- All services can run on the same nodes (shared cluster) with independent scaling, health checks, and routing.

## 4. From Monorepo to Polyrepo

- When a service stabilizes or needs independent versioning, extract its folder into its own Git repo (e.g. `user-service.git`).
- Container build and K8s manifests remain unchanged—only the image source moves to the new repo's CI pipeline.

## 5. Next Steps & Best Practices

- Maintain a single `docker-compose.yml` for local dev in the monorepo.
- Tag and push per-service images with clear versioning.
- Define K8s manifests or Helm charts to deploy all services (can live in a top-level `kubernetes/` folder).
- Document cross-service contracts (OpenAPI) and shared libraries in `docs/` for clear developer onboarding.

---

_This architecture guide lives alongside our code so future maintainers always know where we started and how to evolve._
