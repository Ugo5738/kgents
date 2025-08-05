# Agent Deployment Service

## Overview

The Agent Deployment Service is a core component of the Kgents platform responsible for orchestrating the deployment of AI agents. It takes a published agent version, packages it into a runnable service (e.g., a Docker container), and manages its lifecycle in the deployment environment.

## Features

- Agent deployment from a specific version.
- Tracking the status of deployments (e.g., `pending`, `deploying`, `running`, `failed`).
- Storing deployment metadata, such as the endpoint URL of the running agent.
- Providing endpoints to check the health and status of deployed agents.

# Authentication

<!-- B. Handle Authentication
For Production (The Right Way): When your agent_deployment_service is running in the cloud (e.g., on Google Kubernetes Engine), you will use Workload Identity. This securely associates your service's cloud identity with a GCP service account that has permissions to deploy Cloud Run services (roles/run.admin). The container automatically gets credentials without you needing to manage any secret keys.
For Local Development: You need to provide credentials to your container. The easiest way is to authenticate your local machine's gcloud CLI and mount the credentials into the container.
On your MacBook, run: gcloud auth application-default login
This command creates a credentials file in ~/.config/gcloud/.
You would then update your docker-compose.dev.yml to mount this file into the container. -->
