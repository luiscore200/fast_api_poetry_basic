from typing import Optional,List,Dict
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from src.common.providers.llm_provider import LLMProvider
from src.common.providers.sqlite_provider import SQLiteProvider
from src.common.repositories.qdrant_repository import QdrantRepository


class BusquedaVectorialOutput(BaseModel):
    query_vectorial: str = Field(..., description="Consulta optimizada para búsqueda vectorial.")
    tags: list[str] = Field(default_factory=list, description="Etiquetas para filtrado.")
    categories: list[str] = Field(default_factory=list, description="Categorías relevantes.")
    sentiment: str = Field(default="neutral", description="Sentimiento detectado.")

class SearcherService:
    def __init__(self, provider: str = "groq", temperature: float = 0.0):
        # Se delega la selección de modelo por defecto al LLMProvider
        self.provider = provider
        self.llm_provider = LLMProvider(provider=self.provider, temperature=temperature)
        self.parser = JsonOutputParser(pydantic_object=BusquedaVectorialOutput)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", 
             "Eres un experto en procesamiento de lenguaje natural para motores vectoriales. "
             "Transformarás el mensaje del usuario en una consulta optimizada, extraerás tags, "
             "categorías y sentimiento. Devuelve un JSON acorde al esquema."),
            ("human", "Prompt: {user_prompt}\n\nFormato esperado:\n{format_instructions}")
        ])
        self.qdrant = QdrantRepository()
        self.sqlite = SQLiteProvider()
       # self.qdrant.delete_collection()


        

    async def analyze_prompt(self, user_prompt: str) -> BusquedaVectorialOutput:
        """
        Llama al LLM para obtener la consulta optimizada y metadatos.
        """
        llm = await self.llm_provider.get_instance()
        chain = self.prompt | llm | self.parser
        try:
            bvo: BusquedaVectorialOutput = await chain.ainvoke({
                "user_prompt": user_prompt,
                "format_instructions": self.parser.get_format_instructions()
            })
            return bvo
        except Exception as e:
            print(f"Error analyzing prompt: {e}")
        
            return BusquedaVectorialOutput(query_vectorial=user_prompt) 
            

    async def recommend_ids(self, user_prompt: str, n_results: int = 10) -> Dict:
        # Llamada al LLM → BVO
        llm = await self.llm_provider.get_instance()
        chain = self.prompt | llm | self.parser
        bvo = await chain.ainvoke({
            "user_prompt": user_prompt,
            "format_instructions": self.parser.get_format_instructions()
        })

        # Construcción de filtros planos
        filters = {f"merged_tag_{i}": t for i, t in enumerate(bvo.tags)}
        filters.update({f"merged_category_{i}": c for i, c in enumerate(bvo.categories)})

        # Búsqueda en qdrant → lista de IDs
        ids = self.qdrant.search(bvo.query_vectorial, filters, n_results)

        return {
            "llm": bvo.dict(),
            "document_ids": ids
        }

    def fetch_articles(self, document_ids: List[int]) -> List[Dict]:
        results = []
        for doc_id in document_ids:
            row = self.sqlite.find("articles", where={"id": doc_id})
            if row:
                _id, title, content = row[0]
                results.append({"id": _id, "title": title, "content": content})
        return results
