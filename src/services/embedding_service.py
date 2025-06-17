# embedding_service.py

from langchain_community.embeddings import SentenceTransformerEmbeddings

async def generate_embeddings(chunk):
    # Usando SentenceTransformerEmbeddings para el modelo 'intfloat/e5-small-v2'
    model = SentenceTransformerEmbeddings(model_name='intfloat/e5-small-v2')
    embedding = await model.embed_query(chunk.page_content) # Usar embed_query para obtener el embedding de un solo texto
    return embedding
