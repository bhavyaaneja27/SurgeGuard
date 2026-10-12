"""
SurgeGuard Contextual Anomaly Detection Service (Phase 3).
Combines:
  - Demand-conditioned rule scoring (distinguishing Case 1, 2, 3, 4)
  - Fixed-baseline supply deviation from BaselineForecaster (solving rolling-window decay)
  - Shortage persistence tracking
  - Unsupervised Isolation Forest cross-validation
  - Explainable risk assessment (normal, watch, investigate)
"""
from __future__ import annotations

import os
import pickle
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import logger
from app.schemas.alerts import (
    BaselineComparison,
    RiskCategory,
    SeverityLevel,
    StepAssessment,
)
from app.services.explanations import ExplanationBuilder
from app.services.forecasting import BaselineForecaster, _parse_hour_dow
from app.services.feature_engineering import FeaturePipeline


# Risk category thresholds (configurable)
RISK_THRESHOLD_WATCH = 30.0
RISK_THRESHOLD_INVESTIGATE = 60.0

# Fixed-baseline parameters
_FIXED_SUPPLY_DROP_MILD = 0.10
_FIXED_SUPPLY_DROP_SEVERE = 0.45
_FIXED_SUPPLY_MAX_PTS = 35.0

# SDR thresholds
_SDR_NORMAL = 1.00
_SDR_SHORTAGE = 0.85
_SDR_SEVERE = 0.45
_SDR_MAX_PTS = 25.0

# Duration thresholds
_DURATION_MILD = 2
_DURATION_SEVERE = 8
_DURATION_MAX_PTS = 20.0

# Fare pressure thresholds (points above baseline 100)
_FARE_SPIKE_MILD = 15.0
_FARE_SPIKE_SEVERE = 60.0
_FARE_MAX_PTS = 20.0

# Isolation Forest weight
_ISO_FOREST_WEIGHT = 0.15


