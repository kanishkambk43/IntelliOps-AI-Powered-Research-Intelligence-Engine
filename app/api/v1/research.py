import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.research import ResearchRequest, ResearchResponse
from app.services.research_service import ResearchService

router = APIRouter(prefix="/research")

# ==========================================
# GOAL: Start a new AI Research Job
# SIMPLE EXPLANATION: When you type a question and hit "Enter", 
# this endpoint catches it, runs the LangGraph AI workflow, 
# saves the final AI answer to the PostgreSQL database, and 
# returns it to your screen.
# ==========================================
@router.post(
    "",
    response_model=ResearchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new research query",
)
async def create_research_task(
    payload: ResearchRequest,
    db: AsyncSession = Depends(get_db),
) -> ResearchResponse:
    task = await ResearchService.create_task(db=db, payload=payload)
    return ResearchResponse.model_validate(task)


# ==========================================
# GOAL: Build a "History Dashboard" Sidebar
# SIMPLE EXPLANATION: This grabs a list of all your past AI 
# reports from the database. When you eventually build a web UI, 
# this endpoint is what powers the sidebar showing your past 
# searches (exactly like ChatGPT's history sidebar).
# ==========================================
@router.get(
    "",
    response_model=list[ResearchResponse],
    status_code=status.HTTP_200_OK,
    summary="List recent research tasks",
)
async def list_research_tasks(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> list[ResearchResponse]:
    # Using list_tasks here to match your actual ResearchService method name
    tasks = await ResearchService.list_tasks(db=db, limit=limit)
    return [ResearchResponse.model_validate(task) for task in tasks]


# ==========================================
# GOAL: Load one specific old report
# SIMPLE EXPLANATION: If you click on an old search in your 
# history sidebar, this endpoint uses that specific UUID to 
# fetch just that one report from the database and display 
# it back on your screen.
# ==========================================
@router.get(
    "/{task_id}",
    response_model=ResearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a specific research task by ID",
)
async def get_research_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ResearchResponse:
    task = await ResearchService.get_task_by_id(db=db, task_id=task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research task with ID '{task_id}' not found.",
        )
    return ResearchResponse.model_validate(task)


# ==========================================
# GOAL: Delete a specific old report to clean up junk tests
# SIMPLE EXPLANATION: If you click the "trash" icon on a report in your 
# history, this endpoint tells the database to permanently erase it.
# ==========================================
@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a research task",
)
async def delete_research_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    success = await ResearchService.delete_task(db=db, task_id=task_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research task with ID '{task_id}' not found.",
        )
    return None