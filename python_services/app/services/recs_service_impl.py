import os
import shutil
import time
import chromadb
from collections import deque
from typing import Deque, Dict, List

from fastapi import HTTPException

from ..common.config import ServiceSettings
from ..common.api import GetWineRequest, RecsRequest, Wine


class RecsServiceImpl:
    def __init__(
        self, settings: ServiceSettings, reset: bool = False, catalog_service=None
    ):
        self.recs_demo_failure = settings.recs_demo_failure
        self.catalog_service = catalog_service
        path = os.path.join(settings.data_path, "recs_data")
        if reset and os.path.exists(path):
            shutil.rmtree(path)
        self.chroma_client = chromadb.PersistentClient(path)
        self.collection = self.chroma_client.get_or_create_collection(
            name="my_collection"
        )
        self._init_failure_simulation()

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

    def _init_failure_simulation(self):
        self.query_history: Deque[Dict] = deque()
        self.failure_until: float = 0
        self.WINDOW_SECONDS = 2
        self.QUERY_THRESHOLD = 5
        self.FAILURE_DURATION = 5

    def _check_failure_condition(self, query: str) -> bool:
        current_time = time.time()
        if current_time < self.failure_until:
            raise HTTPException(
                400, "Service temporarily unavailable due to high query volume"
            )
        while (
            self.query_history
            and current_time - self.query_history[0]["timestamp"] > self.WINDOW_SECONDS
        ):
            self.query_history.popleft()

        self.query_history.append({"query": query, "timestamp": current_time})
        unique_queries = len(set(record["query"] for record in self.query_history))

        if unique_queries > self.QUERY_THRESHOLD:
            self.failure_until = current_time + self.FAILURE_DURATION
            raise HTTPException(
                400, "Service temporarily unavailable due to high query volume"
            )

    def get_recommendations_unfiltered(self, params: RecsRequest) -> List[int]:
        q = {}
        q["n_results"] = params.limit
        q["query_texts"] = [params.query]
        results = self.collection.query(**q)
        all_ids = [int(id) for id in results["ids"][0]]
        if self.recs_demo_failure:
            self._check_failure_condition(params.query)
        return all_ids

    def get_recommendations(self, params: RecsRequest) -> List[int]:
        all_ids = self.get_recommendations_unfiltered(params)
        # in a real RAG, we would call into catalog and get more
        # info and iterate. In this case we just want to demonstrate
        # we can call the catalog service and get junction routing
        if len(all_ids) > 0:
            self.catalog_service.get_wine(GetWineRequest(ids=all_ids))

        return all_ids[: params.limit]
