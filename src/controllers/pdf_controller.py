from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from src.validators.pdf_validator import validate_pdf
from src.services.pdf_service import process_pdf

router = APIRouter()

@router.post("/upload-pdf/")
async def upload_pdf(
    id: str = Form(...),
    tags: str = Form(...),
    documents: UploadFile = File(...)
):
    # Validar el archivo PDF
    error_message = await validate_pdf(documents)
    if error_message:
        raise HTTPException(status_code=400, detail=error_message)

    # Procesar el PDF
    metadata_list = await process_pdf(id, tags, documents)
    
    return metadata_list