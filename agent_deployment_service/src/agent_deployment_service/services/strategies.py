# agent_deployment_service/src/agent_deployment_service/services/strategies.py
import abc
import asyncio
import base64
import json
import os
import subprocess
import tarfile
import tempfile
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

try:
    import httpx  # type: ignore
except ImportError:  # Keep import-time light for test environments
    httpx = None  # Will raise helpful errors if methods are invoked

# Optional imports - strategies use gcloud CLI instead
try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
except ImportError:
    client = None
    config = None
    ApiException = Exception  # Fallback to base Exception

from ..config import settings
from ..logging_config import logger


class DeploymentStrategy(abc.ABC):
    """Abstract base class for deployment strategies."""

    @abc.abstractmethod
    async def deploy(self, deployment_id: UUID, image_tag: str) -> Tuple[str, Dict]:
        """Deploy the container and return the endpoint URL and metadata."""
        pass

    @abc.abstractmethod
    async def undeploy(self, deployment_id: UUID):
        """Terminate and clean up the deployment."""
        pass


class CloudRunStrategy(DeploymentStrategy):
    """Deployment strategy for Google Cloud Run."""

    async def deploy(self, deployment_id: UUID, image_tag: str) -> Tuple[str, Dict]:
        service_name = f"agent-runtime-{str(deployment_id).lower()}"
        logger.info(
            f"[CloudRun:{deployment_id}] Deploying to Cloud Run as service: {service_name}"
        )

        command = [
            "gcloud",
            "run",
            "deploy",
            service_name,
            "--image",
            image_tag,
            "--platform",
            "managed",
            "--region",
            settings.GCP_REGION,
            "--port",
            "8080",
            "--allow-unauthenticated",
            "--project",
            settings.GCP_PROJECT_ID,
            "--set-env-vars",
            "LANGFLOW_BACKEND_ONLY=true,LANGFLOW_OPEN_BROWSER=false,LANGFLOW_HOST=0.0.0.0",
            "--timeout",
            "900",  # 15 minutes timeout
            "--memory",
            "1Gi",
            "--cpu",
            "1",
            "--max-instances",
            "1",
            "--format=json",
        ]

        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            deploy_info = json.loads(result.stdout)
            endpoint_url = deploy_info["status"]["url"]
            metadata = {
                "service_name": service_name,
                "region": settings.GCP_REGION,
                "revision": deploy_info["status"].get("latestRevisionName"),
            }
            return endpoint_url, metadata
        except subprocess.CalledProcessError as e:
            error_details = e.stderr or e.stdout
            logger.error(
                f"[CloudRun:{deployment_id}] Deployment command failed: {error_details}"
            )

            # Immediately capture logs for the failed revision
            try:
                log_command = [
                    "gcloud",
                    "logging",
                    "read",
                    f'resource.type="cloud_run_revision" AND resource.labels.service_name="{service_name}"',
                    "--project",
                    settings.GCP_PROJECT_ID,
                    "--limit",
                    "50",
                    "--freshness",
                    "10m",
                    "--format",
                    "value(timestamp,severity,textPayload)",
                ]
                log_result = subprocess.run(
                    log_command, capture_output=True, text=True, timeout=30
                )
                if log_result.stdout:
                    logger.error(
                        f"[CloudRun:{deployment_id}] Container logs:\n{log_result.stdout}"
                    )
                else:
                    logger.warning(
                        f"[CloudRun:{deployment_id}] No container logs found yet"
                    )
            except Exception as log_err:
                logger.warning(
                    f"[CloudRun:{deployment_id}] Failed to capture logs: {log_err}"
                )

            raise RuntimeError(f"gcloud command failed: {error_details}")

    async def undeploy(self, deployment_id: UUID):
        service_name = f"agent-runtime-{str(deployment_id).lower()}"
        logger.info(
            f"[CloudRun:{deployment_id}] Deleting Cloud Run service: {service_name}"
        )

        command = [
            "gcloud",
            "run",
            "services",
            "delete",
            service_name,
            "--platform",
            "managed",
            "--region",
            settings.GCP_REGION,
            "--project",
            settings.GCP_PROJECT_ID,
            "--quiet",
        ]

        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
            logger.info(f"[CloudRun:{deployment_id}] Service deleted successfully.")
        except subprocess.CalledProcessError as e:
            error_details = e.stderr or e.stdout
            # Don't raise an exception, just log it. Maybe the service was already deleted.
            logger.error(
                f"[CloudRun:{deployment_id}] Failed to delete service: {error_details}"
            )


