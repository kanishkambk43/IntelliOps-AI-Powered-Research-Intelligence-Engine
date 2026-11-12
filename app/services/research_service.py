#it actually talks to PostgreSQL, saves the task, runs the business logic (and later, triggers LangGraph), and hands the finished result back to the receptionist(api).
#Keeps all database operations and future AI orchestration logic inside the services layer instead of cluttering our API routes.
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research import ResearchTask
from app.rag.retriever import RAGRetriever
from app.schemas.research import ResearchRequest


class ResearchService:
    @staticmethod
    async def create_task(db: AsyncSession, payload: ResearchRequest) -> ResearchTask:
        # 1. Search the pgvector knowledge base for relevant company documents
        matched_docs = await RAGRetriever.search_similar(
            db=db,
            query=payload.query,
            top_k=2,
        )

        # 2. Format retrieved context so we can see RAG working before plugging in LangGraph
        if matched_docs:
            sources_summary = "\n".join(
                f"- [{doc.title} ({doc.source})]: {doc.content}"
                for doc in matched_docs
            )
            report_text = (
                f"Retrieved {len(matched_docs)} relevant knowledge base chunk(s) for '{payload.query}':\n"
                f"{sources_summary}"
            )
        else:
            report_text = (
                f"No internal documents found yet for '{payload.query}'. "
                "Upload documents via POST /api/v1/documents first."
            )

        # 3. Create and save the research task with the retrieved RAG context
        new_task = ResearchTask(
            query=payload.query,
            status="completed",
            result=report_text,
        )

        db.add(new_task)
        await db.commit()
        await db.refresh(new_task)

        return new_task

    @staticmethod
    async def get_task_by_id(db: AsyncSession, task_id: uuid.UUID) -> ResearchTask | None:
        stmt = select(ResearchTask).where(ResearchTask.id == task_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_tasks(db: AsyncSession, limit: int = 20) -> list[ResearchTask]:
        stmt = select(ResearchTask).order_by(ResearchTask.created_at.desc()).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())