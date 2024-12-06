from typing import Annotated
from fastapi import FastAPI, Query, Request
from .service_api import RemoteSearchService, ServiceSettings, get_fwd_headers
from .catalog import PaginatedList
from .search import SearchRequest, SearchServiceImpl

app = FastAPI()
service = SearchServiceImpl(ServiceSettings())

@app.get(RemoteSearchService.SEARCH)
def search(request: Request, params: Annotated[SearchRequest, Query()]) -> PaginatedList[int]:
    return service.search(get_fwd_headers(request), params)
