from typing import Annotated, List
from fastapi import FastAPI, Query, Header
from .service_api import RemoteCatalogService
from .catalog import CatalogServiceImpl, PaginatedList, Wine

app = FastAPI()
service = CatalogServiceImpl()


@app.get(RemoteCatalogService.GET_WINES)
async def get_wine(
    ids: Annotated[list[int] | None, Query()],
    x_wineinfo_user: Annotated[str | None, Header()] = None,
) -> List[Wine]:
    return service.get_wine(auth_user=x_wineinfo_user, ids=ids)


@app.get(RemoteCatalogService.GET_ALL_WINES_PAGINATED)
async def get_all_wines_paginated(
    page: int,
    page_size: int,
    x_wineinfo_user: Annotated[str | None, Header()] = None,
) -> PaginatedList[Wine]:
    return service.get_all_wines_paginated(
        auth_user=x_wineinfo_user, page=page, page_size=page_size
    )
