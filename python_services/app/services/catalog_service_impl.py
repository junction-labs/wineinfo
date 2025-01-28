import csv
import os
from typing import List
from fastapi import HTTPException
from typing import List
from ..common.config import ServiceSettings
from ..common.api import PaginatedList, Wine


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

    def get_wine(self, ids: List[int]) -> List[Wine]:
        wines = []
        missing_ids = []

        for wine_id in ids:
            if wine_id < len(self.data):
                wines.append(self.data[wine_id])
            else:
                missing_ids.append(wine_id)

        if missing_ids:
            raise HTTPException(
                status_code=404, detail=f"Wines not found: {missing_ids}"
            )

        return wines

    def get_all_wines_paginated(self, page: int, page_size: int) -> PaginatedList[Wine]:
        offset = (page - 1) * page_size
        paginated_wines = self.data[offset : offset + page_size]
        return PaginatedList[Wine](
            items=paginated_wines,
            total=len(self.data),
            page=page,
            page_size=page_size,
            total_pages=(len(self.data) + page_size - 1) // page_size,
        )
