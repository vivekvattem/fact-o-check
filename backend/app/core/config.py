from enum import StrEnum
from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(StrEnum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: AppEnvironment = AppEnvironment.DEVELOPMENT
    app_name: str = "Fact-O-Check"
    api_prefix: str = "/api"
    mongodb_uri: SecretStr = SecretStr("mongodb://localhost:27017")
    mongodb_db_name: str = "fact_o_check"
    cors_origins: str = "http://localhost:5173"
    max_upload_size_bytes: int = Field(default=25 * 1024 * 1024, gt=0)
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: SecretStr = SecretStr("")
    openrouter_api_key: SecretStr = SecretStr("")
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_http_referer: str | None = None
    openrouter_x_title: str | None = "Fact-O-Check"
    debug_token: SecretStr = SecretStr("")
    llm_timeout_seconds: float = Field(default=45, gt=0, le=120)
    extraction_window_chars: int = Field(default=12000, ge=500, le=50000)
    extraction_window_chunks: int = Field(default=20, ge=1, le=100)
    extraction_max_windows: int = Field(default=30, ge=1, le=100)
    extraction_max_output_tokens: int = Field(default=4000, ge=256, le=16000)

    @field_validator("app_name", "mongodb_db_name")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("api_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        if not value.startswith("/"):
            raise ValueError("must start with '/'")
        return value

    @field_validator("mongodb_uri")
    @classmethod
    def validate_mongodb_uri(cls, value: SecretStr) -> SecretStr:
        uri = value.get_secret_value()
        if not uri.startswith(("mongodb://", "mongodb+srv://")):
            raise ValueError("must be a mongodb:// or mongodb+srv:// URI")
        return value

    @field_validator("llm_provider")
    @classmethod
    def normalize_llm_provider(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        if not origins:
            raise ValueError("must contain at least one origin")
        if "*" in origins:
            raise ValueError("must list explicit origins when credentials are enabled")
        return ",".join(origins)

    @field_validator("openrouter_base_url")
    @classmethod
    def validate_openrouter_base_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        if not value.startswith(("http://", "https://")):
            raise ValueError("must be an http:// or https:// URL")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
