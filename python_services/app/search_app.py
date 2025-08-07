from typing import Annotated
from fastapi import FastAPI
import json
from .common.baggage import create_baggage_middleware
from .common.config import ServiceSettings
from .common.api import SearchRequest, PaginatedList, SEARCH_SERVICE
from .services.search_service_impl import SearchServiceImpl

impl = SearchServiceImpl(ServiceSettings())
app = FastAPI()
app.middleware("http")(create_baggage_middleware())


@app.post(SEARCH_SERVICE["catalog_search"]["path"])
def search(
    params: SearchRequest,
) -> PaginatedList[int]:
    return impl.catalog_search(params)
