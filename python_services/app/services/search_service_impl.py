import os
import random
import shutil
import time
from whoosh.fields import Schema, TEXT, ID, NUMERIC, KEYWORD
from whoosh.qparser import MultifieldParser, FuzzyTermPlugin, WildcardPlugin
from whoosh.filedb.filestore import FileStorage
from whoosh.analysis import StandardAnalyzer
from whoosh.query import *
from ..common.config import ServiceSettings
from ..common.api import (
    SearchRequest, PaginatedList, Wine
)

class SearchServiceImpl:
    def __init__(self, settings: ServiceSettings, reset: bool = False):
        schema = Schema(
            id=ID(stored=True),
            title=TEXT(stored=True, analyzer=StandardAnalyzer()),
            description=TEXT(stored=True, analyzer=StandardAnalyzer()),
            variety=KEYWORD(stored=True, commas=True),
            winery=KEYWORD(stored=True, commas=True),
            country=KEYWORD(stored=True, commas=True),
            province=KEYWORD(stored=True, commas=True),
            region_1=KEYWORD(stored=True, commas=True),
            region_2=KEYWORD(stored=True, commas=True),
            points=NUMERIC(stored=True, numtype=int),
            price=NUMERIC(stored=True, numtype=float),
            designation=TEXT(stored=True)
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
        try:
            points_value = int(wine.points) if wine.points and wine.points.strip() else 80
        except (ValueError, TypeError):
            points_value = 80
            
        try:
            price_value = float(wine.price) if wine.price and wine.price.strip() else 20.0
        except (ValueError, TypeError):
            price_value = 20.0
        points_value = max(0, points_value)
        price_value = max(0.0, price_value)
            
        wine_id = str(wine.id) if wine.id is not None else "0"
        doc = {
            'id': wine_id,
            'title': wine.title or "",
            'description': wine.description or "",
            'variety': wine.variety or "",
            'winery': wine.winery or "",
            'country': wine.country or "",
            'province': wine.province or "",
            'region_1': wine.region_1 or "",
            'region_2': wine.region_2 or "",
            'points': points_value,
            'price': price_value,
            'designation': wine.designation or ""
        }
        
        self.writer.add_document(**doc)

    def build_index(self):
        self.writer.commit()
        del self.writer


    def search(self, params: SearchRequest) -> PaginatedList[int]:
        if self.search_demo_latency:
            if random.random() < 0.5:
                time.sleep(10)

        with self.index.searcher() as searcher:
            if params.query.strip():
                parser = MultifieldParser([
                    "title", "description", "variety", "winery", 
                    "country", "province", "region_1", "region_2"
                ], self.index.schema)
                
                if params.fuzzy:
                    parser.add_plugin(FuzzyTermPlugin())
                if params.wildcard:
                    parser.add_plugin(WildcardPlugin())
                
                base_query = parser.parse(params.query)
            else:
                base_query = Every()

            filters = []
            for field, value in params.filters.items():
                if isinstance(value, list):
                    filters.append(Or([Term(field, v) for v in value]))
                else:
                    filters.append(Term(field, value))

            for field, range_dict in params.numeric_ranges.items():
                if 'min' in range_dict or 'max' in range_dict:
                    filters.append(NumericRange(field, 
                                            range_dict.get('min'), 
                                            range_dict.get('max')))

            query = base_query
            if filters:
                query = And([base_query] + filters)

            start = (params.page - 1) * params.page_size
            search_kwargs = {
                'limit': start + params.page_size,
            }
            if params.sort_by:
                search_kwargs['sortedby'] = params.sort_by
                search_kwargs['reverse'] = params.sort_reverse

            results = searcher.search(query, **search_kwargs)
            return PaginatedList[int].model_validate({
                "items": [int(hit["id"]) for hit in results[start : start + params.page_size]],
                "total": len(results),
                "page": params.page,
                "page_size": params.page_size,
                "total_pages": (len(results) + params.page_size - 1),
            })        
