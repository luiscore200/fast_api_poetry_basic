from fastapi.responses import JSONResponse
from typing import Any, Dict

class ResponseManager:
    @staticmethod
    def success(data: Any = None, message: str = "Operación exitosa", status_code: int = 200) -> JSONResponse:
        """Genera una respuesta de éxito estandarizada."""
        response_content = {
            "status": "success",
            "message": message,
            "data": data
        }
        return JSONResponse(content=response_content, status_code=status_code)

    @staticmethod
    def error(message: str = "Ocurrió un error", status_code: int = 500, details: Any = None) -> JSONResponse:
        """Genera una respuesta de error estandarizada."""
        response_content = {
            "status": "error",
            "message": message,
            "details": details
        }
        return JSONResponse(content=response_content, status_code=status_code)
