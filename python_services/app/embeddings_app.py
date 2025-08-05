from typing import List
from fastapi import Depends, FastAPI
from .common.config import ServiceSettings
from .common.api import EmbeddingsSearchRequest, EMBEDDINGS_SERVICE
from .common.baggage import create_baggage_middleware
from .services.embeddings_service_impl import EmbeddingsServiceImpl

settings = ServiceSettings()
impl = EmbeddingsServiceImpl(ServiceSettings(), False)
# the LLM may not be downloaded until we do this, so do it now
impl.catalog_search(EmbeddingsSearchRequest(query="dummy", limit=1))
app = FastAPI()
app.middleware("http")(create_baggage_middleware())


@app.get(EMBEDDINGS_SERVICE["catalog_search"]["path"])
def catalog_search(params: EmbeddingsSearchRequest = Depends()) -> List[int]:
    return impl.catalog_search(params)
