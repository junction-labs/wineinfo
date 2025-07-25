from typing import List
from fastapi import Depends, FastAPI
from .common.config import ServiceSettings
from .common.api import RecsRequest, RECS_SERVICE
from .common.baggage import create_baggage_middleware
from .services.recs_service_impl import RecsServiceImpl

settings = ServiceSettings()
impl = RecsServiceImpl(ServiceSettings(), False)
# the LLM may not be downloaded until we do this, so do it now
impl.semantic_search(RecsRequest(query="dummy", limit=1))
app = FastAPI()
app.middleware("http")(create_baggage_middleware())


@app.get(RECS_SERVICE["semantic_search"]["path"])
def semantic_search(params: RecsRequest = Depends()) -> List[int]:
    return impl.semantic_search(params)
