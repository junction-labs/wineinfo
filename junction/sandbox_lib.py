"""
This module implements a Kubernetes Sandbox system that enables temporary, isolated deployments
of existing services with customizations. It supports forking existing resources, adding new
resources, and configuring custom ingress rules - all while maintaining proper resource 
references and relationships.

Key Features:
- Fork existing K8s resources with customizations via patches
- Deploy to isolated or shared namespaces
- Configure custom ingress/routing rules
- Add supplementary resources
- Maintain referential integrity across resources
- Support for Helm templating

Example Use Cases:

1. Feature Branch Testing
   Create a sandbox to test a feature branch while routing specific test traffic:
   ```python
   sandbox = {
       "name": "feature-123",
       "own_namespace": True,
       "forked_objects": [{
           "name": "auth-service",
           "namespace": "production",
           "kind": "Deployment",
           "patches": [
               PatchUtils.change_image("auth-service:feature-123"),
               PatchUtils.add_env_vars({"DEBUG": "true"}),
               PatchUtils.set_replica_count(1)
           ]
       }],
       "ingress": {
           "hostname": ["api.example.com"],
           "port": 8080,
           "target_name": "auth-service",
           "target_namespace": "production",
           "matches": [{
               "headers": {
                   "x-feature-branch": "feature-123",
               }
           }]
       }
   }
   generator = SandboxGenerator()
   resources = generator.generate(sandbox)
   ```

   2. Debugging Production Issues
   Create a sandbox for debugging with header-based traffic routing:
   ```python
   sandbox = {
       "name": "feature-124",
       "own_namespace": False,  # Share namespace for data access
       "forked_objects": [{
           "name": "order-service",
           "namespace": "production",
           "kind": "Deployment",
           "patches": [
               PatchUtils.add_env_vars({
                   "LOG_LEVEL": "DEBUG",
                   "TRACE_ENABLED": "true"
               }),
               PatchUtils.set_replica_count(1),
               PatchUtils.add_volume_mount("debug-config", "/etc/config")
           ]
       }],
       "new_objects": [{
           "spec": {
               "apiVersion": "v1",
               "kind": "ConfigMap",
               "metadata": {"name": "debug-config"},
               "data": {"config.yaml": "debug_mode: true\\ntrace_all: true"}
           }
       }],
       "ingress": {
           "hostname": ["orders.example.com"],
           "port": 8080,
           "target_name": "order-service",
           "target_namespace": "production",
           "matches": [{
               "headers": {
                   "x-feature-branch": "feature-124",
               }
           }]
       }
   }
   generator = SandboxGenerator()
   resources = generator.generate(sandbox)   
    ```
   
3. Performance Testing Environment
   Create a sandbox for load testing using special headers to route test traffic:
   ```python
   sandbox = {
       "name": "feature-125",
       "own_namespace": True,
       "forked_objects": [{
           "name": "payment-processor",
           "namespace": "staging",
           "kind": "Deployment",
           "patches": [
               PatchUtils.set_resources("2Gi", "1000m", "4Gi", "2000m"),
               PatchUtils.add_volume_mount("metrics", "/metrics")
           ]
       }],
       "new_objects": PatchUtils.simple_additional_service(
           "prometheus", "prom/prometheus:v2.30.0", 9090,
           {"STORAGE_RETENTION": "24h"}
       ),
       "ingress": {
           "hostname": ["payments.example.com"],
           "port": 8080,
           "target_name": "payment-processor",
           "target_namespace": "staging",
           "mirror_proportion": 10,
           "matches": [{
               "headers": {
                   "x-feature-branch": "feature-125",
               }
           }]
       }
   }
   generator = SandboxGenerator()
   resources = generator.generate(sandbox)   
   ```
Usage Notes:
- Use own_namespace=True for complete isolation
- All K8s references (ConfigMaps, Secrets, etc.) are automatically updated

For proper cleanup, sandboxes should be treated as temporary resources and removed
when no longer needed.
"""

import copy
from dataclasses import dataclass
import json
import typing
import junction
import yaml
from kubernetes import config, dynamic
from kubernetes.dynamic.exceptions import ResourceNotFoundError
from typing import Any, Dict, List, Optional, Tuple, Union
import jsonpatch
import jsonmerge
import re

import unittest
from unittest.mock import Mock, patch

class KubePatch(typing.TypedDict):
    patch_type: typing.Literal["strategic"] | typing.Literal["json"] | typing.Literal["merge"]
    patch: str | dict

class SandboxForkedObject(typing.TypedDict):
    name: str
    namespace: str
    kind: str
    patches: List[KubePatch]

class SandboxNewObject(typing.TypedDict):
    spec: str | dict 

class SandboxIngress(typing.TypedDict):
    use_gateway: Optional[bool]
    gateway_name: Optional[str]
    gateway_namespace: Optional[str]
    mirror_proportion: Optional[int]  # Percentage of traffic to mirror (1-100)
    hostname: typing.List[str]
    port: int | None
    matches: typing.List[junction.config.RouteMatch]
    target_name: str
    target_namespace: str

class Sandbox(typing.TypedDict):
    name: str
    own_namespace: bool
    ingress: SandboxIngress
    new_objects: typing.List[SandboxNewObject] | None
    forked_objects: typing.List[SandboxForkedObject] | None

class SandboxError(Exception):
    """Base exception for sandbox-related errors"""
    pass

class ValidationError(SandboxError):
    """Raised when sandbox configuration is invalid"""
    pass

class ResourceError(SandboxError):
    """Raised when there's an error accessing K8s resources"""
    pass

class PatchError(SandboxError):
    """Raised when there's an error applying patches"""
    pass

