"""
Simple client wrapper for Azure Cognitive Search vector index operations.
Phase 2: replace with full Azure SDK client code.
"""

import os
import requests
from app.config import settings

class AzureVectorClient:
    def __init__(self, endpoint: str = None, key: str = None, index_name: str = "vectors"):
        self.endpoint = endpoint or settings.AZURE_SEARCH_ENDPOINT
        self.key = key or settings.AZURE_SEARCH_KEY
        self.index_name = index_name

    def upsert_document(self, doc_id: str, vector: list, metadata: dict):
        url = f"{self.endpoint}/indexes/{self.index_name}/docs/index?api-version=2024-07-01-preview"
        headers = {"api-key": self.key, "Content-Type":"application/json"}
        body = {"value":[{"@search.action":"upload","id":doc_id,"vector":vector,"metadata":metadata}]}
        r = requests.post(url, headers=headers, json=body)
        r.raise_for_status()
        return r.json()

    def query_vector(self, vector: list, top_k: int = 5):
        url = f"{self.endpoint}/indexes/{self.index_name}/docs/search?api-version=2024-07-01-preview"
        headers = {"api-key": self.key, "Content-Type":"application/json"}
        body = {"vector": {"value": vector, "fields":"vector"}, "top": top_k}
        r = requests.post(url, headers=headers, json=body)
        r.raise_for_status()
        return r.json()