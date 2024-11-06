from typing import List
from fastapi import Depends, FastAPI
from .service_api import RemoteRecommendationService
from .recs import RecommendationRequest, RecommendationServiceImpl


app = FastAPI()
service = RecommendationServiceImpl()


@app.get(RemoteRecommendationService.GET_RECOMMENDATIONS)
def get_recommendations(request: RecommendationRequest = Depends()) -> List[int]:
    return service.get_recommendations(request)
