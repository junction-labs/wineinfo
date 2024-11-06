from typing import Annotated
from fastapi import FastAPI, Query
from .service_api import RemoteSearchService
from .catalog import PaginatedList
from .search import SearchRequest, SearchServiceImpl

app = FastAPI()
service = SearchServiceImpl()


@app.get(RemoteSearchService.SEARCH)
def search(request: Annotated[SearchRequest, Query()]) -> PaginatedList[int]:
    return service.search(request)
