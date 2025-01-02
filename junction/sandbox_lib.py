import copy
from dataclasses import dataclass
import typing
import yaml
from kubernetes import config, dynamic
from kubernetes.dynamic.exceptions import ResourceNotFoundError
from typing import Any, Dict, List, Optional
import jsonpatch
import jsonmerge
import junction
from utils import service_hostname

class SandboxIngress(typing.TypedDict):
    #the name of the existing kube service from which traffic will be taken.
    service_name: str 
    #the port on which traffic will be received
    service_port: int 
     #the subset of traffic to be sent to the sandbox
    matches: typing.List[junction.config.RouteMatch]


class SandboxNewObject(typing.TypedDict):
    type: typing.Literal["new"]

class KubePatch(typing.TypedDict):
    patch_type: typing.Literal["strategic"] | typing.Literal["json"] | typing.Literal["merge"]
    patch: str | dict

class SandboxObject(typing.TypedDict):
    type: typing.Literal["fork"] | typing.Literal["new"]
    apiVersion: str
    kind: str
    namespace: str | None
    name: str
    metadata: dict | None# only for new objects, and optional even in that case
    spec: str | dict | None # only for new objects
    patches: List[KubePatch] | None # only for patch objects

class SandboxConfig(typing.TypedDict):
    # must be unique in both source and new namespace
    name: str 

    source_namespace: str

    # if None, then the sandbox resources are created in the source namespace
    new_namespace: str | None 
    
    # a string to format the name of sandbox objects to ensure uniqueness. 
    # Use %s to refer to existing name. If none, then the source name is used
    name_formatter: str | None   

class SandboxSpec(typing.TypedDict):
    config: SandboxConfig
    ingress: SandboxIngress
    objects: typing.List[SandboxObject]

