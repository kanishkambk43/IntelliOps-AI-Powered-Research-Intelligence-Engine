from fastapi import FastAPI
from app.core.config import settings
from app.api.v1 import health


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    )

    # Plug in the v1 health router
    application.include_router(
        health.router,
        prefix=settings.API_V1_PREFIX,
        tags=["System Health"],
    )

    return application


app = create_application()