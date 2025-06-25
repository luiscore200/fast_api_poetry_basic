from typing import List
from pydantic import BaseModel, Field
from typing import List, Dict, Any,Optional

#datos basicos de filtrado
class Metadata(BaseModel):
    tags: List[str] = Field(default_factory=list, description="Lista de tags generados por la IA.")
    categories: List[str] = Field(default_factory=list, description="Lista de categorías generadas por la IA.")

#Clase para la implementacion de un llm para enreiquecer
class LLMOutputSchema(BaseModel):
    enriched_description: str = Field(description="La descripción enriquecida o resumida del documento.")
    generated: Metadata = Field(description="Metadata generada por la IA.")


class ChunkOutput(BaseModel):
    chunk_id: int
    document_id: int
    content: str
    original: Metadata # tags y categories originales
    generated: Metadata  # generado por el LLM
    merged_tags: List[str]
    merged_categories: List[str]
    vector: Optional[List[float]] = None


class FullDocumentChunksOutput(BaseModel):
    enriched_description: str
    chunks: List[ChunkOutput]