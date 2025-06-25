from typing import List, Optional
from qdrant_client.http.models import (
    PointStruct,
    VectorParams,
    Distance,
    Filter,
    FieldCondition,
    MatchAny,
    SearchParams,
    ScoredPoint
)
from src.common.providers.qdrant_provider import get_qdrant_client
from src.common.types.metadata_types import ChunkOutput


def build_filter(tags: list[str], categories: list[str]) -> Optional[Filter]:
    conditions = []

    if tags:
        conditions.append(FieldCondition(key="merged_tags", match=MatchAny(any=tags)))

    if categories:
        conditions.append(FieldCondition(key="merged_categories", match=MatchAny(any=categories)))

    if conditions:
        return Filter(should=conditions)  # lógica OR
    return None


class QdrantRepository:
    def __init__(self, collection_name: str = "documents"):
        self.qdrant_client = get_qdrant_client()
        self.collection_name = collection_name

    def collection_exists(self) -> bool:
        collections = self.qdrant_client.get_collections().collections
        return any(c.name == self.collection_name for c in collections)

    def create_collection_if_not_exists(self, embedding_example: List[float]):
        if not self.collection_exists():
            if embedding_example is None:
                raise ValueError("Se requiere un embedding de ejemplo para definir el tamaño del vector.")
            size = len(embedding_example)
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=size, distance=Distance.COSINE)
            )
            print(f"✅ Colección '{self.collection_name}' creada con dimensión {size}.")

    def delete_collection(self):
        if self.collection_exists():
            self.qdrant_client.delete_collection(collection_name=self.collection_name)
            print(f"🗑️ Colección '{self.collection_name}' eliminada.")

    def insert_chunks(self, chunks: List[ChunkOutput]):
        if not chunks:
            print("⚠️ No se proporcionaron chunks para insertar.")
            return

        self.create_collection_if_not_exists(embedding_example=chunks[0].embedding)

        points: List[PointStruct] = []
        for chunk in chunks:
            if not chunk.embedding:
                continue

            point_id = int(f"{chunk.document_id:03}{chunk.chunk_id:03}")

            points.append(PointStruct(
                id=point_id,
                vector=list(chunk.embedding),
                payload={
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "original_tags": chunk.original.tags,
                    "original_categories": chunk.original.categories,
                    "generated_tags": chunk.generated.tags,
                    "generated_categories": chunk.generated.categories,
                    "merged_tags": chunk.merged_tags,
                    "merged_categories": chunk.merged_categories,
                }
            ))

        self.qdrant_client.upsert(collection_name=self.collection_name, points=points)
        print(f"📌 {len(points)} chunks insertados en Qdrant.")

    def search(
        self,
        query_vector: list[float],
        tags: list[str],
        categories: list[str],
        top_k: int = 3
    ) -> list[ScoredPoint]:
        query_filter = build_filter(tags, categories)

        try:
            results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                search_params=SearchParams(hnsw_ef=128),
                query_filter=query_filter
            )
            print(f"✅ {len(results)} resultados encontrados en Qdrant.")
            return results

        except Exception as e:
            print(f"❌ Error en búsqueda Qdrant: {e}")
            return []
