from typing import List, Optional
from pydantic import BaseModel, Field

class Article(BaseModel):
    """
    Modelo Pydantic para representar un artículo con título, contenido, categorías y tags.
    """
    title: str = Field(..., description="Título del artículo.")
    content: str = Field(..., description="Contenido completo del artículo.")
    categories: List[str] = Field(default_factory=list, description="Lista de categorías asociadas al artículo.")
    tags: List[str] = Field(default_factory=list, description="Lista de tags asociados al artículo.")
