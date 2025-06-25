from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from src.common.managers.response_manager import ResponseManager # Importar ResponseManager
from src.data.data_controller import router as articles_router
from src.common.repositories.qdrant_repository import QdrantRepository
from src.common.services.embeddings_service import EmbeddingService
from src.searcher.searcher_controller import router as search_router

load_dotenv()
app = FastAPI()

app.include_router(articles_router, prefix="/articles") 
app.include_router(search_router, prefix="/assistant") 

# Handler global para excepciones no manejadas
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Maneja excepciones no capturadas y devuelve una respuesta de error estandarizada.
    """
    print(f"Unhandled error: {exc}")
    return ResponseManager.error(
        message=f"Ocurrió un error interno del servidor: {exc}",
        status_code=500,
        details=str(exc)
    )

@app.on_event("startup")
async def startup_event():
    embedding_service = EmbeddingService(model_type="local")
    qdrant_repo = QdrantRepository()

    dummy_vector = await embedding_service.generate("texto de ejemplo")

    # ⚠️ Forzar eliminación para limpiar colección mal creada
   # qdrant_repo.delete_collection()
    qdrant_repo.create_collection_if_not_exists(embedding_example=dummy_vector)

    print("✅ Colección Qdrant recreada con dimensión correcta.")


@app.get("/")
def read_root():
    return {"Hello": "World"}

