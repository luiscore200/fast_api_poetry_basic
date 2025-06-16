async def save_to_chromadb(metadata, chunk):
    embeddings = await generate_embeddings(chunk)  # Generar embeddings para el chunk
    # Aquí implementa la lógica para guardar en Chroma DB
    # Puedes usar la API de ChromaDB según su documentación