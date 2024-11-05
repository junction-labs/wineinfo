import os
import shutil
import chromadb
from typing import List
from .service_api import RecommendationRequest, RecommendationService
from .catalog import Wine



class RecommendationServiceImpl(RecommendationService):
    RECS_DIR = "backend/data/gen/recs_data"

    def __init__(self, reset: bool = False, path: str = RECS_DIR):
        if path:
            if reset and os.path.exists(path):
                shutil.rmtree(path)
            self.chroma_client = chromadb.PersistentClient(path)
        else:
            self.chroma_client = chromadb.Client()
        self.collection = self.chroma_client.get_or_create_collection(name="my_collection")

    def open_index(self):
        self.batch_ids = []
        self.batch_documents = []

    def add_wine(self, wine: Wine):
        self.batch_ids.append(str(wine.id))
        self.batch_documents.append(wine.model_dump_json())
        if len(self.batch_ids) > 1000:
            self.collection.add(ids=self.batch_ids, documents=self.batch_documents)
            self.batch_ids = []
            self.batch_documents = []

    def build_index(self):
        if len(self.batch_ids) > 0:
            self.collection.add(ids=self.batch_ids, documents=self.batch_documents)
        self.batch_ids = []
        self.batch_documents = []

    def get_recommendations(self, request: RecommendationRequest) -> List[int]:
        q = {}
        q["n_results"] =request.limit +len(request.wine_ids) + len(request.exclude_ids)
        q["query_texts"] =[request.query]
        if len(request.wine_ids) > 0:
            q["query_embeddings"] = [ self.collection.get(ids=[str(x) for x in request.wine_ids], include=["embeddings"])["embeddings"] ]
        
        results = self.collection.query(**q)
        all_ids = [int(id) for id in results["ids"][0]]
        return [id for id in all_ids if id not in request.exclude_ids and id not in request.wine_ids][:request.limit]
