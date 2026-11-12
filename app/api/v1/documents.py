#Creates the API endpoints for uploading internal documents and searching them by meaning.
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.rag.retriever import RAGRetriever
from app.schemas.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentSearchRequest,
)

router = APIRouter(prefix="/documents")

#to upload a document (which automatically generates and stores its 384 vector numbers),
@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a document into the pgvector knowledge base",
)
async def ingest_document(
    payload: DocumentCreate,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    chunk = await RAGRetriever.ingest_document(db=db, payload=payload)
    return DocumentResponse.model_validate(chunk)

#one to test semantic vector search directly.
@router.post(
    "/search",
    response_model=list[DocumentResponse],
    status_code=status.HTTP_200_OK,
    summary="Search documents by meaning using cosine similarity",
)
async def search_documents(
    payload: DocumentSearchRequest,
    db: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    chunks = await RAGRetriever.search_similar(
        db=db,
        query=payload.query,
        top_k=payload.top_k,
    )
    return [DocumentResponse.model_validate(chunk) for chunk in chunks]