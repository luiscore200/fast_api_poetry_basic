from typing import List
from qdrant_client.http.models import (
    PointStruct, Filter, FieldCondition, MatchAny, VectorParams, Distance
)
from src.common.providers.qdrant_provider import get_qdrant_client
from src.common.types.metadata_types import ChunkOutput

class QdrantRepository:
    def __init__(self, collection_name: str = "documents"):
        self.client = get_qdrant_client()
        self.collection_name = collection_name

    def collection_exists(self) -> bool:
        collections = self.client.get_collections().collections
        return any(c.name == self.collection_name for c in collections)

    def create_collection_if_not_exists(self, embedding_example: List[float]):
        if not self.collection_exists():
            if embedding_example is None:
                raise ValueError("Se requiere un embedding de ejemplo para definir el tamaño del vector.")
            size = len(embedding_example)
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=size, distance=Distance.COSINE)
            )
            print(f"✅ Colección '{self.collection_name}' creada con dimensión {size}.")

    def delete_collection(self):
        if self.collection_exists():
            self.client.delete_collection(collection_name=self.collection_name)
            print(f"🗑️ Colección '{self.collection_name}' eliminada.")

    def insert_chunks(self, chunks: List[ChunkOutput]):
        if not chunks:
            print("⚠️ No se proporcionaron chunks para insertar.")
            return

        # Garantiza que la colección exista
        self.create_collection_if_not_exists(embedding_example=chunks[0].embedding)

        points: List[PointStruct] = []
        for chunk in chunks:
            if not chunk.embedding:
                continue

            # Usa un ID numérico único para evitar errores de Qdrant
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

        self.client.upsert(collection_name=self.collection_name, points=points)
        print(f"📌 {len(points)} chunks insertados en Qdrant.")

    def search(self, query_vector: List[float], tags: List[str], categories: List[str], top_k: int = 5):
        filters = []

        if tags:
            filters.append(FieldCondition(key="merged_tags", match=MatchAny(any=tags)))
        if categories:
            filters.append(FieldCondition(key="merged_categories", match=MatchAny(any=categories)))

        query_filter = Filter(must=filters) if filters else None

        return self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            query_filter=query_filter
        )
