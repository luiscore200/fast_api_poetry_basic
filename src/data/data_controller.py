from fastapi import APIRouter, HTTPException, Query
from typing import List
from uuid import uuid4

from src.common.types.article_types import Article
from src.common.providers.sqlite_provider import SQLiteProvider
from src.common.services.document_service import DocumentService
from src.common.services.embeddings_service import EmbeddingService
from src.common.types.metadata_types import FullDocumentChunksOutput
from src.common.managers.response_manager import ResponseManager
from src.common.repositories.qdrant_repository import QdrantORM

# Instancias
sqlite_provider = SQLiteProvider()
document_service = DocumentService() 
embedding_service = EmbeddingService(model_type="local") 
document_repo = QdrantORM("documents")
category_repo = QdrantORM("categories")

router = APIRouter()

@router.post("/")
async def create_article(article: Article):
    try:
        print("📥 Recibido artículo:", article.dict())

        # 1. Insertar artículo
        document_id = sqlite_provider.insert("articles", {
            "tittle": article.title,
            "content": article.content
        })
        print(f"✅ Artículo insertado con ID: {document_id}")

        # 2. Insertar categorías
        category_name_to_id = {}
        for category in article.categories:
            existing = sqlite_provider.find("categories", where={"name": category})
            if existing:
                category_id = existing[0][0]
            else:
                category_id = sqlite_provider.insert("categories", {"name": category})

                # Embedding y metadata para nueva categoría
                vector = await embedding_service.generate(category)
                category_vector_data = {
                    "id": str(uuid4()),
                    "payload":{
                        "category_id": category_id,
                        "content": category,
                    },
                    "vector": vector
                }
                category_repo.insert_points([category_vector_data])
                print(f"📊 Nueva categoría vectorizada e insertada en Qdrant: {category}")

            category_name_to_id[category] = category_id

            sqlite_provider.insert("article_categories", {
                "article_id": document_id,
                "category_id": category_id
            })
            print(f"📂 Categoría '{category}' vinculada con ID: {category_id}")

       # 3. Insertar tags y vincular a múltiples categorías
        for tag in article.tags:
            existing = sqlite_provider.find("tags", where={"name": tag})
            if existing:
                tag_id = existing[0][0]
            else:
                tag_id = sqlite_provider.insert("tags", {"name": tag})
                print(f"🏷️ Tag '{tag}' insertado con ID: {tag_id}")

            # Relacionar tag con todas las categorías del artículo
            for category in article.categories:
                category_id = category_name_to_id[category]
                exists = sqlite_provider.find("tag_categories", where={"tag_id": tag_id, "category_id": category_id})
                if not exists:
                    sqlite_provider.insert("tag_categories", {
                        "tag_id": tag_id,
                        "category_id": category_id
                    })

            # Relacionar con el artículo
            sqlite_provider.insert("article_tags", {
                "article_id": document_id,
                "tag_id": tag_id
            })


        # 4. Chunking
        chunks: List[str] = await document_service.split_text(article.content)
        print(f"🧹 Texto dividido en {len(chunks)} chunks")

        # 5. Título a cada chunk
        chunks_with_title: List[str] = [f"Título: {article.title}\n\n{chunk}" for chunk in chunks]

        # 6. Metadata
        result: FullDocumentChunksOutput = await document_service.generate_metadata_chunks(
            chunks=chunks_with_title,
            base_metadata=article,
            document_id=document_id
        )

        # 7. Embeddings
        for chunk in result.chunks:
            chunk.vector = await embedding_service.generate(chunk.content)

        # 8. Insertar en Qdrant
        points = [
            {
                "id": chunk.chunk_id,
                "vector": chunk.vector,
                "payload": {
                    "content": chunk.content,
                    "original_tags": chunk.original.tags,
                    "original_categories": chunk.original.categories,
                    "generated_tags": chunk.generated.tags,
                    "generated_categories": chunk.generated.categories,
                    "merged_tags": chunk.merged_tags,
                    "merged_categories": chunk.merged_categories,
                    "document_id": chunk.document_id,
                },
            }
            for chunk in result.chunks
        ]

        document_repo.insert_points(points)
        
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


@router.get("/count")
def count_documents(collection: str = Query(..., enum=["document", "category"])):
    try:
        collection_name = "documents" if collection == "document" else "categories"
        qdrant = QdrantORM(collection_name)
        count = qdrant.count_points()
        return {"collection": collection_name, "count": count}
    except Exception as e:
        return {"error": str(e)}    