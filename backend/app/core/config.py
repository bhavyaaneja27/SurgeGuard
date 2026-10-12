import json
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    SurgeGuard Application Settings.
    Loaded from environment variables with sensible development defaults.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    APP_NAME: str = "SurgeGuard — Marketplace Integrity Intelligence"
    APP_VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # CORS configuration: accept list of strings or comma-separated string
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    # Database Configuration (Optional for Phase 0 local dev)
    DATABASE_URL: str = ""
    USE_LOCAL_DEMO_DB: bool = True

    # ML & Simulation Settings
    MODEL_ARTIFACTS_DIR: str = "app/models/artifacts"
    DEFAULT_RANDOM_SEED: int = 42

    # Optional Copilot (Gemini API key must stay server-side)
    GEMINI_API_KEY: str = ""


settings = Settings()
