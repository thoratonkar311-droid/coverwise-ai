from app.core.config import Settings


def test_settings_defaults() -> None:
    """Verify default configurations adhere to project specifications."""
    default_db_url = Settings.model_fields["DATABASE_URL"].default
    assert "coverwise" in default_db_url

    settings = Settings()
    assert settings.ENVIRONMENT == "development"
    assert settings.is_development is True
    assert settings.is_production is False
    assert settings.API_V1_STR == "/api"
    assert settings.SECRET_KEY == "change_this_value"



def test_cors_origins_parsing_comma_separated() -> None:
    """Verify CORS origins string is correctly parsed into a list."""
    settings = Settings(ALLOWED_ORIGINS="http://localhost:3000, https://coverwise.ai")
    assert "http://localhost:3000" in settings.ALLOWED_ORIGINS
    assert "https://coverwise.ai" in settings.ALLOWED_ORIGINS


def test_cors_origins_parsing_json_list() -> None:
    """Verify CORS origins JSON list string is parsed properly."""
    settings = Settings(ALLOWED_ORIGINS='["http://localhost:3000", "http://localhost:3001"]')
    assert settings.ALLOWED_ORIGINS == ["http://localhost:3000", "http://localhost:3001"]


def test_production_environment_flag() -> None:
    """Verify is_production property responds to ENVIRONMENT variable."""
    settings = Settings(ENVIRONMENT="production")
    assert settings.is_production is True
    assert settings.is_development is False
