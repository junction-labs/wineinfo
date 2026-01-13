from typing import List
from fastapi import Depends, FastAPI
from pydantic import BaseModel

from .common.config import ServiceSettings
from .common.baggage import create_baggage_middleware
from .services.catalog_service_impl import CatalogServiceImpl
from .common.http_client import HttpClient
from .common.api_stubs import PersistService
from .common.api import GetWinesByUserIdRequest


class CatalogSearchRequest(BaseModel):
    """Unified search request supporting text, semantic, and hybrid search"""
    query: str = ""
    mode: str = "hybrid"  # "text", "semantic", or "hybrid" (default: hybrid)
    scope: str = "catalog"  # "cellar", "catalog", or "all"
    user_id: int | None = None
    filters: dict = {}
    numeric_ranges: dict = {}
    sort_by: str | None = None
    sort_reverse: bool = False
    limit: int = 20


settings = ServiceSettings()
impl = CatalogServiceImpl(ServiceSettings(), False)
persist_service = PersistService(HttpClient(settings.persist_service, settings.use_junction))
app = FastAPI()
app.middleware("http")(create_baggage_middleware())


@app.get("/search/")
def search(params: CatalogSearchRequest = Depends()) -> List[int]:
    """
    Unified search endpoint

    By default uses HYBRID mode (combining BM25 + vector search) for best results.

    Modes (optional):
    - "hybrid" (default): Combines BM25 and vector search - best all-around results
    - "text": BM25 full-text search only - fastest, keyword-based
    - "semantic": Vector similarity only - best for conceptual/descriptive queries

    Scope (optional):
    - "catalog" (default): Search only wines user doesn't own
    - "cellar": Search only wines user owns (requires user_id)
    - "all": Search everything

    All modes support filters, numeric_ranges, and pagination.
    """
    # Get owned wine IDs if user_id provided and scope requires it
    owned_wine_ids = []
    if params.user_id and params.scope in ["cellar", "catalog"]:
        try:
            cellar_wines = persist_service.get_wines_by_user_id(
                GetWinesByUserIdRequest(user_id=params.user_id)
            )
            owned_wine_ids = [wine.id for wine in cellar_wines]
        except Exception as e:
            print(f"Warning: Could not fetch user cellar: {e}")

    return impl.search(
        query=params.query,
        mode=params.mode,
        scope=params.scope,
        owned_wine_ids=owned_wine_ids,
        filters=params.filters,
        numeric_ranges=params.numeric_ranges,
        sort_by=params.sort_by,
        sort_reverse=params.sort_reverse,
        limit=params.limit,
    )
