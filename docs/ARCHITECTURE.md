# SurgeGuard System Architecture

## 1. System Overview

**SurgeGuard** is a research prototype designed to investigate marketplace integrity and algorithmic pricing anomalies in ride-hailing networks. It models spatial and temporal supply-demand dynamics, evaluates contextual anomaly detection models, and simulates counterfactual operational policy interventions.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             REACT FRONTEND (Vite / TS)                      │
│  ┌───────────┐ ┌──────────────┐ ┌─────────────┐ ┌──────────┐ ┌────────────┐ │
│  │ Overview  │ │ Digital Twin │ │ City Map    │ │ Alerts   │ │ Policy Lab │ │
│  └───────────┘ └──────────────┘ └─────────────┘ └──────────┘ └────────────┘ │
│                     ▲                                                       │
│                     │ Typed HTTP Client (lib/api-client.ts)                 │
│                     ▼                                                       │
│                          FASTAPI BACKEND (Python 3.13)                      │
│  ┌───────────────────────┬───────────────────────┬───────────────────────┐  │
│  │ /simulations          │ /assessments & alerts │ /policies/compare     │  │
│  │ /scenarios            │ /zones/intelligence   │ /health & export      │  │
│  └───────────────────────┴───────────────────────┴───────────────────────┘  │
│                                      │                                      │
│  ┌───────────────────────────────────┴───────────────────────────────────┐  │
│  │                     MODULAR ANALYTICS SERVICES                        │  │
│  │  • DataGenerator / Simulator (Deterministic Scenario Modeling)        │  │
│  │  • FeaturePipeline (Rolling Statistics, Volatility, Deviation)        │  │
│  │  • DemandForecaster (Historical Baseline Predictor)                   │  │
│  │  • ContextualAnomalyDetector (Rule Engine + Isolation Forest ML)      │  │
│  │  • PolicySimulator (What-If Interventions & Microeconomic Elasticity) │  │
│  │  • ZoneIntelligenceService (NYC TLC Demo Centroids & Spatial Signals) │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
│  ┌───────────────────────────────────▼───────────────────────────────────┐  │
│  │                      PERSISTENCE DATA ACCESS LAYER                    │  │
│  │  • In-Memory Local Demo Store (Default, zero external dependencies)   │  │
│  │  • Optional PostgreSQL / Supabase Schema (Configured via env vars)    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Service Layer Components

### 2.1 Marketplace Digital Twin & Data Generator (`simulator.py`, `data_generator.py`)
- Simulates realistic, reproducible time-series market clearing at 1-minute resolution (default 120 minutes).
- Models 4 canonical scenario archetypes:
  1. `normal_marketplace`: Organic market fluctuations near equilibrium.
  2. `demand_led_surge`: Passenger booking surge with delayed driver supply repositioning.
  3. `natural_shortage`: Exogenous weather disruption causing simultaneous demand spike and driver offline exit.
  4. `unusual_supply_drop`: Sudden supply withdrawal while demand remains baseline.

### 2.2 Feature Engineering & Anomaly Detection (`anomaly_detection.py`, `feature_engineering.py`)
- Computes rolling supply drop velocity, deviation from moving-median baseline, and shortage duration.
- Ensembles:
  - **Contextual Rule-Based Classifier**: 3-factor weighting of supply drop severity, persistence, and demand context.
  - **Isolation Forest ML Classifier**: Trained with 100 estimators and 5% contamination on normalized rolling features.
- Generates transparent, human-auditable explanations with supporting and weakening signals.

### 2.3 What-If Policy Lab Simulator (`policy_simulator.py`)
- Evaluates operational counterfactuals against the exact baseline starting conditions:
  - `no_intervention`: Baseline control.
  - `targeted_driver_incentive`: Dynamic per-ride driver bonus ($E_s = 0.50$).
  - `rider_discount`: Consumer price discount ($E_d = 0.60$).
  - `supply_recovery_support`: Minimum revenue floor triggered conditionally when ratio drops below 0.85.
- Computes all operational KPIs, trade-offs, and platform cost ($18.50 base fare * delta).

### 2.4 Zone Intelligence Service (`zone_service.py`)
- Monitors 4 synthetic NYC TLC demo zones: Midtown Core, Downtown Financial, Airport Terminal, Uptown Residential.
- Computes real-time spatial indicators: supply/demand ratio, estimated wait times, fare pressure index, active alerts.

---

## 3. Data Persistence Architecture

SurgeGuard employs a dual-mode persistence strategy:
1. **In-Memory Demo Mode (Active)**:
   - When `DATABASE_URL` is unset, all simulation runs, step records, policy evaluations, and assessments are held in memory.
   - Ideal for rapid local evaluation, Colab replication, and zero-configuration development.
2. **PostgreSQL / Supabase Ready**:
   - Seamlessly binds to PostgreSQL when `DATABASE_URL` and `SUPABASE_KEY` are provided.
   - Secrets remain securely on the backend server.

---

## 4. Research Integrity & System Boundaries

- SurgeGuard is a research simulation prototype.
- Ground truth simulation labels (`unusual_supply_drop`, `natural_shortage`) are for benchmarking algorithms and **do not constitute real-world legal proof of driver collusion**.
- All TLC zone boundaries and demand metrics are synthetic demo representations.
