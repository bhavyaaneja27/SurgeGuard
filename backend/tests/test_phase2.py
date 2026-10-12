"""
SurgeGuard Phase 2 Unit & Integration Tests.
Verifies FeaturePipeline, BaselineForecaster, RuleBasedDetector, and EvaluationEngine.
"""
import pickle
import pytest
from app.services.feature_engineering import FeaturePipeline
from app.services.forecasting import BaselineForecaster
from app.services.rule_based_detector import RuleBasedDetector
from app.services.evaluation import EvaluationEngine


def test_feature_pipeline_rolling_extraction():
    pipeline = FeaturePipeline(window_size_steps=6)
    
    # Ingest synthetic records
    records = []
    for step in range(15):
        records.append({
            "step_number": step,
            "timestamp": "2026-10-12T18:00:00Z",
            "zone_id": "zone_midtown_core",
            "ride_requests": 100 + step * 2,
            "available_drivers": 120 - step * 5,
            "completed_rides": 80,
            "unfulfilled_requests": step * 2,
            "estimated_wait_time_minutes": 3.0 + step * 0.5,
            "fare_pressure_index": 1.0 + step * 0.1,
            "supply_demand_ratio": (120 - step * 5) / max(100 + step * 2, 1),
            "scenario_type": "unusual_supply_drop",
            "ground_truth_label": "unusual_supply_drop",
        })

    feat = pipeline.extract_features(records)
    
    assert "supply_drop_pct" in feat
    assert "supply_drop_velocity" in feat
    assert "demand_change_pct" in feat
    assert "shortage_duration" in feat
    assert "fare_pressure_delta" in feat
    assert "wait_time_delta" in feat
    assert "unfulfilled_pct" in feat
    # After supply drops, drop percent should be positive
    assert feat["supply_drop_pct"] > 0


def test_baseline_forecaster_fit_and_pickle():
    forecaster = BaselineForecaster()
    records = [
        {
            "scenario_type": "normal_marketplace",
            "timestamp": "2026-10-12T18:00:00Z",
            "zone_id": "zone_midtown_core",
            "ride_requests": 120.0,
            "available_drivers": 140.0,
        },
        {
            "scenario_type": "normal_marketplace",
            "timestamp": "2026-10-12T18:30:00Z",
            "zone_id": "zone_midtown_core",
            "ride_requests": 124.0,
            "available_drivers": 136.0,
        },
    ]
    forecaster.fit_from_records(records)
    forecaster.compile()

    exp_d, exp_s = forecaster.predict_baseline("zone_midtown_core", 18, 0)
    assert exp_d == pytest.approx(122.0)
    assert exp_s == pytest.approx(138.0)

    # Verify pickle serialization (fixing previous lambda bug)
    pickled = pickle.dumps(forecaster)
    unpickled = pickle.loads(pickled)
    exp_d2, exp_s2 = unpickled.predict_baseline("zone_midtown_core", 18, 0)
    assert exp_d2 == pytest.approx(122.0)
    assert exp_s2 == pytest.approx(138.0)

    # Compute residuals
    res = unpickled.compute_residuals("zone_midtown_core", 18, 0, observed_demand=150.0, observed_supply=100.0)
    assert res["demand_residual_pct"] > 0
    assert res["supply_residual_pct"] < 0


def test_rule_based_detector_scoring():
    rbd = RuleBasedDetector()
    
    # Benign normal feature vector
    normal_features = {
        "supply_drop_pct": 0.02,
        "supply_demand_ratio": 1.1,
        "fare_pressure_delta": 0.05,
        "shortage_duration": 0,
    }
    result_norm = rbd.score_features(normal_features)
    assert result_norm["score"] == 0.0
    assert result_norm["severity"] == "low"

    # Severe anomalous feature vector
    anomalous_features = {
        "supply_drop_pct": 0.55,       # > 0.40 -> 25 pts
        "supply_demand_ratio": 0.40,   # < 0.45 -> 25 pts
        "fare_pressure_delta": 45.0,   # > 40.0 -> 25 pts
        "shortage_duration": 10,       # > 8 -> 25 pts
    }
    result_anom = rbd.score_features(anomalous_features)
    assert result_anom["score"] == 100.0
    assert result_anom["severity"] == "critical"
    assert len(result_anom["reasons"]) == 4


