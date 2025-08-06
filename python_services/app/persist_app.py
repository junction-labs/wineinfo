from typing import List, Tuple, Annotated
from fastapi import FastAPI, Query
from .common.config import ServiceSettings
from .common.api import SQLRequest, PERSIST_SERVICE, Wine, PaginatedList
from .common.baggage import create_baggage_middleware
from .services.persist_service_impl import PersistServiceImpl

impl = PersistServiceImpl(ServiceSettings())
app = FastAPI()
app.middleware("http")(create_baggage_middleware())

@app.post(PERSIST_SERVICE["do_sql"]["path"])
def do_sql(
    params: SQLRequest
) -> List[Tuple]:
    return impl.do_sql(params)

@app.get(PERSIST_SERVICE["get_wine"]["path"])
async def get_wine(
    ids: Annotated[list[int] | None, Query()],
) -> List[Wine]:
    return impl.get_wine(ids)

@app.get(PERSIST_SERVICE["get_all_wines_paginated"]["path"])
async def get_all_wines_paginated(
    page: int, page_size: int
) -> PaginatedList[Wine]:
    return impl.get_all_wines_paginated(page, page_size)

@app.get(PERSIST_SERVICE["get_wines_by_user_id"]["path"])
async def get_wines_by_user_id(
    user_id: int
) -> List[Wine]:
    return impl.get_wines_by_user_id(user_id)