class AnomalyDetector:
    """
    Evaluates rolling features, demand context, and fixed-baseline deviations
    to produce contextual anomaly assessments, risk categories, and explanations.
    """

    def __init__(
        self,
        model_version: str = "v3.0-contextual",
        artifacts_dir: Optional[str] = None,
    ):
        self.model_version = model_version
        self.explanation_builder = ExplanationBuilder()
        self.forecaster = BaselineForecaster()
        self.iso_model: Optional[Any] = None
        self.iso_feature_cols: List[str] = []
        self._artifacts_loaded = False

        if artifacts_dir is None:
            backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            artifacts_dir = os.path.join(backend_root, "app", "models", "artifacts")

        self.artifacts_dir = artifacts_dir
        self._load_artifacts()
        logger.info(f"Initialized AnomalyDetector (Phase 3) model_version={model_version}")

    def _load_artifacts(self) -> None:
        """Safely load forecaster and isolation forest artifacts if available."""
        fc_path = os.path.join(self.artifacts_dir, "forecaster.pkl")
        if os.path.exists(fc_path):
            try:
                with open(fc_path, "rb") as f:
                    self.forecaster = pickle.load(f)
                logger.info(f"AnomalyDetector: Loaded BaselineForecaster from {fc_path}")
            except Exception as e:
                logger.warning(f"Could not load forecaster artifact: {e}")

        iso_path = os.path.join(self.artifacts_dir, "isolation_forest.pkl")
        if os.path.exists(iso_path):
            try:
                with open(iso_path, "rb") as f:
                    iso_art = pickle.load(f)
                self.iso_model = iso_art["model"]
                self.iso_feature_cols = iso_art["feature_cols"]
                logger.info(f"AnomalyDetector: Loaded IsolationForest from {iso_path}")
            except Exception as e:
                logger.warning(f"Could not load isolation forest artifact: {e}")

        self._artifacts_loaded = True

    def assess_step(
        self,
        current_record: Dict[str, Any],
        features: Dict[str, float],
        sustained_shortage_duration: int = 0,
    ) -> StepAssessment:
        """
        Assesses a single time step using demand-conditioned scoring and fixed baseline.
        """
        zone_id = str(current_record.get("zone_id", "zone_midtown_core"))
        ts_str = str(current_record.get("timestamp", ""))
        step_number = int(current_record.get("step_number", 0))

        hour, dow = _parse_hour_dow(ts_str)

        # 1. Fixed Baseline Comparison (expected demand and supply)
        if getattr(self.forecaster, "_fitted", False):
            exp_demand, exp_supply = self.forecaster.predict_baseline(zone_id, hour, dow)
        else:
            exp_demand, exp_supply = 120.0, 135.0

        obs_demand = float(current_record.get("ride_requests", 0.0))
        obs_supply = float(current_record.get("available_drivers", 0.0))

        # Deviation from expected normal supply (positive = supply deficit)
        expected_supply_delta_pct = (exp_supply - obs_supply) / max(exp_supply, 1.0)
        # Deviation from expected normal demand (positive = demand surge)
        expected_demand_delta_pct = (obs_demand - exp_demand) / max(exp_demand, 1.0)

        baseline_comp = BaselineComparison(
            expected_supply=round(exp_supply, 1),
            observed_supply=round(obs_supply, 1),
            expected_demand=round(exp_demand, 1),
            observed_demand=round(obs_demand, 1),
            supply_delta_pct=round(expected_supply_delta_pct, 4),
            demand_delta_pct=round(expected_demand_delta_pct, 4),
        )

        # 2. Demand Condition Categorization (Cases 1, 2, 3, 4)
        demand_case, demand_factor = self._evaluate_demand_context(
            expected_supply_delta_pct, expected_demand_delta_pct
        )

        # 3. Component Scores
        # Component 1: Fixed-baseline supply deficit (sustained drop)
        c_fixed_supply = self._score_fixed_supply(expected_supply_delta_pct)

        # Component 2: Supply-demand ratio deficit
        sdr = float(features.get("supply_demand_ratio", 1.0))
        c_sdr = self._score_sdr(sdr)

        # Component 3: Sustained shortage duration
        c_duration = self._score_duration(sustained_shortage_duration)

        # Component 4: Fare pressure spike
        fare_idx = float(current_record.get("fare_pressure_index", 100.0))
        c_fare = self._score_fare(fare_idx)

        # Base rule score
        base_rule_sum = c_fixed_supply + c_sdr + c_duration + c_fare
        rule_score = round(base_rule_sum * demand_factor, 2)

        # 4. Optional Isolation Forest Score
        iso_score = None
        iso_component = 0.0
        if self.iso_model is not None and self.iso_feature_cols:
            try:
                import pandas as pd
                row = [features.get(c, 0.0) or 0.0 for c in self.iso_feature_cols]
                row_df = pd.DataFrame([row], columns=self.iso_feature_cols)
                # Raw score: lower = more anomalous; offset is ~ -0.5
                raw_score = float(self.iso_model.score_samples(row_df)[0])
                # Calibrated 0-100 score: score_samples ranges roughly [-0.8, -0.4]
                # Invert so higher = more anomalous
                iso_normalized = max(0.0, min(100.0, (-raw_score - 0.40) * 250.0))
                iso_score = round(iso_normalized, 1)
                iso_component = (iso_normalized / 100.0) * 15.0  # up to 15 pts
            except Exception as e:
                logger.warning(f"Isolation Forest inference error: {e}")

        # Final Combined Score (0-100)
        final_score = min(100.0, max(0.0, round(rule_score + iso_component, 2)))

        # 5. Determine Risk Category and Severity
        risk_category = self.determine_risk_category(final_score)
        severity = self.determine_severity(final_score)

        component_scores = {
            "fixed_supply_deficit": round(c_fixed_supply, 2),
            "sdr_deficit": round(c_sdr, 2),
            "shortage_duration": round(c_duration, 2),
            "fare_pressure": round(c_fare, 2),
            "demand_context": round(demand_factor * 10.0, 2),
            "isolation_forest": round(iso_component, 2),
        }

        # 6. Build Human-Readable Explanations
        dq_flags = features.get("data_quality_flags", {})
        explanation_data = self.explanation_builder.build_explanation(
            score=final_score,
            risk_category=risk_category,
            severity=severity,
            features=features,
            baseline_comp=baseline_comp,
            sustained_duration=sustained_shortage_duration,
            component_scores=component_scores,
            demand_case=demand_case,
            data_quality_flags=dq_flags if isinstance(dq_flags, dict) else {},
            iso_score=iso_score,
        )

        return StepAssessment(
            step_number=step_number,
            timestamp=ts_str,
            zone_id=zone_id,
            score=final_score,
            risk_category=risk_category,
            severity=severity,
            interpretation=explanation_data["interpretation"],
            uncertainty=explanation_data["uncertainty"],
            confidence=explanation_data["confidence"],
            demand_trend=explanation_data["demand_trend"],
            supply_deviation_magnitude=explanation_data["supply_deviation_magnitude"],
            sustained_duration_steps=sustained_shortage_duration,
            top_signals=explanation_data["top_signals"],
            supporting_reasons=explanation_data["supporting_reasons"],
            weakening_reasons=explanation_data["weakening_reasons"],
            baseline_comparison=baseline_comp,
            rule_score=rule_score,
            isolation_forest_score=iso_score,
            data_quality_flags=dq_flags if isinstance(dq_flags, dict) else {},
            caveat=explanation_data["caveat"],
        )

    def assess_simulation_run(
        self,
        records: List[Dict[str, Any]],
        pipeline: Optional[FeaturePipeline] = None,
    ) -> List[StepAssessment]:
        """
        Assess an entire simulation time-series sequence with stateful shortage tracking.
        """
        if not records:
            return []

        if pipeline is None:
            pipeline = FeaturePipeline(window_size_steps=6)

        import pandas as pd
        df = pd.DataFrame(records)
        for col in [
            "ride_requests", "available_drivers", "completed_rides",
            "unfulfilled_requests", "estimated_wait_time_minutes",
            "fare_pressure_index", "supply_demand_ratio", "driver_earnings_index", "step_number"
        ]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        df = df.sort_values("step_number").reset_index(drop=True)
        feat_df = pipeline.extract_features_from_dataframe(df)
        feat_records = feat_df.to_dict("records")

        assessments: List[StepAssessment] = []
        sustained_shortage = 0

        for i, rec in df.iterrows():
            rec_dict = rec.to_dict()
            feat_dict = feat_records[i]

            sdr = float(rec_dict.get("supply_demand_ratio", 1.0))
            if sdr < 0.85:
                sustained_shortage += 1
            else:
                sustained_shortage = 0

            assessment = self.assess_step(
                current_record=rec_dict,
                features=feat_dict,
                sustained_shortage_duration=sustained_shortage,
            )
            assessments.append(assessment)

        return assessments

    # ------------------------------------------------------------------
    # Scoring Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _evaluate_demand_context(
        supply_delta_pct: float,
        demand_delta_pct: float,
    ) -> Tuple[str, float]:
        """
        Evaluates demand behavior to distinguish Case 1, 2, 3, 4.
        Returns (case_name, demand_multiplier).
        """
        # Case 1: Supply drops, demand stable (Target anomaly: artificial withholding)
        if supply_delta_pct >= 0.15 and abs(demand_delta_pct) <= 0.12:
            return "case_1_supply_drop_flat_demand", 1.15

        # Case 2: Supply drops, demand surges sharply (External weather shock / natural shortage)
        if supply_delta_pct >= 0.15 and demand_delta_pct > 0.18:
            return "case_2_supply_drop_rising_demand", 0.45

        # Case 3: Demand surges, supply stable or rising (Genuine demand surge)
        if demand_delta_pct > 0.18 and supply_delta_pct <= 0.10:
            return "case_3_demand_surge_stable_supply", 0.15

        # Case 4: Normal equilibrium conditions
        return "case_4_normal_market", 0.10

    @staticmethod
    def _score_fixed_supply(supply_delta_pct: float) -> float:
        """Scales fixed-baseline supply drop percentage linearly to 0-35 pts."""
        if supply_delta_pct <= _FIXED_SUPPLY_DROP_MILD:
            return 0.0
        val = (supply_delta_pct - _FIXED_SUPPLY_DROP_MILD) / max(
            _FIXED_SUPPLY_DROP_SEVERE - _FIXED_SUPPLY_DROP_MILD, 1e-6
        )
        return min(_FIXED_SUPPLY_MAX_PTS, max(0.0, val * _FIXED_SUPPLY_MAX_PTS))

    @staticmethod
    def _score_sdr(sdr: float) -> float:
        """Scales supply-to-demand deficit linearly to 0-25 pts."""
        if sdr >= _SDR_SHORTAGE:
            return 0.0
        val = (_SDR_SHORTAGE - sdr) / max(_SDR_SHORTAGE - _SDR_SEVERE, 1e-6)
        return min(_SDR_MAX_PTS, max(0.0, val * _SDR_MAX_PTS))

    @staticmethod
    def _score_duration(duration_steps: int) -> float:
        """Scales sustained duration linearly to 0-20 pts."""
        if duration_steps <= _DURATION_MILD:
            return 0.0
        val = (duration_steps - _DURATION_MILD) / max(_DURATION_SEVERE - _DURATION_MILD, 1)
        return min(_DURATION_MAX_PTS, max(0.0, val * _DURATION_MAX_PTS))

    @staticmethod
    def _score_fare(fare_idx: float) -> float:
        """Scales fare pressure spike above baseline 100 linearly to 0-20 pts."""
        delta = fare_idx - 100.0
        if delta <= _FARE_SPIKE_MILD:
            return 0.0
        val = (delta - _FARE_SPIKE_MILD) / max(_FARE_SPIKE_SEVERE - _FARE_SPIKE_MILD, 1e-6)
        return min(_FARE_MAX_PTS, max(0.0, val * _FARE_MAX_PTS))

    @staticmethod
    def determine_risk_category(score: float) -> RiskCategory:
        """Maps score to operational risk category: normal, watch, investigate."""
        if score >= RISK_THRESHOLD_INVESTIGATE:
            return "investigate"
        elif score >= RISK_THRESHOLD_WATCH:
            return "watch"
        return "normal"

    @staticmethod
    def determine_severity(score: float) -> SeverityLevel:
        """Maps score to operational severity level."""
        if score >= 80.0:
            return "critical"
        elif score >= 60.0:
            return "high"
        elif score >= 30.0:
            return "medium"
        return "low"


# Module singleton
anomaly_detector = AnomalyDetector()