def test_evaluation_engine_metrics():
    engine = EvaluationEngine()
    
    records = [
        {"ground_truth_label": "unusual_supply_drop", "step_number": 1},
        {"ground_truth_label": "unusual_supply_drop", "step_number": 2},
        {"ground_truth_label": "normal", "step_number": 3},
        {"ground_truth_label": "natural_shortage", "step_number": 4},
    ]
    # Injected detection at step 2 (1 step delay from onset at step 1)
    predictions = [
        {"score": 20.0, "predicted": 0, "severity": "low", "step_number": 1},
        {"score": 70.0, "predicted": 1, "severity": "high", "step_number": 2},
        {"score": 10.0, "predicted": 0, "severity": "low", "step_number": 3},
        {"score": 15.0, "predicted": 0, "severity": "low", "step_number": 4},
    ]

    metrics = engine.evaluate_detector(records, predictions)
    assert metrics.precision == 1.0
    assert metrics.recall == 0.5
    assert metrics.false_positive_rate == 0.0
    assert metrics.detection_delay_minutes == 1.0


def test_artifacts_load_and_features_aligned():
    """Audit Item 8: Verify all exported artifacts exist, load, and have consistent feature schemas."""
    import os
    import json
    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    artifacts_dir = os.path.join(backend_root, "app", "models", "artifacts")

    required_artifacts = [
        "forecaster.pkl", "forecaster_lookup.json", "rule_based_detector_config.json",
        "feature_pipeline_config.json", "isolation_forest.pkl", "evaluation_results.json"
    ]
    for fname in required_artifacts:
        path = os.path.join(artifacts_dir, fname)
        assert os.path.exists(path), f"Missing artifact: {fname}"

    with open(os.path.join(artifacts_dir, "feature_pipeline_config.json")) as f:
        pipe_cfg = json.load(f)

    with open(os.path.join(artifacts_dir, "isolation_forest.pkl"), "rb") as f:
        iso_art = pickle.load(f)

    assert pipe_cfg["features"] == iso_art["feature_cols"], "Feature ordering mismatch!"


def test_forecasting_out_of_sample_vs_baseline():
    """Audit Item 5: Verify out-of-sample forecasting error vs global mean baseline."""
    import os
    import numpy as np
    from app.services.data_generator import data_generator
    from app.services.forecasting import _parse_hour_dow

    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    artifacts_dir = os.path.join(backend_root, "app", "models", "artifacts")
    with open(os.path.join(artifacts_dir, "forecaster.pkl"), "rb") as f:
        forecaster = pickle.load(f)

    # Held-out normal scenario (seed 44)
    test_recs = data_generator.generate_scenario_records("normal_marketplace", seed=44)
    actual = np.array([r["ride_requests"] for r in test_recs])

    # Model predictions
    fc_preds = []
    for r in test_recs:
        h, dow = _parse_hour_dow(r["timestamp"])
        d_exp, _ = forecaster.predict_baseline(r["zone_id"], h, dow)
        fc_preds.append(d_exp)
    fc_preds = np.array(fc_preds)

    global_mean_pred = np.full_like(actual, 122.0)

    fc_mae = np.mean(np.abs(actual - fc_preds))
    gm_mae = np.mean(np.abs(actual - global_mean_pred))

    # BaselineForecaster lookup table must outperform global mean on out-of-sample normal data
    assert fc_mae < gm_mae


def test_scenario_distinguishability_by_demand():
    """Audit Item 4: Verify that demand behavior distinguishes natural shortage from supply drop."""
    import pandas as pd
    from app.services.data_generator import data_generator

    pipeline = FeaturePipeline(window_size_steps=6)

    ns_recs = data_generator.generate_scenario_records("natural_shortage", seed=44)
    ud_recs = data_generator.generate_scenario_records("unusual_supply_drop", seed=44)

    ns_df = pd.DataFrame(ns_recs)
    ud_df = pd.DataFrame(ud_recs)

    ns_feat = pipeline.extract_features_from_dataframe(ns_df)
    ud_feat = pipeline.extract_features_from_dataframe(ud_df)

    # In natural shortage, peak demand rises significantly
    peak_demand_ns = ns_df["ride_requests"].max()
    peak_demand_ud = ud_df["ride_requests"].max()
    baseline_demand = 120.0

    assert peak_demand_ns > baseline_demand * 1.15, "Natural shortage should have noticeable demand rise"
    assert abs(peak_demand_ud - baseline_demand) < 10.0, "Unusual supply drop demand must stay flat"

