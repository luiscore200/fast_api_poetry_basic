import os
from fastapi import UploadFile
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
# Importaciones para los repositorios
from src.repository.chromadb_repository import save_to_chromadb
# Importación para generar embeddings (ya existente)
from src.services.embedding_service import generate_embeddings


async def process_pdf(empresa_id: str, tags: str, document: UploadFile):
    """
    Procesa un archivo PDF: carga, divide en chunks, genera embeddings,
    guarda chunks/embeddings en ChromaDB y elimina el archivo temporal.
    """
    temp_file_path = f"temp_{document.filename}"
    
    try:
        # 1. Guardar el archivo temporalmente
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(await document.read())

        # 2. Cargar el PDF utilizando Langchain
        loader = PyPDFLoader(temp_file_path)
        documents = loader.load()

        # 3. Dividir contenido en chunks
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=50)
        chunks = text_splitter.split_documents(documents)

        # 4. Preparar datos y generar embeddings para Chroma DB
        chunks_list = []
        embeddings_list = []
        metadata_list = []
        for i, chunk in enumerate(chunks):
            metadata = {
                "source": document.filename,
                "empresa_id": empresa_id,
                "tags": [tag.strip() for tag in tags.split(',')] if tags else [], # Convierte la cadena de tags a lista, limpia espacios
                "page": chunk.metadata.get('page', None),
                "chunk_index": i # Usar chunk_index para evitar conflicto con 'chunk' si es usado por Langchain
            }
            embedding = await generate_embeddings(chunk) # generate_embeddings espera un objeto Document
            
            chunks_list.append(chunk.page_content) # Guardar solo el texto del chunk
            embeddings_list.append(embedding)
            metadata_list.append(metadata)

        # 5. Guardar chunks, embeddings y metadata en Chroma DB
        await save_to_chromadb(chunks_list, embeddings_list, metadata_list, empresa_id)

        # 6. Eliminar el archivo temporal
        os.remove(temp_file_path)

        return {"status": "success", "chunks_processed": len(chunks)}

    except Exception as e:
        # Asegurarse de eliminar el archivo temporal si ocurre un error
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise e # Re-lanzar la excepción para que FastAPI la maneje