class PatchUtils:
    @staticmethod
    def _create_container_patch(container: dict, container_name: Optional[str] = None) -> KubePatch:
        if container_name:
            container = {**container, "name": container_name}
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
    def clear_env_vars(container_name: Optional[str] = None) -> KubePatch:
        return PatchUtils._create_container_patch({"env": None}, container_name)

    @staticmethod
    def add_env_vars(env_vars: Dict[str, str], container_name: Optional[str] = None) -> KubePatch:
        container = {"env": [{"name": k, "value": v} for k, v in env_vars.items()]}
        return PatchUtils._create_container_patch(container, container_name)

    @staticmethod
    def set_image(image: str, container_name: Optional[str] = None) -> KubePatch:
        return PatchUtils._create_container_patch({"image": image}, container_name)

    @staticmethod
    def set_resources(
        memory_request: str,
        cpu_request: str,
        memory_limit: Optional[str] = None,
        cpu_limit: Optional[str] = None,
        container_name: Optional[str] = None
    ) -> KubePatch:
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
        return PatchUtils._create_container_patch(container, container_name)

    @staticmethod
    def set_replica_count(count: int) -> KubePatch:
        return {
            "patch_type": "strategic",
            "patch": {
                "spec": {
                    "replicas": count
                }
            }
        }

    @staticmethod
    def merge_pod_metadata(
        annotations: Optional[Dict[str, str]] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> KubePatch:
        metadata = {}
        if annotations is not None:
            metadata["annotations"] = annotations
        if labels is not None:
            metadata["labels"] = labels
            
        return {
            "patch_type": "strategic",
            "patch": {
                "spec": {
                    "template": {
                        "metadata": metadata
                    }
                }
            }
        }

    @staticmethod
    def clear_init_containers() -> KubePatch:
        """Remove all init containers from the pod."""
        return {
            "patch_type": "strategic",
            "patch": {
                "spec": {
                    "template": {
                        "spec": {
                            "initContainers": None  # Setting to null/None removes the field
                        }
                    }
                }
            }
        }

    @staticmethod
    def add_init_container(
        image: str,
        name: Optional[str] = None,
        command: Optional[List[str]] = None,
        env_vars: Optional[Dict[str, str]] = None
    ) -> KubePatch:
        init_container = {
            "name": name or f"init-{image.split('/')[-1].split(':')[0]}",
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
    
class SandboxError(BaseException):
    pass

class KubeInterface:
    def __init__(self, k8s_client=None):
        self.client = k8s_client or self._create_default_client()
        self._api_cache: Dict[str, Any] = {}

    def _create_default_client(self) -> dynamic.DynamicClient:
        try:
            client = config.new_client_from_config()
            return dynamic.DynamicClient(client)
        except Exception as e:
            raise SandboxError(f"Failed to create Kubernetes client: {str(e)}")

    def get_resource(
        self,
        apiVersion: str,
        kind: str,
        name: str, 
        namespace: str, 
    ) -> dict:
        if (apiVersion,kind) not in self._api_cache:
            try:
                self._api_cache[(apiVersion,kind)] = self.client.resources.get(api_version=apiVersion,kind=kind)
            except Exception as e:
                raise SandboxError(f"Failed to get API for {apiVersion} {kind}: {str(e)}")
        try:
            api = self._api_cache[(apiVersion,kind)]
            return api.get(name=name, namespace=namespace).to_dict()
        except ResourceNotFoundError:
            raise SandboxError(f"Failed to get {apiVersion} {kind} {name} {namespace}")

@dataclass(frozen=True)
class KubeId:
    """helper class represents a reference to a Kubernetes object"""
    kind: str
    name: str
    namespace:str
    
    def __hash__(self):
        return hash((self.kind, self.name, self.namespace))
    
    def __eq__(self, other):
        if not isinstance(other, KubeId):
            return NotImplemented
        return self.kind == other.kind and self.name == other.name and self.namespace == other.namespace

class KubeIdForker:
    """ class that updates name/namespace for a set of kubernetes objects and their references"""
    def __init__(self):
        pass

    @staticmethod
    def new_name(name:str, sandbox_config: SandboxConfig) -> str:
        if "name_formatter" in sandbox_config:
            return sandbox_config["name_formatter"] % name
        return name

    @staticmethod
    def process(resources: List[dict], sandbox_config: SandboxConfig):
        ref_mapping = {}
        for obj in resources:
            # note: this may use old namespace so we do it first
            KubeIdForker._update_references(obj, sandbox_config, ref_mapping) 
            original_ref = KubeId(
                kind=obj["kind"],
                name=obj["metadata"]["name"],
                namespace=obj["metadata"]["namespace"]
            )
            new_ref = KubeId(
                kind= original_ref.kind,
                name=KubeIdForker.new_name(original_ref.name, sandbox_config),
                namespace=sandbox_config.get("new_namespace", original_ref.namespace)
            )      
            obj["metadata"]["name"] = new_ref.name
            obj["metadata"]["namespace"] = new_ref.namespace
            KubeIdForker._add_labels(obj, sandbox_config)
            KubeIdForker._update_selectors(obj, sandbox_config)
            if "new_namespace" in sandbox_config:
                KubeIdForker._update_namespace_references(obj, sandbox_config)
            
            # update mapping for later things in the list
            ref_mapping[original_ref] = new_ref

    @staticmethod
    def add_labels(labelDict: Dict[str, str], sandbox_config: SandboxConfig):
        labelDict["app.kubernetes.io/managed-by"] = "sandbox"
        labelDict["sandbox/name"] = sandbox_config["name"]

    def _add_labels(obj: dict, sandbox_config: SandboxConfig):
        KubeIdForker.add_labels(obj["metadata"].get("labels", {}), sandbox_config)
        if obj["kind"] in ["Deployment", "ReplicaSet", "DaemonSet", "StatefulSet", "Job"]:
            template_labels = obj.get("spec", {}).get("template", {}).get("metadata", {}).get("labels", {})
            KubeIdForker.add_labels(template_labels, sandbox_config)
        elif obj["kind"] == "CronJob":
            # have 2 sets to add
            template_labels = obj.get("spec", {}).get("jobTemplate", {}).get("metadata", {}).get("labels", {})
            KubeIdForker.add_labels(template_labels, sandbox_config)
            template_labels = obj.get("spec", {}).get("jobTemplate", {}).get("spec", {}).get("template", {}).get("metadata", {}).get("labels", {})
            KubeIdForker.add_labels(template_labels, sandbox_config)
    
    def _update_selectors(obj: dict, sandbox_config: SandboxConfig):
        if obj["kind"] in ["Deployment", "ReplicaSet", "DaemonSet", "StatefulSet", "NetworkPolicy"]:
            if obj["kind"] == "NetworkPolicy":
                base = obj.get("spec", {}).get("podSelector", {})
            else:
                base = obj.get("spec", {}).get("selector", {})
            exprs = base.get("matchExpressions")
            if exprs:
                exprs.append({"key": "sandbox/name", "operator": "In", "values": [sandbox_config["name"]]})
            else:
                labels = base.get("matchLabels", {})
                labels["sandbox/name"] = sandbox_config["name"]
        elif obj["kind"] == "Service":
            labels = obj.get("spec", {}).get("selector", {})
            labels["sandbox/name"] = sandbox_config["name"]

    @staticmethod
    def _update_references(obj: dict, sandbox_config: SandboxConfig, ref_mapping: Dict[KubeId, KubeId]):

        if obj["kind"] in ["Deployment", "Job", "ReplicaSet", "DaemonSet", "StatefulSet", "CronJob"]:
            ref_patterns =  [
                ("ServiceAccount", ["spec", "template", "spec"], "serviceAccountName", None),
                ("Secret", ["spec", "template", "spec", "imagePullSecrets", "*"], "name", None),
                ("Secret", ["spec", "template", "spec", "volumes", "*"], "secretName", None),
                ("ConfigMap", ["spec", "template", "spec", "volumes", "*", "configMap"], "name", None),
                ("PersistentVolumeClaim", ["spec", "template", "spec", "volumes", "*", "persistentVolumeClaim"], "claimName", None),
                ("ConfigMap", ["spec", "template", "spec", "containers", "*", "envFrom", "*", "configMapRef"], "name", None),
                ("ConfigMap", ["spec", "template", "spec", "containers", "*", "env", "valueFrom", "configMapKeyRef"], "name", None),
                ("Secret", ["spec", "template", "spec", "containers", "*", "envFrom", "*", "secretRef"], "name", None),
                ("Secret", ["spec", "template", "spec", "containers", "*", "env", "valueFrom", "secretKeyRef"], "name", None),
                ("ConfigMap", ["spec", "template", "spec", "initContainers", "*", "envFrom", "*", "configMapRef"], "name", None),
                ("ConfigMap", ["spec", "template", "spec", "initContainers", "*", "env", "valueFrom", "configMapKeyRef"], "name", None),
                ("Secret", ["spec", "template", "spec", "initContainers", "*", "envFrom", "*", "secretRef"], "name", None),
                ("Secret", ["spec", "template", "spec", "initContainers", "*", "env", "valueFrom", "secretKeyRef"], "name", None),
            ]
        elif obj["kind"] == "HTTPRoute":
            ref_patterns =  [
                ("Service", ["spec", "rules", "*", "backendRefs", "*"], "name", "namespace"),
                ("Service", ["spec", "parentRefs", "*"], "name", "namespace")
            ]
        elif obj["kind"] == "Ingress":
            ref_patterns =  [
                ("Service", ["spec", "rules", "*", "http", "paths", "*", "backend", "service"], "name", "namespace")
            ],
        else:
            return

        for match_kind, path, name_field, namespace_field in ref_patterns:
            for item in KubeIdForker._get_dicts_at_path(obj, path):
                if not isinstance(item, dict):
                    raise SandboxError(f"Unexpected item in matched dicts list: {item}")
                
                name = item.get(name_field)
                if not name:
                    continue
                #if we dont have namespace for a reference, it just the namespace of the object
                if namespace_field:
                    namespace = item.get(namespace_field, obj["metadata"]["namespace"])
                else:
                    namespace = obj["metadata"]["namespace"]
                ref = KubeId(kind=match_kind, name=name, namespace=namespace)
                if ref in ref_mapping:
                    new_ref = ref_mapping[ref]
                    item[name_field] = new_ref.name
                    if namespace_field:
                        item[namespace_field] = new_ref.namespace

 
    @staticmethod
    def _update_namespace_references(obj: dict, sandbox_config: SandboxConfig):
        kind_specific_fields = {
            "RoleBinding": [
                (["subjects"], "namespace"),
            ],
            "ClusterRoleBinding": [
                (["subjects"], "namespace"),
            ],
            "ValidatingWebhookConfiguration": [
                (["webhooks", "*", "clientConfig"], "namespace"),
            ],
            "MutatingWebhookConfiguration": [
                (["webhooks", "*", "clientConfig"], "namespace"),
            ],
        }
        #FIXME: need to update the NetworkPolicy selectors
        fields =  kind_specific_fields.get(obj["kind"], [])
        if fields:
            for path, namespace_field in fields:
                values = KubeIdForker._get_dicts_at_path(obj, path)
                for item in values:
                    namespace = item.get(namespace_field, sandbox_config["source_namespace"])
                    if namespace:
                        item[namespace_field] = sandbox_config["new_namespace"]

  
    def _get_dicts_at_path(obj: dict, path: typing.List[str]) -> typing.List[dict]:
        """pulls out all matches of path from obj, with "*" being a wildcard to iterate lists"""
        results = [obj]
        
        for segment in path:
            next_results = []
            for current in results:
                if isinstance(current, list):
                    if segment == "*":
                        next_results.extend(current)
                elif isinstance(current, dict):
                    value = current.get(segment)
                    if value is not None:
                        next_results.append(value)
            results = next_results
            if not results:  # Early exit if no matches found
                return []
                
        return results
    

class KubePatcher:
    """Class that handles applying different types of patches to Kubernetes resources."""
    
    # Common merge keys for different Kubernetes resource types
    MERGE_KEYS = {
        "containers": "name",
        "initContainers": "name",
        "volumes": "name",
        "env": "name",
        "ports": "containerPort",
        "imagePullSecrets": "name"
    }

    def apply_patch(self, obj: dict, patch: KubePatch) -> dict:
        try:
            match patch["patch_type"]:
                case "json":
                    return jsonpatch.apply_patch(obj, patch["patch"])
                case "merge":
                    return self._deep_merge(obj, patch["patch"])
                case "strategic":
                    return self._apply_strategic_patch(obj, patch["patch"])
                case _:
                    raise ValueError(f"Unsupported patch type: {patch['patch_type']}")
        except Exception as e:
            raise ValueError(f"Failed to apply {patch['patch_type']} patch: {str(e)}")


    def _deep_merge(self, base: dict, patch: dict) -> dict:
        """
        Merges two dictionaries deeply, similar to jsonmerge    .
        Arrays are replaced entirely rather than merged.
        """
        if not isinstance(base, dict) or not isinstance(patch, dict):
            return patch

        result = base.copy()
        for key, patch_value in patch.items():
            if patch_value is None and key in result:
                del result[key]
                continue
                
            if key not in result:
                result[key] = patch_value
                continue
                
            base_value = result[key]
            
            if isinstance(patch_value, dict) and isinstance(base_value, dict):
                result[key] = self._deep_merge(base_value, patch_value)
            else:
                result[key] = patch_value
                
        return result

    def _apply_strategic_patch(self, base: dict, patch: dict) -> dict:
        if not isinstance(base, dict) or not isinstance(patch, dict):
            return patch
            
        result = base.copy()
        
        for key, patch_value in patch.items():
            if key == "$patch" and patch_value == "replace":
                return {k: v for k, v in patch.items() if k != "$patch"}
                
            if patch_value is None and key in result:
                result.pop(key)
                continue
                
            base_value = base.get(key)
            
            if isinstance(patch_value, list) and isinstance(base_value, list):
                merge_key = self.MERGE_KEYS.get(key)
                result[key] = self._merge_lists(base_value, patch_value, merge_key)
            elif isinstance(patch_value, dict) and isinstance(base_value, dict):
                result[key] = self._apply_strategic_patch(base_value, patch_value)
            else:
                result[key] = patch_value
                    
        return result

    def _merge_lists(self, base_list: list, patch_list: list, merge_key: Optional[str] = None) -> list:
        """Merge two lists following Kubernetes strategic merge rules."""
        if not patch_list:
            return base_list
        if not base_list:
            return patch_list
                
        if not merge_key:
            return base_list + patch_list
                
        base_dict = {
            item.get(merge_key): item 
            for item in base_list 
            if isinstance(item, dict)
        }
        result = base_list.copy()
        
        for patch_item in patch_list:
            if not isinstance(patch_item, dict):
                result.append(patch_item)
                continue
                
            key = patch_item.get(merge_key)
            if not key:
                result.append(patch_item)
                continue
            
            if "$patch" in patch_item:
                strategy = patch_item.pop("$patch")
                if strategy == "delete":
                    result = [
                        item for item in result 
                        if not isinstance(item, dict) 
                        or item.get(merge_key) != key
                    ]
                elif strategy == "replace":
                    for i, item in enumerate(result):
                        if isinstance(item, dict) and item.get(merge_key) == key:
                            result[i] = patch_item
                continue
                    
            if key in base_dict:
                idx = next(
                    i for i, item in enumerate(result)
                    if isinstance(item, dict) 
                    and item.get(merge_key) == key
                )
                result[idx] = self._apply_strategic_patch(base_dict[key], patch_item)
            else:
                result.append(patch_item)
        
        return result

class SandboxGenerator:
    """Class that generates a set of kubernetes resources for a sandbox."""

    def __init__(self, k8s_client=None):
        self.k8s_manager = KubeInterface(k8s_client)
    
    def generate(self, spec: SandboxSpec) -> List[Dict[str, Any]]:
        resources = []
        objects = copy.deepcopy(spec["objects"])
        self._add_service_if_needed(objects, spec["ingress"]["service_name"])
        for object in objects:
            resources.append(self._process_object(object, spec["config"]))
 
        KubeIdForker.process(resources, spec["config"])

        if "new_namespace" in spec["config"]:
            # this cant run through the forker as it doesn't have a namespace
            resources.insert(0, {
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": {"name": spec["config"]["new_namespace"]}
            })

        # route has to come after forking ids as it always exists in
        # namespace of the source service
        route = self._generate_http_route(spec["config"], spec["ingress"])
        resources.append(route)
        KubeIdForker.add_labels(route["metadata"].get("labels", {}), spec["config"])
        return resources

    def _add_service_if_needed(self, objects: typing.List[SandboxObject], service_name: str):
        for obj in objects:
            if obj["kind"] == "Service" and obj["name"] == service_name:
                return
 
        objects.append(SandboxObject(
            type="fork",
            name=service_name,
            kind="Service",
            apiVersion="v1"
        ))
        return objects

    
    def _process_object(self, obj: SandboxObject, config: SandboxConfig) -> Dict[str, Any]:
        if obj["type"] == "new":
            spec = obj["spec"]
            if isinstance(spec, str):
                spec = yaml.safe_load(spec) 

            metadata = copy.deepcopy(obj.get("metadata", {}))
            metadata["name"] = obj["name"]
            metadata["namespace"] = config["source_namespace"]

            return {
                "apiVersion": obj["apiVersion"],
                "kind": obj["kind"],
                "metadata": metadata,
                "spec": spec,
            }
        else:
            try:
                resource = self.k8s_manager.get_resource(
                    apiVersion=obj["apiVersion"],
                    kind=obj["kind"],
                    name=obj["name"],
                    namespace=config["source_namespace"]
                )
                resource = copy.deepcopy(resource)
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
                metadata["namespace"] = config["source_namespace"]
                for patch in obj.get("patches", []):
                    resource = KubePatcher().apply_patch(resource, patch)
                return resource
            except Exception as e:
                raise SandboxError(f"Failed to process {obj['name']}: {str(e)}")


    def _generate_http_route(self, sandbox_config: SandboxConfig, ingress: SandboxIngress) -> Dict[str, Any]:
        original_backend: config.Service = {
            "type": "kube",
            "name": ingress['service_name'],
            "namespace": sandbox_config['source_namespace'],
        }
        new_backend: config.Service = {
            "type": "kube",
            "name": KubeIdForker.new_name(ingress['service_name'], sandbox_config),
            "namespace": sandbox_config.get("new_namespace", sandbox_config['source_namespace']),
        }
        # route always lives in the source namespace, and we generate 1 per sandbox,
        # which means we need to generate a unique name even if we done have a formatter
        route_name = f"{ingress['service_name']}-{sandbox_config['name']}-route"
        if "name_formatter" in sandbox_config:
            route_name =  KubeIdForker.new_name(f"{ingress['service_name']}-route", sandbox_config)

        route: config.Route = {
            "id": route_name,
            "hostnames": [service_hostname(original_backend)],
            "ports": [ingress['service_port']],
            "rules": [
                {
                    "matches": ingress['matches'],
                    "backends": [{**new_backend, "port": ingress['service_port']}],
                },
                {
                    "backends": [{**original_backend, "port": ingress['service_port']}],
                },
            ],
        }
        spec = junction.dump_kube_route(route=route, namespace=sandbox_config['source_namespace'])
        return yaml.safe_load(spec)

  
def generate_sandbox_yaml(sandbox: SandboxSpec) -> str:
    generator = SandboxGenerator()
    resources = generator.generate(sandbox)
    return yaml.dump_all(resources, default_flow_style=False)

##
##
## UNIT TESTS BELOW
##
##
import unittest
from unittest.mock import Mock

class TestReferenceUpdater(unittest.TestCase):
        
    def test_reference_updating_deployment(self):
        # Test updating references in a deployment with volumes and env vars

        resources = [
            
            # We give a service account and config map the same name, but only include service
            # account, so only is should change
            {"kind": "ServiceAccount", "metadata": {"name": "app-config", "namespace": "default"}},    

            #lets do a secret by name
            {"kind": "Secret", "metadata": {"name": "app-secrets", "namespace": "default"}},    

            #lets do a secret by ref
            {"kind": "Secret", "metadata": {"name": "env-secrets", "namespace": "default"}},    
            
            #okay now the deployment which refers to them
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": "web-app",
                    "namespace": "default"
                },
                "spec": {
                    "template": {
                        "spec": {
                            "serviceAccountName": "app-config",
                            "volumes": [
                                {"name": "config", "configMap": {"name": "app-config"}},
                                {"name": "secrets", "secretName": "app-secrets"}
                            ],
                            "containers": [{
                                "name": "main",
                                "envFrom": [
                                    {"configMapRef": {"name": "env-config"}},
                                    {"secretRef": {"name": "env-secrets"}}
                                ]
                            }]
                        }
                    }
                }
            }
        ]
        config = { 
            "name": "test-sandbox", 
            "source_namespace": "default", 
            "new_namespace": "foo", #should affect nothing else
            "name_formatter": "prefix-%s" }
        KubeIdForker.process(resources, config)
        
        # Verify deployment name and namespace updated
        deployment = resources[3]
        self.assertEqual(deployment["metadata"]["name"], "prefix-web-app")
        self.assertEqual(deployment["metadata"]["namespace"], "foo")
        
        # Verify references updated as appropriate
        spec = deployment["spec"]["template"]["spec"]
        self.assertEqual(spec["serviceAccountName"], "prefix-app-config")
        self.assertEqual(spec["volumes"][0]["configMap"]["name"], "app-config")
        self.assertEqual(spec["volumes"][1]["secretName"], "prefix-app-secrets")
        self.assertEqual(
            spec["containers"][0]["envFrom"][0]["configMapRef"]["name"], 
            "env-config"
        )
        self.assertEqual(
            spec["containers"][0]["envFrom"][1]["secretRef"]["name"], 
            "prefix-env-secrets"
        )

    def test_selector_handling_shared_namespace(self):
        """Test that selectors are prefixed when sharing namespace"""
        resources = [{
            "kind": "Deployment",
            "metadata": {
                "name": "web-app",
                "namespace": "default"
            },
            "spec": {
                "selector": {
                    "matchLabels": {"app": "web", "tier": "frontend"}
                },
                "template": {
                    "metadata": {
                        "labels": {"app": "web", "tier": "frontend"}
                    }
                }
            }
        }, {
            "kind": "Service",
            "metadata": {
                "name": "web-app",
                "namespace": "default"
            },
            "spec": {
                "selector": {"app": "web", "tier": "frontend"}
            }
        }]
        
        config = { "name": "test-sandbox", "source_namespace": "default", "name_formatter": "test-sandbox-%s" }
        KubeIdForker.process(resources, config)
        
        # Verify all selectors and labels are updated
        deployment = resources[0]
        self.assertEqual(
            deployment["spec"]["selector"]["matchLabels"],
            {"app": "web", "tier": "frontend", 'sandbox/name': 'test-sandbox'}
        )
        self.assertEqual(
            deployment["spec"]["template"]["metadata"]["labels"],
            {"app": "web", "tier": "frontend", 'sandbox/name': 'test-sandbox', 'app.kubernetes.io/managed-by': 'sandbox'}
        )
        self.assertEqual(deployment["metadata"]["name"], "test-sandbox-web-app")
        self.assertEqual(deployment["metadata"]["namespace"], "default")
        
        service = resources[1]
        self.assertEqual(
            service["spec"]["selector"],
            {"app": "web", "tier": "frontend", 'sandbox/name': 'test-sandbox'}
        )
        self.assertEqual(service["metadata"]["name"], "test-sandbox-web-app")
        self.assertEqual(service["metadata"]["namespace"], "default")


