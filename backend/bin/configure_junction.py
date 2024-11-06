import os, sys

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir)
    )
)
from typing import List
import junction
import urllib
from backend.app.service_api import RemoteCatalogService, ServiceSettings


def parse_url(url: str, is_kube: bool) -> junction.config.VirtualHost:
    parsed = urllib.parse.urlparse(url)
    if parsed.port is None:
        if parsed.scheme == "https":
            port = 443
        else:
            port = 80
    else:
        port = parsed.port

    if is_kube:
        cells = parsed.hostname.split(".")
        if len(cells) != 5:
            raise ValueError(
                "To configure junction for kube, hostnames need to be fully qualified"
            )

        return junction.config.VirtualHost(
            name=cells[0], namespace=cells[1], port=port, type="KubeService"
        )
    else:
        return junction.config.VirtualHost(
            hostname=parsed.hostname, port=port, type="Dns"
        )


if __name__ == "__main__":
    settings = ServiceSettings()
    catalog_vhost: junction.config.VirtualHost = parse_url(
        settings.catalog_service, settings.using_kube
    )
    test_catalog_vhost: junction.config.VirtualHost = parse_url(
        settings.test_catalog_service, settings.using_kube
    )
    routes: List[junction.config.Route] = [
        {
            "vhost": catalog_vhost,
            "rules": [
                {
                    "matches": [
                        {"path": {"value": RemoteCatalogService.GET_WINES}},
                        {"header": {"name": "x-test", "value": "true"}}
                    ],
                    "timeouts": {"backend_request": 0.05},
                    "backends": [
                        {
                            **catalog_vhost,
                            "weight": 50,
                        },
                        {
                            **test_catalog_vhost,
                            "weight": 50,
                        },
                    ],
                },
                {
                    "matches": [{"path": {"value": RemoteCatalogService.GET_WINES}}],
                    "timeouts": {"backend_request": 0.05},
                    "backends": [ catalog_vhost ]
                },
                {
                    "matches": [{"path": {"value": RemoteCatalogService.GET_ALL_WINES_PAGINATED}}],
                    "timeouts": {"backend_request": 0.2},
                    "retry": junction.config.RouteRetry(
                        codes=[502], attempts=2, backoff=0.001
                    ),
                    "backends": [ catalog_vhost ]
                },
            ],
        }
    ]
