# Dynamo Kubernetes Operator Documentation

## Overview

Dynamo operator is a Kubernetes operator that simplifies the deployment, configuration, and lifecycle management of Dynamo pipelines. It automates the reconciliation of custom resources to ensure your desired state is always achieved. This operator is ideal for users who want to manage complex deployments using declarative YAML definitions and Kubernetes-native tooling.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Custom Resource Definitions (CRDs)](#custom-resource-definitions-crds)
- [Installation](#installation)
- [Usage](#usage)
- [Examples](#examples)
- [Reconciliation Logic](#reconciliation-logic)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [References](#references)

---

## Architecture

- **Operator Deployment:**  
  Deployed as a Kubernetes `Deployment` in a specific namespace.

- **Controllers:**  
  - `DynamoDeploymentController`: Watches `DynamoDeployment` CRs and orchestrates service pipelines.
  - `DynamoNimDeploymentController`: Watches `DynamoNimDeployment` CRs and handles individual runtime deployments.
  - `DynamoNimRequestController`: Watches `DynamoNimRequest` CRs and manages image builds and artifact tracking.

- **Workflow:**  
  1. A custom resource is created by the user or API server.
  2. The corresponding controller detects the change and runs reconciliation.
  3. Kubernetes resources (Deployments, Services, etc.) are created or updated to match the CR spec.
  4. Status fields are updated to reflect the current state.

---

## Custom Resource Definitions (CRDs)

### CRD: `DynamoDeployment`

| Field             | Type     | Description                                           | Required | Default |
|------------------|----------|-------------------------------------------------------|----------|---------|
| `dynamoNim`      | string   | Reference to the dynamoNim identifier                     | Yes      |         |
| `services`       | map      | Map of service names to runtime configurations. This allows to override the service configuration defined in the DynamoNim.        | No      |         |

**API Version:** `nvidia.com/v1alpha1`  
**Scope:** Namespaced

#### Example
```yaml
apiVersion: nvidia.com/v1alpha1
kind: DynamoDeployment
metadata:
  name: disagg
spec:
  dynamoNim: frontend:jh2o6dqzpsgfued4
  envs:
    - name: GLOBAL_ENV_VAR
      value: some_global_value
  services:
    Frontend:
      replicas: 1
      envs:
        - name: SPECIFIC_ENV_VAR
          value: some_specific_value
    Processor:
      replicas: 1
      envs:
        - name: SPECIFIC_ENV_VAR
          value: some_specific_value
    VllmWorker:
      replicas: 1
      envs:
        - name: SPECIFIC_ENV_VAR
          value: some_specific_value
    PrefillWorker:
      replicas: 1
      envs:
        - name: SPECIFIC_ENV_VAR
          value: some_specific_value
    Router:
      replicas: 0
      envs:
        - name: SPECIFIC_ENV_VAR
          value: some_specific_value
```

---

### CRD: `DynamoNimDeployment`

| Field                   | Type     | Description                                        | Required | Default |
|------------------------|----------|----------------------------------------------------|----------|---------|
| `dynamoNamespace`      | string   | Namespace of the DynamoNim                  | Yes      |         |
| `dynamoNim`            | string   | Name of the dynamoNim artifact                         | Yes      |         |
| `dynamoTag`            | string   | FQDN of the service to run          | Yes      |         |
| `envs`                 | array    | Environment variables for runtime                  | No       | []      |
| `externalServices`     | map      | External service dependencies                      | No       |         |
| `serviceName`          | string   | Logical name of the service being deployed         | Yes      |         |
| `annotations`       | map      | Additional metadata annotations for the pod                                | No       |         |
| `labels`            | map      | Custom labels applied to the deployment and pod                            | No       |         |
| `resources`         | object   | Resource limits and requests (CPU, memory, GPU)                             | No       |         |
| `autoscaling`       | object   | Autoscaling rules for the deployment                                        | No       |         |
| `envFromSecret`     | string   | Reference to a secret for injecting env vars                                | No       |         |
| `pvc`               | object   | Persistent volume claim configuration                                       | No       |         |
| `ingress`           | object   | Ingress configuration for exposing the service                              | No       |         |
| `extraPodMetadata`  | object   | Additional labels and annotations for the pod                               | No       |         |
| `extraPodSpec`      | object   | Custom PodSpec fields to merge into the generated pod                       | No       |         |
| `livenessProbe`     | object   | Kubernetes liveness probe                                                   | No       |         |
| `readinessProbe`    | object   | Kubernetes readiness probe                                                  | No       |         |
| `replicas`          | int      | Number of replicas to run                                                   | No       | 1       |

**API Version:** `nvidia.com/v1alpha1`  
**Scope:** Namespaced

#### Example
```yaml
apiVersion: nvidia.com/v1alpha1
kind: DynamoNimDeployment
metadata:
  name: test-41fa991-vllmworker
spec:
  dynamoNamespace: dynamo
  dynamoNim: frontend--jh2o6dqzpsgfued4
  dynamoTag: graphs.disagg:Frontend
  envs:
    - name: DYN_DEPLOYMENT_CONFIG
      value: '<long JSON config>'
  externalServices:
    PrefillWorker:
      deploymentSelectorKey: dynamo
      deploymentSelectorValue: PrefillWorker/dynamo
  resources:
    limits:
      cpu: "10"
      gpu: "1"
      memory: 20Gi
    requests:
      cpu: "10"
      gpu: "1"
      memory: 20Gi
  serviceName: Frontend
```

---

### CRD: `DynamoNimRequest`

| Field       | Type   | Description                             | Required | Default |
|-------------|--------|-----------------------------------------|----------|---------|
| `bentoTag`  | string | Full tag of the service image to build  | Yes      |         |

**API Version:** `nvidia.com/v1alpha1`  
**Scope:** Namespaced

#### Example
```yaml
apiVersion: nvidia.com/v1alpha1
kind: DynamoNimRequest
metadata:
  name: frontend--jh2o6dqzpsgfued4
spec:
  bentoTag: frontend:jh2o6dqzpsgfued4
```


---

## Installation

[See installation steps](dynamo_cloud.md#deployment-steps)

---

## Deploying a Dynamo Pipeline using the Operator

[See deployment steps](operator_deployment.md)

---

## Reconciliation Logic

### DynamoDeployment

- **Actions:**
  - Create a DynamoNimRequest CR to build the docker image
  - Create a DynamoNimDeployment CR for each service defined in the DynamoNim
- **Status Management:**
  - `.status.conditions`: Reflects readiness, failure, progress states
  - `.status.state`: overall state of the deployment, based on the state of the DynamoNimDeployments

### DynamoNimDeployment

- **Actions:**
  - Create a Deployment, Service, and Ingress for the service
- **Status Management:**
  - `.status.conditions`: Reflects readiness, failure, progress states

### DynamoNimRequest

- **Actions:**
  - Create a job to build the docker image
- **Status Management:**
  - `.status.conditions`: Reflects readiness, failure, progress states

---

## Configuration


- **Environment Variables:**  

| Name | Description | Default |
|------|-------------|---------|
| `ADD_NAMESPACE_PREFIX_TO_IMAGE_NAME` | Adds namespace prefix to image names | `false` |
| `BENTO_IMAGE_BUILD_ENGINE` | Engine used for building images | `buildkit` |
| `BUILDKIT_URL` | BuildKit daemon URL | `tcp://dynamo-platform-dynamo-operator-buildkitd:1234` |
| `DOCKER_REGISTRY_BENTO_REPOSITORY_NAME` | Repository name for dynamo images | `yatai-bentos` |
| `DOCKER_REGISTRY_IN_CLUSTER_SERVER` | In-cluster registry server address | `""` |
| `DOCKER_REGISTRY_SECURE` | Use secure connection for registry | `true` |
| `DOCKER_REGISTRY_SERVER` | Docker registry server address | `nvcr.io/nvidian/nim-llm-dev` |
| `DOCKER_REGISTRY_USERNAME` | Registry authentication username | `username` |
| `DYNAMO_INGRESS_SUFFIX` | Suffix for ingress hostnames | `dev.aire.nvidia.com` |
| `ESTARGZ_ENABLED` | Enable eStargz image optimization | `false` |
| `INTERNAL_IMAGES_BUILDKIT` | BuildKit image | `quay.io/bentoml/buildkit:master` |
| `LOG_LEVEL` | Logging verbosity level | `info` |
| `YATAI_DEPLOYMENT_NAMESPACE` | Namespace for deployments | `dynamo` |
| `YATAI_ENDPOINT` | Yatai service endpoint | `http://dynamo-store` |
| `YATAI_IMAGE_BUILDER_NAMESPACE` | Namespace for image building | `dynamo` |
| `YATAI_SYSTEM_NAMESPACE` | System namespace | `dynamo` |

- **Flags:**  
  | Flag                  | Description                                | Default |
  |-----------------------|--------------------------------------------|---------|
  | `--natsAddr`      | Address of NATS server                   |"" |
  | `--etcdAddr` | Address of etcd server        | "" |


---

## Troubleshooting

| Symptom                | Possible Cause           | Solution                          |
|------------------------|---------------------------|-----------------------------------|
| Resource not created   | RBAC missing              | Ensure correct ClusterRole/Binding|
| Status not updated     | CRD schema mismatch       | Regenerate CRDs with kubebuilder  |
| Image build hangs      | Misconfigured NimRequest  | Check image build logs            |

---

## Development

- **Code Structure:**  

The operator is built using Kubebuilder and the operator-sdk, with the following structure:

  - `controllers/` – Reconciliation logic
  - `api/v1alpha1/` – CRD types
  - `config/` – Manifests and Helm charts

---

## References

- [Kubernetes Operator Pattern](https://kubernetes.io/docs/concepts/extend-kubernetes/operator/)
- [Custom Resource Definitions](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/)
- [Operator SDK](https://sdk.operatorframework.io/)
- [Helm Best Practices for CRDs](https://helm.sh/docs/chart_best_practices/custom_resource_definitions/)
