from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

SeverityLevel = Literal["low", "medium", "high", "critical"]
RiskCategory = Literal["normal", "watch", "investigate"]
UncertaintyLevel = Literal["low", "medium", "high"]

InterpretationClass = Literal[
    "Likely natural shortage",
    "Unusual shortage — investigate",
    "Demand-led surge",
    "Normal equilibrium",
    "Insufficient evidence",
]


class BaselineComparison(BaseModel):
    expected_supply: float
    observed_supply: float
    expected_demand: float
    observed_demand: float
    supply_delta_pct: float
    demand_delta_pct: float = 0.0


class ContributingSignal(BaseModel):
    name: str
    weight: float
    value: float
    description: str
    direction: Literal["supporting", "weakening", "neutral"]


class StepAssessment(BaseModel):
    step_number: int
    timestamp: str
    zone_id: str
    score: float = Field(..., ge=0.0, le=100.0, description="Overall risk prioritization score (0-100)")
    risk_category: RiskCategory
    severity: SeverityLevel
    interpretation: InterpretationClass
    uncertainty: UncertaintyLevel
    confidence: float = Field(..., ge=0.0, le=1.0)
    
    # Detailed Contextual Explanations
    demand_trend: str
    supply_deviation_magnitude: float
    sustained_duration_steps: int
    top_signals: List[ContributingSignal] = Field(default_factory=list)
    supporting_reasons: List[str] = Field(default_factory=list)
    weakening_reasons: List[str] = Field(default_factory=list)
    
    # Baseline comparison metrics
    baseline_comparison: BaselineComparison
    
    # Model Component Scores
    rule_score: float = 0.0
    isolation_forest_score: Optional[float] = None
    data_quality_flags: Dict[str, Any] = Field(default_factory=dict)
    
    caveat: str = Field(
        default="Score is an operational prioritisation signal on synthetic data. Not proof of driver collusion or legal wrongdoing."
    )


class RunAssessmentSummary(BaseModel):
    run_id: str
    scenario_type: str
    zone_id: str
    total_steps: int
    normal_steps_count: int
    watch_steps_count: int
    investigate_steps_count: int
    max_score: float
    mean_score: float
    peak_risk_category: RiskCategory
    dominant_interpretation: InterpretationClass
    model_version: str
    assessed_at: str
    disclaimer: str = (
        "RESEARCH PROTOTYPE DISCLAIMER: All assessments are generated from synthetic simulation traces "
        "for algorithmic auditing. They do NOT prove real-world collusion or driver intent."
    )


class RunAssessmentResponse(BaseModel):
    summary: RunAssessmentSummary
    assessments: List[StepAssessment]
    alerts_only: List[StepAssessment] = Field(
        default_factory=list,
        description="Steps flagged with risk_category 'watch' or 'investigate'"
    )


class AnomalyAlert(BaseModel):
    id: str
    run_id: str
    zone_id: str
    event_time: datetime
    score: float = Field(..., ge=0.0, le=100.0, description="Display score 0-100 prioritisation signal")
    severity: SeverityLevel
    interpretation: InterpretationClass
    reasons_json: List[str] = Field(default_factory=list, description="Feature contributions/reasons")
    baseline_comparison: BaselineComparison
    model_version: str
    caveat: str = Field(
        default="Anomaly score is a prioritisation signal based on synthetic simulation; not proof of collusion.",
        description="Transparent limitation disclosure"
    )
    data_quality_json: Optional[Dict[str, Any]] = None
