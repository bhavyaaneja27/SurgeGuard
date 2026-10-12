"""
Feature Engineering Pipeline Service.
Computes zone/time-level features from rolling windows as specified in PRD Section 8.2.

Features computed (no future data leakage):
  - supply_drop_pct           : % drop in available_drivers vs. rolling window baseline
  - supply_drop_velocity      : rate of change (step-over-step) in supply
  - demand_change_pct         : % change in ride_requests vs. rolling window baseline
  - supply_demand_ratio       : available_drivers / max(ride_requests, 1)
  - baseline_supply_deviation : z-score of current supply vs. window mean/std
  - shortage_duration         : consecutive steps where supply_demand_ratio < threshold
  - wait_time_delta           : change in estimated_wait_time_minutes vs. window mean
  - fare_pressure_delta       : change in fare_pressure_index vs. window mean
  - unfulfilled_pct           : unfulfilled_requests / max(ride_requests, 1)
  - data_quality_flags        : dict of data sanity indicators

Phase 2 implementation.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from app.core.logging import logger


# Tunable constants
_SDR_SHORTAGE_THRESHOLD = 0.85  # supply/demand ratio below this = shortage step
_MIN_WINDOW_FOR_STD = 3          # minimum window entries needed to compute std-dev


class FeaturePipeline:
    """
    Transforms raw simulation/telemetry steps into rolling-window anomaly features.
    Accepts a list of step dicts (oldest-first) and computes features for the LAST step,
    using only past steps in the window (no future leakage).
    """

    def __init__(self, window_size_steps: int = 6):
        if window_size_steps < 2:
            raise ValueError("window_size_steps must be >= 2")
        self.window_size_steps = window_size_steps
        logger.info(
            f"FeaturePipeline initialized: window_size_steps={window_size_steps}"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_features(self, step_window: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Calculate rolling window metrics for the last step in step_window.

        Args:
            step_window: List of raw step dicts (oldest first), length >= 1.
                         The last element is the 'current' step being scored.

        Returns:
            Feature dict with float values, plus 'data_quality_flags' nested dict.

        Raises:
            ValueError: If step_window is empty or required keys are missing.
        """
        if not step_window:
            raise ValueError("step_window must not be empty")

        current = step_window[-1]
        _validate_step(current)

        # Use up to window_size_steps - 1 past steps (exclude current)
        past_steps = step_window[:-1][-(self.window_size_steps - 1):]

        supply_vals = [s["available_drivers"] for s in past_steps]
        demand_vals = [s["ride_requests"] for s in past_steps]

        curr_supply = float(current["available_drivers"])
        curr_demand = float(current["ride_requests"])
        curr_sdr = float(current["supply_demand_ratio"])
        curr_wait = float(current["estimated_wait_time_minutes"])
        curr_fare = float(current["fare_pressure_index"])
        curr_unfulfilled = float(current["unfulfilled_requests"])

        # --- supply_drop_pct ---
        supply_drop_pct = _pct_change_vs_window_mean(curr_supply, supply_vals, sign=-1)

        # --- supply_drop_velocity ---
        supply_drop_velocity = 0.0
        if past_steps:
            prev_supply = float(past_steps[-1]["available_drivers"])
            supply_drop_velocity = (prev_supply - curr_supply) / max(abs(prev_supply), 1.0)

        # --- demand_change_pct ---
        demand_change_pct = _pct_change_vs_window_mean(curr_demand, demand_vals, sign=1)

        # --- supply_demand_ratio (direct from record, sanity-checked) ---
        supply_demand_ratio = max(0.0, curr_sdr)

        # --- baseline_supply_deviation (z-score) ---
        baseline_supply_deviation = _zscore(curr_supply, supply_vals)

        # --- shortage_duration (consecutive shortage steps in window) ---
        shortage_duration = _count_consecutive_shortage(
            step_window, _SDR_SHORTAGE_THRESHOLD
        )

        # --- wait_time_delta ---
        wait_vals = [s["estimated_wait_time_minutes"] for s in past_steps]
        wait_time_delta = _delta_vs_window_mean(curr_wait, wait_vals)

        # --- fare_pressure_delta ---
        fare_vals = [s["fare_pressure_index"] for s in past_steps]
        fare_pressure_delta = _delta_vs_window_mean(curr_fare, fare_vals)

        # --- unfulfilled_pct ---
        unfulfilled_pct = curr_unfulfilled / max(curr_demand, 1.0)

        # --- data quality flags ---
        dq_flags = _data_quality_flags(
            current, supply_vals, demand_vals, self.window_size_steps
        )

        features: Dict[str, Any] = {
            "supply_drop_pct": round(supply_drop_pct, 4),
            "supply_drop_velocity": round(supply_drop_velocity, 4),
            "demand_change_pct": round(demand_change_pct, 4),
            "supply_demand_ratio": round(supply_demand_ratio, 4),
            "baseline_supply_deviation": round(baseline_supply_deviation, 4),
            "shortage_duration": shortage_duration,
            "wait_time_delta": round(wait_time_delta, 4),
            "fare_pressure_delta": round(fare_pressure_delta, 4),
            "unfulfilled_pct": round(unfulfilled_pct, 4),
            "data_quality_flags": dq_flags,
        }

        return features

    def extract_features_from_dataframe(self, df) -> "pd.DataFrame":
        """
        Apply rolling feature extraction across an entire DataFrame of steps.
        Returns a new DataFrame with one feature row per step (features are NaN
        for the first (window_size_steps - 1) rows due to warm-up).

        Requires pandas and assumes df is sorted by step_number ascending.
        """
        try:
            import pandas as pd
        except ImportError as exc:
            raise ImportError("pandas is required for batch feature extraction") from exc

        records = df.to_dict("records")
        feature_rows = []

        for i, _step in enumerate(records):
            window_start = max(0, i - self.window_size_steps + 1)
            window = records[window_start: i + 1]
            try:
                feats = self.extract_features(window)
                feats["step_number"] = _step.get("step_number", i)
                feats["timestamp"] = _step.get("timestamp")
                feats["zone_id"] = _step.get("zone_id")
                feats["scenario_type"] = _step.get("scenario_type")
                feats["ground_truth_label"] = _step.get("ground_truth_label")
                # Flatten data_quality_flags
                for k, v in feats.pop("data_quality_flags", {}).items():
                    feats[f"dq_{k}"] = v
                feature_rows.append(feats)
            except Exception as exc:
                logger.warning(f"Feature extraction failed at step {i}: {exc}")
                feature_rows.append({"step_number": _step.get("step_number", i)})

        return pd.DataFrame(feature_rows)