class TestKubePatcher(unittest.TestCase):
    def setUp(self):
        self.patcher = KubePatcher()

    def test_deep_merge(self):
        """Test merging nested dictionaries"""
        base = {
            "metadata": {
                "labels": {"app": "web", "env": "prod"},
                "annotations": {"created-by": "user1"}
            },
            "spec": {"replicas": 3}
        }
        patch = {
            "metadata": {
                "labels": {"env": "dev", "version": "v2"},
                "finalizers": ["kubernetes"]
            }
        }
        result = self.patcher._deep_merge(base, patch)
        self.assertEqual(result["metadata"]["labels"], {
            "app": "web",
            "env": "dev",
            "version": "v2"
        })
        self.assertEqual(result["metadata"]["annotations"], {"created-by": "user1"})
        self.assertEqual(result["metadata"]["finalizers"], ["kubernetes"])
        self.assertEqual(result["spec"]["replicas"], 3)


    def test_strategic_merge_patch(self):
        """Test strategic merge patch behavior matches Kubernetes"""
        base_obj = {
            "spec": {
                "template": {
                    "spec": {
                        "containers": [{
                            "name": "app",
                            "image": "old-image:latest",
                            "env": [
                                {"name": "DEBUG", "value": "false"},
                                {"name": "REGION", "value": "us-east"}
                            ],
                            "ports": [
                                {"containerPort": 8080, "protocol": "TCP"},
                                {"containerPort": 9090, "protocol": "TCP"}
                            ],
                            "volumeMounts": [
                                {"name": "config", "mountPath": "/etc/config"}
                            ]
                        }]
                    }
                }
            }
        }

        test_cases = [
            {
                "name": "remove field with null",
                "patch": {
                    "patch_type": "strategic",
                    "patch": {
                        "spec": {
                            "template": {
                                "spec": {
                                    "containers": [{
                                        "name": "app",
                                        "env": None  # Should remove env array
                                    }]
                                }
                            }
                        }
                    }
                },
                "expected": {
                    "has_env": False,
                    "has_ports": True,  # Other fields preserved
                    "image": "old-image:latest"  # Original image kept
                }
            },
            {
                "name": "replace container with directive",
                "patch": {
                    "patch_type": "strategic",
                    "patch": {
                        "spec": {
                            "template": {
                                "spec": {
                                    "containers": [{
                                        "name": "app",
                                        "$patch": "replace",
                                        "image": "new-image:latest"
                                    }]
                                }
                            }
                        }
                    }
                },
                "expected": {
                    "has_env": False,  # Everything replaced
                    "has_ports": False,
                    "image": "new-image:latest"
                }
            },
            {
                "name": "merge list with delete directive",
                "patch": {
                    "patch_type": "strategic",
                    "patch": {
                        "spec": {
                            "template": {
                                "spec": {
                                    "containers": [{
                                        "name": "app",
                                        "ports": [{
                                            "containerPort": 8080,
                                            "$patch": "delete"
                                        }]
                                    }]
                                }
                            }
                        }
                    }
                },
                "expected": {
                    "ports_count": 1,  # One port removed
                    "remaining_port": 9090
                }
            }
        ]

        for case in test_cases:
            with self.subTest(name=case["name"]):
                obj_copy = yaml.safe_load(yaml.dump(base_obj))
                result = self.patcher.apply_patch(obj_copy, case["patch"])
                
                container = result["spec"]["template"]["spec"]["containers"][0]
                
                expected = case["expected"]
                if "has_env" in expected:
                    self.assertEqual("env" in container, expected["has_env"])
                
                if "has_ports" in expected:
                    self.assertEqual("ports" in container, expected["has_ports"])
                
                if "image" in expected:
                    self.assertEqual(container["image"], expected["image"])
                
                if "ports_count" in expected:
                    self.assertEqual(len(container["ports"]), expected["ports_count"])
                
                if "remaining_port" in expected:
                    self.assertEqual(
                        container["ports"][0]["containerPort"],
                        expected["remaining_port"]
                    )

    def test_json_patch(self):
        """Test JSON Patch functionality"""
        base_obj = {"foo": "bar", "items": [1, 2, 3]}
        patch = {
            "patch_type": "json",
            "patch": [
                {"op": "replace", "path": "/foo", "value": "baz"},
                {"op": "add", "path": "/items/1", "value": 1.5}
            ]
        }
        
        result = self.patcher.apply_patch(base_obj, patch)
        self.assertEqual(result["foo"], "baz")
        self.assertEqual(result["items"], [1, 1.5, 2, 3])

    def test_merge_patch(self):
        """Test JSON Merge Patch functionality"""
        base_obj = {
            "foo": "bar",
            "nested": {
                "a": 1,
                "b": 2
            }
        }
        patch = {
            "patch_type": "merge",
            "patch": {
                "foo": "baz",
                "nested": {
                    "b": 3,
                    "c": 4
                }
            }
        }
        
        result = self.patcher.apply_patch(base_obj, patch)
        self.assertEqual(result["foo"], "baz")
        self.assertEqual(result["nested"]["a"], 1)  # Preserved
        self.assertEqual(result["nested"]["b"], 3)  # Updated
        self.assertEqual(result["nested"]["c"], 4)  # Added

