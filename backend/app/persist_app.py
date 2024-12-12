from typing import List, Tuple
from fastapi import FastAPI, Request

from .services.persist import PersistServiceImpl
from .services.service_api import RemotePersistService, SQLRequest, ServiceSettings, get_fwd_headers

app = FastAPI()
service = PersistServiceImpl(ServiceSettings())

@app.post(RemotePersistService.DO_SQL)
def do_sql(request: Request, sql_request: SQLRequest) -> List[Tuple]:
    return service.do_sql(get_fwd_headers(request), sql_request)
