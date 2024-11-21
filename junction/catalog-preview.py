""" """

import junction
from utils import kubectl_apply

from junction.config import Route, RouteMatch, Target

catalog: Target = {
    "name": "wineinfo-catalog",
    "namespace": "default",
}

catalog_next: Target = {
    "name": "wineinfo-catalog-next",
    "namespace": "default",
}

is_admin: RouteMatch = {"headers": [{"name": "x-wineinfo-user", "value": "admin"}]}

route: Route = {
    "vhost": catalog,
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
    method="GET",
    url="http://wineinfo-catalog.default.svc.cluster.local",
    headers={},
)

assert route["vhost"] == {**catalog, "port": None}
assert rule_idx == len(route["rules"]) - 1
assert backend == {**catalog, "port": 80}

(route, rule_idx, backend) = junction.check_route(
    routes=[route],
    method="GET",
    url="http://wineinfo-catalog.default.svc.cluster.local",
    headers={"x-wineinfo-user": "admin"},
)
assert route["vhost"] == {**catalog, "port": None}
assert rule_idx == 0
assert backend == {**catalog_next, "port": 80}

kubectl_apply(junction.dump_kube_route(route))
