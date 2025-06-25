from typing import Optional, List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from qdrant_client.http.models import ScoredPoint
from uuid import uuid4

from src.common.providers.llm_provider import LLMProvider
from src.common.providers.sqlite_provider import SQLiteProvider
from src.common.repositories.qdrant_repository import QdrantORM
from src.common.services.embeddings_service import EmbeddingService


class CategoryDetectionOutput(BaseModel):
    categories: List[str] = Field(..., description="Categorías potencialmente relevantes extraídas del prompt.")


class FinalQueryOutput(BaseModel):
    query_vectorial: str = Field(..., description="Consulta optimizada para búsqueda vectorial.")
    tags: list[str] = Field(default_factory=list, description="Etiquetas para filtrado.")


class DocumentSearcherService:
    def __init__(self):
        self.llm_provider = LLMProvider()
        self.category_parser = JsonOutputParser(pydantic_object=CategoryDetectionOutput)
        self.query_parser = JsonOutputParser(pydantic_object=FinalQueryOutput)
        self.category_prompt = ChatPromptTemplate.from_messages([
            ("system", "Eres un experto en comprensión semántica. Dado un prompt, extrae un array con las categorías más relevantes. Responde solo con un JSON válido con la clave 'categories'."),
            ("human", "{user_prompt}\n\nFormato esperado:\n{format_instructions}")
        ])
        self.query_prompt = ChatPromptTemplate.from_messages([
            ("system", "Eres un experto en motores de búsqueda vectorial. A partir de un prompt y un conjunto de tags, genera una nueva consulta optimizada y filtra solo los tags más relevantes. Responde con un JSON con las claves 'query_vectorial' y 'tags'."),
            ("human", "Prompt: {user_prompt}\nTags sugeridos: {tags}\n\nFormato esperado:\n{format_instructions}")
        ])
        self.qdrant_documents = QdrantORM("documents")
        self.qdrant_categories = QdrantORM("categories")
        self.sqlite = SQLiteProvider()
        self.embedding_service = EmbeddingService(model_type="local")

    async def detect_categories(self, user_prompt: str, provider: str = "groq") -> List[str]:
        print("🧠 Detectando categorías iniciales...")
        try:
            llm = await self.llm_provider.get_instance(provider=provider)
            chain = self.category_prompt | llm | self.category_parser
            result = await chain.ainvoke({
                "user_prompt": user_prompt,
                "format_instructions": self.category_parser.get_format_instructions()
            })
            if isinstance(result, dict):
                result = CategoryDetectionOutput(**result)
            print(f"📤 Categorías detectadas: {result.categories}")
            return result.categories
        except Exception as e:
            print(f"❌ Error detectando categorías: {e}")
            return []

    async def search_category_ids(self, categories: List[str], top_k: int = 2) -> List[int]:
        print("🔍 Buscando categorías vectorialmente en Qdrant...")
        category_ids = set()
        for category in categories:
            print(f"🔎 Vectorizando categoría: {category}")
            vector = await self.embedding_service.generate(category)
            points = self.qdrant_categories.search(query_vector=vector, top_k=top_k)
            for point in points:
                category_id = point.payload.get("category_id")
                if category_id:
                    category_ids.add(category_id)
        print(f"📥 IDs de categorías encontradas: {list(category_ids)}")
        return list(category_ids)

    def get_tags_by_category_ids(self, category_ids: List[int]) -> List[str]:
        print("📚 Buscando tags SQL por categorías...")
        tag_set = set()
        for category_id in category_ids:
            rows = self.sqlite.find("tag_categories", where={"category_id": category_id})
            for row in rows:
                tag_id = row[1]  # tag_id
                tag_row = self.sqlite.find("tags", where={"id": tag_id})
                if tag_row:
                    tag_set.add(tag_row[0][1])
        tags = list(tag_set)
        print(f"🏷️ Tags obtenidos: {tags}")
        return tags

    async def suggest_final_query(self, user_prompt: str, tags: List[str], provider: str = "groq") -> FinalQueryOutput:
        print("🧠 Generando consulta final...")
        try:
            llm = await self.llm_provider.get_instance(provider=provider)
            chain = self.query_prompt | llm | self.query_parser
            result = await chain.ainvoke({
                "user_prompt": user_prompt,
                "tags": ", ".join(tags),
                "format_instructions": self.query_parser.get_format_instructions()
            })
            if isinstance(result, dict):
                result = FinalQueryOutput(**result)
            print(f"📤 Consulta final generada: {result.dict()}")
            return result
        except Exception as e:
            print(f"❌ Error generando consulta final: {e}")
            return FinalQueryOutput(query_vectorial=user_prompt, tags=[])

    async def run_search(self, user_prompt: str, top_k: int = 3, provider: str = "groq") -> Dict[str, Any]:
        print("🚀 Iniciando búsqueda completa...")
        try:
            categories = await self.detect_categories(user_prompt, provider)
            category_ids = await self.search_category_ids(categories)
            tags = self.get_tags_by_category_ids(category_ids)
            final_query = await self.suggest_final_query(user_prompt, tags, provider)

            print("🧬 Generando vector de búsqueda...")
            vector = await self.embedding_service.generate(final_query.query_vectorial)
            print("🔎 Ejecutando búsqueda de documentos...")
            results = self.qdrant_documents.search(query_vector=vector, filters={"merged_tags": final_query.tags}, top_k=top_k)

            document_ids = [r.payload.get("document_id") for r in results if r.payload.get("document_id") is not None]
            articles = [self.sqlite.find("articles", where={"id": doc_id})[0] for doc_id in document_ids if self.sqlite.find("articles", where={"id": doc_id})]

            print(f"📄 Documentos encontrados: {document_ids}")
            return {
                "llm": final_query.dict(),
                "vector_results": [
                    {
                        "document_id": r.payload.get("document_id"),
                        "score": r.score,
                        "tags": r.payload.get("merged_tags", [])
                    } for r in results
                ],
                "articles": [
                    {"id": row[0], "title": row[1], "content": row[2]} for row in articles
                ]
            }

        except Exception as e:
            print(f"❌ Error general en run_search: {e}")
            return {
                "llm": {},
                "vector_results": [],
                "articles": [],
                "error": str(e)
            }
