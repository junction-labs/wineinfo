import os
import shutil
import time
import chromadb
from typing import Dict, List
from .service_api import RecsRequest, RecsService, ServiceSettings
from .catalog import Wine

class LRUCache:
    class Node:
        def __init__(self, key, value):
            self.key = key
            self.value = value
            self.prev = None
            self.next = None

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = {}  # key -> Node
        self.head = self.Node(0, 0)
        self.tail = self.Node(0, 0)
        self.head.next = self.tail
        self.tail.prev = self.head

    def _remove(self, node):
        node.prev.next = node.next
        node.next.prev = node.prev

    def _add(self, node):
        node.prev = self.head
        node.next = self.head.next
        self.head.next.prev = node
        self.head.next = node

    def get(self, key):
        if key in self.cache:
            node = self.cache[key]
            # Move to front (most recently used)
            self._remove(node)
            self._add(node)
            return node.value
        return None

    def put(self, key, value):
        if key in self.cache:
            self._remove(self.cache[key])
        
        node = self.Node(key, value)
        self.cache[key] = node
        self._add(node)
        
        if len(self.cache) > self.capacity:
            lru_node = self.tail.prev
            self._remove(lru_node)
            del self.cache[lru_node.key]

    def peek_oldest(self):
        """
        Returns (key, value) tuple of the least recently used item
        without modifying its position in the cache.
        Returns None if cache is empty.
        """
        if not self.cache:
            return None
        oldest = self.tail.prev
        if oldest == self.head:
            return None
        return (oldest.key, oldest.value)

    def __len__(self):
        return len(self.cache)

    def clear(self):
        self.cache.clear()
        self.head.next = self.tail
        self.tail.prev = self.head


class RecsServiceImpl(RecsService):

    def __init__(self, settings: ServiceSettings, reset: bool = False):
        path = os.path.join(settings.data_path, "recs_data")        
        if reset and os.path.exists(path):
            shutil.rmtree(path)
        self.chroma_client = chromadb.PersistentClient(path)
        self.collection = self.chroma_client.get_or_create_collection(
            name="my_collection"
        )
        self.cache = LRUCache(10)

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

    def get_recommendations_uncached(self, request: RecsRequest) -> List[int]:
        q = {}
        q["n_results"] = ( request.limit )
        q["query_texts"] = [request.query]
        results = self.collection.query(**q)
        all_ids = [int(id) for id in results["ids"][0]]
        return all_ids[: request.limit]


    def get_recommendations(self, headers: Dict, request: RecsRequest) -> List[int]:
        username = headers.get("x-username", "")
        key = f"{username}_{request.query}"
        cached = self.cache.get(key)
        if cached:
            return cached
        result = self.get_recommendations_uncached(request)
        self.cache.put(key, result)
        return result
    
