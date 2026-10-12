#!/usr/bin/env python3
"""
CLI Script: Evaluate Phase 2 Anomaly Detectors Against Labelled Synthetic Scenarios.

Loads all scenario CSVs, extracts features, runs both:
  - Rule-Based Detector (transparent baseline)
  - Isolation Forest (if artifact exists from train_models.py)

Prints actual precision, recall, FPR, PR-AUC, ROC-AUC, detection delay.
Also prints a per-scenario breakdown and threshold sensitivity table.

Usage:
    python scripts/evaluate_models.py --data-path ../data/synthetic --model-dir ../app/models/artifacts
"""
import argparse
import csv
import json
import os
import pickle
import sys
from collections import defaultdict

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure backend root is on sys.path
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from app.services.feature_engineering import FeaturePipeline
from app.services.rule_based_detector import RuleBasedDetector
from app.services.evaluation import EvaluationEngine


def load_csv_records(csv_dir: str) -> list:
    """Load all synthetic CSV files and return as flat list."""
    all_records = []
    for fname in sorted(os.listdir(csv_dir)):
        if not fname.endswith(".csv") or fname.startswith("."):
            continue
        fpath = os.path.join(csv_dir, fname)
        try:
            with open(fpath, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                file_records = [dict(row) for row in reader]
            if file_records:
                scenario = file_records[0].get("scenario_type", "unknown")
                print(f"  Loaded {len(file_records):>5} records  [{scenario:30s}] {fname}")
                all_records.extend(file_records)
        except Exception as e:
            print(f"  [WARN] Could not read {fname}: {e}")
    return all_records


def cast_numeric(records: list) -> list:
    """Cast all numeric fields to float/int in-place."""
    numeric_fields = [
        "ride_requests", "available_drivers", "completed_rides",
        "unfulfilled_requests", "estimated_wait_time_minutes",
        "fare_pressure_index", "supply_demand_ratio", "driver_earnings_index",
        "step_number",
    ]
    for rec in records:
        for field in numeric_fields:
            if field in rec:
                try:
                    rec[field] = float(rec[field])
                except (ValueError, TypeError):
                    rec[field] = 0.0
    return records


def extract_features_from_records(records: list, pipeline: FeaturePipeline) -> list:
    """
    Group records by (scenario_type, zone_id), extract rolling features per group,
    then flatten back to a single aligned list matching records order.
    """
    import pandas as pd

    df = pd.DataFrame(records)
    for col in ["ride_requests", "available_drivers", "completed_rides",
                "unfulfilled_requests", "estimated_wait_time_minutes",
                "fare_pressure_index", "supply_demand_ratio", "driver_earnings_index",
                "step_number"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    feat_df = pipeline.extract_features_from_dataframe(df)
    return feat_df.to_dict("records")


def _sep(label="", width=72):
    if label:
        pad = max(0, width - len(label) - 4)
        print(f"\n-- {label} {'-' * pad}")
    else:
        print("-" * width)


def main():
    parser = argparse.ArgumentParser(
        description="SurgeGuard Phase 2: Evaluate anomaly detectors on synthetic labelled data."
    )
    parser.add_argument(
        "--data-path",
        type=str,
        default="../data/synthetic",
        help="Path to synthetic scenario CSV directory"
    )
    parser.add_argument(
        "--model-dir",
        type=str,
        default="../app/models/artifacts",
        help="Path to trained model artifacts from train_models.py"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=40.0,
        help="Binary classification threshold for rule-based detector score (0-100)"
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=6,
        help="Rolling window size (must match training)"
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default=None,
        help="Optional path to write JSON results"
    )

    args = parser.parse_args()

    data_path = os.path.abspath(args.data_path)
    model_dir = os.path.abspath(args.model_dir)

    print(f"\n{'=' * 72}")
    print(f"  SurgeGuard  |  Phase 2 Evaluation Suite")
    print(f"{'=' * 72}")
    print(f"  Data:       {data_path}")
    print(f"  Model Dir:  {model_dir}")
    print(f"  Threshold:  {args.threshold}")
    print(f"  Window:     {args.window_size}\n")

    # ----------------------------------------------------------------
    # Load data
    # ----------------------------------------------------------------
    _sep("Loading data")
    all_records = load_csv_records(data_path)
    if not all_records:
        print("[ERROR] No records loaded. Ensure CSV files exist in data-path.")
        return 1
    all_records = cast_numeric(all_records)
    print(f"\n  Total: {len(all_records)} records across all scenarios")

    # ----------------------------------------------------------------
    # Extract features
    # ----------------------------------------------------------------
    _sep("Extracting features")
    pipeline = FeaturePipeline(window_size_steps=args.window_size)
    feature_dicts = extract_features_from_records(all_records, pipeline)
    print(f"  Feature extraction complete. Features per step: {len([k for k in feature_dicts[0] if isinstance(feature_dicts[0].get(k), (int, float)) and not k.startswith('dq_')])}")

    # ----------------------------------------------------------------
    # Rule-Based Detector evaluation
    # ----------------------------------------------------------------
    _sep("Rule-Based Detector (Transparent Baseline)")
    rbd = RuleBasedDetector()
    engine = EvaluationEngine()

    rbd_predictions = []
    for i, feat in enumerate(feature_dicts):
        result = rbd.score_features(feat)
        rbd_predictions.append({
            "step_number": all_records[i].get("step_number", i),
            "score": result["score"],
            "predicted": 1 if result["score"] >= args.threshold else 0,
            "severity": result["severity"],
            "model_version": "rule_based_detector_v2.0",
        })

    rbd_metrics = engine.evaluate_detector(all_records, rbd_predictions)

    print(f"\n  Rule-Based Detector @ threshold={args.threshold}")
    print(f"  {'Metric':<30} {'Value':>10}")
    print(f"  {'-' * 42}")
    print(f"  {'Precision':<30} {rbd_metrics.precision:>10.4f}")
    print(f"  {'Recall':<30} {rbd_metrics.recall:>10.4f}")
    print(f"  {'False Positive Rate':<30} {rbd_metrics.false_positive_rate:>10.4f}")
    print(f"  {'PR-AUC':<30} {rbd_metrics.pr_auc or 'N/A':>10}")
    print(f"  {'ROC-AUC':<30} {rbd_metrics.roc_auc or 'N/A':>10}")
    print(f"  {'Detection Delay (steps)':<30} {rbd_metrics.detection_delay_minutes:>10.2f}")
    print(f"\n  Class Balance:")
    for label, count in sorted(rbd_metrics.class_balance.items()):
        print(f"    {label:<35} {count:>6} steps")
    print(f"\n  Caveats:")
    for c in rbd_metrics.caveats:
        print(f"    * {c}")

    # ----------------------------------------------------------------
    # Threshold sensitivity table (PR curve)
    # ----------------------------------------------------------------
    _sep("Threshold Sensitivity (Rule-Based Detector)")
    rbd_scores = [p["score"] for p in rbd_predictions]
    thresholds = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0]
    thr_results = engine.evaluate_at_thresholds(all_records, rbd_scores, thresholds)

    print(f"\n  {'Threshold':>10}  {'Precision':>10}  {'Recall':>8}  {'FPR':>8}  {'TP':>5}  {'FP':>5}  {'FN':>5}")
    print(f"  {'-' * 65}")
    for row in thr_results:
        print(f"  {row['threshold']:>10.0f}  {row['precision']:>10.4f}  {row['recall']:>8.4f}  {row['fpr']:>8.4f}  {row['tp']:>5}  {row['fp']:>5}  {row['fn']:>5}")

    # ----------------------------------------------------------------
    # Per-scenario breakdown
    # ----------------------------------------------------------------
    _sep("Per-Scenario Score Distribution")
    scenario_scores = defaultdict(list)
    for i, pred in enumerate(rbd_predictions):
        label = all_records[i].get("ground_truth_label", "unknown")
        scenario_scores[label].append(pred["score"])

    print(f"\n  {'Scenario':<35}  {'Steps':>6}  {'Mean Score':>10}  {'Flagged%':>9}")
    print(f"  {'-' * 65}")
    for label in sorted(scenario_scores):
        scores = scenario_scores[label]
        mean_s = sum(scores) / len(scores)
        flagged_pct = sum(1 for s in scores if s >= args.threshold) / len(scores) * 100
        print(f"  {label:<35}  {len(scores):>6}  {mean_s:>10.2f}  {flagged_pct:>8.1f}%")

    # ----------------------------------------------------------------
    # Isolation Forest evaluation (if artifact exists)
    # ----------------------------------------------------------------
    iso_path = os.path.join(model_dir, "isolation_forest.pkl")
    iso_metrics = None
    if os.path.exists(iso_path):
        _sep("Isolation Forest Comparison")
        try:
            import numpy as np
            with open(iso_path, "rb") as f:
                iso_artifact = pickle.load(f)

            iso_model = iso_artifact["model"]
            feature_cols = iso_artifact["feature_cols"]

            # Build feature matrix
            X = []
            valid_indices = []
            for i, feat in enumerate(feature_dicts):
                row = [feat.get(c, 0.0) or 0.0 for c in feature_cols]
                if any(v != 0.0 for v in row):
                    X.append(row)
                    valid_indices.append(i)

            if len(X) > 0:
                import pandas as pd
                X_df = pd.DataFrame(X, columns=feature_cols)
                # IsolationForest: predict returns -1 (anomaly) or 1 (normal)
                iso_preds_raw = iso_model.predict(X_df)
                iso_scores_raw = iso_model.score_samples(X_df)  # lower = more anomalous
                # Convert to 0/1: -1 -> 1 (anomalous), 1 -> 0 (normal)
                # Normalize scores to 0-100 range (invert so higher = more anomalous)
                min_s, max_s = iso_scores_raw.min(), iso_scores_raw.max()
                iso_scores_norm = (1 - (iso_scores_raw - min_s) / max(max_s - min_s, 1e-6)) * 100

                iso_predictions = []
                for i_raw, (orig_idx, pred_raw, score_norm) in enumerate(
                    zip(valid_indices, iso_preds_raw, iso_scores_norm)
                ):
                    iso_predictions.append({
                        "step_number": all_records[orig_idx].get("step_number", orig_idx),
                        "score": float(score_norm),
                        "predicted": 1 if pred_raw == -1 else 0,
                        "model_version": "isolation_forest_v2.0",
                    })

                # Align with ground_truth (only valid_indices rows)
                gt_subset = [all_records[i] for i in valid_indices]
                iso_metrics = engine.evaluate_detector(gt_subset, iso_predictions)

                print(f"\n  Isolation Forest @ built-in contamination threshold")
                print(f"  {'Metric':<30} {'Value':>10}")
                print(f"  {'-' * 42}")
                print(f"  {'Precision':<30} {iso_metrics.precision:>10.4f}")
                print(f"  {'Recall':<30} {iso_metrics.recall:>10.4f}")
                print(f"  {'False Positive Rate':<30} {iso_metrics.false_positive_rate:>10.4f}")
                print(f"  {'PR-AUC':<30} {iso_metrics.pr_auc or 'N/A':>10}")
                print(f"  {'ROC-AUC':<30} {iso_metrics.roc_auc or 'N/A':>10}")
                print(f"  {'Detection Delay (steps)':<30} {iso_metrics.detection_delay_minutes:>10.2f}")

                _sep("Baseline Comparison Summary")
                print(f"\n  {'Model':<35}  {'Precision':>10}  {'Recall':>8}  {'FPR':>8}  {'PR-AUC':>8}  {'Delay':>6}")
                print(f"  {'-' * 75}")
                r = rbd_metrics
                print(f"  {'Rule-Based Detector':<35}  {r.precision:>10.4f}  {r.recall:>8.4f}  {r.false_positive_rate:>8.4f}  {r.pr_auc or 0:>8.4f}  {r.detection_delay_minutes:>6.2f}")
                m = iso_metrics
                print(f"  {'Isolation Forest':<35}  {m.precision:>10.4f}  {m.recall:>8.4f}  {m.false_positive_rate:>8.4f}  {m.pr_auc or 0:>8.4f}  {m.detection_delay_minutes:>6.2f}")

        except Exception as e:
            print(f"  [WARN] Isolation Forest evaluation failed: {e}")
            import traceback; traceback.print_exc()
    else:
        print(f"\n  [INFO] No isolation_forest.pkl found at {iso_path}.")
        print(f"         Run train_models.py first to generate it.")

    # ----------------------------------------------------------------
    # Final summary caveats
    # ----------------------------------------------------------------
    _sep("Important Caveats")
    print("""
  * All metrics are computed on controlled synthetic scenarios with injected labels.
  * Ground-truth labels were generated by the synthetic simulator -- not real incidents.
  * 'unusual_supply_drop' is the positive class. 'natural_shortage' and 'normal' are negatives.
  * This system is a research prototype. It does NOT prove real-world collusion.
  * False-positive rate on natural shortage steps is the critical fairness metric.
    """)

    # ----------------------------------------------------------------
    # Optional JSON output
    # ----------------------------------------------------------------
    if args.output_json:
        results = {
            "rule_based_detector": {
                "precision": rbd_metrics.precision,
                "recall": rbd_metrics.recall,
                "false_positive_rate": rbd_metrics.false_positive_rate,
                "pr_auc": rbd_metrics.pr_auc,
                "roc_auc": rbd_metrics.roc_auc,
                "detection_delay_minutes": rbd_metrics.detection_delay_minutes,
                "class_balance": rbd_metrics.class_balance,
                "threshold": args.threshold,
            },
            "threshold_sensitivity": thr_results,
            "caveats": rbd_metrics.caveats,
        }
        if iso_metrics:
            results["isolation_forest"] = {
                "precision": iso_metrics.precision,
                "recall": iso_metrics.recall,
                "false_positive_rate": iso_metrics.false_positive_rate,
                "pr_auc": iso_metrics.pr_auc,
                "roc_auc": iso_metrics.roc_auc,
                "detection_delay_minutes": iso_metrics.detection_delay_minutes,
            }
        out_path = os.path.abspath(args.output_json)
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"  [OK] Results written to: {out_path}")

    print(f"{'=' * 72}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

