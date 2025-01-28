from typing import List, Tuple
from fastapi import FastAPI
from .common.config import ServiceSettings
from .common.api import SQLRequest, PERSIST_SERVICE
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
