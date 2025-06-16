from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from src.repositories.chromadb_repository import save_to_chromadb

async def process_pdf(empresa_id: str, tags: str, document: UploadFile):
    # Guardar el archivo temporalmente
    temp_file_path = f"temp_{document.filename}"
    with open(temp_file_path, "wb") as temp_file:
        temp_file.write(await document.read())

    # Cargar el PDF utilizando Langchain
    loader = PyPDFLoader(temp_file_path)
    documents = loader.load()

    # Dividir contenido en chunks
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=50)
    chunks = text_splitter.split_documents(documents)

    # Anexar metadata y guardar en Chroma DB
    metadata_list = []
    for i, chunk in enumerate(chunks):
        metadata = {
            "source": document.filename,
            "empresa_id": empresa_id,
            "tags": tags.split(','),  # Convierte la cadena de tags a lista
            "page": chunk.metadata.get('page', None),  # Ajusta según la metadata
            "chunk": i
        }
        # Guardar en Chroma DB
        await save_to_chromadb(metadata, chunk)  # Implementa la función en el repositorio
        
        metadata_list.append(metadata)

    return metadata_list