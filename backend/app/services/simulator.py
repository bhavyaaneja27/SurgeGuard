"""
Marketplace Digital Twin Simulation Service.
Coordinates scenario execution, summary metrics computation, and export utilities.
"""

import csv
import io
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import logger
from app.schemas.simulation import (
    ScenarioDefinition,
    ScenarioType,
    SimulationCreateRequest,
    SimulationRunResponse,
    SimulationStepRecord,
    SimulationSummaryMetrics,
)
from app.services.data_generator import data_generator, SCENARIO_METADATA, ZONE_BASELINES
from app.services.persistence import persistence_service


class MarketplaceSimulator:
    """
    Simulation orchestrator for the SurgeGuard Digital Twin.
    """

    def __init__(self):
        logger.info("Initialized MarketplaceSimulator service")

    def get_available_scenarios(self) -> List[ScenarioDefinition]:
        """
        Return the list of standard scenario archetypes available in SurgeGuard.
        """
        scenarios: List[ScenarioDefinition] = []
        for s_type, meta in SCENARIO_METADATA.items():
            scenarios.append(
                ScenarioDefinition(
                    id=f"scenario_{s_type}",
                    name=meta["name"],
                    description=meta["description"],
                    scenario_type=s_type,
                    default_seed=42,
                    default_duration_minutes=120,
                    default_intensity=0.7,
                    supported_zones=list(ZONE_BASELINES.keys()),
                    ground_truth_label=meta["ground_truth_label"],
                )
            )
        return scenarios

    def compute_summary_metrics(
        self, steps: List[Dict[str, Any]]
    ) -> SimulationSummaryMetrics:
        """
        Aggregate operational statistics from generated simulation steps.
        """
        if not steps:
            return SimulationSummaryMetrics(
                average_demand=0.0,
                average_supply=0.0,
                peak_demand=0.0,
                min_supply=0.0,
                total_requests=0,
                total_completed_rides=0,
                fulfillment_rate_pct=0.0,
                average_wait_time_minutes=0.0,
                max_wait_time_minutes=0.0,
                peak_fare_pressure=100.0,
                average_fare_pressure=100.0,
                average_supply_demand_ratio=1.0,
                critical_steps_count=0,
            )

        demands = [s["ride_requests"] for s in steps]
        supplies = [s["available_drivers"] for s in steps]
        completed = [s["completed_rides"] for s in steps]
        wait_times = [s["estimated_wait_time_minutes"] for s in steps]
        fare_pressures = [s["fare_pressure_index"] for s in steps]
        ratios = [s["supply_demand_ratio"] for s in steps]

        total_req = int(sum(demands))
        total_comp = int(sum(completed))
        fulfillment = round((total_comp / max(1, total_req)) * 100.0, 1)

        critical_count = sum(
            1 for s in steps if s["fare_pressure_index"] >= 135.0 or s["estimated_wait_time_minutes"] >= 6.5
        )

        return SimulationSummaryMetrics(
            average_demand=round(float(sum(demands) / len(demands)), 1),
            average_supply=round(float(sum(supplies) / len(supplies)), 1),
            peak_demand=round(float(max(demands)), 1),
            min_supply=round(float(min(supplies)), 1),
            total_requests=total_req,
            total_completed_rides=total_comp,
            fulfillment_rate_pct=fulfillment,
            average_wait_time_minutes=round(float(sum(wait_times) / len(wait_times)), 1),
            max_wait_time_minutes=round(float(max(wait_times)), 1),
            peak_fare_pressure=round(float(max(fare_pressures)), 1),
            average_fare_pressure=round(float(sum(fare_pressures) / len(fare_pressures)), 1),
            average_supply_demand_ratio=round(float(sum(ratios) / len(ratios)), 2),
            critical_steps_count=critical_count,
        )

    def run_simulation(
        self, req: SimulationCreateRequest
    ) -> Tuple[SimulationRunResponse, List[Dict[str, Any]]]:
        """
        Execute simulation, calculate summaries, and persist to storage.
        """
        run_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)

        # Generate deterministic synthetic time series
        step_records = data_generator.generate_scenario_records(
            scenario_type=req.scenario_type,
            zone_id=req.zone_id,
            duration_minutes=req.duration_minutes,
            event_intensity=req.event_intensity,
            seed=req.seed,
        )

        # Add run_id to each step record
        for step in step_records:
            step["run_id"] = run_id

        summary = self.compute_summary_metrics(step_records)
        completed_at = datetime.now(timezone.utc)

        meta = SCENARIO_METADATA.get(
            req.scenario_type, SCENARIO_METADATA["normal_marketplace"]
        )

        run_response = SimulationRunResponse(
            run_id=run_id,
            scenario_id=f"scenario_{req.scenario_type}",
            scenario_name=meta["name"],
            scenario_type=req.scenario_type,
            zone_id=req.zone_id,
            duration_minutes=req.duration_minutes,
            event_intensity=req.event_intensity,
            seed=req.seed,
            status="completed",
            started_at=started_at,
            completed_at=completed_at,
            model_version="v0.1-synthetic",
            data_mode="SYNTHETIC_SIMULATION",
            storage_type="in_memory_demo",
            total_steps=len(step_records),
            summary_metrics=summary,
        )

        # Persist
        persistence_service.save_simulation_run(run_response, step_records)

        return run_response, step_records

    def get_run(self, run_id: str) -> Optional[SimulationRunResponse]:
        return persistence_service.get_simulation_run(run_id)

    def get_run_steps(self, run_id: str) -> Optional[List[Dict[str, Any]]]:
        return persistence_service.get_simulation_steps(run_id)

    def export_run_data(self, run_id: str, format_type: str = "csv") -> Tuple[str, str, str]:
        """
        Returns (content, media_type, filename).
        Uses standard library csv/json for robust zero-dependency export.
        """
        steps = persistence_service.get_simulation_steps(run_id)
        if not steps:
            raise KeyError(f"Simulation run {run_id} not found")

        if format_type.lower() == "json":
            content = json.dumps(steps, indent=2)
            media_type = "application/json"
            filename = f"surgeguard_run_{run_id[:8]}.json"
        else:
            # CSV export using standard library csv.DictWriter
            output = io.StringIO()
            if steps:
                fieldnames = list(steps[0].keys())
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(steps)
            content = output.getvalue()
            media_type = "text/csv"
            filename = f"surgeguard_run_{run_id[:8]}.csv"

        return content, media_type, filename


simulator_service = MarketplaceSimulator()
