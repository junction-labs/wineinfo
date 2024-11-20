from typing import Annotated, List

import junction.requests
import requests
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .catalog import PaginatedList, Wine
from .recs import RecommendationRequest
from .search import SearchRequest
from .service_api import (
    HttpCaller,
    RemoteCatalogService,
    RemoteRecommendationService,
    RemoteSearchService,
    ServiceSettings,
)

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
    request = RecommendationRequest(
        query=query, wine_ids=cellar_ids, limit=10, exclude_ids=[]
    )
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
