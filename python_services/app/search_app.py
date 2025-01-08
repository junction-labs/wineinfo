from typing import Annotated
from fastapi import FastAPI, Query
from .common.baggage import create_baggage_middleware
from .common.config import ServiceSettings
from .common.api import SearchRequest, PaginatedList, SEARCH_SERVICE
from .services.search_service_impl import SearchServiceImpl


# only reason we do this is so we can use implementation
# class in the data gen binary
impl = SearchServiceImpl(ServiceSettings())
app = FastAPI()
app.middleware("http")(create_baggage_middleware())


@app.get(SEARCH_SERVICE["search"]["path"])
def search(
    params: Annotated[SearchRequest, Query()],
) -> PaginatedList[int]:
    return impl.search(params)