# ------------------------------------------------------------------
# Private helpers (pure functions, no side effects)
# ------------------------------------------------------------------

def _validate_step(step: Dict[str, Any]) -> None:
    required = [
        "available_drivers", "ride_requests", "supply_demand_ratio",
        "estimated_wait_time_minutes", "fare_pressure_index", "unfulfilled_requests"
    ]
    missing = [k for k in required if k not in step]
    if missing:
        raise ValueError(f"Step dict missing required keys: {missing}")


def _safe_mean(values: List[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


def _safe_std(values: List[float]) -> float:
    if len(values) < _MIN_WINDOW_FOR_STD:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def _pct_change_vs_window_mean(current: float, window_vals: List[float], sign: int = 1) -> float:
    """
    Returns sign * (current - window_mean) / max(window_mean, 1.0).
    sign=1 for demand increases, sign=-1 so supply drops are positive.
    """
    mean = _safe_mean(window_vals)
    if mean is None:
        return 0.0
    return sign * (current - mean) / max(abs(mean), 1.0)


def _zscore(current: float, window_vals: List[float]) -> float:
    """Z-score of current relative to window distribution."""
    mean = _safe_mean(window_vals)
    std = _safe_std(window_vals)
    if mean is None:
        return 0.0
    if std < 1e-6:
        return 0.0
    return (current - mean) / std


def _delta_vs_window_mean(current: float, window_vals: List[float]) -> float:
    """Absolute delta from window mean."""
    mean = _safe_mean(window_vals)
    if mean is None:
        return 0.0
    return current - mean


def _count_consecutive_shortage(
    step_window: List[Dict[str, Any]], threshold: float
) -> int:
    """
    Count consecutive steps (from the most recent backwards) where
    supply_demand_ratio < threshold.
    """
    count = 0
    for step in reversed(step_window):
        sdr = step.get("supply_demand_ratio", 1.0)
        if float(sdr) < threshold:
            count += 1
        else:
            break
    return count


def _data_quality_flags(
    current: Dict[str, Any],
    supply_vals: List[float],
    demand_vals: List[float],
    window_size: int,
) -> Dict[str, Any]:
    """
    Returns boolean/numeric quality flags for the current step.
    """
    supply = float(current.get("available_drivers", 0))
    demand = float(current.get("ride_requests", 0))
    sdr = float(current.get("supply_demand_ratio", 1.0))
    fare = float(current.get("fare_pressure_index", 100))

    return {
        "window_full": len(supply_vals) >= window_size - 1,
        "supply_below_minimum": supply < 5.0,
        "demand_below_minimum": demand < 5.0,
        "sdr_implausible": sdr > 10.0 or sdr < 0.0,
        "fare_implausible": fare < 50.0 or fare > 400.0,
        "window_size_actual": len(supply_vals) + 1,
    }


# Module-level singleton (for import convenience)
feature_pipeline = FeaturePipeline()