class KubernetesStrategy(DeploymentStrategy):
    """Deployment strategy for Kubernetes."""

    def __init__(self):
        if client is None or config is None:
            raise ImportError(
                "Kubernetes Python client not installed. "
                "Install with: pip install kubernetes"
            )
        try:
            config.load_incluster_config()
        except Exception:  # Catch any exception since config might be None
            try:
                config.load_kube_config()
            except Exception as e:
                logger.warning(f"Could not load Kubernetes config: {e}")
        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.core_v1 = client.CoreV1Api()
        self.namespace = "agent-runtimes"  # Deploy agents to a dedicated namespace

    async def deploy(self, deployment_id: UUID, image_tag: str) -> Tuple[str, Dict]:
        service_name = f"agent-runtime-{str(deployment_id).lower()}"
        labels = {"app": service_name, "deployment-id": str(deployment_id)}

        # 1. Define the Deployment
        deployment_manifest = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": service_name, "labels": labels},
            "spec": {
                "replicas": 1,
                "selector": {"matchLabels": labels},
                "template": {
                    "metadata": {"labels": labels},
                    "spec": {
                        "containers": [
                            {
                                "name": "agent-runtime",
                                "image": image_tag,
                                "ports": [{"containerPort": 8080}],
                            }
                        ]
                    },
                },
            },
        }

        # 2. Define the Service to expose the Deployment
        service_manifest = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": service_name, "labels": labels},
            "spec": {
                "selector": labels,
                "ports": [{"port": 80, "targetPort": 8080}],
                "type": "ClusterIP",  # Internal traffic only
            },
        }

        try:
            logger.info(
                f"[K8s:{deployment_id}] Creating Deployment '{service_name}'..."
            )
            self.apps_v1.create_namespaced_deployment(
                body=deployment_manifest, namespace=self.namespace
            )

            logger.info(f"[K8s:{deployment_id}] Creating Service '{service_name}'...")
            self.core_v1.create_namespaced_service(
                body=service_manifest, namespace=self.namespace
            )

            # The internal K8s DNS name is the endpoint
            endpoint_url = f"http://{service_name}.{self.namespace}.svc.cluster.local"
            metadata = {"service_name": service_name, "namespace": self.namespace}

            return endpoint_url, metadata
        except ApiException as e:
            error_body = json.loads(e.body)
            error_message = error_body.get(
                "message", "An error occurred during Kubernetes deployment."
            )
            logger.error(f"[K8s:{deployment_id}] API Exception: {error_message}")
            raise RuntimeError(f"Kubernetes deployment failed: {error_message}")

    async def undeploy(self, deployment_id: UUID):
        service_name = f"agent-runtime-{str(deployment_id).lower()}"
        logger.info(
            f"[K8s:{deployment_id}] Deleting Deployment and Service '{service_name}'..."
        )

        try:
            # Delete the Deployment
            self.apps_v1.delete_namespaced_deployment(
                name=service_name, namespace=self.namespace
            )
            # Delete the Service
            self.core_v1.delete_namespaced_service(
                name=service_name, namespace=self.namespace
            )
            logger.info(f"[K8s:{deployment_id}] Resources deleted successfully.")
        except ApiException as e:
            if e.status != 404:  # Ignore "Not Found" errors
                error_body = json.loads(e.body)
                error_message = error_body.get(
                    "message", "An error occurred during cleanup."
                )
                logger.error(
                    f"[K8s:{deployment_id}] Failed to delete resources: {error_message}"
                )


