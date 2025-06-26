from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from google.generativeai import configure, GenerativeModel
from langchain_core.language_models.chat_models import BaseChatModel
from typing import Dict, Optional,List,Any
from langchain_core.messages import AIMessage, HumanMessage
import os
from pydantic import PrivateAttr



class GoogleGeminiWrapper(BaseChatModel):
    _model: Any = PrivateAttr()
    _temperature: float = PrivateAttr()

    def __init__(self, model_name: str, api_key: str, temperature: float = 0.7):
        super().__init__()
        configure(api_key=api_key)
        self._model = GenerativeModel(model_name)
        self._temperature = temperature

    @property
    def _llm_type(self) -> str:
        return "google_gemini"

    def _generate(self, messages: List[Any], stop: Optional[List[str]] = None) -> AIMessage:
        prompt = "\n".join([msg.content for msg in messages])
        response = self._model.generate_content(prompt, generation_config={"temperature": self._temperature})
        return AIMessage(content=response.text)

    async def ainvoke(self, input: str, **kwargs) -> str:
        response = self._model.generate_content(input, generation_config={"temperature": self._temperature})
        return response.text
    



class LLMProvider:
    def __init__(self):
        self.models: Dict[str, BaseChatModel] = {}
        self._initialize_all()

    def _initialize_all(self):
        # GROQ
        if groq_api_key := os.getenv("GROQ_API_KEY"):
            self.models["groq"] = ChatGroq(
                model=os.getenv("GROQ_CHAT_MODEL", "llama3-8b-8192"),
                api_key=groq_api_key,
                temperature=0.0
            )

        # OPENAI
        if openai_api_key := os.getenv("OPENAI_API_KEY"):
            self.models["openai"] = ChatOpenAI(
                model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4"),
                api_key=openai_api_key,
                temperature=0.7
            )

        # GOOGLE
        google_model = self._init_google_model()
        if google_model:
            self.models["google"] = google_model

    def _init_google_model(self) -> Optional[BaseChatModel]:
        google_key = os.getenv("GOOGLE_API_KEY")
        google_model_name = os.getenv("GOOGLE_CHAT_MODEL", "gemini-pro")
        if not google_key:
            return None
        return GoogleGeminiWrapper(model_name=google_model_name, api_key=google_key, temperature=0.7)

    async def get_instance(self, provider: str = "groq") -> BaseChatModel:
        model = self.models.get(provider.lower())
        if not model:
            raise ValueError(f"Modelo para proveedor '{provider}' no inicializado.")
        return model
