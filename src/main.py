from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from src.common.managers.response_manager import ResponseManager # Importar ResponseManager

load_dotenv()
app = FastAPI()

# Handler global para excepciones no manejadas
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Maneja excepciones no capturadas y devuelve una respuesta de error estandarizada.
    """
    # Aquí puedes añadir lógica para loggear el error si es necesario
    print(f"Unhandled error: {exc}")

    # Usar ResponseManager para formatear la respuesta de error
    return ResponseManager.error(
        message=f"Ocurrió un error interno del servidor: {exc}",
        status_code=500,
        details=str(exc) # Opcional: incluir detalles de la excepción
    )


@app.get("/")
def read_root():
    return {"Hello": "World"}
