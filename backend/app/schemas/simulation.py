from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


ScenarioType = Literal[
    "normal_marketplace",
    "demand_led_surge",
    "natural_shortage",
    "unusual_supply_drop",
]

DataMode = Literal[
    "SYNTHETIC_SIMULATION",
    "HISTORICAL_CONTEXT",
    "MODEL_OUTPUT"
]


class ScenarioDefinition(BaseModel):
    id: str = Field(..., description="Unique scenario identifier")
    name: str = Field(..., description="Display name of scenario")
    description: str = Field(..., description="Explanation of dynamics and assumptions")
    scenario_type: ScenarioType = Field(..., description="Archetype of scenario")
    default_seed: int = 42
    default_duration_minutes: int = 120
    default_intensity: float = 0.7
    supported_zones: List[str] = Field(
        default_factory=lambda: [
            "zone_midtown_core",
            "zone_downtown_financial",
            "zone_airport_terminal",
            "zone_uptown_residential",
        ]
    )
    ground_truth_label: str = Field(
        ...,
        description="Ground-truth label for offline evaluation only (not real-world driver behavior)"
    )


class SimulationCreateRequest(BaseModel):
    scenario_type: ScenarioType = Field(..., description="Scenario archetype")
    zone_id: str = Field(default="zone_midtown_core", description="Target zone identifier")
    duration_minutes: int = Field(default=120, ge=30, le=480, description="Simulation duration in steps/minutes")
    event_intensity: float = Field(default=0.7, ge=0.1, le=1.0, description="Intensity factor for shocks (0.1 to 1.0)")
    seed: int = Field(default=42, description="Random seed for deterministic reproducibility")


class SimulationStepRecord(BaseModel):
    step_number: int
    timestamp: str
    zone_id: str
    scenario_id: str
    scenario_type: ScenarioType
    random_seed: int
    ride_requests: float
    available_drivers: float
    completed_rides: int
    unfulfilled_requests: int
    estimated_wait_time_minutes: float
    fare_pressure_index: float  # Baseline 100.0
    supply_demand_ratio: float
    driver_earnings_index: float  # Baseline 100.0
    context_type: str
    ground_truth_label: str
    annotation: Optional[str] = None

    # Convenience aliases for frontend compatibility
    @property
    def demand(self) -> float:
        return self.ride_requests

    @property
    def available_supply(self) -> float:
        return self.available_drivers


SimulationStep = SimulationStepRecord


class SimulationSummaryMetrics(BaseModel):
    average_demand: float
    average_supply: float
    peak_demand: float
    min_supply: float
    total_requests: int
    total_completed_rides: int
    fulfillment_rate_pct: float
    average_wait_time_minutes: float
    max_wait_time_minutes: float
    peak_fare_pressure: float
    average_fare_pressure: float
    average_supply_demand_ratio: float
    critical_steps_count: int


class SimulationRunResponse(BaseModel):
    run_id: str
    scenario_id: str
    scenario_name: str
    scenario_type: ScenarioType
    zone_id: str
    duration_minutes: int
    event_intensity: float
    seed: int
    status: Literal["completed", "running", "failed"]
    started_at: datetime
    completed_at: datetime
    model_version: str = "v0.1-synthetic"
    data_mode: DataMode = "SYNTHETIC_SIMULATION"
    storage_type: Literal["in_memory_demo", "postgresql_persisted"] = "in_memory_demo"
    total_steps: int
    summary_metrics: SimulationSummaryMetrics
    disclaimer: str = (
        "SYNTHETIC SIMULATION: Values are synthetically generated for research and algorithm benchmarking. "
        "Ground-truth labels do not represent real-world driver collusion."
    )
