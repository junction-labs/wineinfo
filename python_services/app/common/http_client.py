from typing import Dict, Literal
import junction.requests
import requests
from .baggage import baggage_mgr


class HttpClientOptions:
    headers: Dict = {}
    use_baggage_mgr: bool = True
    baggage_updates: Dict[str, str] = {}


class HttpClient:
    def __init__(self, base_url: str, use_junction: bool = False):
        self.base_url = base_url.rstrip("/")
        self.session = (
            junction.requests.Session() if use_junction else requests.Session()
        )

    def _get_headers(
        self, method: Literal["GET", "POST"], options: HttpClientOptions
    ) -> Dict:
        headers = options.headers.copy()
        if method == "POST":
            headers["Content-Type"] = "application/json"
        baggage = {}
        if options.use_baggage_mgr:
            baggage = baggage_mgr.get_current()
        if options.baggage_updates:
            baggage.update(options.baggage_updates)
        if len(baggage) > 0:
            headers["baggage"] = ",".join([f"{k}={v}" for k, v in baggage.items()])
            print(f"baggage: {headers['baggage']}")
        return headers

    def get(
        self, path: str, request: Dict, options: HttpClientOptions = HttpClientOptions()
    ) -> Dict:
        headers = self._get_headers("GET", options)
        response = self.session.get(self.base_url + path, params=request, headers=headers)
        response.raise_for_status()
        return response.json()

    def post(
        self, path: str, request: Dict, options: HttpClientOptions = HttpClientOptions()
    ) -> Dict:
        headers = self._get_headers("POST", options)
        response = self.session.post(self.base_url + path, json=request, headers=headers)
        response.raise_for_status()
        return response.json()
