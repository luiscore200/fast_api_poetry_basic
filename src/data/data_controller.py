from fastapi import APIRouter, HTTPException
from typing import List
from src.common.types.article_types import Article
from src.common.providers.sqlite_provider import SQLiteProvider
from src.common.services.document_service import DocumentService
from src.common.services.embeddings_service import EmbeddingService
from src.common.types.metadata_types import FullDocumentChunksOutput
from src.common.managers.response_manager import ResponseManager
from src.common.repositories.qdrant_repository import QdrantRepository

# Instancias
sqlite_provider = SQLiteProvider()
document_service = DocumentService() 
embedding_service = EmbeddingService(model_type="local") 
qdrant_repo = QdrantRepository()

router = APIRouter()

@router.post("/")
async def create_article(article: Article):
    try:
        print("📥 Recibido artículo:", article.dict())

        # 1. Insertar el artículo en SQLite
        document_id = sqlite_provider.insert("articles", {
            "tittle": article.title,
            "content": article.content
        })
        print(f"✅ Artículo insertado con ID: {document_id}")

        # 2. Insertar tags y relaciones
        for tag in article.tags:
            existing_tags = sqlite_provider.find("tags", where={"name": tag})
            if existing_tags:
                tag_id = existing_tags[0][0]
            else:
                tag_id = sqlite_provider.insert("tags", {"name": tag})
            sqlite_provider.insert("article_tags", {
                "article_id": document_id,
                "tag_id": tag_id
            })

        # 3. Insertar categorías y relaciones
        for cat in article.categories:
            existing_cats = sqlite_provider.find("categories", where={"name": cat})
            if existing_cats:
                cat_id = existing_cats[0][0]
            else:
                cat_id = sqlite_provider.insert("categories", {"name": cat})
            sqlite_provider.insert("article_categories", {
                "article_id": document_id,
                "category_id": cat_id
            })
            print(f"📂 Categoría '{cat}' insertada con ID: {cat_id}")

        # 4. Chunkear el contenido
        chunks: List[str] = await document_service.split_text(article.content)
        print(f"🧩 Texto dividido en {len(chunks)} chunks")

        # 5. Añadir el título a cada chunk
        chunks_with_title: List[str] = [f"Título: {article.title}\n\n{chunk}" for chunk in chunks]
        print("🏷️ Título añadido a cada chunk")

        # 6. Generar metadatos
        result: FullDocumentChunksOutput = await document_service.generate_metadata_chunks(
            chunks=chunks_with_title,
            base_metadata=article,
            document_id=document_id
        )
        print("📄 Metadata generada para chunks")

        # 7. Generar embeddings
        for chunk in result.chunks:
            embedding_vector = await embedding_service.generate(chunk.content)
            chunk.embedding = embedding_vector
            print(f"🔢 Embedding generado para chunk_id={chunk.chunk_id}")
        

        # 8. Guardar en qdrantDB
        qdrant_repo.insert_chunks(result.chunks)
        print(f"✅ Chunks guardados en qdrantDB")

        return ResponseManager.success(
            data=result.dict(),
            message="Artículo procesado exitosamente",
            status_code=201
        )

    except Exception as e:
        print("❌ Error durante el procesamiento:", str(e))
        return ResponseManager.error(
            message="Error al procesar el artículo",
            details=str(e),
            status_code=500
        )

@router.get("/count-vectors")
async def count_vectors():
    try:
        count = qdrant_repo.collection.count()
        return {"status": "success", "vector_count": count}
    except Exception as e:
        return {"status": "error", "message": str(e)}
