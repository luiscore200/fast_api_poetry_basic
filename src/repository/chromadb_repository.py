import chromadb
from typing import List, Dict, Any

# Configurar el cliente de ChromaDB
# Puedes usar un cliente persistente para guardar los datos en disco
# Asegúrate de que el directorio 'chroma_db_data' exista o sea creado
client = chromadb.PersistentClient(path="./chroma_db_data")

async def save_to_chromadb(
    chunks_list: List[str],
    embeddings_list: List[List[float]], # Asumiendo que los embeddings son List[float]
    metadata_list: List[Dict[str, Any]],
    empresa_id: str
):
    """
    Guarda una lista de chunks, sus embeddings y metadatos en una colección de ChromaDB
    específica para la empresa.

    Args:
        chunks_list: Lista de cadenas de texto de los chunks.
        embeddings_list: Lista de embeddings correspondientes a los chunks.
        metadata_list: Lista de diccionarios de metadatos correspondientes a los chunks.
        empresa_id: ID de la empresa para nombrar la colección.
    """
    collection_name = f"empresa_{empresa_id}"

    try:
        # Obtener o crear la colección
        collection = client.get_or_create_collection(name=collection_name)

        # Preparar IDs únicos para cada documento
        # Una estrategia simple es usar un índice, o combinar source, page y chunk_index
        # Asegúrate de que los IDs sean únicos dentro de la colección
        ids = [f"{metadata['source']}_page{metadata.get('page', 'N/A')}_chunk{metadata.get('chunk_index', i)}"
               for i, metadata in enumerate(metadata_list)]

        # Añadir los datos a la colección
        collection.add(
            embeddings=embeddings_list,
            documents=chunks_list,
            metadatas=metadata_list,
            ids=ids
        )
        print(f"Guardados {len(chunks_list)} chunks en la colección '{collection_name}' de ChromaDB.")

    except Exception as e:
        print(f"Error al guardar en ChromaDB: {e}")
        # Dependiendo del caso, podrías querer lanzar la excepción
        raise e

# TODO: Considerar estrategias de manejo de IDs más robustas si es necesario.
# TODO: Implementar manejo de errores y reintentos.
# TODO: Considerar la estrategia de inicialización del cliente (persistente vs en memoria, ubicación).
