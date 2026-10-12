"""
Persistence & Data Storage Service.
Manages storage and retrieval of simulation runs and time-series steps.
Operates with in-memory storage for Phase 1 local development while supporting
seamless transition to PostgreSQL / Supabase when configured.
"""

from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.core.logging import logger
from app.schemas.simulation import SimulationRunResponse


class PersistenceService:
    """
    Data access layer for simulation runs and time steps.
    """

    def __init__(self):
        self.is_connected = bool(settings.DATABASE_URL)
        # In-memory dictionary store for local demo mode: run_id -> (run_response, steps)
        self._demo_runs: Dict[str, SimulationRunResponse] = {}
        self._demo_steps: Dict[str, List[Dict[str, Any]]] = {}
        self._demo_assessments: Dict[str, Any] = {}
        logger.info(
            f"Initialized PersistenceService: Database configured={self.is_connected}, "
            f"Local demo in-memory storage active."
        )

    def is_database_ready(self) -> bool:
        return self.is_connected

    def save_simulation_run(
        self,
        run: SimulationRunResponse,
        steps: List[Dict[str, Any]],
    ) -> None:
        """
        Persist a simulation run and its time series steps.
        """
        self._demo_runs[run.run_id] = run
        self._demo_steps[run.run_id] = steps
        logger.info(f"Persisted simulation run {run.run_id} ({len(steps)} steps) in memory")

    def get_simulation_run(self, run_id: str) -> Optional[SimulationRunResponse]:
        """
        Fetch summary metadata for a specific run.
        """
        return self._demo_runs.get(run_id)

    def get_simulation_steps(self, run_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch time series steps for replay or export.
        """
        return self._demo_steps.get(run_id)

    def list_simulation_runs(self) -> List[SimulationRunResponse]:
        """
        List all recorded simulation runs in current session.
        """
        return list(self._demo_runs.values())

    def save_run_assessment(self, run_id: str, assessment: Any) -> None:
        """
        Save Phase 3 contextual assessment for a simulation run.
        """
        self._demo_assessments[run_id] = assessment
        logger.info(f"Persisted assessment for run {run_id}")

    def get_run_assessment(self, run_id: str) -> Optional[Any]:
        """
        Retrieve Phase 3 contextual assessment for a simulation run.
        """
        return self._demo_assessments.get(run_id)

    def list_run_assessments(self) -> List[Any]:
        """
        List all recorded assessments in current session.
        """
        return list(self._demo_assessments.values())


persistence_service = PersistenceService()

