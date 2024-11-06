from abc import ABC, abstractmethod
from fastapi import HTTPException, Query
from pydantic_settings import BaseSettings
from pydantic import BaseModel, Field, TypeAdapter
from typing import Dict, List, Optional


class HttpCaller:
    def __init__(self, base_url: str, session):
        self.base_url = base_url.rstrip("/")
        self.session = session

    def get(self, url: str, request: BaseModel | Dict) -> Dict:
        try:
            if not isinstance(request, dict):
                request = request.model_dump()
            response = self.session.get(f"{self.base_url}{url}", params=request)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Remote request to {url} failed: {str(e)}"
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
    def get_wine(self, ids: List[int]) -> List[Wine]:
        pass

    @abstractmethod
    def get_all_wines_paginated(self, page: int, page_size: int) -> PaginatedList[Wine]:
        pass


class RemoteCatalogService(CatalogService):
    def __init__(self, caller: HttpCaller):
        self.caller = caller

    GET_WINES = "/wines/"

    def get_wine(self, ids: List[int]) -> List[Wine]:
        return TypeAdapter(List[Wine]).validate_python(
            self.caller.get(RemoteCatalogService.GET_WINES, {"ids": ids})
        )

    GET_ALL_WINES_PAGINATED = "/wines/batch/"

    def get_all_wines_paginated(self, page: int, page_size: int) -> PaginatedList[Wine]:
        return PaginatedList[Wine].model_validate(
            self.caller.get(
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
    def search(self, request: SearchRequest) -> PaginatedList[int]:
        pass


class RemoteSearchService:
    def __init__(self, caller: HttpCaller):
        self.caller = caller

    SEARCH = "/search/"

    def search(self, request: SearchRequest) -> PaginatedList[int]:
        return PaginatedList[int].model_validate(
            self.caller.get(RemoteSearchService.SEARCH, request)
        )


class RecommendationRequest(BaseModel):
    query: str
    limit: int = 20
    wine_ids: Optional[List[int]] = Field(Query([]))
    exclude_ids: Optional[List[int]] = Field(Query([]))


class RecommendationService(ABC):
    @abstractmethod
    def get_recommendations(self, request: RecommendationRequest) -> List[int]:
        pass


class RemoteRecommendationService(RecommendationService):
    def __init__(self, caller: HttpCaller):
        self.caller = caller

    GET_RECOMMENDATIONS = "/recommendations/"

    def get_recommendations(self, request: RecommendationRequest) -> List[int]:
        return TypeAdapter(List[int]).validate_python(
            self.caller.get(RemoteRecommendationService.GET_RECOMMENDATIONS, request)
        )


class ServiceSettings(BaseSettings):
    catalog_service: str = "http://localhost:8001"
    search_service: str = "http://localhost:8002"
    recs_service: str = "http://localhost:8003"
    using_kube: bool = False
    use_junction: bool = False
    data_path: str = "backend/data/gen"
