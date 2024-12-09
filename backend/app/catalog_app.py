from typing import Annotated, List
from fastapi import FastAPI, Query, Request
from .services.service_api import RemoteCatalogService, ServiceSettings, get_fwd_headers
from .services.catalog import CatalogServiceImpl, PaginatedList, Wine


app = FastAPI()
service = CatalogServiceImpl(ServiceSettings())


@app.get(RemoteCatalogService.GET_WINES)
async def get_wine(
    request: Request, 
    ids: Annotated[list[int] | None, Query()]) -> List[Wine]:
    return service.get_wine(get_fwd_headers(request), ids=ids)


@app.get(RemoteCatalogService.GET_ALL_WINES_PAGINATED)
async def get_all_wines_paginated(
    request: Request, 
    page: int,
    page_size: int) -> PaginatedList[Wine]:
    return service.get_all_wines_paginated(get_fwd_headers(request), page, page_size
    )
