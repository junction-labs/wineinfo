from typing import Annotated
from fastapi import FastAPI, Query

from catalog import PaginatedList
from search import SEARCH_DIR, SearchRequest, SearchServiceImpl

app = FastAPI()
service = SearchServiceImpl(SEARCH_DIR)

@app.get("/search/")
def search(request: Annotated[SearchRequest, Query()]) -> PaginatedList[int]:
    return service.search(request)
