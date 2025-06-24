# src/common/providers/qdrant_provider.py
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
import os

_qdrant_client = None

def get_qdrant_client() -> QdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_KEY")
        )
    return _qdrant_client
