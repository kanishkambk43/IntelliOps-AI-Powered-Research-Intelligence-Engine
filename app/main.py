from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text

from app.core.config import settings
from app.api.v1 import health, research
from app.db.base import Base
from app.db.session import engine
from app.models import research as research_model  # noqa: F401
from app.models import document as document_model  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Runs right BEFORE the server starts taking requests ---
    async with engine.begin() as conn:
        # 1. Turn on the pgvector extension inside PostgreSQL
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # 2. Create all tables (research_tasks and document_chunks)
        await conn.run_sync(Base.metadata.create_all)
    yield
    # --- Runs right AFTER the server shuts down ---
    await engine.dispose()


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        lifespan=lifespan,
    )

    # Plug in the v1 routers
    application.include_router(
        health.router,
        prefix=settings.API_V1_PREFIX,
        tags=["System Health"],
    )
    application.include_router(
        research.router,
        prefix=settings.API_V1_PREFIX,
        tags=["Research Intelligence"],
    )

    return application


app = create_application()