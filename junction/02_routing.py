import junction
from utils import kubectl_apply, service_hostname

catalog = junction.config.ServiceKube(type="kube", name="wineinfo-catalog", namespace="default")
catalog_next = junction.config.ServiceKube(type="kube", name="wineinfo-catalog-next", namespace="default")

is_admin = junction.config.RouteMatch(headers = [{"name": "x-username", "value": "admin"}])

route: junction.config.Route = {
    "id": "catalog",
    "hostnames": [ service_hostname(catalog) ],
    "rules": [
        {
            "matches": [is_admin],
            "backends": [{ **catalog_next, "port": 80 }],
        },
        {
            "backends": [{ **catalog, "port": 80 }],
        },
    ],
}

(route, rule_idx, backend) = junction.check_route(
    routes=[route],
    method="GET",
    url="http://" + service_hostname(catalog) + "/",
    headers={},
)

assert rule_idx == len(route["rules"]) - 1
assert backend == { **catalog, "port": 80 }

(route, rule_idx, backend) = junction.check_route(
    routes=[route],
    method="GET",
    url="http://" + service_hostname(catalog) + "/",
    headers={"x-username": "admin"},
)
assert rule_idx == 0
assert backend == { **catalog_next, "port": 80 }

print(junction.dump_kube_route(route=route, namespace="default"))

kubectl_apply(junction.dump_kube_route(route=route, namespace="default"))
