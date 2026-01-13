import os
import random
import time
import turbopuffer as tpuf
from typing import List, Tuple, Dict

from ..common.config import ServiceSettings
from ..common.api import Wine


class CatalogServiceImpl:
    """Unified search service using Turbopuffer for both full-text and vector search"""

    def __init__(self, settings: ServiceSettings, reset: bool = False):
        self.settings = settings
        self.search_demo_latency = settings.search_demo_latency

        # Initialize embedding provider
        self.embedding_provider = settings.embedding_provider
        self.embedding_model_name = settings.embedding_model

        if self.embedding_provider == "local":
            # Use sentence-transformers for local embeddings
            from sentence_transformers import SentenceTransformer
            print(f"Loading local embedding model: {self.embedding_model_name}")
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
            print(f"Model loaded successfully (dimension: {self.embedding_dim})")
        elif self.embedding_provider == "openai":
            # Use OpenAI API for embeddings
            from openai import OpenAI
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY must be set when using embedding_provider='openai'")
            self.openai_client = OpenAI(api_key=settings.openai_api_key)
            self.embedding_dim = 1536  # text-embedding-3-small dimension
            print(f"Using OpenAI embeddings: {self.embedding_model_name}")
        else:
            raise ValueError(f"Unknown embedding_provider: {self.embedding_provider}")

        # Initialize turbopuffer client - single namespace for everything
        self.client = tpuf.Turbopuffer(
            api_key=settings.turbopuffer_api_key,
            region=settings.turbopuffer_region,
        )
        self.namespace_name = f"{settings.turbopuffer_namespace}-catalog"
        self.ns = self.client.namespace(self.namespace_name)

        # Verify connection by checking namespace exists/is accessible
        try:
            # Try a simple query to verify connection works
            test_result = self.ns.query(top_k=1)
            print(f"✓ Connected to Turbopuffer namespace: {self.namespace_name}")
        except Exception as e:
            # This is expected if namespace doesn't exist yet (first time setup)
            if "was not found" in str(e):
                print(f"ℹ️  Turbopuffer namespace '{self.namespace_name}' not found - will be created on first write")
            else:
                print(f"⚠️  Warning: Could not connect to Turbopuffer: {e}")
                print(f"   Check your TURBOPUFFER_API_KEY and region settings")

        # If reset, delete all existing vectors to allow dimension changes
        if reset:
            try:
                print(f"Reset mode: deleting all vectors in namespace '{self.namespace_name}'")
                self.ns.delete_all()
                print(f"✓ Namespace cleared successfully")
            except Exception as e:
                print(f"Note: Could not clear namespace (may not exist yet): {e}")

        self.batch_rows = []

    def _create_embedding(self, text: str) -> List[float]:
        """Create an embedding vector for the given text"""
        try:
            if self.embedding_provider == "local":
                # Use sentence-transformers
                embedding = self.embedding_model.encode(text, convert_to_numpy=True)
                return embedding.tolist()
            elif self.embedding_provider == "openai":
                # Use OpenAI API
                response = self.openai_client.embeddings.create(
                    model=self.embedding_model_name,
                    input=text
                )
                return response.data[0].embedding
        except Exception as e:
            print(f"Error creating embedding: {e}")
            # Fallback to random vectors
            import random
            return [random.random() for _ in range(self.embedding_dim)]

    def open_index(self):
        """Prepare for batch writing"""
        self.batch_rows = []

    def add_wine(self, wine: Wine):
        """Add a wine to the batch for indexing with both full-text and vector"""
        try:
            points_value = int(wine.points) if wine.points and wine.points.strip() else 80
        except (ValueError, TypeError):
            points_value = 80

        try:
            price_value = float(wine.price) if wine.price and wine.price.strip() else 20.0
        except (ValueError, TypeError):
            price_value = 20.0

        points_value = max(0, points_value)
        price_value = max(0.0, price_value)
        wine_id = int(wine.id) if wine.id is not None else 0

        # Create a combined text field for full-text search
        searchable_text = " ".join(filter(None, [
            wine.title or "",
            wine.description or "",
            wine.variety or "",
            wine.winery or "",
            wine.country or "",
            wine.province or "",
            wine.region_1 or "",
            wine.region_2 or "",
            wine.designation or ""
        ]))

        # Create text for embedding (richer semantic content)
        semantic_text = wine.model_dump_json()

        # Create embedding vector
        vector = self._create_embedding(semantic_text)

        row = {
            'id': wine_id,
            'vector': vector,
            'text': searchable_text,  # For BM25 full-text search
            'title': wine.title or "",
            'description': wine.description or "",
            'variety': wine.variety or "",
            'winery': wine.winery or "",
            'country': wine.country or "",
            'province': wine.province or "",
            'region_1': wine.region_1 or "",
            'region_2': wine.region_2 or "",
            'points': points_value,
            'price': price_value,
            'designation': wine.designation or ""
        }

        self.batch_rows.append(row)

        # Write in batches of 1000 for better performance
        if len(self.batch_rows) >= 1000:
            self._write_batch()

    def _write_batch(self):
        """Write the current batch to turbopuffer"""
        if not self.batch_rows:
            return

        print(f"Writing batch of {len(self.batch_rows)} wines to turbopuffer catalog")
        self.ns.write(
            upsert_rows=self.batch_rows,
            distance_metric='cosine_distance',
            schema={
                "text": {
                    "type": "string",
                    "full_text_search": True,  # Enable BM25
                    "filterable": False,  # Only used for search, not filtering (50% discount)
                },
                "title": {"type": "string", "filterable": False},  # Display only (50% discount)
                "description": {"type": "string", "filterable": False},  # Display only (50% discount)
                "designation": {"type": "string", "filterable": False},  # Display only (50% discount)
                "variety": {"type": "string"},  # Filterable: users filter by grape type
                "winery": {"type": "string"},  # Filterable: users may filter by producer
                "country": {"type": "string"},  # Filterable: geographic filtering
                "province": {"type": "string"},  # Filterable: geographic filtering
                "region_1": {"type": "string"},  # Filterable: geographic filtering
                "region_2": {"type": "string"},  # Filterable: geographic filtering
                "points": {"type": "int"},  # Filterable: rating range queries
                "price": {"type": "float"},  # Filterable: price range queries
            }
        )
        self.batch_rows = []

    def build_index(self):
        """Commit any remaining wines in the batch"""
        if self.batch_rows:
            self._write_batch()
        print("Catalog index build complete")

    def _merge_hybrid_results(self, multi_results, limit: int):
        """Merge results from vector and BM25 searches using Reciprocal Rank Fusion (RRF)"""
        from collections import defaultdict

        # RRF constant (typically 60)
        k = 60

        # Calculate RRF scores for each document
        rrf_scores = defaultdict(float)
        doc_data = {}  # Store document attributes

        # Process results from each query (vector and BM25)
        # multi_results.results is a list of Result objects, each with a .rows attribute
        for result in multi_results.results:
            for rank, row in enumerate(result.rows, start=1):
                doc_id = row.id
                # RRF formula: 1 / (k + rank)
                rrf_scores[doc_id] += 1.0 / (k + rank)
                # Store document data (attributes from any result)
                if doc_id not in doc_data:
                    doc_data[doc_id] = row

        # Sort by RRF score (highest first) and take top limit
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)[:limit]

        # Return documents in sorted order
        return [doc_data[doc_id] for doc_id in sorted_ids]

    def _build_filters(self, filters: Dict, numeric_ranges: Dict) -> Tuple:
        """Build turbopuffer filter expressions"""
        filter_parts = []

        # Add keyword filters
        for field, value in filters.items():
            if isinstance(value, list):
                # OR condition for multiple values
                or_parts = [(field, "Eq", v) for v in value]
                filter_parts.append(("Or", or_parts))
            else:
                filter_parts.append((field, "Eq", value))

        # Add numeric range filters
        for field, range_dict in numeric_ranges.items():
            if 'min' in range_dict and 'max' in range_dict:
                filter_parts.append((field, "Gte", range_dict['min']))
                filter_parts.append((field, "Lte", range_dict['max']))
            elif 'min' in range_dict:
                filter_parts.append((field, "Gte", range_dict['min']))
            elif 'max' in range_dict:
                filter_parts.append((field, "Lte", range_dict['max']))

        # Combine all filters with AND
        if len(filter_parts) == 0:
            return None
        elif len(filter_parts) == 1:
            return filter_parts[0]
        else:
            return ("And", tuple(filter_parts))

    def search(
        self,
        query: str = "",
        mode: str = "text",  # "text", "semantic", or "hybrid"
        scope: str = "catalog",  # "catalog", "cellar", or "all"
        owned_wine_ids: List[int] = None,
        filters: Dict = None,
        numeric_ranges: Dict = None,
        sort_by: str = None,
        sort_reverse: bool = False,
        limit: int = 10,
    ) -> List[int]:
        """
        Unified search interface supporting text, semantic, and hybrid search

        Args:
            query: Search query string
            mode: "text" (BM25), "semantic" (vector), or "hybrid" (combined)
            scope: "catalog" (exclude owned), "cellar" (only owned), or "all"
            owned_wine_ids: List of wine IDs owned by user (for scope filtering)
            filters: Dictionary of field filters
            numeric_ranges: Dictionary of numeric range filters
            sort_by: Field to sort by (text mode only)
            sort_reverse: Reverse sort order
            limit: Maximum number of results

        Returns:
            List of wine IDs
        """
        print(f"Search mode={mode}, scope={scope}, query='{query}', limit={limit}")

        if self.search_demo_latency and random.random() < 0.5:
            print("Adding demo latency (10s sleep)")
            time.sleep(10)

        filters = filters or {}
        numeric_ranges = numeric_ranges or {}
        filter_expr = self._build_filters(filters, numeric_ranges)
        owned_wine_ids = owned_wine_ids or []
        owned_set = set(owned_wine_ids)

        # Fetch more results if we need to filter by scope
        search_limit = limit * 3 if scope in ["cellar", "catalog"] and owned_wine_ids else limit

        try:
            if mode == "semantic":
                # Vector search only
                query_vector = self._create_embedding(query)
                query_result = self.ns.query(
                    rank_by=("vector", "ANN", query_vector),
                    top_k=search_limit,
                    filters=filter_expr,
                    include_attributes=["points", "price"]
                )
                results = query_result.rows  # Extract rows from response

            elif mode == "hybrid":
                # Hybrid search: combine BM25 and vector using multi_query
                query_vector = self._create_embedding(query)
                multi_results = self.ns.multi_query(
                    queries=[
                        {
                            "rank_by": ("vector", "ANN", query_vector),
                            "top_k": search_limit,
                            "filters": filter_expr,
                            "include_attributes": ["points", "price"]
                        },
                        {
                            "rank_by": ("text", "BM25", query),
                            "top_k": search_limit,
                            "filters": filter_expr,
                            "include_attributes": ["points", "price"]
                        },
                    ]
                )
                # Merge results using reciprocal rank fusion (RRF)
                results = self._merge_hybrid_results(multi_results, search_limit)

            else:  # "text" mode (default)
                if query.strip():
                    # BM25 text search
                    query_result = self.ns.query(
                        rank_by=("text", "BM25", query),
                        top_k=search_limit * 2,  # Fetch more for sorting
                        filters=filter_expr,
                        include_attributes=["points", "price"]
                    )
                    results = query_result.rows  # Extract rows from response
                else:
                    # No query, just filter
                    query_result = self.ns.query(
                        top_k=search_limit * 2,
                        filters=filter_expr,
                        include_attributes=["points", "price"]
                    )
                    results = query_result.rows  # Extract rows from response

                # Sort if requested (and not using BM25 ranking)
                if sort_by and not query.strip():
                    sort_key_map = {row.id: getattr(row, sort_by, 0) for row in results}
                    results = sorted(results, key=lambda r: sort_key_map.get(r.id, 0), reverse=sort_reverse)

            # Extract IDs
            result_ids = [row.id for row in results]

            # Apply scope filtering
            if scope == "cellar" and owned_set:
                # Only keep wines user owns
                result_ids = [wine_id for wine_id in result_ids if wine_id in owned_set]
                print(f"Filtered to cellar wines: {len(result_ids)} results")
            elif scope == "catalog" and owned_set:
                # Remove wines user owns
                result_ids = [wine_id for wine_id in result_ids if wine_id not in owned_set]
                print(f"Filtered out owned wines: {len(result_ids)} results")

            # Limit to requested number
            result_ids = result_ids[:limit]
            print(f"Search completed - Returning {len(result_ids)} results")
            return result_ids

        except Exception as e:
            print(f"Search error: {e}")
            return []
