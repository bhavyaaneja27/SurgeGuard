from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class EvaluationMetricsResponse(BaseModel):
    model_version: str
    dataset_version: str
    precision: float
    recall: float
    false_positive_rate: float
    pr_auc: Optional[float] = None
    roc_auc: Optional[float] = None
    class_balance: Dict[str, int] = Field(default_factory=dict)
    detection_delay_minutes: float
    caveats: List[str] = Field(
        default_factory=lambda: [
            "Metrics computed on controlled synthetic scenarios with injected patterns.",
            "Labels do not reflect or prove real-world collusion incidents."
        ]
    )
