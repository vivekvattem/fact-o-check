from collections.abc import AsyncIterator

import httpx
import pytest
from beanie import init_beanie
from mongomock_motor import AsyncMongoMockClient

from app.db.registry import DOCUMENT_MODELS
from app.main import app


@pytest.fixture(autouse=True)
async def initialize_test_models() -> AsyncIterator[None]:
    mongo_client = AsyncMongoMockClient()
    await init_beanie(
        database=mongo_client.fact_o_check_test,
        document_models=DOCUMENT_MODELS,
    )
    yield
    mongo_client.close()


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
