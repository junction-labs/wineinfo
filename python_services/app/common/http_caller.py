from fastapi import HTTPException
from pydantic import BaseModel
from typing import Dict
import junction.requests
import requests
from .config import ServiceSettings

class HttpCaller:
    def __init__(self, base_url: str, settings: ServiceSettings):
        self.base_url = base_url.rstrip("/")
        self.session = junction.requests.Session() if settings.use_junction else requests.Session()

    def get(self, headers: Dict, url: str, request: BaseModel | Dict) -> Dict:
        try:
            if not isinstance(request, dict):
                request = request.model_dump()

            response = self.session.get(
                f"{self.base_url}{url}",
                params=request,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Remote GET request to {url} failed: {str(e)}"
            )

    def post(self, headers: Dict, url: str, request: BaseModel | Dict) -> Dict:
        try:
            if not isinstance(request, dict):
                request = request.model_dump()

            response = self.session.post(
                f"{self.base_url}{url}",
                json=request,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Remote POST request to {url} failed: {str(e)}"
            )
