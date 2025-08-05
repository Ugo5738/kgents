# agent_deployment_service/src/agent_deployment_service/services/strategies.py
import abc
import json
import subprocess
from typing import Dict, Tuple
from uuid import UUID

from kubernetes import client, config
from kubernetes.client.rest import ApiException

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
            "--allow-unauthenticated",
            "--project",
            settings.GCP_PROJECT_ID,
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
        try:
            # Tries to load config from in-cluster service account first,
            # then falls back to local kubeconfig file.
            config.load_incluster_config()
            logger.info("Loaded Kubernetes in-cluster configuration.")
        except config.ConfigException:
            config.load_kube_config()
            logger.info("Loaded local Kubernetes configuration from kubeconfig.")

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
