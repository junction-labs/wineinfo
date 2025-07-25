from typing import List, Tuple
import typing
from pydantic import BaseModel


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


class ServiceMethodDef(typing.TypedDict):
    method: str
    path: str
    params: BaseModel | None
    response: BaseModel | List[BaseModel] | None


class GetWineRequest(BaseModel):
    ids: List[int]


class GetAllWinesPaginatedRequest(BaseModel):
    page: int
    page_size: int


CATALOG_SERVICE = {
    "get_wine": ServiceMethodDef(
        method="GET",
        path="/wines/",
        params=GetWineRequest,
        response=List[Wine],
    ),
    "get_all_wines_paginated": ServiceMethodDef(
        method="GET",
        path="/wines/batch/",
        params=GetAllWinesPaginatedRequest,
        response=PaginatedList[Wine],
    ),
}

class SearchRequest(BaseModel):
    query: str
    page: int = 1
    page_size: int = 20
    filters: dict = {}
    sort_by: str | None = None
    sort_reverse: bool = False
    fuzzy: bool = False
    wildcard: bool = False
    numeric_ranges: dict = {}


SEARCH_SERVICE = {
    "search": ServiceMethodDef(
        method="GET",
        path="/search/",
        params=SearchRequest,
        response=PaginatedList[int],
    )
}
class RecsRequest(BaseModel):
    query: str
    limit: int = 20


RECS_SERVICE = {
    "semantic_search": ServiceMethodDef(
        method="GET",
        path="/recommendations/",
        params=RecsRequest,
        response=List[int],
    )
}

class SQLRequest(BaseModel):
    query: str
    params: list[str | int] | None


PERSIST_SERVICE = {
    "do_sql": ServiceMethodDef(
        method="POST", path="/do_sql/", params=SQLRequest, response=List[Tuple]
    )
}

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class SommelierChatRequest(BaseModel):
    message: str
    conversation_history: List[ChatMessage] = []
    cellar_wine_ids: List[int] = []

class SommelierChatResponse(BaseModel):
    response: str
    recommended_wines: List[Wine]

SOMMELIER_SERVICE = {
    "chat": ServiceMethodDef(
        method="POST", path="/chat/", params=SommelierChatRequest, response=SommelierChatResponse
    )
}