class PatchUtils:
    @staticmethod
    def add_env_vars(env_vars: Dict[str, str], container_name: str = None) -> KubePatch:
        """Create a patch to add environment variables"""
        container = {"env": [{"name": k, "value": v} for k, v in env_vars.items()]}
        if container_name:
            container["name"] = container_name
            
        return {
            "patch_type": "strategic",
            "patch": {
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [container]
                        }
                    }
                }
            }
        }

    @staticmethod
    def change_image(image: str, container_name: str = None) -> KubePatch:
        """Create a patch to change container image"""
        container = {"image": image}
        if container_name:
            container["name"] = container_name
            
        return {
            "patch_type": "strategic",
            "patch": {
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [container]
                        }
                    }
                }
            }
        }

    @staticmethod
    def set_resources(
        memory_request: str,
        cpu_request: str,
        memory_limit: Optional[str] = None,
        cpu_limit: Optional[str] = None,
        container_name: str = None
    ) -> KubePatch:
        """Create a patch to set container resources"""
        resources = {
            "requests": {
                "memory": memory_request,
                "cpu": cpu_request
            }
        }
        if memory_limit or cpu_limit:
            resources["limits"] = {}
            if memory_limit:
                resources["limits"]["memory"] = memory_limit
            if cpu_limit:
                resources["limits"]["cpu"] = cpu_limit

        container = {"resources": resources}
        if container_name:
            container["name"] = container_name

        return {
            "patch_type": "strategic",
            "patch": {
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [container]
                        }
                    }
                }
            }
        }

    @staticmethod
    def set_replica_count(count: int) -> KubePatch:
        """Create a patch to set replica count"""
        return {
            "patch_type": "strategic",
            "patch": {
                "spec": {
                    "replicas": count
                }
            }
        }

    @staticmethod
    def set_liveness_probe(
        path: str = "/healthz",
        port: int = 8080,
        initial_delay: int = 10,
        period: int = 10,
        container_name: str = None
    ) -> KubePatch:
        """Create a patch to set HTTP liveness probe"""
        probe = {
            "livenessProbe": {
                "httpGet": {
                    "path": path,
                    "port": port
                },
                "initialDelaySeconds": initial_delay,
                "periodSeconds": period
            }
        }
        if container_name:
            probe["name"] = container_name

        return {
            "patch_type": "strategic",
            "patch": {
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [probe]
                        }
                    }
                }
            }
        }

    @staticmethod
    def set_readiness_probe(
        path: str = "/ready",
        port: int = 8080,
        initial_delay: int = 5,
        period: int = 10,
        container_name: str = None
    ) -> KubePatch:
        """Create a patch to set HTTP readiness probe"""
        probe = {
            "readinessProbe": {
                "httpGet": {
                    "path": path,
                    "port": port
                },
                "initialDelaySeconds": initial_delay,
                "periodSeconds": period
            }
        }
        if container_name:
            probe["name"] = container_name

        return {
            "patch_type": "strategic",
            "patch": {
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [probe]
                        }
                    }
                }
            }
        }

    @staticmethod
    def add_volume_mount(
        name: str,
        mount_path: str,
        container_name: str = None
    ) -> KubePatch:
        """Create a patch to add a volume mount to container(s)"""
        container = {
            "volumeMounts": [{
                "name": name,
                "mountPath": mount_path
            }]
        }
        if container_name:
            container["name"] = container_name

        return {
            "patch_type": "strategic",
            "patch": {
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [container]
                        }
                    }
                }
            }
        }

    @staticmethod
    def add_config_volume(
        name: str,
        config_map_name: str
    ) -> KubePatch:
        """Create a patch to add a ConfigMap volume to pod"""
        return {
            "patch_type": "strategic",
            "patch": {
                "spec": {
                    "template": {
                        "spec": {
                            "volumes": [{
                                "name": name,
                                "configMap": {
                                    "name": config_map_name
                                }
                            }]
                        }
                    }
                }
            }
        }

    @staticmethod
    def add_secret_volume(
        name: str,
        secret_name: str
    ) -> KubePatch:
        """Create a patch to add a Secret volume to pod"""
        return {
            "patch_type": "strategic",
            "patch": {
                "spec": {
                    "template": {
                        "spec": {
                            "volumes": [{
                                "name": name,
                                "secret": {
                                    "secretName": secret_name
                                }
                            }]
                        }
                    }
                }
            }
        }

    @staticmethod
    def set_pod_annotations(annotations: Dict[str, str]) -> KubePatch:
        """Create a patch to set pod template annotations"""
        return {
            "patch_type": "strategic",
            "patch": {
                "spec": {
                    "template": {
                        "metadata": {
                            "annotations": annotations
                        }
                    }
                }
            }
        }

    @staticmethod
    def set_pod_labels(labels: Dict[str, str]) -> KubePatch:
        """Create a patch to set pod template labels"""
        return {
            "patch_type": "strategic",
            "patch": {
                "spec": {
                    "template": {
                        "metadata": {
                            "labels": labels
                        }
                    }
                }
            }
        }

    @staticmethod
    def set_security_context(
        run_as_user: Optional[int] = None,
        run_as_group: Optional[int] = None,
        read_only_root: Optional[bool] = None,
        container_name: str = None
    ) -> KubePatch:
        """Create a patch to set container security context"""
        security_context = {}
        if run_as_user is not None:
            security_context["runAsUser"] = run_as_user
        if run_as_group is not None:
            security_context["runAsGroup"] = run_as_group
        if read_only_root is not None:
            security_context["readOnlyRootFilesystem"] = read_only_root

        container = {"securityContext": security_context}
        if container_name:
            container["name"] = container_name

        return {
            "patch_type": "strategic",
            "patch": {
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [container]
                        }
                    }
                }
            }
        }

    @staticmethod
    def add_init_container(
        name: str,
        image: str,
        command: Optional[List[str]] = None,
        env_vars: Optional[Dict[str, str]] = None
    ) -> KubePatch:
        """Create a patch to add an init container"""
        init_container = {
            "name": name,
            "image": image
        }
        if command:
            init_container["command"] = command
        if env_vars:
            init_container["env"] = [
                {"name": k, "value": v} for k, v in env_vars.items()
            ]

        return {
            "patch_type": "strategic",
            "patch": {
                "spec": {
                    "template": {
                        "spec": {
                            "initContainers": [init_container]
                        }
                    }
                }
            }
        }

    @staticmethod
    def simple_additional_service(
        name: str,
        image: str,
        port: int,
        env_vars: Optional[Dict[str, str]] = None
    ) -> List[SandboxNewObject]:
        """Create mock service deployment and service resources"""
        deployment = {
            "spec": {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": name
                },
                "spec": {
                    "replicas": 1,
                    "selector": {
                        "matchLabels": {
                            "app": name
                        }
                    },
                    "template": {
                        "metadata": {
                            "labels": {
                                "app": name
                            }
                        },
                        "spec": {
                            "containers": [{
                                "name": name,
                                "image": image,
                                "ports": [{
                                    "containerPort": port
                                }]
                            }]
                        }
                    }
                }
            }
        }

        if env_vars:
            deployment["spec"]["spec"]["template"]["spec"]["containers"][0]["env"] = [
                {"name": k, "value": v} for k, v in env_vars.items()
            ]

        service = {
            "spec": {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {
                    "name": name
                },
                "spec": {
                    "selector": {
                        "app": name
                    },
                    "ports": [{
                        "port": port
                    }]
                }
            }
        }
        return [deployment, service]

