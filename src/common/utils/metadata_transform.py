import uuid # Importar uuid
from typing import List,Dict, Union



def generate_unique_chunk_id() -> str:
    """
    Genera un ID de chunk único usando UUID v4.
    """
    return str(uuid.uuid4()) # Generar UUID y convertir a string
