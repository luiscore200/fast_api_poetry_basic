from typing import List, Optional, Dict, Any, Union
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    PointStruct,
    VectorParams,
    Distance,
    Filter,
    FieldCondition,
    MatchAny,
    SearchParams,
    ScoredPoint,
)
from src.common.providers.qdrant_provider import get_qdrant_client


class QdrantORM:
    def __init__(self, collection_name: str):
        self.client: QdrantClient = get_qdrant_client()
        self.collection_name = collection_name

    def collection_exists(self) -> bool:
        collections = self.client.get_collections().collections
        return any(c.name == self.collection_name for c in collections)

    def create_collection_if_not_exists(
        self,
        vector_dim: int,
        payload_schema: Optional[Dict[str, Dict[str, str]]] = None
    ):
        if not self.collection_exists():
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_dim, distance=Distance.COSINE)
            )
            print(f"✅ Colección '{self.collection_name}' creada con dimensión {vector_dim}.")

            # Crear índices para filtrado, si se proporciona un esquema
            if payload_schema:
                for field_name, index_config in payload_schema.items():
                    try:
                        self.client.create_payload_index(
                            collection_name=self.collection_name,
                            field_name=field_name,
                            field_schema=index_config["type"]
                        )
                        print(f"🔍 Índice creado para '{field_name}' tipo {index_config['type']}")
                    except Exception as e:
                        print(f"❌ Error creando índice para '{field_name}': {e}")

    def delete_collection(self):
        if self.collection_exists():
            self.client.delete_collection(collection_name=self.collection_name)
            print(f"🗑️ Colección '{self.collection_name}' eliminada.")

    def insert_points(self, points: List[Dict[str, Any]]):
        if not points:
            print("⚠️ No se proporcionaron puntos para insertar.")
            return

        sample_vector = points[0].get("vector")
        if not sample_vector:
            raise ValueError("Cada punto debe incluir un vector.")

        self.create_collection_if_not_exists(vector_dim=len(sample_vector))

        point_structs = [
            PointStruct(id=p["id"], vector=p["vector"], payload=p.get("payload", {})) # Eliminar str()
            for p in points
        ]

        self.client.upsert(collection_name=self.collection_name, points=point_structs)
        print(f"📌 {len(points)} puntos insertados en '{self.collection_name}'.")


    def search(
        self,
        query_vector: List[float],
        filters: Optional[Dict[str, Union[str, List[str]]]] = None,
        top_k: int = 5
    ) -> List[ScoredPoint]:
        qdrant_filter = self._build_filter(filters)
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                search_params=SearchParams(hnsw_ef=128),
                query_filter=qdrant_filter
            )
            print(f"✅ {len(results)} resultados encontrados en '{self.collection_name}'.")
            return results
        except Exception as e:
            print(f"❌ Error en búsqueda Qdrant: {e}")
            return []

    def _build_filter(self, filters: Optional[Dict[str, Union[str, List[str]]]]) -> Optional[Filter]:
        if not filters:
            return None

        conditions = []
        for key, value in filters.items():
            if isinstance(value, list):
                conditions.append(FieldCondition(key=key, match=MatchAny(any=value)))
            else:
                conditions.append(FieldCondition(key=key, match=MatchAny(any=[value])))

        return Filter(should=conditions) if conditions else None
    
    def count_points(self, filters: Optional[Dict[str, Union[str, List[str]]]] = None) -> int:
        qdrant_filter = self._build_filter(filters)
        try:
            count_result = self.client.count(
                collection_name=self.collection_name,
                count_filter=qdrant_filter,
                exact=True  # Usa True para contar todos, no aproximado
            )
            return count_result.count
        except Exception as e:
            print(f"❌ Error al contar puntos en '{self.collection_name}': {e}")
            return 0
