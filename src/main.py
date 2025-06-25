from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from src.common.managers.response_manager import ResponseManager # Importar ResponseManager
from src.data.data_controller import router as articles_router
from src.common.repositories.qdrant_repository import QdrantORM
from src.common.services.embeddings_service import EmbeddingService
from src.searcher.searcher_controller import router as search_router

load_dotenv()
app = FastAPI() # Eliminar json_encoders para UUID

app.include_router(articles_router, prefix="/document") 
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
    print("🔄 Inicializando colecciones en Qdrant...")
    embedding_service = EmbeddingService(model_type="local")

    dummy_vector = await embedding_service.generate("texto de ejemplo")
    
   
        
    
    document_payload = {
            "document_id": {"type": "integer"},
            "merged_tags": {"type": "keyword"},
            "merged_categories": {"type": "keyword"}
        }         
    category_payload = {
            "category_id": {"type": "integer"},
            "content": {"type": "text"},
            
        }  
    
              
    repo = QdrantORM("documents")
    #repo.delete_collection() 
    repo.create_collection_if_not_exists(vector_dim=len(dummy_vector), payload_schema=document_payload)

    category_repo = QdrantORM("categories")
    #category_repo.delete_collection() 

    category_repo.create_collection_if_not_exists(vector_dim=len(dummy_vector), payload_schema=category_payload)


    print("✅ Colecciones Qdrant listas.")


@app.get("/")
def read_root():
    return {"Hello": "World"}
