from typing import List
from fastapi import FastAPI
from pydantic import BaseModel
from .common.http_client import HttpClient
from .common.config import ServiceSettings
from .common.api_stubs import CatalogService, PersistService, RecsService, SearchService
from .common.baggage import create_baggage_middleware
from .services.sommelier_service_impl import SommelierServiceImpl
from .common.api import Wine



settings = ServiceSettings()
catalog_service = CatalogService(
    HttpClient(settings.catalog_service, settings.use_junction)
)
search_service = SearchService(
    HttpClient(settings.search_service, settings.use_junction)
)
recs_service = RecsService(
    HttpClient(settings.recs_service, settings.use_junction)
)
persist_service = PersistService(
    HttpClient(settings.persist_service, settings.use_junction)
)
impl = SommelierServiceImpl(catalog_service, search_service, recs_service, persist_service)

app = FastAPI()
app.middleware("http")(create_baggage_middleware())


@app.post("/chat/", response_model=SommelierChatResponse)
async def sommelier_chat(request: SommelierChatRequest) -> SommelierChatResponse:
    conversation_history = [{"role": msg.role, "content": msg.content} for msg in request.conversation_history]
    
    result = impl.chat(
        message=request.message,
        conversation_history=conversation_history,
        cellar_wine_ids=request.cellar_wine_ids
    )
    wine_objects = [Wine(**wine) for wine in result["recommended_wines"]]
    return SommelierChatResponse(
        response=result["response"],
        recommended_wines=wine_objects
    )
