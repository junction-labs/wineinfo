from fastapi import HTTPException
from typing import Dict, Literal
import junction.requests
import requests
from .baggage import baggage_mgr


class HttpClient:
    def __init__(self, base_url: str, use_junction: bool = False):
        self.base_url = base_url.rstrip("/")
        self.session = (
            junction.requests.Session() if use_junction else requests.Session()
        )

    def request(
        self,
        method: Literal["get", "post", "GET", "POST"],
        url: str,
        request: Dict,
    ) -> Dict:
        try:
            method = method.lower()
            headers = {}
            baggage = baggage_mgr.get_current()
            if baggage:
                headers["baggage"] = baggage_mgr.to_headers(baggage)

            kwargs = {
                "headers": headers,
                "get": {"params": request},
                "post": {"json": request},
            }

            response = getattr(self.session, method)(
                f"{self.base_url}{url}", **kwargs[method]
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Remote {method.upper()} request to {url} failed: {str(e)}",
            )

    def get(self, url: str, request: Dict) -> Dict:
        return self.request("get", url, request)

    def post(self, url: str, request: Dict) -> Dict:
        return self.request("post", url, request)
