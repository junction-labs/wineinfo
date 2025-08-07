from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from .common.http_client import HttpClient
from .common.config import ServiceSettings
from .common.api_stubs import PersistService, EmbeddingsService, SearchService
from .common.baggage import create_baggage_middleware, baggage_mgr
from .services.sommelier_service_impl import SommelierServiceImpl
from .common.api import SommelierChatRequest
import json
import asyncio
import queue
from typing import AsyncGenerator
import traceback

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
impl = SommelierServiceImpl(
    persist_service, 
    search_service, 
    embeddings_service,
    openai_api_key=settings.openai_api_key, 
    openai_model=settings.openai_model,
    openai_temperature=settings.openai_temperature,
    openai_max_tokens=settings.openai_max_tokens,
    openai_tool_choice=settings.openai_tool_choice,
    openai_base_url=settings.openai_base_url
)

app = FastAPI()
app.middleware("http")(create_baggage_middleware())


@app.post("/chat/")
async def chat(request: SommelierChatRequest) -> StreamingResponse:
    user_id = baggage_mgr.get_user_id()
    conversation_history = [{"role": msg.role, "content": msg.content} for msg in request.conversation_history]
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        try:
            yield f"data: {json.dumps({'type': 'status', 'message': 'Starting chat...'})}\n\n"

            state_queue = queue.Queue()
            chat_completed = asyncio.Event()
            
            def state_callback(callback_type: str, message: str):
                state_queue.put((callback_type, message))
            
            async def run_chat():
                try:
                    return await asyncio.to_thread(
                        impl.chat,
                        request.message,
                        conversation_history,
                        user_id,
                        state_callback
                    )
                except Exception:
                    print(f"ERROR: Full traceback: {traceback.format_exc()}")
                    raise
                finally:
                    chat_completed.set()
            
            chat_task = asyncio.create_task(run_chat())
            
            while not chat_completed.is_set() or not state_queue.empty():
                try:
                    callback_type, message = state_queue.get_nowait()
                    yield f"data: {json.dumps({'type': callback_type, 'message': message})}\n\n"
                except queue.Empty:
                    if chat_completed.is_set():
                        break
                    await asyncio.sleep(0.1)
            
            result = await chat_task

            # Convert Wine objects to dictionaries for JSON serialization
            recommended_wines_dict = [wine.model_dump() for wine in result['recommended_wines']]
            yield f"data: {json.dumps({'type': 'complete', 'response': result['response'], 'recommended_wines': recommended_wines_dict})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
