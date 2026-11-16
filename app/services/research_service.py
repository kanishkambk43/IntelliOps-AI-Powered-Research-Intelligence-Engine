#it actually talks to PostgreSQL, saves the task, runs the business logic (and later, triggers LangGraph), and hands the finished result back to the receptionist(api).
#Keeps all database operations and future AI orchestration logic inside the services layer instead of cluttering our API routes.
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.research_graph import research_graph
from app.models.research import ResearchTask
from app.schemas.research import ResearchRequest


class ResearchService:
    @staticmethod
    async def create_task(db: AsyncSession, payload: ResearchRequest) -> ResearchTask:
        # 1. Package the user question and database session into our LangGraph state clipboard
        # 1. Package the user question and database session into our LangGraph state clipboard
        initial_state = {
            "original_query": payload.query,
            "search_query": payload.query,
            "db": db,
            "context": [],
            "retry_count": 0,
            "is_relevant": False,
            "report": "",
        }

        # 2. Run the LangGraph workflow (Finds docs -> Gemini writes report)
        final_state = await research_graph.ainvoke(initial_state)
        ai_report = final_state.get("report", "Error: Failed to generate report.")

        # 3. Save the final AI report permanently into PostgreSQL
        new_task = ResearchTask(
            query=payload.query,
            status="completed",
            result=ai_report,
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