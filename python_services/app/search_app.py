from functools import lru_cache
import os
import random
import shutil
import time
from whoosh.filedb.filestore import FileStorage
from whoosh.fields import Schema, TEXT, ID, NUMERIC
from whoosh.qparser import MultifieldParser
from typing import Annotated
from fastapi import Depends, FastAPI, Query, Request
from .common.config import ServiceSettings
from .common.api import SearchRequest, PaginatedList, Wine, SEARCH_SERVICE__SEARCH


class SearchServiceImpl:
    def __init__(self, settings: ServiceSettings, reset: bool = False):
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
            price=NUMERIC(stored=True),
        )
        self.search_demo_latency = settings.search_demo_latency
        path = os.path.join(settings.data_path, "search_data")
        if reset and os.path.exists(path):
            shutil.rmtree(path)
        if not os.path.exists(path):
            os.mkdir(path)
        self.storage = FileStorage(path, supports_mmap=False)
        if reset:
            self.index = self.storage.create_index(indexname="index", schema=schema)
        else:
            self.index = self.storage.open_index(indexname="index")

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
            price=float(wine.price) if wine.price else 0.0,
        )

    def build_index(self):
        self.writer.commit()
        del self.writer

# only reason we do this is so we can use implementation 
# class in the data gen binary
@lru_cache()
def get_impl() -> SearchServiceImpl:
    return SearchServiceImpl(ServiceSettings())
app = FastAPI()

@app.get(SEARCH_SERVICE__SEARCH)
def search(
    request: Request, 
    params: Annotated[SearchRequest, Query()],
    impl: SearchServiceImpl = Depends(get_impl)) -> PaginatedList[int]:

        if impl.search_demo_latency:
            if random.random() < 0.5:
                time.sleep(10)

        with impl.index.searcher() as searcher:
            fields = [
                "title",
                "description",
                "variety",
                "winery",
                "country",
                "province",
                "region_1",
                "region_2",
            ]
            parser = MultifieldParser(fields, impl.index.schema)
            query = parser.parse(params.query)
            start = (params.page - 1) * params.page_size
            results = searcher.search(query, limit=None)
            return PaginatedList[int].model_validate(
                {
                    "items": [
                        int(hit["id"])
                        for hit in results[start : start + params.page_size]
                    ],
                    "total": len(results),
                    "page": params.page,
                    "page_size": params.page_size,
                    "total_pages": (len(results) + params.page_size - 1)
                    // params.page_size,
                }
            )