class KubernetesResourceManager:
    """
    Helper class handles interactions with the Kubernetes API.
    Provides methods for resource discovery and manipulation.
    """
    
    def __init__(self, k8s_client=None):
        """Initialize with optional K8s client, otherwise create default"""
        self.client = k8s_client or self._create_default_client()
        self._api_cache: Dict[str, Any] = {}

    def _create_default_client(self) -> dynamic.DynamicClient:
        """Creates a default dynamic client from current context"""
        try:
            client = config.new_client_from_config()
            return dynamic.DynamicClient(client)
        except Exception as e:
            raise ResourceError(f"Failed to create Kubernetes client: {str(e)}")

    def get_resource(
        self, 
        name: str, 
        namespace: str, 
        kind: Optional[str] = None
    ) -> Optional[dict]:
        """
        Fetches a Kubernetes resource by name and namespace.
        Optionally filters by kind for faster lookup.
        """
        try:
            if kind:
                return self._get_resource_by_kind(name, namespace, kind)
            return self._discover_resource(name, namespace)
        except ResourceNotFoundError:
            return None
        except Exception as e:
            raise ResourceError(f"Error accessing resource {name}: {str(e)}")

    def _get_resource_by_kind(self, name: str, namespace: str, kind: str) -> Optional[dict]:
        """Fetches a resource when the kind is known"""
        try:
            api = self._get_api_for_kind(kind)
            return api.get(name=name, namespace=namespace).to_dict()
        except ResourceNotFoundError:
            return None

    def _discover_resource(self, name: str, namespace: str) -> Optional[dict]:
        """
        Attempts to discover a resource by trying different APIs.
        Used when kind is unknown.
        """
        for api in self.client.resources:
            try:
                result = api.get(name=name, namespace=namespace).to_dict()
                return result
            except ResourceNotFoundError:
                continue
            except Exception:
                continue
        return None

    def _get_api_for_kind(self, kind: str) -> Any:
        """Gets or caches API client for a specific kind"""
        if kind not in self._api_cache:
            try:
                self._api_cache[kind] = self.client.resources.get(kind=kind)
            except Exception as e:
                raise ResourceError(f"Failed to get API for kind {kind}: {str(e)}")
        return self._api_cache[kind]

    def clean_metadata(self, resource: dict) -> dict:
        """ Removes internal metadata fields that shouldn't be copied. """
        resource = resource.copy()
        metadata = resource.get("metadata", {})
        remove_fields = {
            "resourceVersion",
            "uid",
            "creationTimestamp",
            "generation",
            "managedFields",
            "ownerReferences",
            "finalizers"
        }
        for field in remove_fields:
            metadata.pop(field, None)
        resource.pop("status", None)
        return resource


