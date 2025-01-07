from contextvars import ContextVar
from typing import Dict
import requests
from fastapi import Request


class BaggageManager:
    def __init__(self):
        self._context: ContextVar[Dict[str, str]] = ContextVar("baggage", default={})

    def get_current(self) -> Dict[str, str]:
        return self._context.get()

    def set_current(self, baggage: Dict[str, str]) -> None:
        self._context.set(baggage)

    def parse_headers(self, headers) -> Dict[str, str]:
        """Parse baggage headers into a dict"""
        baggage = {}
        # Handle both single string and list of headers
        if isinstance(headers, str):
            headers = [headers]

        for header in headers:
            for item in header.split(","):
                if "=" in item:
                    k, v = item.split("=", 1)
                    baggage[k.strip()] = v.strip()
        return baggage

    def to_headers(self, baggage: Dict[str, str]) -> list[str]:
        """Convert baggage dict to list of header strings"""
        return [f"{k}={v}" for k, v in baggage.items()]


# Global instance
baggage_mgr = BaggageManager()


# FastAPI middleware
def create_baggage_middleware():
    async def baggage_middleware(request: Request, call_next):
        if baggage_headers := request.headers.getlist("baggage"):
            baggage = baggage_mgr.parse_headers(baggage_headers)
            baggage_mgr.set_current(baggage)
        response = await call_next(request)
        return response

    return baggage_middleware


# Requests integration
class BaggageSession(requests.Session):
    def request(self, method, url, **kwargs):
        baggage = baggage_mgr.get_current()
        if baggage:
            headers = kwargs.get("headers", {})
            headers.setdefault("baggage", [])
            headers["baggage"].extend(baggage_mgr.to_headers(baggage))
            kwargs["headers"] = headers
        return super().request(method, url, **kwargs)


# Helper function to create a session
def create_baggage_session() -> BaggageSession:
    return BaggageSession()
