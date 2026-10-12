"""
Model Evaluation Service.
Calculates precision, recall, false-positive rate, PR-AUC, ROC-AUC, and detection delay
on synthetic test sets with ground-truth labels.

Phase 2 implementation.
Ensures natural shortage scenarios are specifically evaluated to report false-positive rate.
Uses sklearn for PR/ROC curve integration but falls back to manual trapezoidal integration.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import logger
from app.schemas.metrics import EvaluationMetricsResponse


# Label mapping: which ground_truth_label values are "anomalous"?
_ANOMALOUS_LABELS = {"unusual_supply_drop"}
_NATURAL_SHORTAGE_LABEL = "natural_shortage"  # primary source of false positives


class EvaluationEngine:
    """
    Evaluates anomaly detectors against ground-truth synthetic labels.
    Ensures natural shortage scenarios are evaluated to compute false-positive rate.

    Usage:
        engine = EvaluationEngine()
        results = engine.evaluate_detector(ground_truth_records, prediction_records)
    """

    def __init__(self):
        logger.info("Initialized EvaluationEngine (Phase 2)")

    def evaluate_detector(
        self,
        ground_truth: List[Dict[str, Any]],
        predictions: List[Dict[str, Any]],
    ) -> EvaluationMetricsResponse:
        """
        Computes precision, recall, false-positive rate, PR-AUC, ROC-AUC, and detection latency.

        Args:
            ground_truth: List of dicts with keys: ground_truth_label, step_number, zone_id.
            predictions:  List of dicts with keys: step_number, score (0-100), predicted (0 or 1).
                          Must be aligned with ground_truth by index.

        Returns:
            EvaluationMetricsResponse (Pydantic model)
        """
        if len(ground_truth) != len(predictions):
            raise ValueError(
                f"ground_truth ({len(ground_truth)} rows) and predictions ({len(predictions)} rows) must be the same length."
            )

        y_true = [_label_to_binary(r.get("ground_truth_label", "normal")) for r in ground_truth]
        y_pred = [int(p.get("predicted", 0)) for p in predictions]
        y_score = [float(p.get("score", 0.0)) / 100.0 for p in predictions]  # normalize to [0,1]

        # --- Core metrics ---
        tp, fp, tn, fn = _confusion_matrix(y_true, y_pred)
        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        fpr = fp / max(fp + tn, 1)

        # --- PR-AUC & ROC-AUC ---
        pr_auc = _compute_pr_auc(y_true, y_score)
        roc_auc = _compute_roc_auc(y_true, y_score)

        # --- Detection delay ---
        detection_delay = _compute_detection_delay(ground_truth, predictions)

        # --- Class balance ---
        from collections import Counter
        label_counts = Counter(r.get("ground_truth_label", "normal") for r in ground_truth)
        class_balance = dict(label_counts)

        # --- Per-scenario FPR breakdown (specifically for natural_shortage) ---
        ns_fpr = _compute_natural_shortage_fpr(ground_truth, predictions)

        model_version = predictions[0].get("model_version", "unknown") if predictions else "unknown"

        caveats = [
            "Metrics computed on controlled synthetic scenarios with injected patterns.",
            "Labels do not reflect or prove real-world collusion incidents.",
            f"Natural shortage FPR: {ns_fpr:.3f} (fraction of natural shortage steps flagged as anomalous).",
            "PR-AUC uses trapezoidal integration over threshold sweep.",
        ]

        return EvaluationMetricsResponse(
            model_version=model_version,
            dataset_version="synthetic_phase2_seed42",
            precision=round(precision, 4),
            recall=round(recall, 4),
            false_positive_rate=round(fpr, 4),
            pr_auc=round(pr_auc, 4) if pr_auc is not None else None,
            roc_auc=round(roc_auc, 4) if roc_auc is not None else None,
            class_balance=class_balance,
            detection_delay_minutes=round(detection_delay, 2),
            caveats=caveats,
        )

    def evaluate_at_thresholds(
        self,
        ground_truth: List[Dict[str, Any]],
        scores: List[float],
        thresholds: Optional[List[float]] = None,
    ) -> List[Dict[str, float]]:
        """
        Evaluate precision, recall, FPR at multiple score thresholds.
        Returns a list of dicts suitable for PR curve plotting.

        Args:
            ground_truth: list of ground-truth step dicts
            scores:       list of anomaly scores (0-100) per step
            thresholds:   list of threshold values to test; defaults to [0, 10, 20, ... 100]
        """
        if thresholds is None:
            thresholds = [float(t) for t in range(0, 105, 5)]

        y_true = [_label_to_binary(r.get("ground_truth_label", "normal")) for r in ground_truth]
        results = []

        for thr in thresholds:
            y_pred = [1 if s >= thr else 0 for s in scores]
            tp, fp, tn, fn = _confusion_matrix(y_true, y_pred)
            prec = tp / max(tp + fp, 1)
            rec = tp / max(tp + fn, 1)
            fpr = fp / max(fp + tn, 1)
            results.append({
                "threshold": thr,
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "fpr": round(fpr, 4),
                "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            })

        return results


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------

def _label_to_binary(label: str) -> int:
    """1 = anomalous (unusual_supply_drop), 0 = normal/natural shortage."""
    return 1 if label in _ANOMALOUS_LABELS else 0


def _confusion_matrix(y_true: List[int], y_pred: List[int]) -> Tuple[int, int, int, int]:
    """Returns (TP, FP, TN, FN)."""
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    return tp, fp, tn, fn


def _compute_pr_auc(y_true: List[int], y_score: List[float]) -> Optional[float]:
    """Trapezoidal PR-AUC over threshold sweep [0, 1] at 101 points."""
    if sum(y_true) == 0:
        return None  # No positive samples — PR-AUC undefined

    thresholds = [i / 100.0 for i in range(101)]
    precisions, recalls = [], []

    for thr in thresholds:
        y_pred = [1 if s >= thr else 0 for s in y_score]
        tp, fp, tn, fn = _confusion_matrix(y_true, y_pred)
        prec = tp / max(tp + fp, 1)
        rec = tp / max(tp + fn, 1)
        precisions.append(prec)
        recalls.append(rec)

    # Trapezoidal integration over recall axis (descending thresholds → increasing recall)
    recalls_rev = list(reversed(recalls))
    precs_rev = list(reversed(precisions))
    auc = sum(
        abs(recalls_rev[i + 1] - recalls_rev[i]) * (precs_rev[i + 1] + precs_rev[i]) / 2.0
        for i in range(len(recalls_rev) - 1)
    )
    return auc


def _compute_roc_auc(y_true: List[int], y_score: List[float]) -> Optional[float]:
    """Trapezoidal ROC-AUC over threshold sweep."""
    if sum(y_true) == 0 or sum(y_true) == len(y_true):
        return None  # Degenerate case

    thresholds = [i / 100.0 for i in range(101)]
    tprs, fprs = [], []

    for thr in thresholds:
        y_pred = [1 if s >= thr else 0 for s in y_score]
        tp, fp, tn, fn = _confusion_matrix(y_true, y_pred)
        tprs.append(tp / max(tp + fn, 1))
        fprs.append(fp / max(fp + tn, 1))

    # Trapezoidal integration
    fprs_rev = list(reversed(fprs))
    tprs_rev = list(reversed(tprs))
    auc = sum(
        abs(fprs_rev[i + 1] - fprs_rev[i]) * (tprs_rev[i + 1] + tprs_rev[i]) / 2.0
        for i in range(len(fprs_rev) - 1)
    )
    return auc


def _compute_detection_delay(
    ground_truth: List[Dict[str, Any]],
    predictions: List[Dict[str, Any]],
) -> float:
    """
    Average number of steps between anomaly onset and first correct detection.
    Only counts windows where ground_truth transitions from normal to anomalous.
    Returns 0.0 if no anomalous segments are found.
    """
    delays: List[int] = []
    in_anomaly = False
    onset_step: Optional[int] = None
    first_detected: Optional[int] = None

    for i, (gt, pred) in enumerate(zip(ground_truth, predictions)):
        is_anomalous = _label_to_binary(gt.get("ground_truth_label", "normal")) == 1
        is_flagged = int(pred.get("predicted", 0)) == 1

        if is_anomalous and not in_anomaly:
            in_anomaly = True
            onset_step = int(gt.get("step_number", i))
            first_detected = None

        if in_anomaly and is_flagged and first_detected is None:
            first_detected = int(gt.get("step_number", i))

        if not is_anomalous and in_anomaly:
            # Anomaly window ended
            if onset_step is not None and first_detected is not None:
                delays.append(first_detected - onset_step)
            elif onset_step is not None and first_detected is None:
                delays.append(999)  # Missed: never detected
            in_anomaly = False
            onset_step = None
            first_detected = None

    # Handle anomaly still active at end of sequence
    if in_anomaly and onset_step is not None:
        if first_detected is not None:
            delays.append(first_detected - onset_step)
        else:
            delays.append(999)

    if not delays:
        return 0.0
    valid = [d for d in delays if d < 999]
    return sum(valid) / len(valid) if valid else float("inf")


def _compute_natural_shortage_fpr(
    ground_truth: List[Dict[str, Any]],
    predictions: List[Dict[str, Any]],
) -> float:
    """
    Fraction of natural_shortage steps that were incorrectly flagged as anomalous.
    This is the key false-positive risk metric (natural shortage vs. unusual supply drop).
    """
    ns_total = 0
    ns_flagged = 0
    for gt, pred in zip(ground_truth, predictions):
        if gt.get("ground_truth_label") == _NATURAL_SHORTAGE_LABEL:
            ns_total += 1
            if int(pred.get("predicted", 0)) == 1:
                ns_flagged += 1
    return ns_flagged / max(ns_total, 1)