class PatchManager:
    """
    Helper class handles the application and management of patches to 
    Kubernetes resources. Supports different patch types and Helm template 
    preservation.
    """
    
    @classmethod
    def apply_patch(cls, obj: dict, patch: KubePatch) -> dict:
        """
        Applies a patch to a Kubernetes object.
        Preserves Helm templates and handles different patch types.
        """
        try:
            patch_data = cls._prepare_patch_data(patch["patch"])
            
            match patch["patch_type"]:
                case "json":
                    return jsonpatch.apply_patch(obj, patch_data)
                case "merge":
                    return jsonmerge.merge(obj, patch_data)
                case "strategic":
                    merger = jsonmerge.Merger(
                        [(
                            "merge_arrays",
                            ["*"],
                            {
                                "by": "name",
                                "match_subkeys": ["name", "key"]
                            }
                        )]
                    )
                    return merger.merge(obj, patch_data)
                case _:
                    raise PatchError(f"Unsupported patch type: {patch['patch_type']}")
        except Exception as e:
            raise PatchError(f"Failed to apply {patch['patch_type']} patch: {str(e)}")

    @classmethod
    def _prepare_patch_data(cls, patch_data: Union[str, dict]) -> Any:

        if isinstance(patch_data, dict):
            return patch_data

        stripped = patch_data.strip()
        if stripped.startswith('{{') and stripped.endswith('}}'):
            return patch_data
            
        helm_templates: Dict[str, str] = {}
        template_counter = 0
        
        def replace_template(match):
            nonlocal template_counter
            placeholder = f"__HELM_TEMPLATE_{template_counter}__"
            helm_templates[placeholder] = match.group(0)
            template_counter += 1
            return placeholder
        preserved = re.sub(r'{{[^}]+}}', replace_template, patch_data)
        try:
            data = json.loads(preserved)
            return cls._restore_templates(data, helm_templates)
        except json.JSONDecodeError:
            return patch_data

    @classmethod
    def _restore_templates(
        cls, 
        obj: Any, 
        templates: Dict[str, str]
    ) -> Any:
        """Recursively restores Helm templates in parsed JSON"""
        if isinstance(obj, str):
            for placeholder, template in templates.items():
                obj = obj.replace(placeholder, template)
            return obj
        elif isinstance(obj, dict):
            return {k: cls._restore_templates(v, templates) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [cls._restore_templates(i, templates) for i in obj]
        return obj


@dataclass(frozen=True)
class ObjectRef:
    """helper class represents a reference to a Kubernetes object"""
    name: str
    namespace: Optional[str] = None
    
    def __hash__(self):
        return hash((self.name, self.namespace))
    
    def __eq__(self, other):
        if not isinstance(other, ObjectRef):
            return NotImplemented
        return self.name == other.name and self.namespace == other.namespace

class ReferenceUpdater:
    def __init__(self, resources: List[dict], sandbox: Sandbox):
        self.ref_mapping = {}
        
        for obj in resources:
            if not isinstance(obj, dict) or "metadata" not in obj:
                continue
                
            original_ref = ObjectRef(
                name=obj["metadata"].get("name"),
                namespace=obj["metadata"].get("namespace")
            )
            if sandbox["own_namespace"]:
                self.ref_mapping[original_ref] = ObjectRef(
                    name=original_ref.name,
                    namespace=sandbox['name']
                )      
            else:
                self.ref_mapping[original_ref] = ObjectRef(
                    name=f"{sandbox['name']}-{original_ref.name}",
                    namespace=original_ref.namespace
                )      

    def process(self, resources: List[dict]) -> List[dict]:
        return [self._update_resource_metadata(obj, self.sandbox, self.ref_mapping) for obj in resources]

    CLUSTER_SCOPED_KINDS = {
        "ClusterRole",
        "ClusterRoleBinding",
        "CustomResourceDefinition",
        "PriorityClass",
        "StorageClass",
        "VolumeSnapshotClass",
        "PodSecurityPolicy",
        "NodeClass",
        "RuntimeClass",
    }

    @staticmethod
    def get_reference_fields(kind: str) -> typing.List[typing.Tuple[typing.List[str], str, typing.Optional[str]]]:
        """Returns a list of reference field locations and their name/namespace field names."""
        common_refs = [
            (["spec", "serviceAccountName"], "name", None),
            (["spec", "configMapRef"], "name", "namespace"),
            (["spec", "secretRef"], "name", "namespace"),
            (["spec", "volumes"], "secretName", None),
            (["spec", "volumes"], "configMap.name", None),
            (["spec", "template", "spec", "volumes"], "secretName", None),
            (["spec", "template", "spec", "volumes"], "configMap.name", None),
            (["spec", "template", "spec", "serviceAccountName"], "name", None),
            (["spec", "template", "spec", "imagePullSecrets"], "name", None),
            (["spec", "template", "spec", "containers", "*", "envFrom", "*", "configMapRef"], "name", None),
            (["spec", "template", "spec", "containers", "*", "envFrom", "*", "secretRef"], "name", None),
            (["spec", "template", "spec", "initContainers", "*", "envFrom", "*", "configMapRef"], "name", None),
            (["spec", "template", "spec", "initContainers", "*", "envFrom", "*", "secretRef"], "name", None)
        ]
        
        kind_specific_refs = {
            "Service": [
                (["spec", "selector"], "app", None),
                (["spec", "selector"], "app.kubernetes.io/name", None)
            ],
            "HTTPRoute": [
                (["spec", "rules", "*", "backendRefs", "*"], "name", "namespace"),
                (["spec", "parentRefs", "*"], "name", "namespace")
            ],
            "Ingress": [
                (["spec", "rules", "*", "http", "paths", "*", "backend", "service"], "name", "namespace")
            ],
            "NetworkPolicy": [
                (["spec", "podSelector"], "matchLabels.app", None)
            ]
        }
        return common_refs + kind_specific_refs.get(kind, [])

    @staticmethod
    def _get_additional_namespace_fields(kind: str) -> List[Tuple[List[str], str]]:
        """Returns paths to additional namespace fields for specific kinds."""
        kind_specific_fields = {
            "RoleBinding": [
                (["subjects"], "namespace"),
            ],
            "ClusterRoleBinding": [
                (["subjects"], "namespace"),
            ],
            "NetworkPolicy": [
                (["spec", "ingress", "*", "from", "*", "namespaceSelector"], "matchLabels.kubernetes.io/metadata.name"),
                (["spec", "egress", "*", "to", "*", "namespaceSelector"], "matchLabels.kubernetes.io/metadata.name"),
            ],
            "ValidatingWebhookConfiguration": [
                (["webhooks", "*", "clientConfig"], "namespace"),
            ],
            "MutatingWebhookConfiguration": [
                (["webhooks", "*", "clientConfig"], "namespace"),
            ],
        }
        return kind_specific_fields.get(kind, [])

    @staticmethod
    def _update_resource_metadata(obj: dict, sandbox: Sandbox, ref_mapping: Dict[ObjectRef, ObjectRef]) -> dict:
        if not isinstance(obj, dict) or "metadata" not in obj:
            return obj
        
        obj = copy.deepcopy(obj)
        kind = obj.get("kind")
        
        original_ref = ObjectRef(
            name=obj["metadata"].get("name"),
            namespace=obj["metadata"].get("namespace")
        )
        
        # Only handle namespace for namespaced resources
        if kind not in ReferenceUpdater.CLUSTER_SCOPED_KINDS:
            if original_ref in ref_mapping:
                new_ref = ref_mapping[original_ref]
                obj["metadata"]["name"] = new_ref.name
                if new_ref.namespace:
                    obj["metadata"]["namespace"] = new_ref.namespace
        else:
            # For cluster-scoped resources, only update name if needed
            if original_ref in ref_mapping:
                new_ref = ref_mapping[original_ref]
                obj["metadata"]["name"] = new_ref.name
                # Explicitly remove namespace if present
                obj["metadata"].pop("namespace", None)
        
        ref_patterns = ReferenceUpdater.get_reference_fields(kind)
        for path, name_field, namespace_field in ref_patterns:
            value = ReferenceUpdater._get_value_at_path(obj, path)
            if not value:
                continue
                
            if isinstance(value, list):
                for item in value:
                    ReferenceUpdater._update_ref_in_item(item, name_field, namespace_field, ref_mapping)
            elif isinstance(value, dict):
                ReferenceUpdater._update_ref_in_item(value, name_field, namespace_field, ref_mapping)
        
        for path, namespace_field in ReferenceUpdater._get_additional_namespace_fields(kind):
            value = ReferenceUpdater._get_value_at_path(obj, path)
            if not value:
                continue
                
            if isinstance(value, list):
                for item in value:
                    if sandbox["own_namespace"]:
                        ReferenceUpdater._set_nested_field(item, namespace_field, sandbox["name"])
            elif isinstance(value, dict):
                if sandbox["own_namespace"]:
                    ReferenceUpdater._set_nested_field(value, namespace_field, sandbox["name"])
        
        return obj

    @staticmethod
    def _get_value_at_path(obj: dict, path: typing.List[str]) -> typing.Any:
        current = obj
        for part in path:
            if part == "*" and isinstance(current, list):
                return [ReferenceUpdater._get_value_at_path(item, path[1:]) for item in current]
            elif isinstance(current, dict):
                current = current.get(part, {})
            else:
                return None
        return current

    @staticmethod
    def _get_nested_field(d: dict, field: str) -> Optional[Any]:
        parts = field.split('.')
        current = d
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    @staticmethod
    def _set_nested_field(d: dict, field: str, value: Any):
        parts = field.split('.')
        current = d
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value

    @staticmethod
    def _update_ref_in_item(item: dict, name_field: str, namespace_field: Optional[str], ref_mapping: Dict[ObjectRef, ObjectRef]):
        if not isinstance(item, dict):
            return
            
        name = ReferenceUpdater._get_nested_field(item, name_field)
        if not name:
            return
            
        namespace = ReferenceUpdater._get_nested_field(item, namespace_field) if namespace_field else None
        ref = ObjectRef(name=name, namespace=namespace)
        if ref in ref_mapping:
            new_ref = ref_mapping[ref]
            ReferenceUpdater._set_nested_field(item, name_field, new_ref.name)
            if namespace_field and new_ref.namespace:
                ReferenceUpdater._set_nested_field(item, namespace_field, new_ref.namespace)

class SandboxGenerator:
    """
    Main class for generating sandbox resources.
    """
    def __init__(self, k8s_client=None):
        self.k8s_manager = KubernetesResourceManager(k8s_client)
        self.patch_manager = PatchManager()
    
    @classmethod
    def validate_sandbox_config(cls, sandbox: Sandbox) -> List[str]:
        errors: List[str] = []
        
        if not cls._is_valid_field(sandbox, "name"):
            errors.append("Sandbox name is required")
            
        if "ingress" not in sandbox:
            errors.append("Ingress configuration is required")
        else:
            ingress = sandbox["ingress"]
            errors.extend(cls._validate_ingress(ingress))
        
        if "forked_objects" in sandbox:
            for obj in sandbox["forked_objects"]:
                errors.extend(cls._validate_forked_object(obj))
        
        if "new_objects" in sandbox:
            for obj in sandbox["new_objects"]:
                errors.extend(cls._validate_additional_object(obj))
                
        return errors

    @classmethod
    def _validate_ingress(cls, ingress: Dict) -> List[str]:
        errors: List[str] = []
        
        required_fields = {
            "hostname": "Ingress hostname",
            "target_name": "Ingress target_name",
            "target_namespace": "Ingress target_namespace"
        }
        
        for field, message in required_fields.items():
            if not cls._is_valid_field(ingress, field):
                errors.append(f"{message} is required")
        
        if "port" in ingress:
            port = ingress["port"]
            if port is not None:
                if isinstance(port, str) and not cls._is_helm_template(port):
                    errors.append("Port must be an integer or Helm template")
                elif isinstance(port, int) and not (1 <= port <= 65535):
                    errors.append("Port must be between 1 and 65535")
        
        if "matches" in ingress:
            for match in ingress["matches"]:
                errors.extend(cls._validate_route_match(match))
                
        return errors

    @classmethod
    def _validate_forked_object(cls, obj: Dict) -> List[str]:
        errors: List[str] = []
        
        if not cls._is_valid_field(obj, "name"):
            errors.append("Forked object name is required")
        if not cls._is_valid_field(obj, "namespace"):
            errors.append(f"Forked object {obj.get('name', 'unknown')} missing namespace")
        
        if "patches" in obj:
            for patch in obj["patches"]:
                errors.extend(cls._validate_patch(patch, obj.get("name", "unknown")))
                
        return errors

    @classmethod
    def _validate_additional_object(cls, obj: Dict) -> List[str]:
        errors: List[str] = []
        
        if "spec" not in obj:
            errors.append("Additional object missing spec")
            return errors
            
        spec = obj["spec"]
        if isinstance(spec, str):
            if not cls._is_helm_template(spec):
                try:
                    spec = yaml.safe_load(spec)
                except yaml.YAMLError as e:
                    errors.append(f"Invalid YAML spec: {str(e)}")
                    return errors
        
        if isinstance(spec, dict):
            required_fields = ["apiVersion", "kind", "metadata"]
            for field in required_fields:
                if field not in spec and not cls._has_helm_template(spec):
                    errors.append(f"Spec missing {field}")
                    
            if "metadata" in spec:
                if "name" not in spec["metadata"] and not cls._has_helm_template(spec["metadata"]):
                    errors.append("Spec missing metadata.name")
                    
        return errors

    @staticmethod
    def _is_helm_template(value: Any) -> bool:
        return isinstance(value, str) and ('{{' in value or '}}' in value)

    @staticmethod
    def _is_valid_field(obj: Dict, field: str) -> bool:
        return bool(obj.get(field)) or any(
            SandboxGenerator._is_helm_template(v) 
            for v in obj.values()
        )

    @staticmethod
    def _has_helm_template(obj: Dict) -> bool:
        for value in obj.values():
            if SandboxGenerator._is_helm_template(value):
                return True
            if SandboxGenerator._has_helm_template(value):
                return True
        return False

    @classmethod
    def _validate_route_match(cls, match: Dict) -> List[str]:
        errors: List[str] = []
        
        valid_fields = {"path", "headers", "query_params"}
        invalid_fields = set(match.keys()) - valid_fields
        if invalid_fields:
            errors.append(f"Invalid match fields: {', '.join(invalid_fields)}")
            
        if "headers" in match and not isinstance(match["headers"], dict):
            errors.append("Headers must be a dictionary")
            
        if "query_params" in match and not isinstance(match["query_params"], dict):
            errors.append("Query parameters must be a dictionary")
            
        return errors

    @classmethod
    def _validate_patch(cls, patch: Dict, obj_name: str) -> List[str]:
        errors: List[str] = []
        
        if not isinstance(patch, dict):
            errors.append(f"Invalid patch format for {obj_name}")
            return errors
            
        if "patch_type" not in patch:
            errors.append(f"Patch missing patch_type for {obj_name}")
        elif patch["patch_type"] not in ["strategic", "json", "merge"]:
            errors.append(f"Invalid patch_type '{patch['patch_type']}' for {obj_name}")
            
        if "patch" not in patch:
            errors.append(f"Patch missing content for {obj_name}")
        elif not isinstance(patch["patch"], (str, dict)):
            errors.append(f"Patch content must be string or dict for {obj_name}")
            
        return errors

    def _generate_base_resources(self, sandbox: Sandbox) -> List[Dict[str, Any]]:
        resources = []
        if sandbox["own_namespace"]:
            namespace = {
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": {
                    "name": sandbox["name"]
                }
            }
            resources.append(namespace)
        resources.extend(self._generate_ingress_resources(sandbox))
        return resources

    def _generate_ingress_resources(self, sandbox: Sandbox) -> List[Dict[str, Any]]:
        resources = []
        backend = self._get_backend_object(sandbox)
        if not backend:
            raise ResourceError(
                f"Backend {sandbox['ingress']['target_name']} not found in "
                f"namespace {sandbox['ingress']['target_namespace']}"
            )
        
        if backend.get("kind") in ["Deployment", "Rollout"]:
            service = self._generate_service(sandbox)
            resources.append(service)
            route = self._generate_http_route(sandbox, service)
            resources.append(route)
        else:
            route = self._generate_http_route(sandbox, backend)
            resources.append(route)
        return resources

    def _get_backend_object(self, sandbox: Sandbox) -> Optional[Dict[str, Any]]:
        target_name = sandbox["ingress"]["target_name"]
        target_namespace = sandbox["ingress"]["target_namespace"]
        for obj in sandbox["forked_objects"]:
            if (obj["name"] == target_name and 
                obj["namespace"] == target_namespace):
                return self.k8s_manager.get_resource(
                    name=target_name,
                    namespace=target_namespace,
                    kind=obj.get("kind")
                )
        for obj in sandbox["new_objects"]:
            spec = obj.get("spec", {})
            metadata = spec.get("metadata", {})
            if (metadata.get("name") == target_name and 
                metadata.get("namespace") == target_namespace):
                return spec
        return None

    def _generate_service(self, sandbox: Sandbox) -> Dict[str, Any]:
        target_name = sandbox["ingress"]["target_name"]
        service_name = (
            '{{ printf "%s-service" .Values.backendName }}'
            if self._is_helm_template(target_name)
            else f"{target_name}-service"
        )
        return {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": service_name,
                "namespace": sandbox["name"] if sandbox["own_namespace"] 
                           else sandbox["ingress"]["target_namespace"]
            },
            "spec": {
                "selector": {
                    "app": target_name
                },
                "ports": [{
                    "port": 80,
                    "targetPort": sandbox["ingress"]["port"] or 80
                }]
            }
        }

    # FIXME: this does not work if the route already exists
    # FIXME: this does not seem to handle the backend port well, 
    # we may need to add a backend_port to the confgured object
    def _generate_http_route(self, sandbox: Sandbox, backend: Dict[str, Any]) -> Dict[str, Any]:
        route_matches = []
        for match in sandbox["ingress"]["matches"]:
            route_match = {}
            if match.get("path"):
                route_match["path"] = {
                    "type": "PathPrefix",
                    "value": match["path"]
                }
            if match.get("headers"):
                route_match["headers"] = [
                    {"name": k, "value": v} 
                    for k, v in match["headers"].items()
                ]
            if match.get("query_params"):
                route_match["queryParams"] = [
                    {"name": k, "value": v}
                    for k, v in match["query_params"].items()
                ]
            route_matches.append(route_match)


        if sandbox["ingress"].get("mirror_proportion", False):
            mirror_filter = {
                "type": "RequestMirror",
                "requestMirror": {
                    "name": backend["metadata"]["name"],
                    "port": backend["spec"]["ports"][0]["port"]
                }
            }
            mirror_filter["requestMirror"]["proportion"] = sandbox["ingress"]["mirror_proportion"] / 100.0
            backend_ref = {
                "name": sandbox["ingress"]["target_name"],
                "port": sandbox["spec"]["ports"][0]["port"],
                "kind": "Service",
                "group": "",
                "filters": [mirror_filter]
            }
        else:
            backend_ref = {
                "name": backend["metadata"]["name"],
                "port": backend["spec"]["ports"][0]["port"],
                "kind": "Service",
                "group": ""
            }

        route_name = (
            '{{ printf "%s-route" .Values.sandboxName }}'
            if self._is_helm_template(sandbox["name"])
            else f"{sandbox['name']}-route"
        )
        route = {
            "apiVersion": "gateway.networking.k8s.io/v1beta1",
            "kind": "HTTPRoute",
            "metadata": {
                "name": route_name,
                "namespace": sandbox["ingress"]["target_namespace"]
            },
            "spec": {
                "hostnames": sandbox["ingress"]["hostname"],
                "rules": [{
                    "matches": route_matches,
                    "backendRefs": [backend_ref]
                }]
            }
        }
        if sandbox["ingress"].get("use_gateway", False):
            route["spec"]["parentRefs"] = [{
                "name": sandbox["ingress"].get("gateway_name", "gateway"),
                "namespace": sandbox["ingress"].get("gateway_namespace", "default"),
                "kind": "Gateway",
                "group": "gateway.networking.k8s.io"
            }]
        else:
            route["spec"]["parentRefs"] = [{
                "name": sandbox["ingress"]["target_name"],
                "namespace": sandbox["ingress"]["target_namespace"],
                "kind": "Service",
                "group": ""
            }]

        return route


    def _process_forked_objects(self, sandbox: Sandbox) -> List[Dict[str, Any]]:
        resources = []
        for obj in sandbox["forked_objects"]:
            try:
                resource = self.k8s_manager.get_resource(
                    name=obj["name"],
                    namespace=obj["namespace"],
                    kind=obj.get("kind")
                )
                
                if not resource:
                    if self._is_helm_template(obj["name"]):
                        resource = {
                            "apiVersion": "v1",
                            "kind": obj["kind"],
                            "metadata": {
                                "name": obj["name"],
                                "namespace": obj.get("namespace")
                            }
                        }
                    else:
                        raise ResourceError(
                            f"Resource {obj['name']} not found in namespace {obj['namespace']}"
                        )
                resource = self.k8s_manager.clean_metadata(resource)
                for patch in obj.get("patches", []):
                    resource = self.patch_manager.apply_patch(resource, patch)
                resources.append(resource)
            except Exception as e:
                raise ResourceError(f"Failed to process {obj['name']}: {str(e)}")
        
        return resources

    def _process_additional_objects(self, sandbox: Sandbox) -> List[Dict[str, Any]]:
        resources = []
        for obj in sandbox["new_objects"]:
            spec = obj["spec"]
            if isinstance(spec, str) and not self._is_helm_template(spec):
                spec = yaml.safe_load(spec)
            resources.append(spec)
        return resources

    def _add_annotations(self, resources: List[Dict[str, Any]], sandbox: Sandbox):
        for resource in resources:
            if "metadata" not in resource:
                continue
            metadata = resource["metadata"]
            metadata["annotations"] = metadata.get("annotations", {})
            metadata["annotations"]["sandbox-name"] = sandbox["name"]
            metadata["annotations"]["is-sandbox"] = "1"

    def generate(self, sandbox: Sandbox) -> List[Dict[str, Any]]:
        errors = self.validate_sandbox_config(sandbox)
        if errors:
            raise ValidationError(f"Invalid sandbox configuration: {'; '.join(errors)}")
        
        resources = self._generate_base_resources(sandbox)
        resources.extend(self._process_forked_objects(sandbox))
        resources.extend(self._process_additional_objects(sandbox))
        updater = ReferenceUpdater(resources, sandbox)
        resources = updater.process(resources)
        self._add_annotations(resources, sandbox)
        return resources


