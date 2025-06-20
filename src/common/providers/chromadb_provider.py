import chromadb
from chromadb.api.client import Client
from typing import Optional

_chroma_client: Optional[Client] = None

def get_chroma_client(persistent: bool = False, persist_path: str = "./chroma") -> Client:
    global _chroma_client
    if _chroma_client is None:
        if persistent:
            _chroma_client = chromadb.PersistentClient(path=persist_path)
            print(f"Cliente persistente ChromaDB inicializado en {persist_path}")
        else:
            _chroma_client = chromadb.EphemeralClient()
            print("Cliente en memoria ChromaDB inicializado")
    return _chroma_client
