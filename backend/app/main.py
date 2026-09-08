from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.debug import router as debug_router
from app.api.documents import router as documents_router
from app.api.facts import router as facts_router
from app.api.relations import router as relations_router
from app.api.system import router as system_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.db.database import database_manager


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    await database_manager.connect(settings)
    try:
        yield
    finally:
        await database_manager.close()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(application)
    application.include_router(system_router)
    application.include_router(debug_router, prefix=settings.api_prefix)
    application.include_router(documents_router, prefix=settings.api_prefix)
    application.include_router(facts_router, prefix=settings.api_prefix)
    application.include_router(relations_router, prefix=settings.api_prefix)
    return application


app = create_app()
