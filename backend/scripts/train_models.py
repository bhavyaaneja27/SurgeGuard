#!/usr/bin/env python3
"""
CLI Script: Train Phase 2 Pipeline (Baseline Forecaster + Rule-Based Detector).

Loads synthetic scenario CSVs, fits:
  1. BaselineForecaster (zone×hour×day-of-week lookup table from normal_marketplace data)
  2. RuleBasedDetector (no training needed — threshold-based, exported as config JSON)
  3. FeaturePipeline (parameter export for reproducibility)

Optionally fits an Isolation Forest on feature vectors extracted from normal_marketplace
records, serializing the model to app/models/artifacts/ with pickle.

Usage:
    python scripts/train_models.py --data-path ../data/synthetic --output ../app/models/artifacts
"""
import argparse
import json
import os
import pickle
import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from app.services.forecasting import BaselineForecaster
from app.services.feature_engineering import FeaturePipeline
from app.services.rule_based_detector import (
    RuleBasedDetector,
    _SUPPLY_DROP_MILD, _SUPPLY_DROP_SEVERE,
    _SDR_SHORTAGE, _SDR_SEVERE,
    _FARE_MILD, _FARE_SEVERE,
    _DURATION_MILD, _DURATION_SEVERE,
)


def load_csv_records(csv_dir: str) -> dict:
    """Load all synthetic CSV files into a dict keyed by scenario_type."""
    import csv
    scenario_records: dict = {}
    all_records = []

    for fname in os.listdir(csv_dir):
        if not fname.endswith(".csv") or fname.startswith("."):
            continue
        fpath = os.path.join(csv_dir, fname)
        file_records = []
        try:
            with open(fpath, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    file_records.append(dict(row))
        except Exception as e:
            print(f"  [WARN] Could not read {fname}: {e}")
            continue

        if file_records:
            scenario = file_records[0].get("scenario_type", "unknown")
            scenario_records.setdefault(scenario, []).extend(file_records)
            all_records.extend(file_records)
            print(f"  [OK] Loaded {len(file_records)} records from {fname} (scenario={scenario})")

    return scenario_records, all_records


def build_feature_matrix(records: list, pipeline: FeaturePipeline) -> tuple:
    """Extract features for a flat list of records (grouped by scenario_type)."""
    import pandas as pd

    df = pd.DataFrame(records)
    # Cast numeric columns
    for col in ["ride_requests", "available_drivers", "completed_rides",
                "unfulfilled_requests", "estimated_wait_time_minutes",
                "fare_pressure_index", "supply_demand_ratio", "driver_earnings_index",
                "step_number"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df = df.sort_values("step_number").reset_index(drop=True)
    feat_df = pipeline.extract_features_from_dataframe(df)
    return feat_df


def main():
    parser = argparse.ArgumentParser(
        description="SurgeGuard Phase 2: Train Baseline Forecaster and Rule-Based Detector."
    )
    parser.add_argument(
        "--data-path",
        type=str,
        default="../data/synthetic",
        help="Path to synthetic CSV training records"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="../app/models/artifacts",
        help="Target folder for serialized model artifacts"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=6,
        help="Rolling window size for FeaturePipeline"
    )
    parser.add_argument(
        "--no-isolation-forest",
        action="store_true",
        help="Skip Isolation Forest training (rule-based only)"
    )

    args = parser.parse_args()

    print(f"\n[SurgeGuard] Phase 2 Training Pipeline")
    print(f"  Data Path:   {args.data_path}")
    print(f"  Artifacts:   {args.output}")
    print(f"  Seed:        {args.seed}")
    print(f"  Window Size: {args.window_size}\n")

    data_path = os.path.abspath(args.data_path)
    artifacts_path = os.path.abspath(args.output)
    os.makedirs(artifacts_path, exist_ok=True)

    if not os.path.isdir(data_path):
        print(f"[ERROR] Data path not found: {data_path}")
        return 1

    # ----------------------------------------------------------------
    # Step 1: Load all synthetic CSVs
    # ----------------------------------------------------------------
    print("[Step 1/4] Loading synthetic scenario data...")
    scenario_records, all_records = load_csv_records(data_path)

    if not all_records:
        print("[ERROR] No records loaded. Ensure CSV files exist in data-path.")
        return 1

    print(f"  Total records loaded: {len(all_records)}")
    for sc, recs in scenario_records.items():
        print(f"    {sc}: {len(recs)} records")

    # ----------------------------------------------------------------
    # Step 2: Fit BaselineForecaster
    # ----------------------------------------------------------------
    print("\n[Step 2/4] Fitting BaselineForecaster on normal_marketplace data...")
    forecaster = BaselineForecaster()
    normal_records = scenario_records.get("normal_marketplace", [])

    if not normal_records:
        print("  [WARN] No normal_marketplace records found. Using zone defaults.")
        forecaster._use_synthetic_defaults()
        forecaster.compile()
    else:
        forecaster.fit_from_records(normal_records)
        forecaster.compile()

    # Serialize the forecaster's lookup table as JSON (human-readable)
    lookup_export = {
        zone: {
            f"{hour},{dow}": list(val)
            for (hour, dow), val in cells.items()
        }
        for zone, cells in forecaster._lookup.items()
    }
    lookup_path = os.path.join(artifacts_path, "forecaster_lookup.json")
    with open(lookup_path, "w") as f:
        json.dump(lookup_export, f, indent=2)

    # Also serialize as pickle for fast loading
    pickle_path = os.path.join(artifacts_path, "forecaster.pkl")
    with open(pickle_path, "wb") as f:
        pickle.dump(forecaster, f)

    n_zones = len(forecaster._lookup)
    n_cells = sum(len(v) for v in forecaster._lookup.values())
    print(f"  Fitted {n_zones} zones, {n_cells} lookup cells")
    print(f"  Saved: {lookup_path}")
    print(f"  Saved: {pickle_path}")

    # ----------------------------------------------------------------
    # Step 3: Export RuleBasedDetector thresholds
    # ----------------------------------------------------------------
    print("\n[Step 3/4] Exporting RuleBasedDetector threshold config...")
    rbd_config = {
        "model_type": "rule_based_detector",
        "version": "v2.0-phase2",
        "thresholds": {
            "supply_drop_mild": _SUPPLY_DROP_MILD,
            "supply_drop_severe": _SUPPLY_DROP_SEVERE,
            "sdr_shortage": _SDR_SHORTAGE,
            "sdr_severe": _SDR_SEVERE,
            "fare_mild": _FARE_MILD,
            "fare_severe": _FARE_SEVERE,
            "duration_mild": _DURATION_MILD,
            "duration_severe": _DURATION_SEVERE,
        },
        "score_threshold_binary": 40.0,
        "caveat": "Score is a prioritisation signal on synthetic data. Not proof of collusion.",
    }
    rbd_path = os.path.join(artifacts_path, "rule_based_detector_config.json")
    with open(rbd_path, "w") as f:
        json.dump(rbd_config, f, indent=2)
    print(f"  Saved: {rbd_path}")

    # ----------------------------------------------------------------
    # Step 4: Feature Pipeline config export
    # ----------------------------------------------------------------
    print("\n[Step 4/4] Exporting FeaturePipeline config...")
    pipeline_config = {
        "model_type": "feature_pipeline",
        "version": "v2.0-phase2",
        "window_size_steps": args.window_size,
        "sdr_shortage_threshold": 0.85,
        "features": [
            "supply_drop_pct", "supply_drop_velocity", "demand_change_pct",
            "supply_demand_ratio", "baseline_supply_deviation", "shortage_duration",
            "wait_time_delta", "fare_pressure_delta", "unfulfilled_pct",
        ],
    }
    pipeline_path = os.path.join(artifacts_path, "feature_pipeline_config.json")
    with open(pipeline_path, "w") as f:
        json.dump(pipeline_config, f, indent=2)
    print(f"  Saved: {pipeline_path}")

    # ----------------------------------------------------------------
    # Optional: Isolation Forest on normal_marketplace features
    # ----------------------------------------------------------------
    if not args.no_isolation_forest and normal_records:
        print("\n[Optional] Training Isolation Forest on normal_marketplace features...")
        try:
            from sklearn.ensemble import IsolationForest
            import pandas as pd
            import numpy as np

            pipeline = FeaturePipeline(window_size_steps=args.window_size)
            feat_df = build_feature_matrix(normal_records, pipeline)

            feature_cols = [
                "supply_drop_pct", "supply_drop_velocity", "demand_change_pct",
                "supply_demand_ratio", "baseline_supply_deviation", "shortage_duration",
                "wait_time_delta", "fare_pressure_delta", "unfulfilled_pct",
            ]
            available_cols = [c for c in feature_cols if c in feat_df.columns]
            X_train = feat_df[available_cols].dropna()

            if len(X_train) < 10:
                print("  [WARN] Not enough clean feature rows for Isolation Forest. Skipping.")
            else:
                iso_forest = IsolationForest(
                    n_estimators=100,
                    contamination=0.05,
                    random_state=args.seed,
                )
                iso_forest.fit(X_train)

                iso_path = os.path.join(artifacts_path, "isolation_forest.pkl")
                with open(iso_path, "wb") as f:
                    pickle.dump({
                        "model": iso_forest,
                        "feature_cols": available_cols,
                        "version": "v2.0-phase2",
                        "seed": args.seed,
                    }, f)
                print(f"  Trained on {len(X_train)} rows with features: {available_cols}")
                print(f"  Saved: {iso_path}")

        except ImportError:
            print("  [WARN] scikit-learn not available. Skipping Isolation Forest.")
        except Exception as e:
            print(f"  [WARN] Isolation Forest training failed: {e}")

    print(f"\n[SUCCESS] Phase 2 Training complete. Artifacts in: {artifacts_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

