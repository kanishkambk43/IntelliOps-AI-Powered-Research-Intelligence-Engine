import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.research import ResearchRequest, ResearchResponse
from app.services.research_service import ResearchService

router = APIRouter(prefix="/research")


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
    tasks = await ResearchService.list_tasks(db=db, limit=limit)
    return [ResearchResponse.model_validate(task) for task in tasks]


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