class CloudBuildStrategy:
    """Build strategy using Google Cloud Build."""

    async def trigger_workflow(
        self, deployment_id: str, image_tag: str, build_context_path: str
    ) -> str:
        """Trigger Cloud Build and return build ID."""
        logger.info(f"[CloudBuild:{deployment_id}] Submitting build for {image_tag}")

        # Create tarball of build context
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tar_file:
            tar_path = tar_file.name
            with tarfile.open(tar_path, "w:gz") as tar:
                tar.add(build_context_path, arcname=".")

        try:
            # Submit to Cloud Build
            cloud_build_cmd = [
                "gcloud",
                "builds",
                "submit",
                "--tag",
                image_tag,
                "--project",
                settings.GCP_PROJECT_ID,
                "--timeout",
                "20m",
                "--machine-type",
                "n1-highcpu-8",
                "--async",  # Return immediately with build ID
                "--format",
                "value(id)",
                tar_path,
            ]

            result = subprocess.run(
                cloud_build_cmd,
                capture_output=True,
                text=True,
                check=True,
                env=os.environ.copy(),
            )

            build_id = result.stdout.strip()
            logger.info(
                f"[CloudBuild:{deployment_id}] Build submitted with ID: {build_id}"
            )
            return build_id

        finally:
            # Clean up tar file
            if os.path.exists(tar_path):
                os.unlink(tar_path)

    async def wait_for_build(
        self, run_id: str, deployment_id: str, timeout: int = 600
    ) -> bool:
        """Wait for Cloud Build completion."""
        logger.info(f"[CloudBuild:{deployment_id}] Waiting for build {run_id}")

        # Poll Cloud Build status
        check_cmd = [
            "gcloud",
            "builds",
            "describe",
            run_id,
            "--project",
            settings.GCP_PROJECT_ID,
            "--format",
            "value(status)",
        ]

        start_time = time.time()
        while time.time() - start_time < timeout:
            result = subprocess.run(
                check_cmd, capture_output=True, text=True, env=os.environ.copy()
            )

            status = result.stdout.strip()
            logger.info(f"[CloudBuild:{deployment_id}] Build status: {status}")

            if status == "SUCCESS":
                return True
            elif status in ["FAILURE", "TIMEOUT", "CANCELLED"]:
                raise RuntimeError(f"Cloud Build failed with status: {status}")

            await asyncio.sleep(10)

        raise TimeoutError(f"Cloud Build timed out after {timeout} seconds")


