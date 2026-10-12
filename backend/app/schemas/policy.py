from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from app.schemas.simulation import ScenarioType

PolicyType = Literal[
    "no_intervention",
    "targeted_driver_incentive",
    "rider_discount",
    "supply_recovery_support",
    "cooldown_freeze",
]


class PolicyComparisonRequest(BaseModel):
    run_id: Optional[str] = None
    scenario_type: Optional[ScenarioType] = Field(
        default="unusual_supply_drop",
        description="Scenario archetype if run_id is omitted"
    )
    zone_id: Optional[str] = Field(
        default="zone_midtown_core",
        description="Marketplace zone if run_id is omitted"
    )
    duration_minutes: Optional[int] = Field(
        default=120, ge=30, le=480,
        description="Duration in minutes if running new baseline"
    )
    event_intensity: Optional[float] = Field(
        default=0.75, ge=0.1, le=1.0,
        description="Shock severity if running new baseline"
    )
    seed: Optional[int] = Field(
        default=42,
        description="Deterministic random seed"
    )
    policies: List[PolicyType] = Field(
        default=[
            "no_intervention",
            "targeted_driver_incentive",
            "rider_discount",
            "supply_recovery_support",
        ],
        description="List of policy interventions to simulate and compare side-by-side"
    )
    incentive_amount_pct: float = Field(
        default=25.0, ge=5.0, le=100.0,
        description="Targeted driver incentive bonus percentage (5% to 100%)"
    )
    discount_amount_pct: float = Field(
        default=20.0, ge=5.0, le=50.0,
        description="Rider price discount percentage (5% to 50%)"
    )
    recovery_support_pct: float = Field(
        default=30.0, ge=5.0, le=60.0,
        description="Supply recovery subsidy floor percentage (5% to 60%)"
    )


class PolicyTimelineStep(BaseModel):
    step_number: int
    timestamp: str
    ride_requests: float
    available_drivers: float
    completed_rides: int
    unfulfilled_requests: int
    wait_time_minutes: float
    fare_pressure_index: float


class PolicyOutcomeMetrics(BaseModel):
    ride_requests: int
    available_drivers: float
    completed_rides: int
    unfulfilled_requests: int
    fulfillment_rate_pct: float
    average_wait_time_minutes: float
    max_wait_time_minutes: float
    fare_pressure_index: float
    peak_fare_pressure: float
    driver_earnings_index: float
    simulated_driver_incentive_cost: float
    simulated_rider_discount_cost: float
    estimated_intervention_cost: float
    cost_per_recovered_ride: Optional[float] = None


class PolicyOutcomeDeltas(BaseModel):
    ride_requests_delta: int
    available_drivers_delta: float
    rides_delta: int
    unfulfilled_delta: int
    fulfillment_rate_delta: float
    wait_time_delta: float
    fare_pressure_delta: float
    earnings_delta: float
    cost_delta: float


class PolicyRunComparison(BaseModel):
    policy_type: PolicyType
    policy_name: str
    description: str
    parameters_json: Dict[str, Any]
    metrics: PolicyOutcomeMetrics
    deltas_versus_baseline: PolicyOutcomeDeltas
    timeline: List[PolicyTimelineStep]
    assumptions: List[str]
    trade_offs_and_limitations: List[str]


class PolicyComparisonResponse(BaseModel):
    run_id: str
    scenario_type: str
    zone_id: str
    seed: int
    baseline_policy: PolicyType = "no_intervention"
    comparisons: List[PolicyRunComparison]
    disclaimer: str = (
        "Simulated counterfactual estimates under documented economic assumptions. "
        "Not guaranteed real-world causal outcomes."
    )
