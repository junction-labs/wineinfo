from typing import List
from fastapi import Depends, FastAPI, Request
from .service_api import RemoteRecsService, ServiceSettings, get_fwd_headers
from .recs import RecsRequest, RecsServiceImpl


app = FastAPI()
service = RecsServiceImpl(ServiceSettings())


@app.get(RemoteRecsService.GET_RECOMMENDATIONS)
def get_recommendations(request: Request, params: RecsRequest = Depends()) -> List[int]:
    return service.get_recommendations(get_fwd_headers(request), params)
