# SPDX-FileCopyrightText: Copyright (c) 2024-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
import typing as t
from datetime import datetime

import requests

from dynamo.sdk.core.protocol.deployment import (
    Deployment,
    DeploymentManager,
    DeploymentResponse,
    DeploymentStatus,
    Service,
)


class KubernetesDeploymentManager(DeploymentManager):
    """
    Implementation of DeploymentManager that talks to the dynamo_store deployment API.
    Accepts **kwargs for backend-specific options.
    Handles error reporting and payload construction according to the API schema.
    Raises exceptions for errors; CLI handles user interaction.
    """

    def __init__(self, endpoint: str):
        self.endpoint = endpoint.rstrip("/")
        self.session = requests.Session()
        self.namespace = "default"

    def _upload_pipeline(
        self, pipeline: str, services: t.List[Service], **kwargs
    ) -> None:
        """Upload the entire pipeline as a single component/version, with a manifest of all services."""
        session = self.session
        endpoint = self.endpoint
        pipeline_name, pipeline_version = pipeline.split(":")

        comp_url = f"{endpoint}/api/v1/dynamo_components"
        comp_payload = {
            "name": pipeline_name,
            "description": f"Registered by Dynamo's KubernetesDeploymentManager for {pipeline_name}:{pipeline_version}",
        }
        resp = session.post(comp_url, json=comp_payload)
        if resp.status_code not in (200, 201, 409, 422):
            print(resp.status_code)
            raise RuntimeError(f"Failed to create component: {resp.text}")

        ver_url = f"{endpoint}/api/v1/dynamo_components/{pipeline_name}/versions"
        build_at = kwargs.get("build_at")
        if not build_at:
            build_at = datetime.utcnow()
        if isinstance(build_at, str):
            try:
                build_at = datetime.fromisoformat(build_at)
            except Exception:
                build_at = datetime.utcnow()

        # Build manifest: a list of all service dicts
        manifest = {
            "pipeline": pipeline_name,
            "version": pipeline_version,
            "services": [
                {
                    "service": svc.name,
                    "apis": svc.apis,
                    "size_bytes": svc.size_bytes,
                }
                for svc in services
            ],
        }

        ver_payload = {
            "description": f"Auto-registered version for {pipeline_name}:{pipeline_version}",
            "version": pipeline_version,
            "manifest": manifest,
            "build_at": build_at.isoformat(),
        }
        resp = session.post(ver_url, json=ver_payload)
        if resp.status_code not in (200, 201, 409):
            raise RuntimeError(f"Failed to create component version: {resp.text}")

    def create_deployment(self, deployment: Deployment, **kwargs) -> DeploymentResponse:
        """Create a new deployment. Ensures all components and versions are registered/uploaded before creating the deployment."""
        # For each service/component in the deployment, upload it to the API store
        self._upload_pipeline(
            pipeline=deployment.pipeline or deployment.namespace,
            services=deployment.services,
            **kwargs,
        )

        # Now create the deployment
        dev = kwargs.get("dev", False)
        labels = kwargs.get("labels")
        secrets = kwargs.get("secrets")
        services = kwargs.get("services", {})
        access_authorization = kwargs.get("access_authorization", False)
        payload = {
            "name": deployment.name,
            "component": deployment.pipeline or deployment.namespace,
            "dev": dev,
            "envs": deployment.envs,
            "labels": labels,
            "secrets": secrets,
            "services": services,
            "access_authorization": access_authorization,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        url = f"{self.endpoint}/api/v2/deployments"
        try:
            resp = self.session.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            msg = e.response.text if e.response is not None else str(e)
            raise RuntimeError((status, msg, url))

    def update_deployment(
        self, deployment_id: str, deployment: Deployment, **kwargs
    ) -> None:
        """Update an existing deployment."""
        dev = kwargs.get("dev", False)
        labels = kwargs.get("labels")
        secrets = kwargs.get("secrets")
        access_authorization = kwargs.get("access_authorization", False)
        payload = {
            "name": deployment.name,
            "component": deployment.pipeline or deployment.namespace,
            "dev": dev,
            "envs": deployment.envs,
            "labels": labels,
            "secrets": secrets,
            "services": deployment.services,
            "access_authorization": access_authorization,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        url = f"{self.endpoint}/api/v2/deployments/{deployment_id}"
        try:
            resp = self.session.put(url, json=payload)
            resp.raise_for_status()
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            msg = e.response.text if e.response is not None else str(e)
            raise RuntimeError((status, msg, url))

    def get_deployment(self, deployment_id: str, **kwargs) -> DeploymentResponse:
        """Get deployment details."""
        url = f"{self.endpoint}/api/v2/deployments/{deployment_id}"
        try:
            resp = self.session.get(url)
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            msg = e.response.text if e.response is not None else str(e)
            raise RuntimeError((status, msg, url))

    def list_deployments(self, **kwargs) -> list[DeploymentResponse]:
        """List all deployments."""
        url = f"{self.endpoint}/api/v2/deployments"
        try:
            resp = self.session.get(url)
            resp.raise_for_status()
            data = resp.json()
            return data.get("items", [])
        except requests.HTTPError as e:
            msg = e.response.text if e.response is not None else str(e)
            raise RuntimeError(
                (e.response.status_code if e.response else None, msg, url)
            )

    def delete_deployment(self, deployment_id: str, **kwargs) -> None:
        """Delete a deployment."""
        url = f"{self.endpoint}/api/v2/deployments/{deployment_id}"
        try:
            resp = self.session.delete(url)
            resp.raise_for_status()
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            msg = e.response.text if e.response is not None else str(e)
            raise RuntimeError((status, msg, url))

    def get_status(
        self,
        deployment_id: t.Optional[str] = None,
        deployment: t.Optional[DeploymentResponse] = None,
    ) -> DeploymentStatus:
        if deployment_id:
            dep = self.get_deployment(deployment_id)
        elif deployment:
            dep = deployment
        else:
            raise ValueError("Either deployment_id or deployment must be provided")
        status = dep.get("status", "unknown")
        if status == "running":
            return DeploymentStatus.RUNNING
        elif status == "failed":
            return DeploymentStatus.FAILED
        elif status == "deploying":
            return DeploymentStatus.IN_PROGRESS
        elif status == "terminated":
            return DeploymentStatus.TERMINATED
        else:
            return DeploymentStatus.PENDING

    def wait_until_ready(self, deployment_id: str, timeout: int = 3600) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            status = self.get_status(deployment_id)
            if status == DeploymentStatus.RUNNING:
                return True
            elif status == DeploymentStatus.FAILED:
                return False
            time.sleep(5)
        return False

    def get_endpoint_urls(
        self,
        deployment_id: t.Optional[str] = None,
        deployment: t.Optional[DeploymentResponse] = None,
    ) -> list[str]:
        if deployment_id:
            dep = self.get_deployment(deployment_id)
        elif deployment:
            dep = deployment
        else:
            raise ValueError("Either deployment_id or deployment must be provided")
        return dep.get("urls", [])
