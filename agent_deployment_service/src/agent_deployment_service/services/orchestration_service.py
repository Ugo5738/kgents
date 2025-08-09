# agent_deployment_service/src/agent_deployment_service/services/orchestration_service.py
import asyncio
import json
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Optional
from uuid import UUID

import docker
from docker.errors import APIError, BuildError
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from .strategies import get_deployment_strategy, get_build_strategy
from ..config import Settings
from ..db import get_session_factory
from ..models.deployment import Deployment, DeploymentStatus
from ..clients import management_client
from ..logging_config import logger

# Get settings
settings = Settings()

# Initialize Docker client from the environment
try:
    docker_client = docker.from_env()
except docker.errors.DockerException:
    logger.error("Could not connect to Docker daemon. Is Docker running?")
    docker_client = None


# Initialize Jinja2 environment
template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
jinja_env = Environment(loader=FileSystemLoader(template_dir))


async def get_deployment_status(deployment_id: UUID) -> dict:
    """Fetch the current deployment status and metadata from the database.

    Returns a plain dict for easy JSON serialization.
    """
    SessionFactory = get_session_factory()
    async with SessionFactory() as session:
        deployment = await session.get(Deployment, deployment_id)
        if not deployment:
            return {"id": str(deployment_id), "found": False, "status": None}

        return {
            "id": str(deployment.id),
            "status": getattr(deployment.status, "value", deployment.status),
            "endpoint_url": deployment.endpoint_url,
            "deployment_metadata": deployment.deployment_metadata,
            "error_message": deployment.error_message,
            "created_at": getattr(deployment, "created_at", None),
            "updated_at": getattr(deployment, "updated_at", None),
        }


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

            # Choose template based on deployment type
            # Use 'deploy_real_agent' flag on Deployment to select real agent image
            try:
                deploy_real_agent = bool(getattr(deployment, "deploy_real_agent", False))
            except Exception:
                deploy_real_agent = False
            template_name = "Dockerfile.agent.j2" if deploy_real_agent else "Dockerfile.j2"
            template = jinja_env.get_template(template_name)
            dockerfile_content = (
                template.render()
            )  # No variables needed for this simple template
            with open(os.path.join(build_dir_path, "Dockerfile"), "w") as f:
                f.write(dockerfile_content)

            # 4. Use the Docker SDK to build the image
            def _build_with_platform(platform_value: str | None):
                kw = {
                    "path": build_dir_path,
                    "tag": image_tag,
                    "rm": True,
                    "pull": True,
                    "nocache": True,
                }
                if platform_value:
                    kw["platform"] = platform_value
                logger.info(
                    f"[Deployment:{deployment_id}] Building Docker image: {image_tag} (platform: {platform_value or 'default'})"
                )
                return docker_client.images.build(**kw)

            # Determine build strategy from settings
            build_strategy = settings.BUILD_STRATEGY.lower()
            
            # For Cloud Run deployments, we need linux/amd64 images
            if settings.DEPLOYMENT_STRATEGY.lower() == "cloud_run":
                logger.info(
                    f"[Deployment:{deployment_id}] Cloud Run deployment detected; using {build_strategy} for linux/amd64"
                )
                
                # Get build strategy instance (now consistent for both cloud_build and github_actions)
                build_strategy_instance = get_build_strategy(build_strategy)
                logger.info(f"[Deployment:{deployment_id}] Using {build_strategy} for cross-platform build")
                
                # Trigger the build workflow
                run_id = await build_strategy_instance.trigger_workflow(
                    deployment_id=str(deployment_id),
                    image_tag=image_tag,
                    build_context_path=build_dir_path
                )
                
                logger.info(f"[Deployment:{deployment_id}] {build_strategy} workflow triggered, run ID: {run_id}")
                
                # Wait for build completion
                build_success = await build_strategy_instance.wait_for_build(
                    run_id=run_id,
                    deployment_id=str(deployment_id),
                    timeout=600  # 10 minutes
                )
                
                if build_success:
                    logger.info(f"[Deployment:{deployment_id}] {build_strategy} build completed successfully")
                    image_pushed = True
                else:
                    raise RuntimeError(f"{build_strategy} build failed")
            else:
                # Use regular platform detection with fallback for other deployment strategies
                preferred_platform = settings.DOCKER_BUILD_PLATFORM
                logger.info(
                    f"[Deployment:{deployment_id}] Building with platform: {preferred_platform or 'default'}"
                )
                
                try:
                    image, build_logs = _build_with_platform(preferred_platform)
                except BuildError as be:
                    msg = str(be).lower()
                    # If manifest/arch issues on arm64, retry with linux/amd64
                    retry_amd64 = (
                        preferred_platform is None
                        and (
                            "no matching manifest" in msg
                            or "exec format" in msg
                            or ("platform" in msg and "not supported" in msg)
                        )
                    )
                    if retry_amd64:
                        logger.warning(
                            f"[Deployment:{deployment_id}] Build failed due to platform/manifest issue. Retrying with linux/amd64..."
                        )
                        image, build_logs = _build_with_platform("linux/amd64")
                    else:
                        # If we were explicitly using linux/amd64 and hit destination image error, retry without platform
                        retry_no_platform = preferred_platform is not None and "failed to get destination image" in msg
                        if retry_no_platform:
                            logger.warning(
                                f"[Deployment:{deployment_id}] Build failed with destination image error on {preferred_platform}. Retrying without platform..."
                            )
                            image, build_logs = _build_with_platform(None)
                        else:
                            raise
            if 'build_logs' in locals():
                for log in build_logs:
                    if "stream" in log:
                        logger.debug(f"[Build:{deployment_id}] {log['stream'].strip()}")

            # 5. Push the image to the registry (skip if buildx already pushed)
            if not locals().get('image_pushed', False):
                logger.info(
                    f"[Deployment:{deployment_id}] Pushing image to {settings.GCR_HOSTNAME}..."
                )
                for line in docker_client.images.push(
                    image_tag, stream=True, decode=True
                ):
                    if "status" in line:
                        logger.info(f"[Push:{deployment_id}] {line['status']}")
                    if "error" in line:
                        logger.error(f"[Push:{deployment_id}] {line['error']}")
                        raise RuntimeError(f"Failed to push image: {line['error']}")

                logger.info(f"[Deployment:{deployment_id}] Image pushed successfully.")
            else:
                logger.info(f"[Deployment:{deployment_id}] Image already pushed via buildx.")

            # 6. Use the selected strategy to deploy
            strategy = get_deployment_strategy(settings.DEPLOYMENT_STRATEGY)
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
    strategy = get_deployment_strategy(settings.DEPLOYMENT_STRATEGY)
    await strategy.undeploy(deployment_id)
