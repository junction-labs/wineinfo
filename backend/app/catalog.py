from fastapi import HTTPException
from typing import List
import csv
from .service_api import CatalogService, PaginatedList, Wine

class CatalogServiceImpl(CatalogService):
    CATALOG_FILE = "backend/data/gen/catalog_data.csv"

    def __init__(self, path: str = CATALOG_FILE):
        self.data: List[Wine] = []
        if path:
            with open(path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    row = {k: v if v is not None else '' for k, v in row.items()}
                    self.add_wine(Wine.model_validate(row))

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
                status_code=404, 
                detail=f"Wines not found: {missing_ids}"
            )
            
        return wines

    def get_all_wines_paginated(self, page: int, page_size: int) -> PaginatedList[Wine]:
        offset = (page - 1) * page_size
        paginated_wines = self.data[offset:offset + page_size]
        return PaginatedList[Wine](
            items=paginated_wines, 
            total=len(self.data), 
            page=page, 
            page_size=page_size, 
            total_pages=(len(self.data) + page_size - 1) // page_size)

    def add_wine(self, wine: Wine) -> Wine:
        wine.id = len(self.data)
        self.data.append(wine)
        return wine
