from typing import Dict, List, Tuple
from pydantic import BaseModel
from pydantic import TypeAdapter
from .http_caller import HttpCaller

class Wine(BaseModel):
    id: int | None
    title: str
    country: str
    description: str
    designation: str
    points: str
    price: str
    province: str
    region_1: str
    region_2: str
    taster_name: str
    taster_twitter_handle: str
    variety: str
    winery: str


class PaginatedList[T](BaseModel):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    class Config:
        generic_types_only = True


# GET, params = list[int], response = List[Wine]
CAT_SERVICE__GET_WINE = "/wines/"

# GET, params = none, int, response = PaginatedList[Wine]
CAT_SERVICE__GET_ALL_WINES_PAGINATED = "/wines/batch/"

class SearchRequest(BaseModel):
    query: str
    page: int = 1
    page_size: int = 20

# GET, params = SearchRequest, response = PaginatedList[int]
SEARCH_SERVICE__SEARCH = "/search/"

class RecsRequest(BaseModel):
    query: str
    limit: int = 20

# GET, params = RecsRequest, response = PaginatedList[int]
RECS_SERVICE__GET_RECOMMENDATIONS = "/recommendations/"

class SQLRequest(BaseModel):
    query: str
    params: list[str | int] | None

# POST, body = SQLRequest, response = dict
PERSIST_SERVICE__DO_SQL = "/do_sql/"

#
# This is the only one called from python at the moment
#
class RemotePersistService:
    def __init__(self, caller: HttpCaller):
        self.caller = caller

    def do_sql(self, headers: Dict, sql_request: SQLRequest) -> List[Tuple]:
        return TypeAdapter(List[Tuple]).validate_python(
            self.caller.post(headers, PERSIST_SERVICE__DO_SQL, sql_request)
        )
