"""
SurgeGuard Phase 2 Validation Audit Script.
Executes defensible Train (seed 42) / Validation (seed 43) / Test (seed 44) evaluation.
Reports:
  1. Demand Forecaster MAE/RMSE vs simple baselines (out-of-sample)
  2. Rule-Based Detector threshold selection on Validation set and evaluation on Test set
  3. Feature attribution analysis explaining natural shortage vs unusual supply drop scores
  4. Isolation Forest decision score evaluation
"""
import os
import sys
import json
import pickle
import numpy as np
import pandas as pd
from sklearn.metrics import (
    precision_score, recall_score, roc_auc_score,
    average_precision_score, confusion_matrix
)

# Ensure backend root on sys.path
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from app.services.data_generator import data_generator
from app.services.feature_engineering import FeaturePipeline
from app.services.forecasting import BaselineForecaster, _parse_hour_dow
from app.services.rule_based_detector import RuleBasedDetector
from app.services.evaluation import EvaluationEngine

SCENARIOS = ["normal_marketplace", "demand_led_surge", "natural_shortage", "unusual_supply_drop"]


def generate_split_dataset(seed: int) -> pd.DataFrame:
    """Generate all 4 scenarios for a specific random seed."""
    all_records = []
    for sc in SCENARIOS:
        recs = data_generator.generate_scenario_records(sc, seed=seed)
        all_records.extend(recs)
    df = pd.DataFrame(all_records)
    for col in [
        "ride_requests", "available_drivers", "completed_rides",
        "unfulfilled_requests", "estimated_wait_time_minutes",
        "fare_pressure_index", "supply_demand_ratio", "driver_earnings_index", "step_number"
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def audit_forecasting(forecaster: BaselineForecaster, train_df: pd.DataFrame, test_df: pd.DataFrame):
    """Compute out-of-sample MAE and RMSE against global mean and naive lag-1 baselines."""
    print("\n" + "=" * 70)
    print("  AUDIT ITEM 5: Demand Forecasting Error & Leakage Analysis")
    print("=" * 70)

    train_normal = train_df[train_df["scenario_type"] == "normal_marketplace"]
    global_mean = float(train_normal["ride_requests"].mean())

    results = {}
    for sc in SCENARIOS:
        sc_df = test_df[test_df["scenario_type"] == sc].sort_values("step_number").reset_index(drop=True)
        actual = sc_df["ride_requests"].values

        # Forecaster predictions
        preds_fc = []
        for _, row in sc_df.iterrows():
            h, dow = _parse_hour_dow(str(row["timestamp"]))
            d_exp, _ = forecaster.predict_baseline(str(row["zone_id"]), h, dow)
            preds_fc.append(d_exp)
        preds_fc = np.array(preds_fc)

        # Baseline 1: Global Mean from training set
        preds_gm = np.full_like(actual, global_mean)

        # Baseline 2: Naive lag-1 persistence
        preds_lag1 = np.roll(actual, 1)
        preds_lag1[0] = actual[0]

        def errs(act, pred):
            mae = float(np.mean(np.abs(act - pred)))
            rmse = float(np.sqrt(np.mean((act - pred) ** 2)))
            return mae, rmse

        mae_fc, rmse_fc = errs(actual, preds_fc)
        mae_gm, rmse_gm = errs(actual, preds_gm)
        mae_lag, rmse_lag = errs(actual, preds_lag1)

        results[sc] = {
            "forecaster": {"mae": round(mae_fc, 2), "rmse": round(rmse_fc, 2)},
            "global_mean": {"mae": round(mae_gm, 2), "rmse": round(rmse_gm, 2)},
            "naive_lag1": {"mae": round(mae_lag, 2), "rmse": round(rmse_lag, 2)},
        }

        print(f"  [{sc:<22}] Forecaster: MAE={mae_fc:5.2f}, RMSE={rmse_fc:5.2f} | GlobalMean: MAE={mae_gm:5.2f} | NaiveLag1: MAE={mae_lag:5.2f}")

    return results


def audit_detectors(train_df: pd.DataFrame, val_df: pd.DataFrame, test_df: pd.DataFrame, artifacts_dir: str):
    """Train on seed 42, tune threshold on Val (seed 43), test on Test (seed 44)."""
    pipeline = FeaturePipeline(window_size_steps=6)
    rbd = RuleBasedDetector()
    engine = EvaluationEngine()

    # Load Isolation Forest from artifact
    iso_path = os.path.join(artifacts_dir, "isolation_forest.pkl")
    with open(iso_path, "rb") as f:
        iso_artifact = pickle.load(f)
    iso_model = iso_artifact["model"]
    feature_cols = iso_artifact["feature_cols"]

    # Extract features for Val and Test
    val_feat_df = pipeline.extract_features_from_dataframe(val_df)
    test_feat_df = pipeline.extract_features_from_dataframe(test_df)

    y_val = (val_df["ground_truth_label"] == "unusual_supply_drop").astype(int).values
    y_test = (test_df["ground_truth_label"] == "unusual_supply_drop").astype(int).values

    val_records = val_df.to_dict("records")
    test_records = test_df.to_dict("records")

    val_scores = [rbd.score_features(r)["score"] for r in val_feat_df.to_dict("records")]
    test_scores = [rbd.score_features(r)["score"] for r in test_feat_df.to_dict("records")]

    print("\n" + "=" * 70)
    print("  AUDIT ITEM 3: Validation Set Threshold Selection & PR Trade-off")
    print("=" * 70)
    print(f"  {'Threshold':>10}  {'Precision':>10}  {'Recall':>8}  {'FPR':>8}  {'F1':>8}  {'NS-FPR':>8}")
    print("  " + "-" * 62)

    val_threshold_results = []
    best_f1 = -1.0
    best_thr = 40.0

    for thr in [10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 50.0]:
        y_pred = (np.array(val_scores) >= thr).astype(int)
        tp = int(np.sum((y_val == 1) & (y_pred == 1)))
        fp = int(np.sum((y_val == 0) & (y_pred == 1)))
        fn = int(np.sum((y_val == 1) & (y_pred == 0)))
        tn = int(np.sum((y_val == 0) & (y_pred == 0)))

        prec = tp / max(tp + fp, 1)
        rec = tp / max(tp + fn, 1)
        fpr = fp / max(fp + tn, 1)
        f1 = (2 * prec * rec) / max(prec + rec, 1e-6)

        # Natural shortage steps FPR
        ns_mask = (val_df["ground_truth_label"] == "natural_shortage").values
        ns_fpr = float(np.sum(ns_mask & (y_pred == 1)) / max(np.sum(ns_mask), 1))

        if f1 > best_f1:
            best_f1 = f1
            best_thr = thr

        val_threshold_results.append({
            "threshold": thr, "precision": round(prec, 4), "recall": round(rec, 4),
            "fpr": round(fpr, 4), "f1": round(f1, 4), "ns_fpr": round(ns_fpr, 4)
        })
        print(f"  {thr:>10.0f}  {prec:>10.4f}  {rec:>8.4f}  {fpr:>8.4f}  {f1:>8.4f}  {ns_fpr:>8.4f}")

    print(f"\n  Validation Selected Threshold: {best_thr} (Best F1 = {best_f1:.4f})")

    # Evaluate on held-out Test set (seed 44)
    print("\n" + "=" * 70)
    print(f"  AUDIT ITEM 1 & 7: Held-Out Test Evaluation (Seed 44) @ thr={best_thr}")
    print("=" * 70)

    # Rule-Based Detector Test
    test_y_pred = (np.array(test_scores) >= best_thr).astype(int)
    rbd_test_preds = [
        {"step_number": r.get("step_number", i), "score": test_scores[i], "predicted": test_y_pred[i], "severity": "audit"}
        for i, r in enumerate(test_records)
    ]
    rbd_test_metrics = engine.evaluate_detector(test_records, rbd_test_preds)

    # Baseline thr=40 test
    test_y_pred_40 = (np.array(test_scores) >= 40.0).astype(int)
    rbd_test_preds_40 = [
        {"step_number": r.get("step_number", i), "score": test_scores[i], "predicted": test_y_pred_40[i], "severity": "audit"}
        for i, r in enumerate(test_records)
    ]
    rbd_test_metrics_40 = engine.evaluate_detector(test_records, rbd_test_preds_40)

    # Isolation Forest Test
    X_test = test_feat_df[feature_cols].copy()
    iso_preds_raw = iso_model.predict(X_test)
    iso_scores_raw = iso_model.score_samples(X_test)
    min_s, max_s = iso_scores_raw.min(), iso_scores_raw.max()
    iso_scores_norm = (1 - (iso_scores_raw - min_s) / max(max_s - min_s, 1e-6)) * 100

    iso_test_preds = [
        {"step_number": test_records[i].get("step_number", i), "score": float(iso_scores_norm[i]), "predicted": 1 if p == -1 else 0}
        for i, p in enumerate(iso_preds_raw)
    ]
    iso_test_metrics = engine.evaluate_detector(test_records, iso_test_preds)

    print(f"\n  {'Model':<35}  {'Precision':>10}  {'Recall':>8}  {'FPR':>8}  {'PR-AUC':>8}  {'ROC-AUC':>8}  {'NS-FPR':>8}")
    print("  " + "-" * 85)
    r = rbd_test_metrics
    ns_r = float(np.sum((test_df['ground_truth_label'] == 'natural_shortage').values & (test_y_pred == 1)) / 120)
    print(f"  {'Rule-Based (Val-Selected thr=' + str(int(best_thr)) + ')':<35}  {r.precision:>10.4f}  {r.recall:>8.4f}  {r.false_positive_rate:>8.4f}  {r.pr_auc:>8.4f}  {r.roc_auc:>8.4f}  {ns_r:>8.4f}")

    r40 = rbd_test_metrics_40
    ns_r40 = float(np.sum((test_df['ground_truth_label'] == 'natural_shortage').values & (test_y_pred_40 == 1)) / 120)
    print(f"  {'Rule-Based (Default thr=40)':<35}  {r40.precision:>10.4f}  {r40.recall:>8.4f}  {r40.false_positive_rate:>8.4f}  {r40.pr_auc:>8.4f}  {r40.roc_auc:>8.4f}  {ns_r40:>8.4f}")

    m = iso_test_metrics
    ns_m = float(np.sum((test_df['ground_truth_label'] == 'natural_shortage').values & (iso_preds_raw == -1)) / 120)
    print(f"  {'Isolation Forest (Unsupervised)':<35}  {m.precision:>10.4f}  {m.recall:>8.4f}  {m.false_positive_rate:>8.4f}  {m.pr_auc:>8.4f}  {m.roc_auc:>8.4f}  {ns_m:>8.4f}")

    # Feature contribution breakdown for Item 4
    print("\n" + "=" * 70)
    print("  AUDIT ITEM 4: Feature Contribution Breakdown (Natural vs Unusual)")
    print("=" * 70)
    for sc in ["natural_shortage", "unusual_supply_drop"]:
        sc_df = test_feat_df[test_df["scenario_type"] == sc]
        raw_df = test_df[test_df["scenario_type"] == sc]
        sc_scores = [rbd.score_features(r) for r in sc_df.to_dict("records")]
        tot_score = np.mean([s["score"] for s in sc_scores])
        c1 = np.mean([s["components"]["supply_drop_pct"]["score"] for s in sc_scores])
        c2 = np.mean([s["components"]["supply_demand_ratio"]["score"] for s in sc_scores])
        c3 = np.mean([s["components"]["fare_pressure_delta"]["score"] for s in sc_scores])
        c4 = np.mean([s["components"]["shortage_duration"]["score"] for s in sc_scores])
        d_mean = raw_df["ride_requests"].mean()
        s_mean = raw_df["available_drivers"].mean()
        d_chg = sc_df["demand_change_pct"].mean()
        print(f"  [{sc}] Mean Score: {tot_score:.2f} (supply_drop={c1:.2f}, sdr={c2:.2f}, fare={c3:.2f}, duration={c4:.2f})")
        print(f"      Physical averages: Demand={d_mean:.1f}, Supply={s_mean:.1f}, demand_change_pct={d_chg:.4f}")

    return {
        "val_threshold_results": val_threshold_results,
        "selected_threshold": best_thr,
        "test_results": {
            "rule_based_selected": {
                "threshold": best_thr,
                "precision": rbd_test_metrics.precision,
                "recall": rbd_test_metrics.recall,
                "fpr": rbd_test_metrics.false_positive_rate,
                "pr_auc": rbd_test_metrics.pr_auc,
                "roc_auc": rbd_test_metrics.roc_auc,
                "natural_shortage_fpr": round(ns_r, 4),
            },
            "rule_based_thr40": {
                "threshold": 40.0,
                "precision": rbd_test_metrics_40.precision,
                "recall": rbd_test_metrics_40.recall,
                "fpr": rbd_test_metrics_40.false_positive_rate,
                "pr_auc": rbd_test_metrics_40.pr_auc,
                "roc_auc": rbd_test_metrics_40.roc_auc,
                "natural_shortage_fpr": round(ns_r40, 4),
            },
            "isolation_forest": {
                "precision": iso_test_metrics.precision,
                "recall": iso_test_metrics.recall,
                "fpr": iso_test_metrics.false_positive_rate,
                "pr_auc": iso_test_metrics.pr_auc,
                "roc_auc": iso_test_metrics.roc_auc,
                "natural_shortage_fpr": round(ns_m, 4),
            },
        },
    }


def main():
    print("SURGEGUARD PHASE 2 VALIDATION AUDIT")
    artifacts_dir = os.path.abspath(os.path.join(backend_root, "app", "models", "artifacts"))

    # Load fitted forecaster from artifact
    with open(os.path.join(artifacts_dir, "forecaster.pkl"), "rb") as f:
        forecaster = pickle.load(f)

    # Generate Defensible Split: Train=Seed 42, Val=Seed 43, Test=Seed 44
    train_df = generate_split_dataset(seed=42)
    val_df = generate_split_dataset(seed=43)
    test_df = generate_split_dataset(seed=44)

    fc_results = audit_forecasting(forecaster, train_df, test_df)
    det_results = audit_detectors(train_df, val_df, test_df, artifacts_dir)

    out_audit = {
        "forecasting": fc_results,
        "detector_audit": det_results,
    }
    out_path = os.path.join(artifacts_dir, "validation_audit_results.json")
    with open(out_path, "w") as f:
        json.dump(out_audit, f, indent=2)
    print(f"\n[OK] Validation audit results written to: {out_path}\n")


if __name__ == "__main__":
    main()