class TestSandboxGenerator(unittest.TestCase):
    def setUp(self):
        self.mock_k8s_client = Mock()
        self.generator = SandboxGenerator(self.mock_k8s_client)

    def test_generator(self):
        """Test generating resources for a sandbox"""
        test_cases = [
            {
                "type": "namespace_no_formatter",
                "expected": {
                    "deployment_name": "my-deployment",
                    "deployment_namespace": "newnamespace",
                    "service_name": "backend-svc",
                    "service_namespace": "newnamespace",
                    "should_have_namespace_resource": True
                }
            },
            {
                "type": "formatter_no_namespace",
                "expected": {
                    "deployment_name": "myprefix-my-deployment",
                    "deployment_namespace": "original",
                    "service_name": "myprefix-backend-svc",
                    "service_namespace": "original",
                    "should_have_namespace_resource": False
                }
            }
        ]

        for case in test_cases:
            with self.subTest(type=case["type"]):
                sandbox = {
                    "config": {
                        "name": "test-sandbox",
                        "source_namespace": "original",
                    },
                    "ingress": {
                        "matches": [ junction.config.RouteMatch(headers=[{"name": "x-username", "value": "admin"}]) ],
                        "service_name": "backend-svc",
                        "service_port": 80
                    },
                    "objects": [{
                        "type": "fork",
                        "name": "my-deployment",
                        "namespace": "original",
                        "kind": "Deployment",
                        "apiVersion": "apps/v1",
                        "patches": []
                    }]
                }
                if case["type"] == "namespace_no_formatter":
                    sandbox["config"]["new_namespace"] = "newnamespace"
                else:
                    sandbox["config"]["name_formatter"] = "myprefix-%s"

                # Mock the service and deployment that will be retrieved
                mock_deployment = {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "metadata": {
                        "name": "my-deployment",
                        "namespace": "original"
                    },
                    "spec": {
                        "selector": {
                            "matchLabels": {
                                "app": "my-label"
                            }
                        },
                        "template": {
                            "metadata": {
                                "labels": {
                                    "app": "my-label"
                                }
                            }
                        }
                    }
                }
                mock_service = {
                    "apiVersion": "v1",
                    "kind": "Service",
                    "metadata": {
                        "name": "backend-svc",
                        "namespace": "original"
                    },
                    "spec": {
                        "selector": {
                            "app": "my-label"
                        }
                    }
                }

                self.generator.k8s_manager.get_resource = Mock(side_effect=[mock_deployment, mock_service])
                resources = self.generator.generate(sandbox)

                # Check namespace resource presence
                namespace_resource = next(
                    (r for r in resources if r["kind"] == "Namespace"), None
                )
                if case["expected"]["should_have_namespace_resource"]:
                    self.assertIsNotNone(namespace_resource)
                    self.assertEqual(namespace_resource["metadata"]["name"], "newnamespace")
                else:
                    self.assertIsNone(namespace_resource)

                # Check deployment name and namespace
                deployment = next(
                    (r for r in resources if r["kind"] == "Deployment"), None
                )
                self.assertEqual(deployment["metadata"]["name"], 
                               case["expected"]["deployment_name"])
                self.assertEqual(deployment["metadata"]["namespace"], 
                               case["expected"]["deployment_namespace"])
                
                # Check service configuration
                service = next(
                    (r for r in resources if r["kind"] == "Service"), None
                )
                self.assertIsNotNone(service, "Service should be created")
                
                self.assertEqual(service["metadata"]["name"], 
                               case["expected"]["service_name"])
                self.assertEqual(service["metadata"]["namespace"], 
                               case["expected"]["service_namespace"])
                
                service_spec = service["spec"]
                self.assertDictEqual(
                    service_spec["selector"],
                    deployment["spec"]["selector"]["matchLabels"],
                    "Service selector should exactly match deployment labels"
                )
 
                #now the route
                route = next(
                    (r for r in resources if r["kind"] == "HTTPRoute"), None
                )
                self.assertIsNotNone(route, "HTTPRoute should be created")
                self.assertEqual(route["metadata"]["namespace"], "original") 

if __name__ == '__main__':
    unittest.main()
