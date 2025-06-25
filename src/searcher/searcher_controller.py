from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.searcher.searcher_service import SearcherService
from src.common.managers.response_manager import ResponseManager

router = APIRouter()
searcher_service = SearcherService()

class SearchQuery(BaseModel):
    request: str
    top_k: int = 3

@router.post("/searcher")
async def search_documents(query: SearchQuery):
    try:
        result = await searcher_service.run_search(
            user_prompt=query.request,
            top_k=query.top_k
        )

        return ResponseManager.success(
            data=result,
            message="Búsqueda completada con éxito"
        )

    except Exception as e:
        print(f"❌ Error en búsqueda: {e}")
        return ResponseManager.error(
            message="Error en la búsqueda semántica",
            details=str(e),
            status_code=500
        )
