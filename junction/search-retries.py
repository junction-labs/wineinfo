""" """
import os, sys
import junction
from utils import kubectl_apply

from junction.config import Route, Target
sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir)
    )
)
from backend.app.service_api import RemoteSearchService

search: Target = {
    "name": "wineinfo-search",
    "namespace": "default",
}

route: Route = {
    "vhost": search,
    "rules": [
        {
            "matches": [{"path": {"value": RemoteSearchService.SEARCH}}],
            "retry": junction.config.RouteRetry(
                codes=[502], attempts=2, backoff=0.001
            ),
            "backends": [{**search, "port": 80}],
            #later: "timeouts": {"backend_request": 0.2},
        },
    ],
}

(route, rule_idx, backend) = junction.check_route(
    routes=[route],
    method="GET",
    url="http://wineinfo-catalog.default.svc.cluster.local" + RemoteSearchService.SEARCH,
    headers={},
)

assert route["vhost"] == {**search, "port": None}
assert rule_idx == len(route["rules"]) - 1
assert backend == {**search, "port": 80}

# now apply
#kubectl_apply(junction.dump_kube_route(route))
