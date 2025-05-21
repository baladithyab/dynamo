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

import typing as t
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


@dataclass
class Resources:
    """Resources for a service."""

    cpu: str | None = None  # example: "3", "300m"
    memory: str | None = None  # example: "10Gi", "1024Mi"
    gpu: str | None = None  # example: "4"

    def __post_init__(self):
        # Validate and normalize CPU format (e.g., "3", "300m")
        if self.cpu is not None:
            self.cpu = self.cpu.strip()
            if not (
                self.cpu.isdigit() or (self.cpu[:-1].isdigit() and self.cpu[-1] == "m")
            ):
                raise ValueError(
                    f"Invalid CPU format: {self.cpu}. Expected format like '3' or '300m'"
                )

        # Validate and normalize memory format (e.g., "10Gi", "1024Mi")
        if self.memory is not None:
            self.memory = self.memory.strip()
            valid_suffixes = [
                "Ki",
                "Mi",
                "Gi",
                "Ti",
                "Pi",
                "Ei",
                "K",
                "M",
                "G",
                "T",
                "P",
                "E",
            ]
            if not any(
                self.memory.endswith(suffix) and self.memory[: -len(suffix)].isdigit()
                for suffix in valid_suffixes
            ):
                if not self.memory.isdigit():
                    raise ValueError(
                        f"Invalid memory format: {self.memory}. Expected format like '10Gi' or '1024Mi'"
                    )

        # Validate and normalize GPU format (should be a number)
        if self.gpu is not None:
            self.gpu = self.gpu.strip()
            if not self.gpu.isdigit():
                raise ValueError(
                    f"Invalid GPU format: {self.gpu}. Expected a number like '1' or '4'"
                )


class DeploymentStatus(str, Enum):
    """Status of a dynamo deployment."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RUNNING = "running"
    FAILED = "failed"
    TERMINATED = "terminate"
    SCALED_TO_ZERO = "scaled_to_zero"

    @property
    def color(self) -> str:
        return {
            DeploymentStatus.RUNNING: "green",
            DeploymentStatus.IN_PROGRESS: "yellow",
            DeploymentStatus.PENDING: "yellow",
            DeploymentStatus.FAILED: "red",
            DeploymentStatus.TERMINATED: "red",
            DeploymentStatus.SCALED_TO_ZERO: "yellow",
        }.get(self, "white")


@dataclass
class ScalingPolicy:
    policy: str
    parameters: dict[str, t.Union[int, float, str]] = field(default_factory=dict)


@dataclass
class Env:
    name: str
    value: str = ""


@dataclass
class Service:
    """The entry service of a deployment."""

    service_name: str
    name: str
    namespace: str
    version: str
    cmd: t.List[str] = field(default_factory=list)
    resources: Resources | None = None
    envs: t.List[Env] = field(default_factory=list)
    secrets: t.List[str] = field(default_factory=list)
    scaling: ScalingPolicy = field(default_factory=lambda: ScalingPolicy(policy="none"))
    apis: dict = field(default_factory=dict)
    size_bytes: int = 0


@dataclass
class Deployment:
    """Graph deployment."""

    name: str
    namespace: str
    pipeline: t.Optional[str] = None
    entry_service: t.Optional[Service] = None
    envs: t.Optional[t.List[dict]] = None


# Type alias for deployment responses (e.g., from backend APIs)
DeploymentResponse = dict[str, t.Any]


class DeploymentManager(ABC):
    """Interface for managing dynamo graph deployments."""

    @abstractmethod
    def create_deployment(
        self, deployment: Deployment, pipeline: t.Optional[str], **kwargs
    ) -> DeploymentResponse:
        """Create new deployment.

        Args:
            deployment: Deployment configuration
            pipeline: Pipeline name (tag result of `dynamo build`). If not provided, the namespace of the deployment will be used.
            **kwargs: Additional backend-specific arguments

        Returns:
            The created deployment
        """
        pass

    @abstractmethod
    def update_deployment(
        self, deployment_id: str, deployment: Deployment, **kwargs
    ) -> None:
        """Update an existing deployment.

        Args:
            deployment_id: The ID of the deployment to update
            deployment: New deployment configuration
            **kwargs: Additional backend-specific arguments
        """
        pass

    @abstractmethod
    def get_deployment(self, deployment_id: str, **kwargs) -> DeploymentResponse:
        """Get deployment details.

        Args:
            deployment_id: The ID of the deployment
            **kwargs: Additional backend-specific arguments

        Returns:
            Dictionary containing deployment details
        """
        pass

    @abstractmethod
    def list_deployments(self, **kwargs) -> list[DeploymentResponse]:
        """List all deployments.

        Args:
            **kwargs: Additional backend-specific arguments

        Returns:
            List of dictionaries containing deployment id and details
        """
        pass

    @abstractmethod
    def delete_deployment(self, deployment_id: str, **kwargs) -> None:
        """Delete a deployment.

        Args:
            deployment_id: The ID of the deployment to delete
            **kwargs: Additional backend-specific arguments
        """
        pass

    @abstractmethod
    def get_status(
        self,
        deployment_id: t.Optional[str] = None,
        deployment: t.Optional[DeploymentResponse] = None,
    ) -> DeploymentStatus:
        """Get the current status of a deployment.

        Args (one of):
            deployment_id: The ID of the deployment
            deployment: The deployment response

        Returns:
            The current status of the deployment
        """
        pass

    @abstractmethod
    def wait_until_ready(self, deployment_id: str, timeout: int = 3600) -> bool:
        """Wait until a deployment is ready.

        Args:
            deployment_id: The ID of the deployment
            timeout: Maximum time to wait in seconds

        Returns:
            True if deployment became ready, False if timed out
        """
        pass

    @abstractmethod
    def get_endpoint_urls(
        self,
        deployment_id: t.Optional[str] = None,
        deployment: t.Optional[DeploymentResponse] = None,
    ) -> list[str]:
        """Get the list of endpoint urls attached to a deployment.

        Args (one of):
            deployment_id: The ID of the deployment
            deployment: The deployment response

        Returns:
            List of deployment's endpoint urls
        """
        pass
