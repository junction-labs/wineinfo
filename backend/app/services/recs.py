import os
import shutil
import time
import chromadb
from collections import deque
from typing import Deque, Dict, List
from .service_api import RecsRequest, RecsService, ServiceSettings
from .catalog import Wine


class RecsServiceImpl(RecsService):

    def __init__(self, settings: ServiceSettings, reset: bool = False):
        self.recs_demo_failure = settings.recs_demo_failure
        path = os.path.join(settings.data_path, "recs_data")        
        if reset and os.path.exists(path):
            shutil.rmtree(path)
        self.chroma_client = chromadb.PersistentClient(path)
        self.collection = self.chroma_client.get_or_create_collection(
            name="my_collection"
        )
        # it seems like chroma does not load any data until the first query is
        # made, causing unacceptable latency for it. Lets do a single call on
        # initialization to avoid it.
        self.collection.query(n_results=1, query_texts=["dummy"])

        # Initialize failure simulation components
        self.query_history: Deque[Dict] = deque()
        self.failure_until: float = 0
        self.WINDOW_SECONDS = 2
        self.QUERY_THRESHOLD = 5
        self.FAILURE_DURATION = 5    
   
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

    def _check_failure_condition(self, query: str) -> bool:
        current_time = time.time()
        if current_time < self.failure_until:
            raise RuntimeError("Service temporarily unavailable due to high query volume")
        while (self.query_history and 
               current_time - self.query_history[0]["timestamp"] > self.WINDOW_SECONDS):
            self.query_history.popleft()
        self.query_history.append({"query":query, "timestamp":current_time })
        unique_queries = len(set(record["query"] for record in self.query_history))

        if unique_queries > self.QUERY_THRESHOLD:
            self.failure_until = current_time + self.FAILURE_DURATION
            raise RuntimeError("Service temporarily unavailable due to high query volume")


    def get_recommendations(self, _: Dict, request: RecsRequest) -> List[int]:
        q = {}
        q["n_results"] = ( request.limit )
        q["query_texts"] = [request.query]
        results = self.collection.query(**q)
        all_ids = [int(id) for id in results["ids"][0]]
        if self.recs_demo_failure:
            self._check_failure_condition(request.query)
        return all_ids[: request.limit]
