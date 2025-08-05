# agent_deployment_service/src/agent_deployment_service/services/orchestration_service.py
import asyncio
import json
import os
import subprocess
import tempfile
from uuid import UUID

import docker
import httpx
from docker.errors import APIError, BuildError
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients import management_client
from ..config import settings
from ..db import get_session_factory
from ..logging_config import logger
from ..models import Deployment, DeploymentStatus
from ..models.deployment import Deployment, DeploymentStatus
from .strategies import CloudRunStrategy, DeploymentStrategy, KubernetesStrategy

# Initialize Docker client from the environment
try:
    docker_client = docker.from_env()
except docker.errors.DockerException:
    logger.error("Could not connect to Docker daemon. Is Docker running?")
    docker_client = None


# Initialize Jinja2 environment
template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
jinja_env = Environment(loader=FileSystemLoader(template_dir))


async def update_deployment_status(
    deployment_id: UUID, status: DeploymentStatus, **kwargs
):
    """Helper to update deployment status in the DB in its own session."""
    SessionFactory = get_session_factory()
    async with SessionFactory() as session:
        deployment = await session.get(Deployment, deployment_id)
        if deployment:
            deployment.status = status
            for key, value in kwargs.items():
                if hasattr(deployment, key):
                    setattr(deployment, key, value)
            await session.commit()
            logger.info(
                f"[Deployment:{deployment_id}] Status updated to {status.value}"
            )


def get_deployment_strategy() -> DeploymentStrategy:
    """Selects the deployment strategy based on configuration."""
    strategy_name = settings.DEPLOYMENT_STRATEGY.lower()
    if strategy_name == "kubernetes":
        logger.info("Using Kubernetes deployment strategy.")
        return KubernetesStrategy()
    elif strategy_name == "cloud_run":
        logger.info("Using Google Cloud Run deployment strategy.")
        return CloudRunStrategy()
    else:
        raise ValueError(f"Unknown deployment strategy: '{strategy_name}'")


async def start_deployment_process(deployment_id: UUID):
    """
    Main asynchronous function to deploy a Langflow agent using a configured strategy.
    """
    logger.info(f"[Deployment:{deployment_id}] Starting deployment process.")

    if not docker_client:
        await update_deployment_status(
            deployment_id,
            DeploymentStatus.FAILED,
            error_message="Deployment service cannot connect to Docker daemon.",
        )
        return

    # Fetch deployment record to get agent/version IDs
    SessionFactory = get_session_factory()
    async with SessionFactory() as session:
        deployment = await session.get(Deployment, deployment_id)
        if not deployment:
            logger.error(
                f"[Deployment:{deployment_id}] Deployment record not found in database."
            )
            return
        agent_id = deployment.agent_id
        version_id = deployment.agent_version_id

    try:
        # 1. Update status to DEPLOYING
        await update_deployment_status(deployment_id, DeploymentStatus.DEPLOYING)

        # 2. Call the agent_management_service to get the agent's config
        logger.info(
            f"[Deployment:{deployment_id}] Fetching agent config for version {version_id}..."
        )
        version_config = await management_client.get_agent_version_config(
            agent_id, version_id
        )
        langflow_flow_json = version_config.get("config_snapshot", {}).get(
            "langflow_data"
        )
        if not langflow_flow_json:
            raise ValueError(
                "Langflow flow JSON not found in agent version configuration."
            )

        # Prepare for image build
        image_name = f"agent-runtime-{str(deployment_id).lower()}"
        image_tag = f"{settings.GCR_HOSTNAME}/{image_name}:latest"

        with tempfile.TemporaryDirectory() as build_dir:
            build_dir_path = os.path.realpath(build_dir)
            logger.info(
                f"[Deployment:{deployment_id}] Created Docker build context at: {build_dir_path}"
            )

            # 3. Use a Dockerfile template (Jinja2)
            with open(os.path.join(build_dir_path, "flow.json"), "w") as f:
                json.dump(langflow_flow_json, f)

            template = jinja_env.get_template("Dockerfile.j2")
            dockerfile_content = (
                template.render()
            )  # No variables needed for this simple template
            with open(os.path.join(build_dir_path, "Dockerfile"), "w") as f:
                f.write(dockerfile_content)

            # 4. Use the Docker SDK to build the image
            logger.info(
                f"[Deployment:{deployment_id}] Building Docker image: {image_tag}"
            )
            image, build_logs = docker_client.images.build(
                path=build_dir_path, tag=image_tag, rm=True
            )
            for log in build_logs:
                if "stream" in log:
                    logger.debug(f"[Build:{deployment_id}] {log['stream'].strip()}")

            # 5. Push the image to a container registry
            logger.info(
                f"[Deployment:{deployment_id}] Pushing image to {settings.GCR_HOSTNAME}..."
            )
            docker_client.images.push(image_tag, stream=True, decode=True)
            # You can iterate through the push logs here if needed

            # 6. Use the selected strategy to deploy
            strategy = get_deployment_strategy()
            logger.info(
                f"[Deployment:{deployment_id}] Using deployment strategy: {strategy.__class__.__name__}"
            )
            endpoint_url, metadata = await strategy.deploy(deployment_id, image_tag)

            # 7. Update status to RUNNING
            await update_deployment_status(
                deployment_id,
                DeploymentStatus.RUNNING,
                endpoint_url=endpoint_url,
                deployment_metadata=metadata,
            )
            logger.info(
                f"[Deployment:{deployment_id}] Deployment successful! Endpoint: {endpoint_url}"
            )

    except (BuildError, APIError, ValueError, Exception) as e:
        error_message = f"Deployment failed: {str(e)}"
        logger.error(f"[Deployment:{deployment_id}] {error_message}", exc_info=True)
        # 8. Update status to FAILED
        await update_deployment_status(
            deployment_id, DeploymentStatus.FAILED, error_message=error_message
        )


async def start_undeploy_process(deployment_id: UUID):
    """Terminates and deletes a deployed service using the configured strategy."""
    logger.info(f"[Undeploy:{deployment_id}] Starting undeployment process.")
    strategy = get_deployment_strategy()
    await strategy.undeploy(deployment_id)
