import logging
from typing import Any

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import Settings
from app.db.registry import DOCUMENT_MODELS

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self) -> None:
        self.client: AsyncIOMotorClient[dict[str, Any]] | None = None
        self.database: AsyncIOMotorDatabase[dict[str, Any]] | None = None

    async def connect(self, settings: Settings) -> None:
        logger.info("Initializing MongoDB connection")
        self.client = AsyncIOMotorClient(
            settings.mongodb_uri.get_secret_value(),
            serverSelectionTimeoutMS=5_000,
            appname=settings.app_name,
        )
        self.database = self.client[settings.mongodb_db_name]
        try:
            await self.client.admin.command("ping")
            await init_beanie(database=self.database, document_models=DOCUMENT_MODELS)
        except Exception:
            self.client.close()
            self.client = None
            self.database = None
            logger.exception("MongoDB initialization failed")
            raise
        logger.info("MongoDB connection initialized")

    async def ping(self) -> bool:
        if self.client is None:
            return False
        try:
            await self.client.admin.command("ping")
        except Exception:
            logger.warning("MongoDB readiness check failed", exc_info=True)
            return False
        return True

    async def close(self) -> None:
        if self.client is not None:
            self.client.close()
        self.client = None
        self.database = None
        logger.info("MongoDB connection closed")


database_manager = DatabaseManager()


def get_database_manager() -> DatabaseManager:
    return database_manager

