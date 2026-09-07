import httpx

from app.db.database import get_database_manager
from app.main import app


class FakeDatabaseManager:
    def __init__(self, connected: bool) -> None:
        self.connected = connected

    async def ping(self) -> bool:
        return self.connected


async def test_ready_returns_connected(client: httpx.AsyncClient) -> None:
    app.dependency_overrides[get_database_manager] = lambda: FakeDatabaseManager(True)
    try:
        response = await client.get("/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "connected"}


async def test_ready_returns_structured_error_when_database_is_unavailable(
    client: httpx.AsyncClient,
) -> None:
    app.dependency_overrides[get_database_manager] = lambda: FakeDatabaseManager(False)
    try:
        response = await client.get("/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "database_unavailable",
            "message": "MongoDB connection is unavailable",
        }
    }

