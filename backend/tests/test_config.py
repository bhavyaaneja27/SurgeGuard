from app.core.config import Settings


def test_cors_origins_parsing():
    """
    Ensure CORS origins accept string comma-separated and list formats.
    """
    settings_custom = Settings(
        CORS_ORIGINS="http://localhost:3000, http://example.com"
    )
    assert "http://localhost:3000" in settings_custom.CORS_ORIGINS
    assert "http://example.com" in settings_custom.CORS_ORIGINS
    assert isinstance(settings_custom.CORS_ORIGINS, list)


def test_default_settings():
    """
    Verify reproducible default seed and local demo database setting.
    """
    settings_default = Settings()
    assert settings_default.DEFAULT_RANDOM_SEED == 42
    assert settings_default.USE_LOCAL_DEMO_DB is True
    assert settings_default.API_V1_PREFIX == "/api/v1"
