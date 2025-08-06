from fastapi import FastAPI
from .common.http_client import HttpClient
from .common.config import ServiceSettings
from .common.api_stubs import PersistService, EmbeddingsService, SearchService
from .common.baggage import create_baggage_middleware, baggage_mgr
from .services.sommelier_service_impl import SommelierServiceImpl
from .common.api import SommelierChatRequest, SommelierChatResponse, Wine



settings = ServiceSettings()
search_service = SearchService(
    HttpClient(settings.search_service, settings.use_junction)
)
embeddings_service = EmbeddingsService(
    HttpClient(settings.embeddings_service, settings.use_junction)
)
persist_service = PersistService(
    HttpClient(settings.persist_service, settings.use_junction)
)
impl = SommelierServiceImpl(persist_service, search_service, embeddings_service)

app = FastAPI()
app.middleware("http")(create_baggage_middleware())


@app.post("/chat/", response_model=SommelierChatResponse)
async def sommelier_chat(request: SommelierChatRequest) -> SommelierChatResponse:
    user_id = baggage_mgr.get_user_id()
    conversation_history = [{"role": msg.role, "content": msg.content} for msg in request.conversation_history]
    
    result = impl.chat(
        message=request.message,
        conversation_history=conversation_history,
        user_id=user_id
    )
    wine_objects = [Wine(**wine) for wine in result["recommended_wines"]]
    return SommelierChatResponse(
        response=result["response"],
        recommended_wines=wine_objects
    )
