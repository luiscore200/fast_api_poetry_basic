import asyncio
from typing import List, Dict,Optional
from anyio import to_thread
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.common.types.metadata_types import ChunkOutput, FullDocumentChunksOutput,Metadata
from src.common.types.article_types import Article

class DocumentService:
    def __init__(self):
        pass

    async def split_text(
        self,
        text: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[str]:
        """
        Divide un string de texto en chunks planos.

        Args:
            text: Texto a dividir.
            chunk_size: Tamaño del chunk.
            chunk_overlap: Solapamiento entre chunks.

        Returns:
            Lista de strings (chunks de texto).
        """
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
       
        documents = await to_thread.run_sync(text_splitter.create_documents, [text])
        return [doc.page_content for doc in documents]

    async def generate_metadata_chunks(
        self,
        chunks: List[str],
        base_metadata: Article,
        document_id: int,
        generated_metadata: Optional[Metadata] = None
        
    ) -> FullDocumentChunksOutput:
        """
        Genera la salida estructurada con metadatos a partir de chunks planos.

        Args:
            chunks: Lista de strings que representan los fragmentos del documento.
            base_metadata: Diccionario base con metadatos (tags, categorías, etc).
            document_id: ID del documento original en la base de datos.

        Returns:
            FullDocumentChunksOutput con metadata.
        """
        outputs = [
        ChunkOutput(
            chunk_id=i,
            document_id=document_id,
            content=chunk,
            original={
                "tags": base_metadata.tags,
                "categories": base_metadata.categories
            },
            generated=generated_metadata if generated_metadata else Metadata(),
            merged_tags=(
                list(set(base_metadata.tags + generated_metadata.tags))
                if generated_metadata else base_metadata.tags
            ),
            merged_categories=(
                list(set(base_metadata.categories + generated_metadata.categories))
                if generated_metadata else base_metadata.categories
            )
        )
        for i, chunk in enumerate(chunks)
        ]
        return FullDocumentChunksOutput(
            enriched_description=" ",#.join(chunks),
            chunks=outputs
        )
