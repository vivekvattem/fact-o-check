import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_cors_origins_are_parsed_from_comma_separated_value() -> None:
    settings = Settings(
        mongodb_uri="mongodb://localhost:27017",
        cors_origins="http://localhost:5173, https://example.com",
        _env_file=None,
    )

    assert settings.cors_origin_list == ["http://localhost:5173", "https://example.com"]


def test_cors_origins_reject_wildcard_with_credentials() -> None:
    with pytest.raises(ValidationError, match="explicit origins"):
        Settings(cors_origins="*", _env_file=None)


def test_invalid_mongodb_uri_is_rejected() -> None:
    with pytest.raises(ValidationError, match="mongodb"):
        Settings(mongodb_uri="postgresql://localhost/example", _env_file=None)


def test_mongodb_atlas_uri_is_supported() -> None:
    settings = Settings(
        mongodb_uri="mongodb+srv://user:password@example.mongodb.net",
        _env_file=None,
    )

    assert settings.mongodb_uri.get_secret_value().startswith("mongodb+srv://")


def test_invalid_api_prefix_is_rejected() -> None:
    with pytest.raises(ValidationError, match="must start"):
        Settings(api_prefix="api", _env_file=None)


def test_upload_size_must_be_positive() -> None:
    with pytest.raises(ValidationError, match="greater than 0"):
        Settings(max_upload_size_bytes=0, _env_file=None)
