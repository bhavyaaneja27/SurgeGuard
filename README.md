# SurgeGuard — Marketplace Integrity Intelligence

> **ML-Powered Ride-Hailing Marketplace Monitoring & Simulation Platform**

[![Status](https://img.shields.io/badge/Status-Fully%20Integrated-0f4c3a)](file:///c:/Users/user/Desktop/Projects/SurgeGuard)
[![Backend](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python-blue)](file:///c:/Users/user/Desktop/Projects/SurgeGuard/backend)
[![Frontend](https://img.shields.io/badge/Frontend-React%2019%20%7C%20Vite%20%7C%20Tailwind%20CSS-teal)](file:///c:/Users/user/Desktop/Projects/SurgeGuard/frontend)
[![Backend Tests](https://img.shields.io/badge/Backend%20Tests-28%20Passing-success)](file:///c:/Users/user/Desktop/Projects/SurgeGuard/backend)
[![Frontend Tests](https://img.shields.io/badge/Frontend%20Tests-8%20Passing-success)](file:///c:/Users/user/Desktop/Projects/SurgeGuard/frontend)

---

## 1. Project Overview & Research Boundaries

SurgeGuard is an operations and research intelligence platform for ride-hailing marketplaces. It forecasts rider demand and driver availability, detects unusual supply shortages using machine learning and baseline rules, explains the evidence behind alerts, and enables operators to test and compare policy interventions in a simulated Digital Twin sandbox.

### Responsible Research Boundaries
- **Research Prototype:** SurgeGuard is a research and operational benchmarking prototype using synthetic marketplace data.
- **No Private Uber Connection:** Does not access internal Uber APIs, private driver tracking telemetry, or live driver accounts.
- **No Individual Attribution:** Operates on aggregated zone/time metrics. Does not accuse, rank, or penalize individual drivers.
- **Explainability First:** Anomaly scores (0–100) are operational prioritisation indicators, not proof of collusion or wrongdoing.
- **Synthetic Data Transparency:** Synthetic scenarios and simulated outcomes are explicitly labelled across all UI components and API responses.

---

## 2. Core Functional Modules

1. **Marketplace Overview Dashboard:**
   - Real-time marketplace KPIs: Available drivers, ride requests, supply-demand gap, passenger wait times, and fare pressure index.
   - Synchronized demand vs. supply trajectory chart.
   - Recent integrity alerts and zone-level operational conditions.
   - Quick workflow actions linking all platform modules.

2. **Digital Twin Simulator:**
   - Deterministic execution of 4 canonical market scenarios (`normal_marketplace`, `demand_led_surge`, `natural_shortage`, `unusual_supply_drop`).
   - Interactive timeline scrubber with 1x/2x/5x playback controls.
   - Live dispatch economics: completed trips, unfulfilled demand, fare surge index, and driver earnings.
   - Instant export of full 1-minute resolution time series in CSV or JSON.

3. **What-If Policy Lab:**
   - Side-by-side comparative simulation of operational interventions against a shared Digital Twin baseline.
   - Supported interventions:
     - **No Intervention:** Baseline control.
     - **Targeted Driver Incentive:** Configurable per-ride driver bonus (+5% to +100%, supply elasticity $E_s = 0.50$).
     - **Rider Fare Discount:** Configurable fare discount (-5% to -50%, demand elasticity $E_d = 0.60$).
     - **Supply Recovery Support:** Conditional floor subsidy (10% to 60%) activated during acute supply deficits ($R_t < 0.85$).
   - Multi-metric KPI cards, delta indicators, comparative time-series trajectory charts, and cost-per-recovered-ride calculations.
   - Direct export of policy comparison matrices in CSV or JSON.

4. **City Map & Spatial Zone Intelligence:**
   - Interactive schematic New York City TLC demo corridors (Midtown Core, Downtown Financial, Airport Terminal, Uptown Residential).
   - Dynamic map overlays: Anomaly Risk Category, Supply-Demand Ratio, Passenger Wait Times, and Fare Pressure Index.
   - Zone selection panel with detailed telemetry, dominant signal interpretation, active anomaly leads, and direct navigation links.

5. **Integrity Alerts & Explainability:**
   - Contextual anomaly detector outputs integrating rule-based diagnostics and Isolation Forest ML.
   - Contributing feature weights, supporting and weakening evidence, and uncertainty indicators.

6. **Model Evaluation & Benchmarks:**
   - Measured performance metrics on synthetic evaluation benchmarks (Precision 0.963, Recall 0.970, F1 0.967, PR-AUC 0.976).
   - Natural shortage false positive rate (0.038) and demand forecasting baselines (MAE 5.2).

7. **Governance & Data Documentation:**
   - In-app interactive Data Dictionary, Model Card specifications, Policy Simulation microeconomic formulations, and persistence architecture notes.

---

## 3. Monorepo Structure

```text
SurgeGuard/
├── frontend/                     # React 19 + Vite + TypeScript + Tailwind CSS + Recharts
│   ├── src/
│   │   ├── components/           # Global Header, Sidebar, Disclaimer Banner
│   │   ├── features/
│   │   │   ├── digital-twin/     # Scenario runner, scrubber & charts
│   │   │   ├── map/              # City Map & zone intelligence
│   │   │   ├── alerts/           # Integrity alerts & explainability
│   │   │   ├── policy-lab/       # What-If policy intervention lab
│   │   │   ├── model-evaluation/ # Metric curves, trade-offs & ROC/PR
│   │   │   └── settings/         # Governance & data documentation
│   │   ├── lib/
│   │   │   ├── api-client.ts     # Typed centralized API client
│   │   │   └── types.ts          # TypeScript domain interfaces
│   │   └── pages/                # Overview dashboard
│   ├── package.json
│   └── vite.config.ts
├── backend/                      # Python 3.13 + FastAPI + Pydantic + scikit-learn
│   ├── app/
│   │   ├── api/routes/           # Endpoints: /health, /simulations, /assessments, /policies, /zones
│   │   ├── core/                 # Config & logging
│   │   ├── schemas/              # Validated Pydantic models
│   │   ├── services/             # Simulator, feature engineering, forecaster, detector, policy lab
│   │   └── main.py               # FastAPI entrypoint
│   ├── tests/                    # Pytest suite (28 passing tests)
│   └── requirements.txt
├── docs/                         # ARCHITECTURE.md, POLICY_SIMULATION.md, DATA_DICTIONARY.md, MODEL_CARD.md
└── README.md
```

---

## 4. Quickstart: Local Setup & Running

### 1. Backend Service

```bash
cd backend

# Create & activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1    # On Windows
# source .venv/bin/activate   # On macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Start FastAPI development daemon
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)
- Interactive OpenAPI Swagger Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Frontend Application

In a separate terminal:

```bash
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```
- Dashboard URL: [http://localhost:5173](http://localhost:5173)

---

## 5. Automated Test Suites

### Backend Unit & Integration Tests (pytest)
```bash
cd backend
python -m pytest tests -v
```
*Executes 28 automated tests covering:*
- Health check and artifact status.
- Simulation execution, step generation, physical boundary sanity, and CSV/JSON export.
- Rolling feature pipeline and demand forecasting baselines.
- Contextual anomaly detector scoring and explainable interpretations.
- Policy comparison simulation (driver incentives, rider discounts, recovery floors, cost modeling).
- Zone intelligence spatial aggregation and endpoint error contracts.

### Frontend Unit Tests & Production Build (Vitest & Vite)
```bash
cd frontend
npm run test
npm run build
```
*Executes 8 Vitest unit tests verifying typed API client communication and validates full TypeScript compilation with production asset bundling.*

---

## 6. Persistence & Deployment Modes

- **In-Memory Demo Mode (Default):** Runs completely self-contained without external database credentials. Ideal for local research evaluation and demonstrations.
- **PostgreSQL / Supabase Ready:** Connects seamlessly when `DATABASE_URL` is configured in `backend/.env`. All secrets are isolated on the server side.