class TestPatchManager(unittest.TestCase):
    def setUp(self):
        self.patch_manager = PatchManager()

    def test_json_patch_deployment(self):
        """Test applying JSON patch to a Deployment"""
        deployment = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "spec": {
                "replicas": 1,
                "template": {
                    "spec": {
                        "containers": [{
                            "name": "app",
                            "image": "nginx:1.19"
                        }]
                    }
                }
            }
        }
        
        patch = {
            "patch_type": "json",
            "patch": [
                {"op": "replace", "path": "/spec/replicas", "value": 3},
                {"op": "replace", "path": "/spec/template/spec/containers/0/image", 
                 "value": "nginx:1.20"}
            ]
        }
        
        result = self.patch_manager.apply_patch(deployment, patch)
        self.assertEqual(result["spec"]["replicas"], 3)
        self.assertEqual(
            result["spec"]["template"]["spec"]["containers"][0]["image"], 
            "nginx:1.20"
        )

    def test_merge_patch_configmap(self):
        """Test applying merge patch to a ConfigMap"""
        configmap = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "data": {
                "key1": "value1",
                "key2": "value2"
            }
        }
        
        patch = {
            "patch_type": "merge",
            "patch": {
                "data": {
                    "key2": "new-value2",
                    "key3": "value3"
                }
            }
        }
        
        result = self.patch_manager.apply_patch(configmap, patch)
        self.assertEqual(result["data"]["key1"], "value1")
        self.assertEqual(result["data"]["key2"], "new-value2")
        self.assertEqual(result["data"]["key3"], "value3")

    def test_strategic_patch_deployment(self):
        """Test applying strategic patch to a Deployment"""
        deployment = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "spec": {
                "template": {
                    "spec": {
                        "containers": [{
                            "name": "app",
                            "env": [{
                                "name": "DEBUG",
                                "value": "false"
                            }]
                        }]
                    }
                }
            }
        }
        
        patch = {
            "patch_type": "strategic",
            "patch": {
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [{
                                "name": "app",
                                "env": [{
                                    "name": "LOG_LEVEL",
                                    "value": "info"
                                }]
                            }]
                        }
                    }
                }
            }
        }
        
        result = self.patch_manager.apply_patch(deployment, patch)
        container = result["spec"]["template"]["spec"]["containers"][0]
        env_vars = {env["name"]: env["value"] for env in container["env"]}
        self.assertEqual(env_vars["DEBUG"], "false")
        self.assertEqual(env_vars["LOG_LEVEL"], "info")

    def test_helm_template_preservation(self):
        deployment = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "spec": {
                "replicas": 1
            }
        }
        
        patch = {
            "patch_type": "merge",
            "patch": {
                "spec": {
                    "replicas": "{{ .Values.replicas }}",
                    "template": {
                        "spec": {
                            "containers": [{
                                "image": "{{ .Values.image }}:{{ .Values.tag }}"
                            }]
                        }
                    }
                }
            }
        }
        
        result = self.patch_manager.apply_patch(deployment, patch)
        self.assertEqual(result["spec"]["replicas"], "{{ .Values.replicas }}")
        self.assertEqual(
            result["spec"]["template"]["spec"]["containers"][0]["image"],
            "{{ .Values.image }}:{{ .Values.tag }}"
        )

