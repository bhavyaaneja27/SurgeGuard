from datetime import datetime, timezone
import os
from fastapi import APIRouter
from app.core.config import settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])

_ARTIFACT_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "models", "artifacts"
)


def _artifacts_present() -> bool:
    """Return True if Phase 2/3 model artifacts exist on disk."""
    required = ["forecaster.pkl", "isolation_forest.pkl"]
    return all(
        os.path.isfile(os.path.join(_ARTIFACT_DIR, f)) for f in required
    )


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """
    Health check and service readiness endpoint.
    Conforms to PRD Section 12 contract:
    Returns status, version, model_status, database_status, and UTC timestamp.

    model_status semantics:
      loaded       — Phase 2/3 artifacts present and services initialised (demo mode)
      not_loaded   — Artifacts missing; system cannot run anomaly detection
      fallback     — Artifacts exist but a non-critical load warning occurred
    """
    model_status = "loaded" if _artifacts_present() else "not_loaded"
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        model_status=model_status,
        database_status="local_demo_mode" if settings.USE_LOCAL_DEMO_DB else "connected",
        timestamp=datetime.now(timezone.utc)
    )
