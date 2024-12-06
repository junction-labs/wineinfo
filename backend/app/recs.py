import os
import shutil
import chromadb
from typing import Dict, List
from .service_api import RecsRequest, RecsService, ServiceSettings
from .catalog import Wine

class RecsServiceImpl(RecsService):

    def __init__(self, settings: ServiceSettings, reset: bool = False):
        path = os.path.join(settings.data_path, "recs_data")        
        if reset and os.path.exists(path):
            shutil.rmtree(path)
        self.chroma_client = chromadb.PersistentClient(path)
        self.collection = self.chroma_client.get_or_create_collection(
            name="my_collection"
        )

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

    def get_recommendations(self, headers: Dict, request: RecsRequest) -> List[int]:
        q = {}
        q["n_results"] = ( request.limit )
        q["query_texts"] = [request.query]
        results = self.collection.query(**q)
        all_ids = [int(id) for id in results["ids"][0]]
        return all_ids[: request.limit]
