from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings
import requests
import junction.requests
from pydantic import BaseModel, TypeAdapter
from catalog import CatalogService, PaginatedList, Wine
from recs import RecommendationRequest, RecommendationService
from search import SearchRequest, SearchService
from typing import Annotated, Dict, List

class HttpCaller:
    def __init__(self, base_url: str, session):
        self.base_url = base_url.rstrip('/')
        self.session = session

    def get(self, url: str, request: BaseModel | Dict) -> Dict:
        try:
            if not isinstance(request, dict):
                request = request.model_dump()
            response = self.session.get(f"{self.base_url}/{url}", params=request)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Remote request to {url} failed: {str(e)}")


class RemoteCatalogService(CatalogService):
    def __init__(self, caller: HttpCaller):
        self.caller = caller

    def get_wine(self, ids: List[int]) -> List[Wine]:
        return TypeAdapter(List[Wine]).validate_python(self.caller.get("wines/", {"ids": ids}))

    def get_all_wines_paginated(self, page: int, page_size: int) -> PaginatedList[Wine]:
        return PaginatedList[Wine].model_validate(self.caller.get("wines/batch/", {"page": page, "page_size": page_size}))


class RemoteSearchService(SearchService):
    def __init__(self, caller: HttpCaller):
        self.caller = caller

    def search(self, request: SearchRequest) -> PaginatedList[int]:
        return PaginatedList[int].model_validate(self.caller.get("search/", request))


class RemoteRecommendationService(RecommendationService):
    def __init__(self, caller: HttpCaller):
        self.caller = caller

    def get_recommendations(self, request: RecommendationRequest) -> List[int]:
        return TypeAdapter(List[int]).validate_python(self.caller.get("recommendations/", request))


class ServiceSettings(BaseSettings):
    catalog_service: str = "http://localhost:8001"
    search_service: str = "http://localhost:8002"
    recs_service: str = "http://localhost:8003"
    use_junction: bool = False

settings = ServiceSettings()

if settings.use_junction:
    session = junction.requests.Session()
else:
    session = requests.Session()
catalog_service = RemoteCatalogService(HttpCaller(settings.catalog_service, session))
search_service = RemoteSearchService(HttpCaller(settings.search_service, session))
recs_service = RemoteRecommendationService(HttpCaller(settings.recs_service, session))


app = FastAPI()

# Need CORS as frontend makes calls to us directly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/cellar/ids")
def get_cellar_ids() -> List[int]:
    return []

@app.post("/cellar/add")
def add_to_cellar(wine_id: int):
    return

@app.post("/cellar/remove")
def remove_from_cellar(wine_id: int):
    return

@app.get("/wines/recommendations")
def get_recommendations(query: str) -> List[Wine]:
    cellar_ids = get_cellar_ids()
    request = RecommendationRequest(query=query, wine_ids=cellar_ids, limit=10, exclude_ids=[])
    wine_ids = recs_service.get_recommendations(request)
    wines = []
    if wine_ids:
        wines = catalog_service.get_wine(wine_ids)
    return wines

@app.get("/wines/search")
def search_wines(request: Annotated[SearchRequest, Query()]) -> PaginatedList[Wine]:
    if not request.query.strip():
        return catalog_service.get_all_wines_paginated(request.page, request.page_size)

    results = search_service.search(request)
    wines = []
    if results.items:
        wines = catalog_service.get_wine(results.items)
    return PaginatedList[Wine](
        items=wines,
        total=results.total,
        page=results.page,
        page_size=results.page_size,
        total_pages=results.total_pages,
    )
