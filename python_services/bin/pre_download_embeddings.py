#!/usr/bin/env python3
"""
Pre-download the ChromaDB embedding model to avoid the 70-second delay during app startup.
This script can run during the Docker build process before the app code is copied.
"""

import sys
import tempfile
import chromadb

def pre_download_embeddings_model():
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            client = chromadb.PersistentClient(temp_dir)
            collection = client.get_or_create_collection("test_collection")
            collection.add(
                ids=["test_id"],
                documents=["This is a test document to trigger model download"],
                metadatas=[{"source": "test"}]
            )
            collection.query(
                query_texts=["test query"],
                n_results=1
            )
            return True
            
        except Exception as e:
            print(f"ERROR: Failed to pre-download embedding model: {e}")
            return False

if __name__ == "__main__":
    success = pre_download_embeddings_model()
    sys.exit(0 if success else 1)
