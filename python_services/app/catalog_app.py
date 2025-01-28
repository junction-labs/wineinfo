from typing import Annotated, List
from fastapi import FastAPI, Query
from .common.config import ServiceSettings
from .common.api import PaginatedList, Wine, CATALOG_SERVICE
from .common.baggage import create_baggage_middleware
from .services.catalog_service_impl import CatalogServiceImpl
from typing import List

impl = CatalogServiceImpl(ServiceSettings())
app = FastAPI()
app.middleware("http")(create_baggage_middleware())


@app.get(CATALOG_SERVICE["get_wine"]["path"])
async def get_wine(
    ids: Annotated[list[int] | None, Query()],
) -> List[Wine]:
    return impl.get_wine(ids)

@app.get(CATALOG_SERVICE["get_all_wines_paginated"]["path"])
async def get_all_wines_paginated(
    page: int, page_size: int
) -> PaginatedList[Wine]:
    return impl.get_all_wines_paginated(page, page_size)
