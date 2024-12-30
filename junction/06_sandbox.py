import yaml
from sandbox_lib import Sandbox, SandboxIngress, generate_sandbox
from utils import service_hostname
import junction.config as config


catalog_service: config.Service = {
    "type": "kube",
    "name": "wineinfo-catalog",
    "namespace": "default",
}

def create_catalog_sandbox(name: str):
    return Sandbox(
        name=name,
        own_namespace=False,
        ingress=SandboxIngress(
            name=service_hostname(catalog_service),
            matches=[config.RouteMatch(headers=[{"name": "x-username", "value": "admin"}])],
        ),
        new_objects=[],
        forked_objects=[])

resources = generate_sandbox(create_catalog_sandbox("example1"))
yaml_docs = []
for resource in resources:
    yaml_docs.append(yaml.dump(resource, default_flow_style=False))
print("\n---\n".join(yaml_docs))    