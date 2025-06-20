from typing import Any

class EmbeddingServiceError(Exception):
    """Excepción personalizada para errores en el servicio de embeddings."""
    def __init__(self, message: str, details: Any = None):
        self.message = message
        self.details = details
        super().__init__(message)

# Puedes añadir otras excepciones personalizadas aquí si es necesario
# class AnotherCustomError(Exception):
#     ...
