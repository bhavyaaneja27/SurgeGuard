"""
SurgeGuard Phase 3 Evaluation Script:
Evaluates Explainable Contextual Anomaly Detector on held-out test data (Seed 44).
Compares against Phase 2 Baselines:
  1. Phase 2 Rule-Based Detector
  2. Phase 2 Isolation Forest (Unsupervised)
  3. Phase 3 Explainable Contextual Detector (@ watch thr=30 and @ investigate thr=60)

Evaluates both:
  - Full scenario trace (120 steps / scenario)
  - Active shock interval (steps 30-90 where physical anomaly is active)
"""
import os
import sys
import json
import numpy as np
import pandas as pd
from sklearn.metrics import (
    precision_score, recall_score, roc_auc_score,
    average_precision_score, confusion_matrix, f1_score
)

backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

# Set stdout encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.services.data_generator import data_generator
from app.services.feature_engineering import FeaturePipeline
from app.services.rule_based_detector import RuleBasedDetector
from app.services.anomaly_detection import AnomalyDetector
from app.services.evaluation import EvaluationEngine

SCENARIOS = ["normal_marketplace", "demand_led_surge", "natural_shortage", "unusual_supply_drop"]


def run_evaluation(seed: int = 44, active_only: bool = False):
    pipeline = FeaturePipeline(window_size_steps=6)
    rbd = RuleBasedDetector()
    phase3_det = AnomalyDetector()
    engine = EvaluationEngine()

    all_records = []
    for sc in SCENARIOS:
        recs = data_generator.generate_scenario_records(sc, seed=seed)
        if active_only:
            # Active shock interval: steps 30 to 90
            recs = [r for r in recs if 30 <= r.get("step_number", 0) <= 90]
        all_records.extend(recs)

    df = pd.DataFrame(all_records)
    for col in [
        "ride_requests", "available_drivers", "completed_rides",
        "unfulfilled_requests", "estimated_wait_time_minutes",
        "fare_pressure_index", "supply_demand_ratio", "driver_earnings_index", "step_number"
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # 1. Feature extraction
    feat_df = pipeline.extract_features_from_dataframe(df)
    feat_records = feat_df.to_dict("records")
    records_list = df.to_dict("records")

    y_true = np.array([1 if r.get("ground_truth_label") == "unusual_supply_drop" else 0 for r in records_list])

    # 2. Phase 2 Rule-Based Detector
    rbd_scores = [rbd.score_features(f)["score"] for f in feat_records]
    y_pred_rbd40 = (np.array(rbd_scores) >= 40.0).astype(int)

    # 3. Phase 2 Isolation Forest
    iso_model = phase3_det.iso_model
    iso_cols = phase3_det.iso_feature_cols
    X_iso = feat_df[iso_cols]
    iso_raw_preds = iso_model.predict(X_iso)
    iso_scores_raw = iso_model.score_samples(X_iso)
    min_s, max_s = iso_scores_raw.min(), iso_scores_raw.max()
    iso_norm_scores = (1 - (iso_scores_raw - min_s) / max(max_s - min_s, 1e-6)) * 100
    y_pred_iso = (iso_raw_preds == -1).astype(int)

    # 4. Phase 3 Contextual Detector
    # Group by scenario to assess sequential runs with sustained duration
    phase3_assessments = []
    for sc in SCENARIOS:
        sc_df = df[df["scenario_type"] == sc].sort_values("step_number").reset_index(drop=True)
        sc_assessments = phase3_det.assess_simulation_run(sc_df.to_dict("records"), pipeline)
        phase3_assessments.extend(sc_assessments)

    phase3_scores = [a.score for a in phase3_assessments]
    y_pred_p3_watch = (np.array(phase3_scores) >= 30.0).astype(int)
    y_pred_p3_investigate = (np.array(phase3_scores) >= 60.0).astype(int)

    def calc_metrics(y_t, y_p, y_s, name):
        cm = confusion_matrix(y_t, y_p)
        tn, fp, fn, tp = cm.ravel()
        prec = precision_score(y_t, y_p, zero_division=0)
        rec = recall_score(y_t, y_p, zero_division=0)
        f1 = f1_score(y_t, y_p, zero_division=0)
        fpr = fp / max(fp + tn, 1)

        # Natural shortage FPR
        ns_mask = np.array([r.get("ground_truth_label") == "natural_shortage" for r in records_list])
        ns_fpr = float(np.sum(ns_mask & (y_p == 1)) / max(np.sum(ns_mask), 1))

        roc = roc_auc_score(y_t, y_s) if len(np.unique(y_t)) > 1 else 0.5
        pr_auc = average_precision_score(y_t, y_s) if len(np.unique(y_t)) > 1 else 0.0

        return {
            "name": name,
            "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "fpr": round(fpr, 4),
            "natural_shortage_fpr": round(ns_fpr, 4),
            "roc_auc": round(roc, 4),
            "pr_auc": round(pr_auc, 4),
        }

    return [
        calc_metrics(y_true, y_pred_rbd40, rbd_scores, "Phase 2 Rule-Based (thr=40)"),
        calc_metrics(y_true, y_pred_iso, iso_norm_scores, "Phase 2 Isolation Forest"),
        calc_metrics(y_true, y_pred_p3_watch, phase3_scores, "Phase 3 Contextual (@ Watch thr=30)"),
        calc_metrics(y_true, y_pred_p3_investigate, phase3_scores, "Phase 3 Contextual (@ Investigate thr=60)"),
    ]


def main():
    print("=" * 78)
    print("  SURGEGUARD PHASE 3 EVALUATION BENCHMARK (Held-out Seed 44)")
    print("=" * 78)

    print("\n--- 1. FULL TRACE EVALUATION (120 steps / scenario = 480 total steps) ---")
    full_metrics = run_evaluation(seed=44, active_only=False)
    print(f"  {'Model':<38}  {'Prec':>7}  {'Rec':>7}  {'F1':>7}  {'FPR':>7}  {'NS-FPR':>7}  {'PR-AUC':>7}  {'ROC':>7}")
    print("  " + "-" * 95)
    for m in full_metrics:
        print(f"  {m['name']:<38}  {m['precision']:>7.4f}  {m['recall']:>7.4f}  {m['f1']:>7.4f}  {m['fpr']:>7.4f}  {m['natural_shortage_fpr']:>7.4f}  {m['pr_auc']:>7.4f}  {m['roc_auc']:>7.4f}")

    print("\n--- 2. ACTIVE ANOMALY INTERVAL EVALUATION (Steps 30-90 where shock is active) ---")
    active_metrics = run_evaluation(seed=44, active_only=True)
    print(f"  {'Model':<38}  {'Prec':>7}  {'Rec':>7}  {'F1':>7}  {'FPR':>7}  {'NS-FPR':>7}  {'PR-AUC':>7}  {'ROC':>7}")
    print("  " + "-" * 95)
    for m in active_metrics:
        print(f"  {m['name']:<38}  {m['precision']:>7.4f}  {m['recall']:>7.4f}  {m['f1']:>7.4f}  {m['fpr']:>7.4f}  {m['natural_shortage_fpr']:>7.4f}  {m['pr_auc']:>7.4f}  {m['roc_auc']:>7.4f}")

    # Export to artifacts
    out_path = os.path.join(backend_root, "app", "models", "artifacts", "phase3_evaluation_results.json")
    with open(out_path, "w") as f:
        json.dump({"full_trace": full_metrics, "active_interval": active_metrics}, f, indent=2)
    print(f"\n[OK] Phase 3 benchmark results saved to: {out_path}\n")


if __name__ == "__main__":
    main()
