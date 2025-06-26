import logging
import time  # ← agregado
from typing import Optional, List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from qdrant_client.http.models import ScoredPoint
import json

from src.common.providers.llm_provider import LLMProvider
from src.common.providers.sqlite_provider import SQLiteProvider
from src.common.repositories.qdrant_repository import QdrantORM
from src.common.services.embeddings_service import EmbeddingService

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class CategoryDetectionOutput(BaseModel):
    categories: List[str] = Field(..., description="Categorías relevantes extraídas del prompt.")

class RefinedQueryOutput(BaseModel):
    refined_prompt: str = Field(..., description="Prompt optimizado para búsqueda vectorial, considerando intención y emoción.")

class DocumentSearcherService:
    def __init__(self):
        self.llm = LLMProvider()
        self.cat_parser = JsonOutputParser(pydantic_object=CategoryDetectionOutput)
        self.refine_parser = JsonOutputParser(pydantic_object=RefinedQueryOutput)

        self.cat_prompt_template = ChatPromptTemplate.from_messages([
            (
                "system",
                "Eres un analizador semántico experto. Tu tarea es analizar el texto del usuario y descomponerlo "
                "en categorías y subtemas siguiendo el formato específico.\n\n"
                "**Formato de salida:** array JSON de cadenas de texto. Cada cadena sigue el formato: "
                "'categoria_general, subtema1, subtema2, subtema3'\n\n"
                "**Reglas:**\n"
                "- Cada cadena debe tener exactamente 4 términos separados por coma.\n"
                "- El primero es una categoría general.\n"
                "- Los siguientes tres son subtemas directamente relacionados.\n"
                "- No uses frases compuestas ('energía renovable' ❌, 'energía' ✅).\n"
                "- Sé específico y evita generalidades vacías.\n"
                "- Genera al menos 2 cadenas si el tema lo permite.\n\n"
                "**Ejemplo 1:**\n"
                "Input: Arquitectura del futuro\n"
                "Output: ['arquitectura, diseño, materiales, sostenibilidad', 'sociedad, tecnología, urbanismo, innovación']\n\n"
                "**Ejemplo 2:**\n"
                "Input: ¿Cómo afecta la falta de sueño al rendimiento laboral?\n"
                "Output: ['salud, sueño, estrés, autocuidado', 'trabajo, productividad, concentración, desempeño']\n\n"
                "Ahora procesa el siguiente input del usuario y responde solo con el array JSON solicitado."
            ),
            ("human", "{user_prompt}\n\nFormato esperado:\n{format_instructions}")
        ])

        self.refine_prompt_template = ChatPromptTemplate.from_messages([
            ("system",
            "Eres un generador experto de prompts enfocados a búsquedas semánticas. "
            "Tu objetivo es reformular el prompt del usuario de forma clara, emocionalmente empática y con intención de búsqueda, "
            "basándote en las categorías sugeridas. El resultado debe mantener el mismo idioma (español) que el prompt original. "
            "No inventes información nueva. Devuelve únicamente un JSON válido con la clave 'refined_prompt'."),
            ("human", "Prompt: {user_prompt}\nCategorías: {categories}\n\nFormato esperado:\n{format_instructions}")
        ])

        self.qdocs = QdrantORM("documents")
        self.qcats = QdrantORM("categories")
        self.sql = SQLiteProvider()
        self.embed = EmbeddingService(model_type="local")

    async def detect_categories(self, user_prompt: str, provider: str = "groq") -> List[str]:
        try:
            logger.info("🧠 Detectando categorías...")
            llm = await self.llm.get_instance(provider=provider)
            chain = self.cat_prompt_template | llm | self.cat_parser

            start = time.perf_counter()
            raw = await chain.ainvoke({
                "user_prompt": user_prompt,
                "format_instructions": self.cat_parser.get_format_instructions()
            })
            elapsed = time.perf_counter() - start
            logger.info(f"🕒 Tiempo de respuesta detect_categories ({provider}): {elapsed:.2f} segundos")

            out = CategoryDetectionOutput(**raw) if isinstance(raw, dict) else raw
            logger.info(f"📤 Categorías detectadas por LLM: {out}")
            return out
        except Exception as e:
            logger.error(f"❌ Error detectando categorías: {e}")
            return []

    async def refine_prompt(self, user_prompt: str, categories: List[str], provider: str = "groq") -> str:
        try:
            logger.info("🧠 Refinando prompt según categorías...")
            llm = await self.llm.get_instance(provider=provider)
            chain = self.refine_prompt_template | llm | self.refine_parser

            start = time.perf_counter()
            raw = await chain.ainvoke({
                "user_prompt": user_prompt,
                "categories": ", ".join(categories),
                "format_instructions": self.refine_parser.get_format_instructions()
            })
            elapsed = time.perf_counter() - start
            logger.info(f"🕒 Tiempo de respuesta refine_prompt ({provider}): {elapsed:.2f} segundos")

            out = RefinedQueryOutput(**raw) if isinstance(raw, dict) else raw
            logger.info(f"📤 Prompt refinado: {out.refined_prompt}")
            return out.refined_prompt
        except Exception as e:
            logger.error(f"❌ Error refinando prompt: {e}")
            return user_prompt
        

    async def get_filter_categories(self, categories: List[str], top_k: int = 2, min_score: float = 0.55) -> List[str]:
        try:
            logger.info("🔍 Obteniendo categorías semánticas desde Qdrant con score mínimo...")
            names = []
            start_total = time.perf_counter()

            for cat in categories:
                logger.info(f"🔎 Vectorizando y buscando: {cat}")
                vec = await self.embed.generate(cat)
                pts: List[ScoredPoint] = self.qcats.search(query_vector=vec, top_k=top_k)

                for p in pts:
                    name = p.payload.get("name")
                    score = p.score
                    logger.info(f"📈 Score: {score:.4f} - Categoría encontrada: {name}")
                    if score >= min_score and name:
                        names.append(name)

            elapsed = time.perf_counter() - start_total
            unique = list(dict.fromkeys(names))
            logger.info(f"📥 Categorías filtradas por score >= {min_score}: {unique}")
            logger.info(f"🕒 Tiempo total en get_filter_categories (Qdrant + embeddings): {elapsed:.2f} segundos")
            return unique

        except Exception as e:
            logger.error(f"❌ Error en búsqueda semántica de categorías: {e}")
            return []


    async def run_search(
        self,
        user_prompt: str,
        top_k: int = 3,
        provider: str = "groq",
        min_score: float = 0.55
    ) -> Dict[str, Any]:
        try:
            logger.info("🚀 Iniciando búsqueda semántica...")
            cats = await self.detect_categories(user_prompt, provider)
            refined = await self.refine_prompt(user_prompt, cats, provider)
            filt_cats = await self.get_filter_categories(cats, top_k=2, min_score=0.6)

            logger.info("🧬 Generando vector del prompt refinado...")
            vec = await self.embed.generate(refined)

            logger.info("🔎 Ejecutando búsqueda en documentos...")
            start_qdrant = time.perf_counter()
            results = self.qdocs.search(
                query_vector=vec,
                filters={"merged_categories": filt_cats},
                top_k=top_k
            )
            elapsed_qdrant = time.perf_counter() - start_qdrant
            logger.info(f"🕒 Tiempo búsqueda en Qdrant (documentos): {elapsed_qdrant:.2f} segundos")

            filtered_results = [r for r in results if r.score >= min_score]
            logger.info(f"📊 Resultados filtrados por score >= {min_score}: {len(filtered_results)}")

            logger.info("📄 Recuperando artículos desde SQL...")
            docs = []
            for r in filtered_results:
                doc_id = r.payload.get("document_id")
                row = self.sql.find("articles", where={"id": doc_id})
                if row:
                    docs.append({
                        "id": row[0][0],
                        "title": row[0][1],
                        "content": row[0][2]
                    })

            return {
                "refined_prompt": refined,
                "vector_results": [
                    {"document_id": r.payload.get("document_id"), "score": r.score}
                    for r in filtered_results
                ],
                "articles": docs,
                "debug_info": {
                    "initial_categories": cats,
                    "filtered_categories": filt_cats
                }
            }

        except Exception as e:
            logger.error(f"❌ Error en ejecución de búsqueda: {e}")
            return {
                "refined_prompt": user_prompt,
                "vector_results": [],
                "articles": [],
                "debug_info": {
                    "initial_categories": [],
                    "filtered_categories": []
                },
                "error": str(e)
            }

