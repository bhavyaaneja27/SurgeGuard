"""
Transparent Rule-Based Baseline Anomaly Detector.

Phase 2 implementation of an interpretable, threshold-driven scoring system.
This is used as a baseline against which ML models (Phase 3) will be compared.

Score components (each 0-25, total 0-100):
  1. supply_drop_pct        : How much has supply dropped vs. rolling window?
  2. supply_demand_ratio    : Is current S/D ratio below shortage threshold?
  3. fare_pressure_delta    : Has fare pressure index risen sharply?
  4. shortage_duration      : How many consecutive shortage steps observed?

Rules are fully auditable and transparent. No black-box inference.
The score is a PRIORITIZATION SIGNAL, not a probability of collusion.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import logger
from app.schemas.alerts import SeverityLevel


# -----------------------------------------------------------------------
# Thresholds (tunable, kept as module constants for auditability)
# -----------------------------------------------------------------------

# Component 1: supply_drop_pct
_SUPPLY_DROP_MILD = 0.05    # 5% drop → starts scoring
_SUPPLY_DROP_SEVERE = 0.40  # 40%+ drop → max score for this component

# Component 2: supply_demand_ratio
_SDR_NORMAL = 1.0           # above this = healthy
_SDR_SHORTAGE = 0.85        # below this = shortage
_SDR_SEVERE = 0.45          # below this = severe shortage

# Component 3: fare_pressure_delta (absolute index points above baseline)
_FARE_MILD = 5.0
_FARE_SEVERE = 40.0

# Component 4: shortage_duration (consecutive shortage steps)
_DURATION_MILD = 2
_DURATION_SEVERE = 8

# Maximum score per component (4 components × 25 = 100 max)
_COMPONENT_MAX = 25.0


class RuleBasedDetector:
    """
    Scores a feature vector using four transparent, interpretable rules.
    Each rule contributes up to 25 points. Total range: 0–100.

    Designed to be the Phase 2 transparent baseline that:
    - Gives precise, explainable reasons for each score
    - Can be directly compared against Isolation Forest in Phase 3
    - Never produces a score without a human-readable explanation
    """

    def __init__(self):
        logger.info("RuleBasedDetector initialized (Phase 2 transparent baseline)")

    def score_features(self, features: Dict[str, float]) -> Dict[str, Any]:
        """
        Score a feature dict produced by FeaturePipeline.extract_features().

        Returns:
            {
                "score": float (0-100),
                "severity": SeverityLevel,
                "components": {component_name: {score, value, reason}},
                "reasons": [str, ...],
                "caveat": str,
            }
        """
        components: Dict[str, Dict[str, Any]] = {}
        reasons: List[str] = []

        # --- Component 1: supply_drop_pct ---
        sdp = float(features.get("supply_drop_pct", 0.0))
        c1 = _clamp_score(_linear_scale(sdp, _SUPPLY_DROP_MILD, _SUPPLY_DROP_SEVERE) * _COMPONENT_MAX)
        components["supply_drop_pct"] = {
            "score": round(c1, 2),
            "value": round(sdp, 4),
            "reason": _supply_drop_reason(sdp),
        }
        if c1 > 0:
            reasons.append(components["supply_drop_pct"]["reason"])

        # --- Component 2: supply_demand_ratio ---
        sdr = float(features.get("supply_demand_ratio", 1.0))
        c2 = _clamp_score(_linear_scale(_SDR_NORMAL - sdr, _SDR_NORMAL - _SDR_SHORTAGE, _SDR_NORMAL - _SDR_SEVERE) * _COMPONENT_MAX)
        components["supply_demand_ratio"] = {
            "score": round(c2, 2),
            "value": round(sdr, 4),
            "reason": _sdr_reason(sdr),
        }
        if c2 > 0:
            reasons.append(components["supply_demand_ratio"]["reason"])

        # --- Component 3: fare_pressure_delta ---
        fpd = float(features.get("fare_pressure_delta", 0.0))
        c3 = _clamp_score(_linear_scale(fpd, _FARE_MILD, _FARE_SEVERE) * _COMPONENT_MAX)
        components["fare_pressure_delta"] = {
            "score": round(c3, 2),
            "value": round(fpd, 4),
            "reason": _fare_reason(fpd),
        }
        if c3 > 0:
            reasons.append(components["fare_pressure_delta"]["reason"])

        # --- Component 4: shortage_duration ---
        dur = int(features.get("shortage_duration", 0))
        c4 = _clamp_score(_linear_scale(dur, _DURATION_MILD, _DURATION_SEVERE) * _COMPONENT_MAX)
        components["shortage_duration"] = {
            "score": round(c4, 2),
            "value": dur,
            "reason": _duration_reason(dur),
        }
        if c4 > 0:
            reasons.append(components["shortage_duration"]["reason"])

        total_score = _clamp_score(c1 + c2 + c3 + c4)
        severity = self.determine_severity(total_score)

        if not reasons:
            reasons = ["All indicators within normal operating bounds."]

        return {
            "score": round(total_score, 2),
            "severity": severity,
            "components": components,
            "reasons": reasons,
            "caveat": (
                "This score is a transparent rule-based prioritisation signal computed on "
                "synthetic simulation data. It is NOT proof of collusion or driver coordination."
            ),
        }

    def determine_severity(self, score: float) -> SeverityLevel:
        """Maps score to severity: low, medium, high, critical."""
        if score >= 80.0:
            return "critical"
        elif score >= 60.0:
            return "high"
        elif score >= 40.0:
            return "medium"
        return "low"

    def batch_score(
        self,
        feature_rows: List[Dict[str, float]],
    ) -> List[Dict[str, Any]]:
        """Score a list of feature dicts, returning a result per row."""
        return [self.score_features(row) for row in feature_rows]

    def predict_binary(
        self,
        feature_rows: List[Dict[str, float]],
        threshold: float = 40.0,
    ) -> List[int]:
        """
        Returns a list of 0/1 predictions (1 = anomalous) for each feature row.
        threshold=40.0 corresponds to the 'medium' severity cutoff.
        """
        return [
            1 if self.score_features(row)["score"] >= threshold else 0
            for row in feature_rows
        ]


# -----------------------------------------------------------------------
# Private helpers
# -----------------------------------------------------------------------

def _linear_scale(value: float, low: float, high: float) -> float:
    """
    Linearly map value from [low, high] -> [0.0, 1.0].
    Returns 0.0 if value <= low, 1.0 if value >= high.
    """
    if high <= low:
        return 0.0
    return max(0.0, min(1.0, (value - low) / (high - low)))


def _clamp_score(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _supply_drop_reason(sdp: float) -> str:
    pct = round(sdp * 100, 1)
    if sdp < _SUPPLY_DROP_MILD:
        return f"Supply within normal range (drop: {pct}%)"
    if sdp < 0.15:
        return f"Minor supply dip detected ({pct}% below rolling mean)"
    if sdp < 0.30:
        return f"Moderate supply drop ({pct}% below rolling mean) — warrants monitoring"
    return f"Significant supply drop ({pct}% below rolling mean) — unusual pattern"


def _sdr_reason(sdr: float) -> str:
    if sdr >= _SDR_NORMAL:
        return f"Supply/demand ratio healthy ({sdr:.2f})"
    if sdr >= _SDR_SHORTAGE:
        return f"Supply/demand ratio borderline ({sdr:.2f}) — mild shortage"
    if sdr >= _SDR_SEVERE:
        return f"Supply/demand ratio low ({sdr:.2f}) — active shortage"
    return f"Supply/demand ratio critically low ({sdr:.2f}) — severe shortage"


def _fare_reason(fpd: float) -> str:
    if fpd < _FARE_MILD:
        return f"Fare pressure normal (delta: {fpd:+.1f} pts)"
    if fpd < 20.0:
        return f"Moderate fare pressure increase ({fpd:+.1f} pts above mean)"
    return f"High fare pressure surge ({fpd:+.1f} pts above mean)"


def _duration_reason(dur: int) -> str:
    if dur < _DURATION_MILD:
        return f"Shortage duration within acceptable range ({dur} steps)"
    if dur < 5:
        return f"Shortage persisting for {dur} consecutive steps"
    return f"Prolonged shortage detected: {dur} consecutive steps below threshold"


# Module-level singleton
rule_based_detector = RuleBasedDetector()
