import junction
import junction.config as config

from utils import kubectl_apply, service_fqdn

catalog: config.Service = {
    "type": "kube",
    "name": "wineinfo-catalog",
    "namespace": "default",
}
catalog_next: config.Service = {
    "type": "kube",
    "name": "wineinfo-catalog-next",
    "namespace": "default",
}

is_admin = config.RouteMatch(headers=[{
    "type": "RegularExpression", 
    "name": "baggage", 
    "value": ".*username=admin(,|$).*"}
])

route: config.Route = {
    "id": "wineinfo-catalog",
    "hostnames": [service_fqdn(catalog)],
    "rules": [
        {
            "matches": [is_admin],
            "backends": [{**catalog_next, "port": 80}],
        },
        {
            "backends": [{**catalog, "port": 80}],
        },
    ],
}

(route, rule_idx, backend) = junction.check_route(
    routes=[route],
    url="http://wineinfo-catalog/",
)
assert rule_idx == len(route["rules"]) - 1
assert backend == {**catalog, "port": 80}

(route, rule_idx, backend) = junction.check_route(
    routes=[route],
    url="http://wineinfo-catalog/",
    headers={"baggage": "username=admin"},
)
assert rule_idx == 0
assert backend == {**catalog_next, "port": 80}

kubectl_apply(junction.dump_kube_route(route=route, namespace="default"))
