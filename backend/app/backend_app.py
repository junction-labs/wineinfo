from typing import Annotated, Dict, List
from fastapi import FastAPI, Query, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .services.catalog import PaginatedList, Wine
from .services.recs import RecsRequest
from .services.search import SearchRequest
from .services.service_api import (
    get_fwd_headers,
    HttpCaller,
    RemoteCatalogService,
    RemotePersistService,
    RemoteRecsService,
    RemoteSearchService,
    ServiceSettings)


settings = ServiceSettings()

catalog_service = RemoteCatalogService(HttpCaller(settings.catalog_service, settings))
search_service = RemoteSearchService(HttpCaller(settings.search_service, settings))
recs_service = RemoteRecsService(HttpCaller(settings.recs_service, settings))
persist_service = RemotePersistService(HttpCaller(settings.persist_service, settings))

app = FastAPI()

# Need CORS as frontend makes calls to us directly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/cellar/list")
def get_cellar(request: Request, x_username: Annotated[str | None, Header()] = None) -> List[Wine]:
    if not x_username:
        raise Exception("No user")
    ret = persist_service.do_sql(get_fwd_headers(request), {
            "query": "SELECT wine_id FROM cellar WHERE user_id = ?",
            "params": [ x_username ]
        })
    wine_ids = [row[0] for row in ret]
    wines = []
    if wine_ids:
        wines = catalog_service.get_wine(get_fwd_headers(request), wine_ids)
    return wines

@app.get("/cellar/add")
def add_to_cellar(request: Request, wine_id: int, x_username: Annotated[str | None, Header()] = None):
    if not x_username:
        raise Exception("No user")
    
    persist_service.do_sql(get_fwd_headers(request), {
            "query": "INSERT INTO cellar (wine_id, user_id) VALUES (?, ?)",
            "params": [ wine_id, x_username ]
        })
                           
@app.get("/cellar/remove")
def remove_from_cellar(request: Request, wine_id: int, x_username: Annotated[str | None, Header()] = None):
    if not x_username:
        raise Exception("No user")

    persist_service.do_sql(get_fwd_headers(request), {
            "query": "DELETE FROM cellar WHERE wine_id = ? AND user_id = ?",
            "params": [ wine_id, x_username ]
        })




@app.get("/wines/recommendations")
def get_recommendations(request: Request, query: str) -> List[Wine]:
    params = RecsRequest(query=query, limit=10)
    wine_ids = recs_service.get_recommendations(get_fwd_headers(request), params)
    wines = []
    if wine_ids:
        wines = catalog_service.get_wine(get_fwd_headers(request), wine_ids)
    return wines


@app.get("/wines/search")
def search_wines(request: Request, 
                 params: Annotated[SearchRequest, Query()]) -> PaginatedList[Wine]:
    h = get_fwd_headers(request)
    if not params.query.strip():
        return catalog_service.get_all_wines_paginated(
            h, params.page, params.page_size,
        )

    results = search_service.search(h, params)
    wines = []
    if results.items:
        wines = catalog_service.get_wine(h, results.items)
    return PaginatedList[Wine](
        items=wines,
        total=results.total,
        page=results.page,
        page_size=results.page_size,
        total_pages=results.total_pages,
    )
