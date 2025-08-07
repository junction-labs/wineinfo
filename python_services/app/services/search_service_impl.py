import os
import random
import shutil
import time
import logging
from whoosh.fields import Schema, TEXT, ID, NUMERIC, KEYWORD
from whoosh.qparser import MultifieldParser, FuzzyTermPlugin, WildcardPlugin
from whoosh.filedb.filestore import FileStorage
from whoosh.analysis import StandardAnalyzer
from whoosh.query import *
from ..common.config import ServiceSettings
from ..common.api import (
    SearchRequest, PaginatedList, Wine
)

# Set up logging
logger = logging.getLogger(__name__)

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


    def catalog_search(self, params: SearchRequest) -> PaginatedList[int]:
        logger.info(f"Starting search with query: '{params.query}', page: {params.page}, page_size: {params.page_size}")
        logger.info(f"Search parameters - fuzzy: {params.fuzzy}, wildcard: {params.wildcard}")
        logger.info(f"Filters: {params.filters}")
        logger.info(f"Numeric ranges: {params.numeric_ranges}")
        logger.info(f"Sort by: {params.sort_by}, reverse: {params.sort_reverse}")
        
        if self.search_demo_latency:
            if random.random() < 0.5:
                logger.warning("Adding demo latency (10s sleep)")
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
                logger.info("No query provided, using Every() query")
                base_query = Every()

            filters = []
            for field, value in params.filters.items():
                if isinstance(value, list):
                    logger.info(f"Adding OR filter for field '{field}' with values: {value}")
                    filters.append(Or([Term(field, v) for v in value]))
                else:
                    logger.info(f"Adding term filter for field '{field}' with value: {value}")
                    filters.append(Term(field, value))

            for field, range_dict in params.numeric_ranges.items():
                if 'min' in range_dict or 'max' in range_dict:
                    min_val = range_dict.get('min')
                    max_val = range_dict.get('max')
                    logger.info(f"Adding numeric range filter for field '{field}': min={min_val}, max={max_val}")
                    filters.append(NumericRange(field, min_val, max_val))

            query = base_query
            if filters:
                logger.info(f"Combining base query with {len(filters)} filters")
                query = And([base_query] + filters)
            else:
                logger.info("No filters applied, using base query only")

            start = (params.page - 1) * params.page_size
            search_kwargs = {
                'limit': start + params.page_size,
            }
            if params.sort_by:
                logger.info(f"Sorting by '{params.sort_by}' (reverse: {params.sort_reverse})")
                search_kwargs['sortedby'] = params.sort_by
                search_kwargs['reverse'] = params.sort_reverse

            results = searcher.search(query, **search_kwargs)
            total_results = len(results)
            page_results = [int(hit["id"]) for hit in results[start : start + params.page_size]]
            total_pages = (total_results + params.page_size - 1) // params.page_size
            
            logger.info(f"Search completed - Total results: {total_results}, Page results: {len(page_results)}")
            
            return PaginatedList[int].model_validate({
                "items": page_results,
                "total": total_results,
                "page": params.page,
                "page_size": params.page_size,
                "total_pages": total_pages,
            })        
