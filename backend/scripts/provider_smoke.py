"""Make one synthetic request through the configured fact provider adapter."""

import asyncio

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.services.fact_extractor import EvidenceContext, ExtractorError, get_fact_extractor


async def main() -> None:
    configure_logging()
    settings = get_settings()
    base_url = settings.openrouter_base_url if settings.llm_provider == "openrouter" else "default"
    print(
        f"provider={settings.llm_provider} model={settings.llm_model} "
        f"base_url={base_url}"
    )
    try:
        extractor = get_fact_extractor(settings)
    except AppError as exc:
        print(f"result={exc.code} message={exc.message}")
        raise SystemExit(1) from None
    try:
        await extractor.extract(
            (EvidenceContext("provider-smoke-test", 1, "Fact-O-Check provider smoke test."),)
        )
    except ExtractorError as exc:
        print(f"result={exc}")
        raise SystemExit(1) from exc
    print("result=ok")


if __name__ == "__main__":
    asyncio.run(main())
