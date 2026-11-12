from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import DocumentChunk
from app.rag.embeddings import get_embedding_service
from app.schemas.document import DocumentCreate


class RAGRetriever:
    @staticmethod
    async def ingest_document( #takes a plain-English document from the user, calls your EmbeddingService to turn it into 384 numbers, and saves both the text and the numbers into PostgreSQL.
        db: AsyncSession,
        payload: DocumentCreate,
    ) -> DocumentChunk:
        # 1. Convert the document content into a 384-dimensional vector
        embedding_service = get_embedding_service()
        vector = embedding_service.embed_text(payload.content)

        # 2. Create the database row with both text and vector numbers
        chunk = DocumentChunk(
            title=payload.title,
            source=payload.source,
            content=payload.content,
            embedding=vector,
        )

        # 3. Save permanently into PostgreSQL
        db.add(chunk)
        await db.commit()
        await db.refresh(chunk)

        return chunk

    @staticmethod
    async def search_similar( # takes a user's question, turns the question into 384 numbers, and asks PostgreSQL pgvector to find the documents whose numbers are mathematically closest in meaning (Cosine Distance)!
        db: AsyncSession,
        query: str,
        top_k: int = 3,
    ) -> list[DocumentChunk]:
        # 1. Convert the user's search question into a 384-dimensional vector
        embedding_service = get_embedding_service()
        query_vector = embedding_service.embed_text(query)

        # 2. Ask pgvector to order all documents by Cosine Distance (closest meaning first!)
        stmt = (
            select(DocumentChunk)
            .order_by(DocumentChunk.embedding.cosine_distance(query_vector))
            .limit(top_k)
        )

        result = await db.execute(stmt)
        return list(result.scalars().all())