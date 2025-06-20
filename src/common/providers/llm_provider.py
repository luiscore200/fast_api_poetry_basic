import os
from dotenv import load_dotenv
import asyncio
from typing import Optional, Any

# Importar el tipo base y las clases de modelos de chat necesarios de Langchain
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
# Añade aquí otras importaciones de modelos si soportas más proveedores

# Cargar variables de entorno al inicio del módulo
load_dotenv()


class LLMProvider:
    def __init__(self, provider: str = "groq", **kwargs):
        self.provider = provider.lower()
        self.kwargs = kwargs
        self.llm_instance: Optional[BaseChatModel] = None

    async def get_instance(self) -> BaseChatModel:
        if self.llm_instance:
            return self.llm_instance

        if self.provider == "openai":
            api_key = self.kwargs.get("api_key") or os.getenv("OPENAI_API_KEY")
            model_name = self.kwargs.get("model", os.getenv("OPENAI_CHAT_MODEL") or "gpt-4")
            if not api_key:
                raise ValueError("OPENAI_API_KEY no configurado.")
            self.llm_instance = ChatOpenAI(
                model=model_name,
                temperature=self.kwargs.get("temperature", 0.7),
                api_key=api_key,
                **self.kwargs
            )

        elif self.provider == "groq":
            api_key = self.kwargs.get("api_key") or os.getenv("GROQ_API_KEY")
            model_name = self.kwargs.get("model", os.getenv("GROQ_CHAT_MODEL") or "llama3-8b-8192")
            if not api_key:
                raise ValueError("GROQ_API_KEY no configurado.")
            self.llm_instance = ChatGroq(
                model=model_name,
                temperature=self.kwargs.get("temperature", 0.7),
                api_key=api_key,
                **self.kwargs
            )

        else:
            raise ValueError(f"Proveedor no soportado: {self.provider}")

        return self.llm_instance