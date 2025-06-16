# embedding_service.py

from langchain.embeddings import LangchainEmbedding

async def generate_embeddings(chunk):
    # Asumiendo que `LangchainEmbedding` es el modelo que deseas usar
    model = LangchainEmbedding.from_pretrained('intfloat/e5-small-v2')
    embedding = await model.get_embedding(chunk.content)  # Ajusta esto según cómo se accede al contenido del chunk
    return embedding
    return embeddings