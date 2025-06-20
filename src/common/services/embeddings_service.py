import os
import asyncio
from dotenv import load_dotenv
from typing import List, Union, Any
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
from anyio.to_thread import run_in_threadpool

from src.common.types.errors_types import EmbeddingServiceError

load_dotenv()

class EmbeddingService:
    def __init__(self, model_type: str = "openai", **kwargs: Any):
        """
        Inicializa el servicio de embeddings con el modelo y proveedor especificado.
        """
        self.model_type = model_type
        self.kwargs = kwargs
        self.embeddings_model: Embeddings = self._initialize_model()

    def _initialize_model(self) -> Embeddings:
        """
        Inicializa el modelo de embeddings según el tipo especificado.
        """
        try:
            if self.model_type == "openai":
                api_key = os.getenv("OPENAI_API_KEY")
                model_name = os.getenv("OPENAI_API_MODEL") or "text-embedding-ada-002"
                if not api_key:
                    raise ValueError("La variable de entorno OPENAI_API_KEY no está configurada.")
                return OpenAIEmbeddings(
                    model=model_name,
                    openai_api_key=api_key,
                    **self.kwargs
                )

            elif self.model_type == "local":
                model_name = self.kwargs.get("model_name") or os.getenv("LOCAL_EMBEDDING_MODEL") or "sentence-transformers/all-MiniLM-L6-v2"
                return HuggingFaceEmbeddings(
                    model_name=model_name,
                    **self.kwargs
                )

            elif self.model_type == "google":
                raise NotImplementedError("Soporte para Google aún no implementado.")

            else:
                raise ValueError(f"Tipo de modelo '{self.model_type}' no soportado.")

        except Exception as e:
            raise EmbeddingServiceError(
                message=f"Fallo al inicializar el modelo de embeddings '{self.model_type}'",
                details=str(e)
            ) from e

    async def generate(
        self,
        text: Union[str, List[str]]
    ) -> Union[List[float], List[List[float]]]:
        """
        Genera embeddings para texto o lista de textos.

        Returns:
            Un vector o lista de vectores.
        """
        try:
            if isinstance(text, str):
                return await run_in_threadpool(self.embeddings_model.embed_query, text)
            elif isinstance(text, list):
                return await run_in_threadpool(self.embeddings_model.embed_documents, text)
            else:
                raise TypeError("El texto debe ser str o List[str]")
        except Exception as e:
            print(f"Error interno al generar embeddings: {e}")
            raise EmbeddingServiceError(
                message="Error al generar embeddings.",
                details=str(e)
            ) from e
