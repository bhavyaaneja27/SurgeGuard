"""
SurgeGuard Explanation Builder & Contextual Interpretation Service (Phase 3).
Synthesizes plain-language explanations, feature attributions, supporting and weakening
reasons, uncertainty indicators, and explicit caveats grounded in computed signals.
"""
from typing import Any, Dict, List, Literal, Optional, Tuple
from app.core.logging import logger
from app.schemas.alerts import (
    BaselineComparison,
    ContributingSignal,
    InterpretationClass,
    RiskCategory,
    SeverityLevel,
    UncertaintyLevel,
)


class ExplanationBuilder:
    """
    Builds auditable, human-readable explanations grounded strictly in computed feature values.
    Does not use generic canned templates that claim signals are present when they are not.
    """

    def __init__(self):
        logger.info("Initialized ExplanationBuilder (Phase 3)")

    def build_explanation(
        self,
        score: float,
        risk_category: RiskCategory,
        severity: SeverityLevel,
        features: Dict[str, float],
        baseline_comp: BaselineComparison,
        sustained_duration: int,
        component_scores: Dict[str, float],
        demand_case: str,
        data_quality_flags: Dict[str, Any],
        iso_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Synthesizes structured explanations including top contributing signals,
        supporting reasons, weakening reasons, uncertainty indicators, and caveats.
        """
        supporting: List[str] = []
        weakening: List[str] = []
        signals: List[ContributingSignal] = []

        obs_s = baseline_comp.observed_supply
        exp_s = baseline_comp.expected_supply
        obs_d = baseline_comp.observed_demand
        exp_d = baseline_comp.expected_demand
        s_delta_pct = baseline_comp.supply_delta_pct
        d_delta_pct = baseline_comp.demand_delta_pct

        sdr = float(features.get("supply_demand_ratio", 1.0))
        fare_delta = float(features.get("fare_pressure_delta", 0.0))
        rolling_sdp = float(features.get("supply_drop_pct", 0.0))

        # --- Signal 1: Fixed-Baseline Supply Deficit ---
        if s_delta_pct >= 0.15:
            supporting.append(
                f"Available driver supply ({obs_s:.1f}) is {s_delta_pct * 100:.1f}% below normal expected baseline ({exp_s:.1f})."
            )
            signals.append(
                ContributingSignal(
                    name="Fixed-Baseline Supply Deficit",
                    weight=component_scores.get("fixed_supply_deficit", 0.0),
                    value=round(s_delta_pct * 100, 1),
                    description=f"{s_delta_pct * 100:.1f}% below forecast baseline",
                    direction="supporting",
                )
            )
        elif s_delta_pct <= -0.10:
            weakening.append(
                f"Available driver supply ({obs_s:.1f}) is {abs(s_delta_pct) * 100:.1f}% higher than expected baseline ({exp_s:.1f})."
            )
            signals.append(
                ContributingSignal(
                    name="Supply Surplus",
                    weight=0.0,
                    value=round(s_delta_pct * 100, 1),
                    description="Supply exceeds expected baseline",
                    direction="weakening",
                )
            )
        else:
            signals.append(
                ContributingSignal(
                    name="Expected Supply Alignment",
                    weight=0.0,
                    value=round(s_delta_pct * 100, 1),
                    description="Supply close to forecast baseline",
                    direction="neutral",
                )
            )

        # --- Signal 2: Demand Trend & Context (Distinguishing factor) ---
        if d_delta_pct > 0.20:
            weakening.append(
                f"Passenger ride requests surged by +{d_delta_pct * 100:.1f}% above expected normal demand, indicating organic demand shock (e.g. rainstorm or major event)."
            )
            signals.append(
                ContributingSignal(
                    name="Organic Demand Surge",
                    weight=component_scores.get("demand_context", 0.0),
                    value=round(d_delta_pct * 100, 1),
                    description=f"Demand surged +{d_delta_pct * 100:.1f}% above normal",
                    direction="weakening",
                )
            )
        elif abs(d_delta_pct) <= 0.12:
            supporting.append(
                f"Passenger demand remains stable ({obs_d:.1f} vs expected {exp_d:.1f}, {d_delta_pct * 100:+.1f}%), showing supply dropped without an organic surge."
            )
            signals.append(
                ContributingSignal(
                    name="Stable Demand Context",
                    weight=component_scores.get("demand_context", 0.0),
                    value=round(d_delta_pct * 100, 1),
                    description="Demand is flat/stable (rules out organic demand spike)",
                    direction="supporting",
                )
            )
        else:
            signals.append(
                ContributingSignal(
                    name="Demand Deviation",
                    weight=0.0,
                    value=round(d_delta_pct * 100, 1),
                    description=f"Demand is {d_delta_pct * 100:+.1f}% vs baseline",
                    direction="neutral",
                )
            )

        # --- Signal 3: Supply-Demand Ratio ---
        if sdr < 0.60:
            supporting.append(
                f"Severe marketplace deficit: supply-demand ratio is {sdr:.2f} (well below healthy threshold 0.85)."
            )
            signals.append(
                ContributingSignal(
                    name="Severe SDR Deficit",
                    weight=component_scores.get("sdr_deficit", 0.0),
                    value=round(sdr, 3),
                    description=f"Ratio {sdr:.2f} indicates acute driver shortage",
                    direction="supporting",
                )
            )
        elif sdr < 0.85:
            supporting.append(
                f"Moderate shortage: supply-demand ratio is {sdr:.2f} (below equilibrium 1.0)."
            )
            signals.append(
                ContributingSignal(
                    name="Moderate SDR Deficit",
                    weight=component_scores.get("sdr_deficit", 0.0),
                    value=round(sdr, 3),
                    description=f"Ratio {sdr:.2f} indicates moderate shortage",
                    direction="supporting",
                )
            )

        # --- Signal 4: Sustained Duration ---
        if sustained_duration >= 5:
            supporting.append(
                f"Sustained deficit: shortage condition has persisted continuously for {sustained_duration} steps."
            )
            signals.append(
                ContributingSignal(
                    name="Shortage Persistence",
                    weight=component_scores.get("shortage_duration", 0.0),
                    value=float(sustained_duration),
                    description=f"Persisting for {sustained_duration} consecutive steps",
                    direction="supporting",
                )
            )
        elif sustained_duration <= 2:
            weakening.append(
                f"Transient fluctuation: shortage condition active for only {sustained_duration} step(s)."
            )

        # --- Signal 5: Fare Pressure ---
        fare_idx = float(features.get("fare_pressure_index", 100.0))
        if fare_idx > 130.0:
            supporting.append(
                f"Elevated fare pressure index ({fare_idx:.1f}, +{fare_idx - 100.0:.1f} pts over baseline 100)."
            )
            signals.append(
                ContributingSignal(
                    name="Surge Pricing Pressure",
                    weight=component_scores.get("fare_pressure", 0.0),
                    value=round(fare_idx, 1),
                    description=f"Fare index {fare_idx:.1f} indicates strong surge pricing",
                    direction="supporting",
                )
            )

        # --- Signal 6: Isolation Forest Corroboration ---
        if iso_score is not None:
            if iso_score >= 60.0:
                supporting.append(
                    f"Unsupervised Isolation Forest independently flags multi-dimensional feature anomaly (score {iso_score:.1f}/100)."
                )
                signals.append(
                    ContributingSignal(
                        name="Isolation Forest Anomaly Signal",
                        weight=component_scores.get("isolation_forest", 0.0),
                        value=round(iso_score, 1),
                        description="Unsupervised model detects atypical multidimensional vector",
                        direction="supporting",
                    )
                )
            elif iso_score < 30.0:
                weakening.append(
                    f"Isolation Forest evaluates feature vector within normal distribution (score {iso_score:.1f}/100)."
                )

        # --- Determine Interpretation Classification ---
        interpretation: InterpretationClass
        has_dq_issues = any(v is True for v in data_quality_flags.values() if isinstance(v, bool))

        if has_dq_issues:
            interpretation = "Insufficient evidence"
            weakening.append("Data quality flags active; measurement uncertainty elevated.")
        elif demand_case == "case_1_supply_drop_flat_demand" and score >= 40.0:
            interpretation = "Unusual shortage — investigate"
        elif demand_case == "case_2_supply_drop_rising_demand" or (d_delta_pct > 0.20 and s_delta_pct > 0.15):
            interpretation = "Likely natural shortage"
        elif demand_case == "case_3_demand_surge_stable_supply" or (d_delta_pct > 0.20 and s_delta_pct <= 0.10):
            interpretation = "Demand-led surge"
        elif score < 30.0:
            interpretation = "Normal equilibrium"
        elif score >= 50.0:
            interpretation = "Unusual shortage — investigate"
        else:
            interpretation = "Likely natural shortage" if d_delta_pct > 0.10 else "Normal equilibrium"

        # --- Uncertainty Calculation ---
        uncertainty: UncertaintyLevel
        confidence: float

        if has_dq_issues:
            uncertainty = "high"
            confidence = 0.35
        elif d_delta_pct > 0.25 and iso_score is not None and iso_score >= 50.0 and score < 50.0:
            # Signal conflict: Isolation Forest flags anomaly, but demand surge explains it
            uncertainty = "medium"
            confidence = 0.65
            weakening.append("Conflicting signals: statistical anomaly detected by Isolation Forest is attenuated by organic passenger surge.")
        elif risk_category == "investigate" and len(supporting) >= 3 and len(weakening) == 0:
            uncertainty = "low"
            confidence = 0.90
        elif risk_category == "normal" and score < 15.0:
            uncertainty = "low"
            confidence = 0.95
        else:
            uncertainty = "medium"
            confidence = 0.75

        # Format demand trend
        if d_delta_pct > 0.15:
            demand_trend = f"Surging (+{d_delta_pct * 100:.1f}% vs normal)"
        elif d_delta_pct < -0.15:
            demand_trend = f"Depressed ({d_delta_pct * 100:.1f}% vs normal)"
        else:
            demand_trend = f"Stable ({d_delta_pct * 100:+.1f}% vs normal)"

        # Sort signals by weight descending
        signals.sort(key=lambda s: s.weight, reverse=True)

        return {
            "interpretation": interpretation,
            "uncertainty": uncertainty,
            "confidence": round(confidence, 2),
            "demand_trend": demand_trend,
            "supply_deviation_magnitude": round(s_delta_pct * 100, 1),
            "sustained_duration_steps": sustained_duration,
            "top_signals": [s.model_dump() for s in signals[:5]],
            "supporting_reasons": supporting,
            "weakening_reasons": weakening,
            "caveat": (
                "RESEARCH PROTOTYPE DISCLAIMER: This assessment is an operational prioritisation lead "
                "computed from synthetic simulation data. It does NOT prove driver collusion, coordination, "
                "or legal wrongdoing. All alerts require human verification."
            ),
        }
