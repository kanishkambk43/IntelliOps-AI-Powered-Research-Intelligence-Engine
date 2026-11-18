#it actually talks to PostgreSQL, saves the task, runs the business logic (and later, triggers LangGraph), and hands the finished result back to the receptionist(api).
#Keeps all database operations and future AI orchestration logic inside the services layer instead of cluttering our API routes.
import time
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.research_graph import research_graph
from app.models.research import ResearchTask
from app.schemas.research import ResearchRequest

class ResearchService:
    @staticmethod
    async def create_task(db: AsyncSession, payload: ResearchRequest) -> ResearchTask:
        initial_state = {
            "original_query": payload.query,
            "search_query": payload.query,
            "db": db,
            "context": [],
            "sources": [],
            "retry_count": 0,
            "is_relevant": False,
            "report": "",
        }

        # --- Start the Stopwatch ---
        start_time = time.perf_counter()

        # Run the multi-step LangGraph workflow
        final_state = await research_graph.ainvoke(initial_state)

        # --- Stop the Stopwatch ---
        end_time = time.perf_counter()
        total_time = round(end_time - start_time, 2)

        new_task = ResearchTask(
            query=payload.query,
            status="completed",
            result=final_state["report"],
            rewritten_query=final_state.get("search_query", payload.query),
            sources=final_state.get("sources", []),
            execution_time_seconds=total_time,
        )
        
        db.add(new_task)
        await db.commit()
        await db.refresh(new_task)

        return new_task

    @staticmethod
    async def get_task_by_id(db: AsyncSession, task_id: UUID) -> ResearchTask | None:
        stmt = select(ResearchTask).where(ResearchTask.id == task_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_tasks(db: AsyncSession, limit: int = 20) -> list[ResearchTask]:
        """Fetch the most recent research tasks for the history dashboard."""
        stmt = select(ResearchTask).order_by(ResearchTask.created_at.desc()).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def delete_task(db: AsyncSession, task_id: UUID) -> bool:
        stmt = select(ResearchTask).where(ResearchTask.id == task_id)
        result = await db.execute(stmt)
        task = result.scalar_one_or_none()
        
        if not task:
            return False
            
        await db.delete(task)
        await db.commit()
        return True