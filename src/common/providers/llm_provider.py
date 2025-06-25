from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_core.language_models.chat_models import BaseChatModel
from typing import Optional, Dict
import os

class LLMProvider:
    def __init__(self):
        self.models: Dict[str, BaseChatModel] = {}
        self._initialize_all()

    def _initialize_all(self):
        # Cargar GROQ
        groq_api_key = os.getenv("GROQ_API_KEY")
        if groq_api_key:
            self.models["groq"] = ChatGroq(
                model=os.getenv("GROQ_CHAT_MODEL", "llama3-8b-8192"),
                api_key=groq_api_key,
                temperature=0.0
            )

        # Cargar OPENAI
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            self.models["openai"] = ChatOpenAI(
                model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4"),
                api_key=openai_api_key,
                temperature=0.7
            )

        # Puedes seguir agregando Anthropic, Mistral, Cohere, etc.

    async def get_instance(self, provider: str = "groq") -> BaseChatModel:
        model = self.models.get(provider.lower())
        if not model:
            raise ValueError(f"Modelo para proveedor '{provider}' no inicializado.")
        return model
