from abc import ABC, abstractmethod
from fastapi import HTTPException, Request
from pydantic import BaseModel, TypeAdapter
from typing import Dict, List, Tuple
import junction.requests
import requests
from pydantic_settings import BaseSettings

class ServiceSettings(BaseSettings):
    catalog_service: str = "http://localhost:8001"
    search_service: str = "http://localhost:8002"
    recs_service: str = "http://localhost:8003"
    persist_service: str = "http://localhost:8004"
    use_junction: bool = False
    data_path: str = "backend/data/gen"
    catalog_demo_mojibake: bool = False
    search_demo_latency: bool = False
    recs_demo_failure: bool = False


def get_fwd_headers(request: Request):
    forwarded_headers = ["x-username"]
    headers = {}
    for header in forwarded_headers:
        if request.headers.get(header):
            headers[header] = request.headers[header]
    return headers


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

class Wine(BaseModel):
    id: int | None
    title: str
    country: str
    description: str
    designation: str
    points: str
    price: str
    province: str
    region_1: str
    region_2: str
    taster_name: str
    taster_twitter_handle: str
    variety: str
    winery: str


class PaginatedList[T](BaseModel):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    class Config:
        generic_types_only = True


class CatalogService(ABC):
    @abstractmethod
    def get_wine(self, headers: Dict, ids: List[int]) -> List[Wine]:
        pass

    @abstractmethod
    def get_all_wines_paginated(
        self, headers: Dict, page: int, page_size: int
    ) -> PaginatedList[Wine]:
        pass


class RemoteCatalogService(CatalogService):
    def __init__(self, caller: HttpCaller):
        self.caller = caller

    GET_WINES = "/wines/"

    def get_wine(self, headers: Dict, ids: List[int]) -> List[Wine]:
        return TypeAdapter(List[Wine]).validate_python(
            self.caller.get(
               headers, 
                RemoteCatalogService.GET_WINES,
                {"ids": ids},
            )
        )

    GET_ALL_WINES_PAGINATED = "/wines/batch/"

    def get_all_wines_paginated(
        self, headers: Dict, page: int, page_size: int
    ) -> PaginatedList[Wine]:
        return PaginatedList[Wine].model_validate(
            self.caller.get(
                headers,
                RemoteCatalogService.GET_ALL_WINES_PAGINATED,
                {"page": page, "page_size": page_size},
            )
        )


class SearchRequest(BaseModel):
    query: str
    page: int = 1
    page_size: int = 20


class SearchService(ABC):
    @abstractmethod
    def search(self, headers: Dict, request: SearchRequest) -> PaginatedList[int]:
        pass


class RemoteSearchService:
    def __init__(self, caller: HttpCaller):
        self.caller = caller

    SEARCH = "/search/"

    def search(
        self, headers: Dict, request: SearchRequest
    ) -> PaginatedList[int]:
        return PaginatedList[int].model_validate(
            self.caller.get(headers, RemoteSearchService.SEARCH, request)
        )


class RecsRequest(BaseModel):
    query: str
    limit: int = 20


class RecsService(ABC):
    @abstractmethod
    def get_recommendations(self, headers: Dict, request: RecsRequest) -> List[int]:
        pass


class RemoteRecsService(RecsService):
    def __init__(self, caller: HttpCaller):
        self.caller = caller

    GET_RECOMMENDATIONS = "/recommendations/"

    def get_recommendations(self, headers: Dict, request: RecsRequest) -> List[int]:
        return TypeAdapter(List[int]).validate_python(
            self.caller.get(headers, RemoteRecsService.GET_RECOMMENDATIONS, request)
        )

class SQLRequest(BaseModel):
    query: str
    params: list[str | int] | None

class PersistService(ABC):
    @abstractmethod
    def do_sql(self, headers: Dict, query: str, params: List) -> List[Tuple]:
        pass


class RemotePersistService(PersistService):
    def __init__(self, caller: HttpCaller):
        self.caller = caller

    DO_SQL = "/do_sql/"

    def do_sql(self, headers: Dict, sql_request: SQLRequest) -> List[Tuple]:
        return TypeAdapter(List[Tuple]).validate_python(
            self.caller.post(headers, RemotePersistService.DO_SQL, sql_request)
        )
