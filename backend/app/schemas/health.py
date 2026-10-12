from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """
    Health check response model conforming to PRD Section 12.
    """
    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        default="healthy",
        description="Current health status of the service"
    )
    version: str = Field(..., description="Service version string")
    model_status: Literal["ready", "loaded", "not_loaded", "fallback"] = Field(
        default="not_loaded",
        description="ML model availability status"
    )
    database_status: Literal["connected", "disconnected", "local_demo_mode"] = Field(
        default="local_demo_mode",
        description="Database readiness status"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Current UTC timestamp of the health check"
    )
