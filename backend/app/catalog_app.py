from typing import Annotated, List
from fastapi import FastAPI, Query
from catalog import CATALOG_FILE, CatalogServiceImpl, PaginatedList, Wine

app = FastAPI()
service = CatalogServiceImpl(CATALOG_FILE)

@app.get("/wines/")
async def get_wine(ids: Annotated[list[int] | None, Query()]) -> List[Wine]:
    return service.get_wine(ids)

@app.get("/wines/batch/")
async def get_all_wines_paginated(page: int, page_size: int) -> PaginatedList[Wine]:
    return service.get_all_wines_paginated(page, page_size)
