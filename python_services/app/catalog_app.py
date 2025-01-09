import csv
from functools import lru_cache
import os
from typing import Annotated, List
from fastapi import Depends, FastAPI, Query
from .common.config import ServiceSettings
from .common.api import PaginatedList, Wine, CATALOG_SERVICE
from .common.baggage import create_baggage_middleware
from fastapi import HTTPException
from typing import List


class CatalogServiceImpl:
    def __init__(self, settings: ServiceSettings, reset: bool = False):
        self.data: List[Wine] = []
        self.file_name = os.path.join(settings.data_path, "catalog_data.csv")
        if not reset:
            with open(self.file_name, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    row = {k: v if v is not None else "" for k, v in row.items()}
                    if settings.catalog_demo_mojibake:
                        row["title"] = row["title"].encode("utf-8").decode("iso-8859-1")
                    self.add_wine(Wine.model_validate(row))

    def add_wine(self, wine: Wine) -> Wine:
        wine.id = len(self.data)
        self.data.append(wine)
        return wine


# only reason we do this is so we can use implementation
# class in the data gen binary
@lru_cache()
def get_impl() -> CatalogServiceImpl:
    return CatalogServiceImpl(ServiceSettings())


app = FastAPI()
app.middleware("http")(create_baggage_middleware())


@app.get(CATALOG_SERVICE["get_wine"]["path"])
async def get_wine(
    ids: Annotated[list[int] | None, Query()],
    impl: CatalogServiceImpl = Depends(get_impl),
) -> List[Wine]:
    wines = []
    missing_ids = []

    for wine_id in ids:
        if wine_id < len(impl.data):
            wines.append(impl.data[wine_id])
        else:
            missing_ids.append(wine_id)

    if missing_ids:
        raise HTTPException(status_code=404, detail=f"Wines not found: {missing_ids}")

    return wines


@app.get(CATALOG_SERVICE["get_all_wines_paginated"]["path"])
async def get_all_wines_paginated(
    page: int, page_size: int, impl: CatalogServiceImpl = Depends(get_impl)
) -> PaginatedList[Wine]:
    offset = (page - 1) * page_size
    paginated_wines = impl.data[offset : offset + page_size]
    return PaginatedList[Wine](
        items=paginated_wines,
        total=len(impl.data),
        page=page,
        page_size=page_size,
        total_pages=(len(impl.data) + page_size - 1) // page_size,
    )
