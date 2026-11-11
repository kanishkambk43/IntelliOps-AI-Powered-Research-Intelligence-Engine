#it actually talks to PostgreSQL, saves the task, runs the business logic (and later, triggers LangGraph), and hands the finished result back to the receptionist(api).
#Keeps all database operations and future AI orchestration logic inside the services layer instead of cluttering our API routes.
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research import ResearchTask
from app.schemas.research import ResearchRequest


class ResearchService:
    @staticmethod
    async def create_task(db: AsyncSession, payload: ResearchRequest) -> ResearchTask:
        # 1. Create a new database row object with the user's question
        new_task = ResearchTask(
            query=payload.query,
            status="completed",
            result=(
                f"[Placeholder Report] Research pipeline initialized for: '{payload.query}'. "
                "LangGraph multi-agent orchestration will be plugged in here next."
            ),
        )

        # 2. Add to the database session and save permanently (commit)
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