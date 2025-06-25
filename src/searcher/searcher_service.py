from typing import Optional, List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from qdrant_client.http.models import ScoredPoint

from src.common.providers.llm_provider import LLMProvider
from src.common.providers.sqlite_provider import SQLiteProvider
from src.common.repositories.qdrant_repository import QdrantORM
from src.common.services.embeddings_service import EmbeddingService


class BusquedaVectorialOutput(BaseModel):
    query_vectorial: str = Field(..., description="Consulta optimizada para búsqueda vectorial.")
    tags: list[str] = Field(default_factory=list, description="Etiquetas para filtrado.")
    categories: list[str] = Field(default_factory=list, description="Categorías relevantes.")
    sentiment: str = Field(default="neutral", description="Sentimiento detectado.")


class SearcherService:
    def __init__(self):
        self.llm_provider = LLMProvider()
        self.parser = JsonOutputParser(pydantic_object=BusquedaVectorialOutput)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system",
             "Eres un experto en procesamiento de lenguaje natural para motores vectoriales. "
             "Transformarás el mensaje del usuario en una consulta optimizada, extraerás tags, "
             "categorías y sentimiento. Las categorías y tags deben ir en español. Devuelve un JSON válido con el esquema dado."),
            ("human", "Prompt: {user_prompt}\n\nFormato esperado:\n{format_instructions}")
        ])
        self.qdrant = QdrantORM("documents")  # ✅ Colección concreta
        self.sqlite = SQLiteProvider()
        self.embedding_service = EmbeddingService(model_type="local")

    async def analyze_prompt(self, user_prompt: str, provider: str = "groq") -> BusquedaVectorialOutput:
        print("🧠 Analizando prompt...")
        try:
            llm = await self.llm_provider.get_instance(provider=provider)
            chain = self.prompt | llm | self.parser
            result = await chain.ainvoke({
                "user_prompt": user_prompt,
                "format_instructions": self.parser.get_format_instructions()
            })

            if isinstance(result, dict):
                result = BusquedaVectorialOutput(**result)
            print("✅ Prompt procesado:", result)
            return result

        except Exception as e:
            print(f"❌ Error analizando prompt: {e}")
            return BusquedaVectorialOutput(query_vectorial=user_prompt)

    async def run_semantic_search(self, bvo: BusquedaVectorialOutput, top_k: int = 3) -> List[ScoredPoint]:
        try:
            print("🔄 Generando vector de la consulta...")
            query_vector = await self.embedding_service.generate(bvo.query_vectorial)
            print("🧬 Vector generado: ", query_vector[:10], "...")

            print("🔎 Ejecutando búsqueda vectorial...")

            filters = {}
            if bvo.tags:
                filters["merged_tags"] = bvo.tags
            if bvo.categories:
                filters["merged_categories"] = bvo.categories

            results: List[ScoredPoint] = self.qdrant.search(
                query_vector=query_vector,
                filters=filters,
                top_k=top_k
            )

            print("📥 Resultados encontrados:")
            for i, r in enumerate(results):
                print(f"  {i+1}. Doc {r.payload.get('document_id')} - Score: {r.score}")

            return results

        except Exception as e:
            print(f"❌ Error en búsqueda semántica: {e}")
            return []

    def run_sql_search(self, document_id: int) -> Optional[Dict[str, Any]]:
        try:
            print(f"🗂️ Buscando artículo en SQL para ID {document_id}...")
            row = self.sqlite.find("articles", where={"id": document_id})
            if row:
                _id, title, content = row[0]
                return {"id": _id, "title": title, "content": content}
            return None
        except Exception as e:
            print(f"❌ Error en búsqueda SQL: {e}")
            return None

    async def run_search(self, user_prompt: str, top_k: int = 3, provider: str = "groq") -> Dict[str, Any]:
        print("🚀 Iniciando búsqueda completa...")
        try:
            bvo = await self.analyze_prompt(user_prompt, provider=provider)

            results = await self.run_semantic_search(bvo, top_k=top_k)

            if not results:
                return {
                    "llm": bvo.dict(),
                    "article": None,
                    "vector_results": []
                }

            top_doc_id = results[0].payload.get("document_id")
            article_data = self.run_sql_search(top_doc_id)

            return {
                "llm": bvo.dict(),
                "article": article_data,
                "vector_results": [
                    {
                        "document_id": r.payload.get("document_id"),
                        "score": r.score,
                        "tags": r.payload.get("merged_tags", []),
                        "categories": r.payload.get("merged_categories", [])
                    } for r in results
                ]
            }

        except Exception as e:
            print(f"❌ Error general en run_search: {e}")
            return {
                "llm": {},
                "article": None,
                "vector_results": [],
                "error": str(e)
            }
