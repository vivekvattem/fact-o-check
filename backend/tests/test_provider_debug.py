from app.api import debug
from app.core.config import Settings, get_settings
from app.main import app
from app.services.fact_extractor import ExtractorError


class FailingExtractor:
    def __init__(self) -> None:
        self.calls = 0

    async def extract(self, window):
        self.calls += 1
        raise ExtractorError(
            "provider_unavailable",
            http_status=401,
            error_type="authentication_error",
            safe_message="Invalid API credentials",
        )


async def test_provider_smoke_requires_token_and_returns_safe_failure(client, monkeypatch):
    configured = Settings(
        _env_file=None,
        llm_provider="openrouter",
        llm_model="openai/gpt-4.1-nano",
        openrouter_api_key="not-returned",
        debug_token="debug-secret",
    )
    extractor = FailingExtractor()
    app.dependency_overrides[get_settings] = lambda: configured
    monkeypatch.setattr(debug, "get_fact_extractor", lambda settings: extractor)
    try:
        assert (await client.post("/api/debug/provider-smoke")).status_code == 401
        assert (
            await client.post(
                "/api/debug/provider-smoke", headers={"X-Debug-Token": "wrong-token"}
            )
        ).status_code == 401
        response = await client.post(
            "/api/debug/provider-smoke", headers={"X-Debug-Token": "debug-secret"}
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "success": False,
        "provider": "openrouter",
        "model": "openai/gpt-4.1-nano",
        "http_status": 401,
        "error_type": "authentication_error",
        "message": "Invalid API credentials",
    }
    assert extractor.calls == 1
    assert "not-returned" not in response.text
    assert "debug-secret" not in response.text
