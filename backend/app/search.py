from abc import ABC, abstractmethod
import os
import shutil
from whoosh.filedb.filestore import RamStorage, FileStorage
from whoosh.fields import Schema, TEXT, ID, NUMERIC
from whoosh.qparser import MultifieldParser
from .service_api import SearchRequest, SearchService
from .catalog import PaginatedList, Wine



class SearchServiceImpl(SearchService):
    SEARCH_DIR = "backend/data/gen/search_data"

    def __init__(self, reset: bool = False, path: str = SEARCH_DIR):
        schema = Schema(
            id=ID(stored=True),
            title=TEXT(stored=True),
            description=TEXT(stored=True),
            variety=TEXT(stored=True),
            winery=TEXT(stored=True),
            country=TEXT(stored=True),
            province=TEXT(stored=True),
            region_1=TEXT(stored=True),
            region_2=TEXT(stored=True),
            points=NUMERIC(stored=True),
            price=NUMERIC(stored=True)
        )
        if path:
            if reset and os.path.exists(path):
                shutil.rmtree(path)
            if not os.path.exists(path):
                os.mkdir(path)
            self.storage = FileStorage(path, supports_mmap=False)
            if reset:
                self.index = self.storage.create_index(indexname="index", schema=schema)
            else:
                self.index = self.storage.open_index(indexname="index")
        else:
            self.storage = RamStorage()
            self.index = self.storage.create_index(schema)

    def open_index(self):
        self.writer = self.index.writer()

    def add_wine(self, wine: Wine):
        self.writer.add_document(
            id=str(wine.id),
            title=wine.title,
            description=wine.description,
            variety=wine.variety,
            winery=wine.winery,
            country=wine.country,
            province=wine.province,
            region_1=wine.region_1 or "",
            region_2=wine.region_2 or "",
            points=float(wine.points) if wine.points else 0.0,
            price=float(wine.price) if wine.price else 0.0
        )

    def build_index(self):
        self.writer.commit()
        del self.writer
 
    def search(self, request: SearchRequest) -> PaginatedList[int]:
        with self.index.searcher() as searcher:
            fields = ["title", "description", "variety", "winery", "country", "province", "region_1", "region_2"]
            parser = MultifieldParser(fields, self.index.schema)
            query = parser.parse(request.query)
            start = (request.page - 1) * request.page_size
            results = searcher.search(query, limit=None)
            return PaginatedList[int].model_validate({
                "items": [int(hit['id']) for hit in results[start:start + request.page_size]],
                "total": len(results),
                "page": request.page,
                "page_size": request.page_size,
                "total_pages": (len(results) + request.page_size - 1) // request.page_size
            })
