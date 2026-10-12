# Model Card: SurgeGuard Marketplace Integrity Anomaly Detection

## 1. Model Details
- **Model Name:** SurgeGuard Supply Anomaly Detection & Baseline Forecasting Pipeline
- **Version:** v0.2.0 (Phase 2 Implementation)
- **Model Architecture:** Hybrid Transparent Rule-Based Baseline Engine (4-factor scoring: supply drop, SDR shortage, fare pressure, duration) + Unsupervised Isolation Forest baseline (100 estimators) + Lookup-based Baseline Forecaster.
- **Organization / Author:** SurgeGuard Research Platform

## 2. Intended Use & Scope
- **Intended Use:** Operational prioritisation signal for ride-hailing marketplace analysts to investigate sudden, unexplained supply drop patterns.
- **Evaluation Sandbox:** Simulated Digital Twin environments with reproducible synthetic scenario seeds.
- **Target Persona:** Marketplace operations analysts, policy evaluation teams, and researchers.

## 3. Explicitly Prohibited Interpretations
- **NOT Proof of Collusion:** The model produces an anomaly prioritisation score (0–100), NOT a probability of collusion or legal wrongdoing.
- **NO Individual Attribution:** The model operates strictly on zone/time aggregated metrics. It does not identify, track, rank, or penalize individual drivers.
- **NO Autonomous Action:** Alerts are investigation leads for human-in-the-loop operational review.

## 4. Training Data & Labeling
- **Training Source:** Synthetic digital twin data generator (`SyntheticDataGenerator`) with 4 scenarios (480 records total, 120 steps each, seed 42):
  1. `normal_marketplace` (120 steps) — Baseline normal operations
  2. `demand_led_surge` (120 steps) — Genuine demand surge with proportional supply response
  3. `natural_shortage` (120 steps) — External weather shock with steady organic demand
  4. `unusual_supply_drop` (120 steps) — Sudden driver drop while organic demand remains normal (labelled positive class)
- **Label Status:** Ground-truth scenario labels exist ONLY in the synthetic generator for offline algorithmic benchmarking.

## 5. Empirical Evaluation Metrics (Phase 2 Benchmark)

Evaluated on 480 steps across all 4 synthetic scenarios with rolling feature window size $W=6$:

### Model Comparison Summary

| Metric | Rule-Based Detector (@ thr=40) | Isolation Forest (@ contamination=0.05) |
|---|:---:|:---:|
| **Precision** | **0.6667** | 0.2849 |
| **Recall** | 0.0667 | **0.4083** |
| **False Positive Rate (FPR)** | **0.0111** | 0.3417 |
| **PR-AUC** | **0.3432** | 0.3034 |
| **ROC-AUC** | 0.5474 | **0.5598** |
| **Detection Delay** | 54.00 steps | **13.00 steps** |
| **Natural Shortage FPR** | **0.0333 (3.3%)** | 0.3583 (35.8%) |

### Rule-Based Detector Threshold Sensitivity

| Threshold | Precision | Recall | FPR | TP | FP | FN |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 10 | 0.3375 | 0.2250 | 0.1472 | 27 | 53 | 93 |
| 20 | 0.3235 | 0.1833 | 0.1278 | 22 | 46 | 98 |
| 30 | 0.4571 | 0.1333 | 0.0528 | 16 | 19 | 104 |
| 40 | 0.6667 | 0.0667 | 0.0111 | 8 | 4 | 112 |
| 50 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 120 |

### Per-Scenario Score Distribution (Rule-Based Detector)

| Scenario | Steps | Mean Score | % Flagged (@ thr=40) |
|---|:---:|:---:|:---:|
| `normal_marketplace` | 120 | 0.01 | 0.0% |
| `demand_led_surge` | 120 | 4.74 | 0.0% |
| `natural_shortage` | 120 | 7.93 | 3.3% |
| `unusual_supply_drop` | 120 | 7.15 | 6.7% |

## 6. Caveats & Ethical Considerations
- Public TLC taxi data does not track Uber driver online/offline toggling.
- Model decisions are accompanied by feature attribution reasons, baseline comparisons, and explicit caveats.
- False-positive rate on natural shortages is the critical fairness metric: the Rule-Based Detector achieves 3.3% FPR on natural shortages compared to 35.8% for Isolation Forest, preventing false alarms during genuine weather disruptions.
- If data quality checks fail or inputs fall outside normal operating parameters, the model outputs an "Insufficient evidence" classification rather than fabricating a score.
