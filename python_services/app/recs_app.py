import logging
from typing import List
from fastapi import Depends, FastAPI
from .common.http_client import HttpClient
from .common.config import ServiceSettings
from .common.api import RecsRequest, RECS_SERVICE
from .common.api_stubs import CatalogService
from .common.baggage import create_baggage_middleware
from .services.recs_service_impl import RecsServiceImpl


settings = ServiceSettings()
catalog_service = CatalogService(
    HttpClient(settings.catalog_service, settings.use_junction)
)
impl = RecsServiceImpl(ServiceSettings(), False, catalog_service)
logger = logging.getLogger('uvicorn.error')


# the LLM may not be downloaded until we do this, so do it now
logger.info("Downloading LLM")
impl.get_recommendations_unfiltered(RecsRequest(query="dummy", limit=1))
logger.info("Call done")
app = FastAPI()
app.middleware("http")(create_baggage_middleware())


@app.get(RECS_SERVICE["get_recommendations"]["path"])
def get_recommendations(
    params: RecsRequest = Depends()
) -> List[int]:
    return impl.get_recommendations(params)