class GitHubActionsStrategy(DeploymentStrategy):
    """Build strategy using GitHub Actions for free cross-platform builds."""

    def __init__(self):
        self.github_token = settings.GITHUB_TOKEN
        self.github_owner = settings.GITHUB_OWNER
        self.github_repo = settings.GITHUB_REPO

        if not self.github_token:
            logger.warning(
                "[GitHub Actions] GITHUB_TOKEN not set, will need manual trigger"
            )

    async def trigger_workflow(
        self, deployment_id: str, image_tag: str, build_context_path: str
    ) -> str:
        """Trigger GitHub Actions workflow and return run ID."""

        if httpx is None:
            raise ImportError(
                "httpx is required for GitHubActionsStrategy. Install with: pip install httpx"
            )

        # Create tar.gz and encode as base64
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tar_file:
            tar_path = tar_file.name
            with tarfile.open(tar_path, "w:gz") as tar:
                tar.add(build_context_path, arcname=".")

        with open(tar_path, "rb") as f:
            build_context_b64 = base64.b64encode(f.read()).decode("utf-8")

        os.unlink(tar_path)

        # Trigger workflow via GitHub API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/actions/workflows/build-agent-image.yml/dispatches",
                headers={
                    "Authorization": f"Bearer {self.github_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
                json={
                    "ref": "main",  # or your default branch
                    "inputs": {
                        "deployment_id": str(deployment_id),
                        "image_tag": image_tag,
                        "build_context": build_context_b64[
                            :65000
                        ],  # GitHub has input size limits
                    },
                },
            )

            if response.status_code == 204:
                logger.info(f"[GitHub:{deployment_id}] Workflow triggered successfully")
                # Get the run ID from recent runs
                await asyncio.sleep(2)  # Wait for workflow to register

                runs_response = await client.get(
                    f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/actions/runs",
                    headers={
                        "Authorization": f"Bearer {self.github_token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                    params={"per_page": 5},
                )

                if runs_response.status_code == 200:
                    runs = runs_response.json()["workflow_runs"]
                    for run in runs:
                        # Find our run by checking inputs (this is a simplification)
                        if run["name"] == "Build Agent Docker Image":
                            return str(run["id"])

                return "unknown"
            else:
                raise RuntimeError(f"Failed to trigger workflow: {response.text}")

    async def wait_for_build(
        self, run_id: str, deployment_id: str, timeout: int = 600
    ) -> bool:
        """Poll GitHub Actions for build completion."""

        if httpx is None:
            raise ImportError(
                "httpx is required for GitHubActionsStrategy. Install with: pip install httpx"
            )

        if not self.github_token:
            logger.info(
                f"[GitHub:{deployment_id}] Waiting for manual workflow completion..."
            )
            await asyncio.sleep(timeout)  # Just wait and hope
            return True

        start_time = time.time()
        async with httpx.AsyncClient() as client:
            while time.time() - start_time < timeout:
                response = await client.get(
                    f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/actions/runs/{run_id}",
                    headers={
                        "Authorization": f"Bearer {self.github_token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                )

                if response.status_code == 200:
                    run_data = response.json()
                    status = run_data["status"]
                    conclusion = run_data.get("conclusion")

                    logger.info(
                        f"[GitHub:{deployment_id}] Build status: {status}, conclusion: {conclusion}"
                    )

                    if status == "completed":
                        if conclusion == "success":
                            return True
                        else:
                            raise RuntimeError(
                                f"GitHub Actions build failed: {conclusion}"
                            )

                await asyncio.sleep(10)

        raise TimeoutError(f"GitHub Actions build timed out after {timeout} seconds")

    async def deploy(self, deployment_id: UUID, image_tag: str) -> Tuple[str, Dict]:
        """This strategy only handles building. Actual deployment is done by CloudRunStrategy."""

        logger.info(
            f"[GitHub:{deployment_id}] GitHub Actions will build, then Cloud Run will deploy"
        )

        # This is called from orchestration_service which already has the build context
        # We'll return placeholder values since actual deployment happens separately
        return "", {
            "build_strategy": "github_actions",
            "note": "Build only, deploy separately",
        }

    async def undeploy(self, deployment_id: UUID):
        """No cleanup needed for GitHub Actions builds."""
        logger.info(f"[GitHub:{deployment_id}] No cleanup needed for GitHub Actions")


def get_deployment_strategy(strategy_name: str) -> DeploymentStrategy:
    """Factory function to get the appropriate DEPLOYMENT strategy (where to deploy)."""
    strategies = {
        "cloud_run": CloudRunStrategy,
        "kubernetes": KubernetesStrategy,
    }

    strategy_class = strategies.get(strategy_name.lower())
    if not strategy_class:
        raise ValueError(f"Unknown deployment strategy: {strategy_name}")

    return strategy_class()


def get_build_strategy(strategy_name: str):
    """Factory function to get the appropriate BUILD strategy (how to build images)."""
    strategies = {
        "cloud_build": CloudBuildStrategy,
        "github_actions": GitHubActionsStrategy,
    }

    strategy_class = strategies.get(strategy_name.lower())
    if not strategy_class:
        raise ValueError(f"Unknown build strategy: {strategy_name}")

    return strategy_class()
