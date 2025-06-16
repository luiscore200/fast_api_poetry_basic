import os
from fastapi import UploadFile

async def validate_pdf(file: UploadFile) -> str:
    # Validar tamaño
    if file.file._file.tell() > 10 * 1024 * 1024:  # más de 10 MB
        return "El archivo PDF no puede ser mayor de 10 MB."

    # Validar tipo de archivo
    if not file.filename.endswith(".pdf"):
        return "El archivo debe ser un PDF."

    # Aquí puedes añadir más validaciones como si el PDF está cifrado o corrupto

    return None