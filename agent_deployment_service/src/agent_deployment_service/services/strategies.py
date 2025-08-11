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
        # Optional override for the ref/branch to dispatch on
        # Prefer explicit env var so we don't need to define it in Settings
        self.github_ref = os.getenv("AGENT_DEPLOYMENT_SERVICE_GITHUB_REF") or getattr(
            settings, "GITHUB_REF", None
        )

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

        # Create tar.gz of build context
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tar_file:
            tar_path = tar_file.name
            with tarfile.open(tar_path, "w:gz") as tar:
                tar.add(build_context_path, arcname=".")

        # Decide transport: inline base64 (<=65k) vs. upload and pass URL
        with open(tar_path, "rb") as f:
            tar_bytes = f.read()
        build_context_b64 = base64.b64encode(tar_bytes).decode("utf-8")

        # Prepare optional URL for large payloads
        build_context_url: Optional[str] = None
        total_b64_len = len(build_context_b64)
        send_len = min(total_b64_len, 65000)
        logger.info(
            f"[GitHub:{deployment_id}] Prepared build context | repo={self.github_owner}/{self.github_repo} | image_tag={image_tag} | tar_size={len(tar_bytes)} bytes | b64_len={total_b64_len} | sending_inline={send_len}"
        )

        # If payload exceeds dispatch input limit, upload as a Release asset
        if total_b64_len > 65000:
            try:
                import httpx as _httpx  # assure type
            except Exception:
                pass
            async with httpx.AsyncClient() as client:
                headers_common = {
                    "Authorization": f"Bearer {self.github_token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                }

                # 1) Create a draft prerelease for this deployment
                tag_name = f"agent-build-context-{deployment_id}-{int(time.time())}"
                create_rel_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/releases"
                rel_payload = {
                    "tag_name": tag_name,
                    "name": f"Agent Build Context {deployment_id}",
                    "body": "Ephemeral build context for workflow_dispatch.",
                    "draft": True,
                    "prerelease": True,
                }
                rel_resp = await client.post(create_rel_url, headers=headers_common, json=rel_payload)
                if rel_resp.status_code not in (201,):
                    logger.error(
                        f"[GitHub:{deployment_id}] Failed to create release: {rel_resp.status_code} {rel_resp.text}"
                    )
                    # Fallback: we will attempt inline even if truncated
                else:
                    rel = rel_resp.json()
                    upload_url_tmpl = rel.get("upload_url", "")  # ends with {?name,label}
                    release_id = rel.get("id")
                    if upload_url_tmpl and release_id:
                        upload_url = upload_url_tmpl.split("{")[0]
                        asset_name = f"build-context-{deployment_id}.tar.gz"
                        params = {"name": asset_name}
                        # 2) Upload the tarball as asset
                        up_headers = {
                            "Authorization": f"Bearer {self.github_token}",
                            "Content-Type": "application/gzip",
                            "Accept": "application/vnd.github+json",
                            "X-GitHub-Api-Version": "2022-11-28",
                        }
                        up_resp = await client.post(upload_url, headers=up_headers, params=params, content=tar_bytes)
                        if up_resp.status_code in (201,):
                            asset = up_resp.json()
                            # Prefer the API asset URL; our workflow uses curl with proper headers
                            build_context_url = asset.get("url") or asset.get("browser_download_url")
                            logger.info(
                                f"[GitHub:{deployment_id}] Uploaded build context asset. url={build_context_url}"
                            )
                        else:
                            logger.error(
                                f"[GitHub:{deployment_id}] Failed to upload asset: {up_resp.status_code} {up_resp.text}"
                            )

        # Cleanup temp file
        try:
            os.unlink(tar_path)
        except Exception:
            pass

        # Trigger workflow via GitHub API
        async with httpx.AsyncClient() as client:
            # Resolve target ref (branch): env override -> repo default branch -> fallback to 'main'
            ref = await self._resolve_ref(client)
            url = (
                f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/actions/workflows/build-agent-image.yml/dispatches"
            )
            logger.info(
                f"[GitHub:{deployment_id}] Dispatching workflow at URL: {url} on ref='{ref}'"
            )

            headers = {
                "Authorization": f"Bearer {self.github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }

            inputs: Dict[str, Any] = {
                "deployment_id": str(deployment_id),
                "image_tag": image_tag,
            }
            if build_context_url:
                # Use URL path and send minimal inline content
                inputs["build_context_url"] = build_context_url
                inputs["build_context"] = ""  # required input, but ignored by workflow when URL is present
            else:
                inputs["build_context"] = build_context_b64[:65000]
            payload = {"ref": ref, "inputs": inputs}

            start_time = time.time()

            # Retry on secondary rate limits or transient errors
            max_attempts = 3
            backoff = 2
            for attempt in range(1, max_attempts + 1):
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 204:
                    break
                # If the workflow on GitHub does not declare certain inputs (e.g. service_name),
                # GitHub returns 422 with an error like: "Unexpected inputs provided: [\"service_name\"]"
                if (
                    response.status_code == 422
                    and "Unexpected inputs" in response.text
                    and "service_name" in response.text
                    and isinstance(payload.get("inputs"), dict)
                    and "service_name" in payload["inputs"]
                ):
                    logger.warning(
                        f"[GitHub:{deployment_id}] Removing unsupported 'service_name' input and retrying..."
                    )
                    # Remove and retry immediately within the loop
                    try:
                        del payload["inputs"]["service_name"]
                    except Exception:
                        pass
                    # small delay to avoid hammering
                    await asyncio.sleep(1)
                    continue
                retry_after = response.headers.get("Retry-After")
                if response.status_code in (429, 403) and retry_after:
                    wait_s = int(retry_after)
                    logger.warning(
                        f"[GitHub:{deployment_id}] Rate limited. Retry-After={wait_s}s (attempt {attempt}/{max_attempts})"
                    )
                    await asyncio.sleep(wait_s)
                    continue
                if attempt < max_attempts:
                    logger.warning(
                        f"[GitHub:{deployment_id}] Dispatch failed (status={response.status_code}). Retrying in {backoff}s..."
                    )
                    await asyncio.sleep(backoff)
                    backoff *= 2
                else:
                    logger.error(
                        f"[GitHub:{deployment_id}] Failed to trigger workflow: status={response.status_code} body={response.text} (X-Request-ID={response.headers.get('x-github-request-id')})"
                    )
                    raise RuntimeError(
                        f"Failed to trigger workflow: {response.status_code} {response.text}"
                    )

            if response.status_code == 204:
                logger.info(
                    f"[GitHub:{deployment_id}] Workflow triggered successfully (X-Request-ID={response.headers.get('x-github-request-id')})"
                )
                # Try to resolve the run ID reliably by polling the specific workflow's runs
                workflow_runs_url = (
                    f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/actions/workflows/build-agent-image.yml/runs"
                )
                # Poll up to ~30s for the run to appear
                for _ in range(6):
                    runs_response = await client.get(
                        workflow_runs_url,
                        headers=headers,
                        params={
                            "event": "workflow_dispatch",
                            "branch": ref,
                            "per_page": 10,
                        },
                    )
                    if runs_response.status_code == 200:
                        runs = runs_response.json().get("workflow_runs", [])
                        # Prefer runs whose display_title includes our deployment_id
                        for run in runs:
                            display_title = run.get("display_title") or ""
                            if str(deployment_id) in display_title:
                                return str(run["id"])
                        # Fallback: the most recent run created after we dispatched
                        for run in runs:
                            created_at = run.get("created_at")
                            # If created_at is within the last minute since we dispatched, assume it's ours
                            if created_at:
                                # We can't parse without datetime; conservative fallback to first run
                                return str(run["id"])
                    await asyncio.sleep(5)

                logger.warning(
                    f"[GitHub:{deployment_id}] Could not locate workflow run ID yet; proceeding without it"
                )
                return "unknown"
            else:
                logger.error(
                    f"[GitHub:{deployment_id}] Failed to trigger workflow: status={response.status_code} body={response.text} (X-Request-ID={response.headers.get('x-github-request-id')})"
                )
                raise RuntimeError(
                    f"Failed to trigger workflow: {response.status_code} {response.text}"
                )

    async def _resolve_ref(self, client: "httpx.AsyncClient") -> str:
        """Resolve which branch/ref to dispatch to.

        Priority:
        1) Explicit env override (settings.GITHUB_REF)
        2) Repository default_branch from GitHub API
        3) 'main' fallback
        """
        if self.github_ref:
            logger.info(f"[GitHub] Using configured ref: {self.github_ref}")
            return self.github_ref

        try:
            resp = await client.get(
                f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}",
                headers={
                    "Authorization": f"Bearer {self.github_token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            if resp.status_code == 200:
                default_branch = resp.json().get("default_branch") or "main"
                logger.info(f"[GitHub] Resolved default branch: {default_branch}")
                return default_branch
            else:
                logger.warning(
                    f"[GitHub] Failed to get default branch (status={resp.status_code}). Falling back to 'main'"
                )
        except Exception as e:
            logger.warning(f"[GitHub] Error resolving default branch: {e}")
        return "main"

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
            headers = {
                "Authorization": f"Bearer {self.github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            # Resolve the branch used for dispatch to filter workflow runs correctly
            ref = await self._resolve_ref(client)

            # Allow discovery if run_id is unknown
            discovered_run_id = run_id
            workflow_runs_url = (
                f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/actions/workflows/build-agent-image.yml/runs"
            )

            while time.time() - start_time < timeout:
                # If we don't know run_id, try to discover it
                if not discovered_run_id or discovered_run_id == "unknown":
                    runs_response = await client.get(
                        workflow_runs_url,
                        headers=headers,
                        params={
                            "event": "workflow_dispatch",
                            "branch": ref,
                            "per_page": 15,
                        },
                    )
                    if runs_response.status_code == 200:
                        runs = runs_response.json().get("workflow_runs", [])
                        for run in runs:
                            display_title = run.get("display_title") or ""
                            if str(deployment_id) in display_title:
                                discovered_run_id = str(run["id"])
                                logger.info(
                                    f"[GitHub:{deployment_id}] Discovered workflow run ID: {discovered_run_id}"
                                )
                                break
                    if not discovered_run_id or discovered_run_id == "unknown":
                        await asyncio.sleep(5)
                        continue

                # Poll the specific run
                run_url = (
                    f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/actions/runs/{discovered_run_id}"
                )
                response = await client.get(run_url, headers=headers)

                if response.status_code == 404:
                    # If run not found, clear and retry discovery
                    logger.warning(
                        f"[GitHub:{deployment_id}] Run {discovered_run_id} not found yet; re-discovering"
                    )
                    discovered_run_id = "unknown"
                    await asyncio.sleep(5)
                    continue

                if response.status_code == 200:
                    run_data = response.json()
                    status = run_data.get("status")
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
