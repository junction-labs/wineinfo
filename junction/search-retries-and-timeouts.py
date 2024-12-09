""" """
import os, sys
sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.path.pardir)
    )
)
import junction
from utils import kubectl_apply
from junction.config import Route, Target
from backend.app.services.service_api import RemoteSearchService

search: Target = {
    "name": "wineinfo-search",
    "namespace": "default",
}
route: Route = {
    "vhost": search,
    "rules": [
        {
            "matches": [{"path": {"value": RemoteSearchService.SEARCH}}],
            "timeouts": {"backend_request": 0.1},
            "retry": junction.config.RouteRetry(
                attempts=5, backoff=0.1
            ),
            "backends": [{**search, "port": 80}],
        },
        {
            "backends": [{**search, "port": 80}],
        },
    ],
}

(matched, rule_idx, backend) = junction.check_route(
    routes=[route],
    method="GET",
    url="http://wineinfo-search.default.svc.cluster.local" + RemoteSearchService.SEARCH + "?term=foo",
    headers={},
)
rule = matched["rules"][rule_idx]
assert "timeouts" in rule
assert "retry" in rule


(matched, rule_idx, backend) = junction.check_route(
    routes=[route],
    method="GET",
    url="http://wineinfo-search.default.svc.cluster.local/foo/",
    headers={},
)
rule = matched["rules"][rule_idx]
assert not "timeouts" in rule
assert not "retry" in rule

kubectl_apply(junction.dump_kube_route(route))
