import junction
import junction.config as config
from utils import kubectl_apply, service_hostname

# just a little sys.path hack to import our Backend code without making this a
# module. in the real world, we hope you don't have to do this!
import os
import sys
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir))
)
from python_services.app.common.api import SEARCH_SERVICE


search: config.Service = {
    "type": "kube",
    "name": "wineinfo-search",
    "namespace": "default",
}

route: config.Route = {
    "id": "wineinfo-search",
    "hostnames": [service_hostname(search)],
    "rules": [
        {
            "matches": [{"path": {"value": SEARCH_SERVICE["search"]["path"]}}],
            "timeouts": {
                "backend_request": 0.1,
            },
            "retry": {
                "attempts": 5,
                "backoff": 0.1,
            },
            "backends": [{**search, "port": 80}],
        },
        {
            "backends": [{**search, "port": 80}],
        },
    ],
}

(matched, rule_idx, backend) = junction.check_route(
    routes=[route],
    url="http://" + service_hostname(search) + SEARCH_SERVICE["search"]["path"] + "?term=foo",
)
rule = matched["rules"][rule_idx]
assert rule["timeouts"]["backend_request"] == 0.1
assert rule["retry"]["attempts"] == 5


(matched, rule_idx, backend) = junction.check_route(
    routes=[route],
    url="http://" + service_hostname(search) + "/foo/",
)
rule = matched["rules"][rule_idx]
assert not "timeouts" in rule
assert not "retry" in rule

kubectl_apply(junction.dump_kube_route(route=route, namespace="default"))