class TestReferenceUpdater(unittest.TestCase):
    def setUp(self):
        self.basic_sandbox = {
            "name": "test-sandbox",
            "own_namespace": True,
            "ingress": {
                "hostname": ["test.example.com"],
                "port": 8080,
                "matches": [],
                "target_name": "backend",
                "target_namespace": "default"
            }
        }

    def test_basic_reference_mapping(self):
        resources = [{
            "metadata": {
                "name": "test-app",
                "namespace": "default"
            }
        }]

        updater = ReferenceUpdater(resources, self.basic_sandbox)
        result = updater.process(resources)

        self.assertEqual(
            result[0]["metadata"]["name"], 
            "test-app",
            "Name should remain unchanged when own_namespace=True"
        )
        self.assertEqual(
            result[0]["metadata"]["namespace"], 
            "test-sandbox",
            "Namespace should be updated to sandbox name"
        )

    def test_reference_mapping_without_own_namespace(self):
        sandbox = {**self.basic_sandbox, "own_namespace": False}
        resources = [{
            "metadata": {
                "name": "test-app",
                "namespace": "default"
            }
        }]

        updater = ReferenceUpdater(resources, sandbox)
        result = updater.process(resources)

        self.assertEqual(
            result[0]["metadata"]["name"], 
            "test-sandbox-test-app",
            "Name should be prefixed with sandbox name"
        )
        self.assertEqual(
            result[0]["metadata"]["namespace"], 
            "default",
            "Namespace should remain unchanged when own_namespace=False"
        )

    def test_cluster_scoped_resources(self):
        resources = [{
            "kind": "ClusterRole",
            "metadata": {
                "name": "test-role",
                "namespace": "default"  # Should be removed
            }
        }]

        updater = ReferenceUpdater(resources, self.basic_sandbox)
        result = updater.process(resources)

        self.assertNotIn(
            "namespace", 
            result[0]["metadata"],
            "Cluster-scoped resource should not have namespace"
        )
        self.assertEqual(
            result[0]["metadata"]["name"],
            "test-role",
            "Cluster-scoped resource name should remain unchanged"
        )

    def test_service_reference_update(self):
        resources = [{
            "kind": "Service",
            "metadata": {
                "name": "test-service",
                "namespace": "default"
            },
            "spec": {
                "selector": {
                    "app": "backend-app",
                    "app.kubernetes.io/name": "backend-app"
                }
            }
        }]

        updater = ReferenceUpdater(resources, self.basic_sandbox)
        result = updater.process(resources)

        self.assertEqual(
            result[0]["spec"]["selector"]["app"],
            "backend-app",
            "Service selector should be updated"
        )
        self.assertEqual(
            result[0]["spec"]["selector"]["app.kubernetes.io/name"],
            "backend-app",
            "Service kubernetes.io selector should be updated"
        )

    def test_pod_spec_references(self):
        resources = [{
            "kind": "Deployment",
            "metadata": {
                "name": "test-deployment",
                "namespace": "default"
            },
            "spec": {
                "template": {
                    "spec": {
                        "serviceAccountName": "test-sa",
                        "volumes": [
                            {
                                "name": "config",
                                "configMap": {
                                    "name": "test-config"
                                }
                            },
                            {
                                "name": "secret",
                                "secretName": "test-secret"
                            }
                        ],
                        "containers": [{
                            "name": "app",
                            "envFrom": [{
                                "configMapRef": {
                                    "name": "test-config"
                                }
                            }]
                        }]
                    }
                }
            }
        }]

        sandbox = {**self.basic_sandbox, "own_namespace": False}
        updater = ReferenceUpdater(resources, sandbox)
        result = updater.process(resources)
        pod_spec = result[0]["spec"]["template"]["spec"]
        
        self.assertEqual(
            pod_spec["serviceAccountName"],
            "test-sandbox-test-sa",
            "ServiceAccount reference should be updated"
        )

        config_volume = next(v for v in pod_spec["volumes"] if v["name"] == "config")
        self.assertEqual(
            config_volume["configMap"]["name"],
            "test-sandbox-test-config",
            "ConfigMap reference in volume should be updated"
        )

        secret_volume = next(v for v in pod_spec["volumes"] if v["name"] == "secret")
        self.assertEqual(
            secret_volume["secretName"],
            "test-sandbox-test-secret",
            "Secret reference in volume should be updated"
        )

        container = pod_spec["containers"][0]
        self.assertEqual(
            container["envFrom"][0]["configMapRef"]["name"],
            "test-sandbox-test-config",
            "ConfigMap reference in envFrom should be updated"
        )

    def test_network_policy_references(self):
        resources = [{
            "kind": "NetworkPolicy",
            "metadata": {
                "name": "test-policy",
                "namespace": "default"
            },
            "spec": {
                "podSelector": {
                    "matchLabels": {
                        "app": "test-app"
                    }
                },
                "ingress": [{
                    "from": [{
                        "namespaceSelector": {
                            "matchLabels": {
                                "kubernetes.io/metadata.name": "other-namespace"
                            }
                        }
                    }]
                }]
            }
        }]

        updater = ReferenceUpdater(resources, self.basic_sandbox)
        result = updater.process(resources)
        namespace_selector = result[0]["spec"]["ingress"][0]["from"][0]["namespaceSelector"]
        self.assertEqual(
            namespace_selector["matchLabels"]["kubernetes.io/metadata.name"],
            "test-sandbox",
            "Namespace selector should be updated to sandbox namespace"
        )

    def test_http_route_references(self):
        resources = [{
            "kind": "HTTPRoute",
            "metadata": {
                "name": "test-route",
                "namespace": "default"
            },
            "spec": {
                "rules": [{
                    "backendRefs": [{
                        "name": "backend-svc",
                        "namespace": "default"
                    }]
                }],
                "parentRefs": [{
                    "name": "gateway",
                    "namespace": "gateway-ns"
                }]
            }
        }]

        updater = ReferenceUpdater(resources, self.basic_sandbox)
        result = updater.process(resources)

        backend_ref = result[0]["spec"]["rules"][0]["backendRefs"][0]
        self.assertEqual(
            backend_ref["namespace"],
            "test-sandbox",
            "Backend reference namespace should be updated"
        )

        parent_ref = result[0]["spec"]["parentRefs"][0]
        self.assertEqual(
            parent_ref["namespace"],
            "test-sandbox",
            "Parent reference namespace should be updated"
        )

