from typing import List
from fastapi import Depends, FastAPI

from recs import RECS_DIR, RecommendationRequest, RecommendationServiceImpl


app = FastAPI()
service = RecommendationServiceImpl(RECS_DIR)

@app.get("/recommendations/")
def search(request: RecommendationRequest = Depends()) -> List[int]:
    return service.get_recommendations(request)
