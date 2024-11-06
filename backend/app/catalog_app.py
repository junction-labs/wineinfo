from typing import Annotated, List
from fastapi import FastAPI, Query
from .service_api import RemoteCatalogService
from .catalog import CatalogServiceImpl, PaginatedList, Wine

app = FastAPI()
service = CatalogServiceImpl()


@app.get(RemoteCatalogService.GET_WINES)
async def get_wine(ids: Annotated[list[int] | None, Query()]) -> List[Wine]:
    return service.get_wine(ids)


@app.get(RemoteCatalogService.GET_ALL_WINES_PAGINATED)
async def get_all_wines_paginated(page: int, page_size: int) -> PaginatedList[Wine]:
    return service.get_all_wines_paginated(page, page_size)