class TestSandboxGenerator(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.mock_k8s_client = Mock()
        self.generator = SandboxGenerator(self.mock_k8s_client)
        
        self.valid_sandbox = {
            "name": "test-sandbox",
            "own_namespace": True,
            "ingress": {
                "hostname": ["test.example.com"],
                "port": 8080,
                "matches": [{
                    "path": "/api",
                    "headers": {"version": "v1"}
                }],
                "target_name": "test-backend",
                "target_namespace": "default"
            },
            "forked_objects": [{
                "name": "test-backend",
                "namespace": "default",
                "kind": "Deployment",
                "patches": []
            }],
            "new_objects": None
        }

    def test_validate_sandbox_config_valid(self):
        errors = SandboxGenerator.validate_sandbox_config(self.valid_sandbox)
        self.assertEqual(len(errors), 0, "Valid sandbox should have no validation errors")

    def test_validate_sandbox_config_missing_required(self):
        invalid_sandbox = {
            "own_namespace": True
        }
        errors = SandboxGenerator.validate_sandbox_config(invalid_sandbox)
        self.assertGreater(len(errors), 0, "Should detect missing required fields")
        self.assertTrue(
            any("name" in error.lower() for error in errors),
            "Should report missing name"
        )

    def test_validate_ingress_config(self):
        sandbox_invalid_port = self.valid_sandbox.copy()
        sandbox_invalid_port["ingress"]["port"] = 70000  # Invalid port number
        errors = SandboxGenerator.validate_sandbox_config(sandbox_invalid_port)
        self.assertTrue(
            any("port" in error.lower() for error in errors),
            "Should detect invalid port"
        )

        sandbox_missing_backend = self.valid_sandbox.copy()
        del sandbox_missing_backend["ingress"]["target_name"]
        errors = SandboxGenerator.validate_sandbox_config(sandbox_missing_backend)
        self.assertTrue(
            any("backend" in error.lower() for error in errors),
            "Should detect missing backend name"
        )

    def test_validate_route_matches(self):
        invalid_match = {
            **self.valid_sandbox,
            "ingress": {
                **self.valid_sandbox["ingress"],
                "matches": [{
                    "invalid_field": "value",  # Invalid field
                    "headers": "invalid"  # Should be dict
                }]
            }
        }
        errors = SandboxGenerator.validate_sandbox_config(invalid_match)
        self.assertTrue(
            any("invalid" in error.lower() for error in errors),
            "Should detect invalid match fields"
        )
        self.assertTrue(
            any("headers" in error.lower() for error in errors),
            "Should detect invalid headers type"
        )

    def test_validate_forked_objects(self):
        """Test validation of forked objects configuration"""
        invalid_forked = {
            **self.valid_sandbox,
            "forked_objects": [{
                "name": "test-object",
                # Missing namespace
                "patches": [{
                    "patch": {},
                    "patch_type": "invalid"  # Invalid patch type
                }]
            }]
        }
        errors = SandboxGenerator.validate_sandbox_config(invalid_forked)
        self.assertTrue(
            any("namespace" in error.lower() for error in errors),
            "Should detect missing namespace"
        )
        self.assertTrue(
            any("patch_type" in error.lower() for error in errors),
            "Should detect invalid patch type"
        )

    def test_validate_additional_objects(self):
        invalid_additional = {
            **self.valid_sandbox,
            "new_objects": [{
                "spec": {
                    "apiVersion": "v1",
                    "kind": "Service",
                }
            }]
        }
        errors = SandboxGenerator.validate_sandbox_config(invalid_additional)
        self.assertTrue(
            any("metadata" in error.lower() for error in errors),
            "Should detect missing metadata"
        )

    @patch("yaml.safe_load")
    def test_validate_additional_objects_yaml(self, mock_yaml_load):
        mock_yaml_load.side_effect = yaml.YAMLError("Invalid YAML")
        invalid_yaml = {
            **self.valid_sandbox,
            "new_objects": [{
                "spec": "invalid: yaml: content"
            }]
        }
        errors = SandboxGenerator.validate_sandbox_config(invalid_yaml)
        self.assertTrue(
            any("yaml" in error.lower() for error in errors),
            "Should detect invalid YAML"
        )

    def test_generate_base_resources(self):
        mock_backend = {
            "kind": "Deployment",
            "metadata": {
                "name": "test-backend",
                "namespace": "default"
            },
            "spec": {
                "ports": [{
                    "port": 8080
                }]
            }
        }
        self.generator.k8s_manager.get_resource.return_value = mock_backend
        resources = self.generator._generate_base_resources(self.valid_sandbox)
        
        self.assertTrue(
            any(r["kind"] == "Namespace" for r in resources),
            "Should generate Namespace resource"
        )
        self.assertTrue(
            any(r["kind"] == "Service" for r in resources),
            "Should generate Service resource"
        )
        self.assertTrue(
            any(r["kind"] == "HTTPRoute" for r in resources),
            "Should generate HTTPRoute resource"
        )

    def test_process_forked_objects(self):
        """Test processing of forked objects"""
        mock_resource = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": "test-backend",
                "namespace": "default",
                "resourceVersion": "123",
                "uid": "abc-123"
            },
            "spec": {
                "replicas": 1
            }
        }
        self.generator.k8s_manager.get_resource.return_value = mock_resource

        sandbox_with_patch = {
            **self.valid_sandbox,
            "forked_objects": [{
                "name": "test-backend",
                "namespace": "default",
                "kind": "Deployment",
                "patches": [{
                    "patch_type": "strategic",
                    "patch": {"spec": {"replicas": 2}}
                }]
            }]
        }

        resources = self.generator._process_forked_objects(sandbox_with_patch)
        
        self.assertEqual(len(resources), 1, "Should process one forked object")
        processed = resources[0]
        self.assertEqual(
            processed["spec"]["replicas"], 
            2, 
            "Should apply patch to forked object"
        )
        self.assertNotIn(
            "resourceVersion", 
            processed["metadata"],
            "Should clean metadata"
        )

    def test_process_additional_objects(self):
        new_objects = {
            **self.valid_sandbox,
            "new_objects": [{
                "spec": {
                    "apiVersion": "v1",
                    "kind": "ConfigMap",
                    "metadata": {
                        "name": "test-config"
                    },
                    "data": {
                        "key": "value"
                    }
                }
            }]
        }

        resources = self.generator._process_additional_objects(new_objects)
        self.assertEqual(len(resources), 1, "Should process one additional object")
        self.assertEqual(
            resources[0]["kind"], 
            "ConfigMap",
            "Should process ConfigMap spec"
        )

    def test_add_annotations(self):
        resources = [{
            "metadata": {
                "name": "test-resource"
            }
        }]

        self.generator.add_annotations(resources, self.valid_sandbox)
        annotations = resources[0]["metadata"]["annotations"]
        self.assertEqual(
            annotations["sandbox-name"],
            "test-sandbox",
            "Should add sandbox name annotation"
        )
        self.assertEqual(
            annotations["is-sandbox"],
            "1",
            "Should add is-sandbox annotation"
        )

    def test_generate_complete(self):
        mock_backend = {
            "kind": "Deployment",
            "metadata": {
                "name": "test-backend",
                "namespace": "default"
            },
            "spec": {
                "ports": [{
                    "port": 8080
                }]
            }
        }
        self.generator.k8s_manager.get_resource.return_value = mock_backend

        resources = self.generator.generate(self.valid_sandbox)
        resource_kinds = {r["kind"] for r in resources}
        expected_kinds = {"Namespace", "Service", "HTTPRoute", "Deployment"}
        self.assertEqual(
            resource_kinds, 
            expected_kinds,
            "Should generate all expected resource kinds"
        )

        for resource in resources:
            self.assertIn(
                "annotations",
                resource["metadata"],
                "All resources should have annotations"
            )

    def test_error_handling(self):
        """Test error handling scenarios"""
        invalid_sandbox = {
            "name": "test-sandbox"
        }
        with self.assertRaises(ValidationError):
            self.generator.generate(invalid_sandbox)
        self.generator.k8s_manager.get_resource.side_effect = ResourceError("Not found")
        with self.assertRaises(ResourceError):
            self.generator.generate(self.valid_sandbox)

        self.generator.k8s_manager.get_resource.side_effect = None
        invalid_patch = {
            **self.valid_sandbox,
            "forked_objects": [{
                "name": "test-backend",
                "namespace": "default",
                "patches": [{
                    "patch_type": "invalid",
                    "patch": {}
                }]
            }]
        }
        with self.assertRaises(PatchError):
            self.generator.generate(invalid_patch)

if __name__ == '__main__':
    unittest.main()
