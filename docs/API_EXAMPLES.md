# SurgeGuard API Specification & Examples

SurgeGuard exposes REST endpoints with versioned `/api/v1` routes and a top-level `/health` readiness check.

## 1. Service Health & Readiness

### `GET /health`
Returns service readiness, version, and dependency status.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "model_status": "not_loaded",
  "database_status": "local_demo_mode",
  "timestamp": "2026-10-12T16:03:05.123456Z"
}
```

---

## 2. Simulation Endpoints (Planned Phase 1)

### `GET /api/v1/scenarios`
List built-in scenarios available for simulation.

**Response (200 OK):**
```json
[
  {
    "id": "scenario-unusual-drop",
    "name": "Abrupt Supply Drop",
    "description": "Sudden 45% driver availability drop with stable passenger demand.",
    "scenario_type": "unusual_supply_drop",
    "seed": 42,
    "parameters": {
      "duration_minutes": 120,
      "intensity": 0.75,
      "zone_id": "zone_midtown_core"
    }
  }
]
```

### `POST /api/v1/simulations`
Execute a seeded scenario simulation.

**Request:**
```json
{
  "scenario_type": "unusual_supply_drop",
  "zone_id": "zone_midtown_core",
  "duration_minutes": 120,
  "event_intensity": 0.75,
  "seed": 42
}
```

**Response (200 OK):**
```json
{
  "run_id": "8f8b89d2-97b1-419b-a0d7-27b0f69a1945",
  "scenario_type": "unusual_supply_drop",
  "seed": 42,
  "status": "completed",
  "started_at": "2026-10-12T16:05:00Z",
  "completed_at": "2026-10-12T16:05:02Z",
  "model_version": "v0.1.0-baseline",
  "data_mode": "SYNTHETIC_SIMULATION",
  "total_steps": 120,
  "summary_metrics": {
    "peak_fare_pressure": 182.5,
    "max_wait_time_minutes": 14.2,
    "unfulfilled_rides": 88
  }
}
```

---

## 3. Alerts & Explainability Endpoints (Planned Phase 3)

### `GET /api/v1/simulations/{run_id}/alerts`
Fetch explainable alerts generated during a simulation run.

**Response (200 OK):**
```json
[
  {
    "id": "alert-4921",
    "run_id": "8f8b89d2-97b1-419b-a0d7-27b0f69a1945",
    "zone_id": "zone_midtown_core",
    "event_time": "2026-10-12T16:45:00Z",
    "score": 84.5,
    "severity": "critical",
    "interpretation": "Unusual shortage — investigate",
    "reasons_json": [
      "Driver availability fell 52% in 10 minutes while demand remained within 4% of expected baseline.",
      "Supply-to-demand ratio dropped to 0.38 (historical baseline: 1.15).",
      "No external weather shock or severe traffic congestion reported for this zone window."
    ],
    "baseline_comparison": {
      "expected_supply": 140.0,
      "observed_supply": 67.0,
      "expected_demand": 125.0,
      "observed_demand": 122.0,
      "supply_delta_pct": -52.1
    },
    "model_version": "v0.1.0-baseline",
    "caveat": "Anomaly score is an operational prioritisation signal based on simulated data; it is not proof of driver collusion."
  }
]
```

---

## 4. Policy Lab Endpoints (Planned Phase 4)

### `POST /api/v1/policies/compare`
Compare interventions on the identical initial starting scenario.

**Request:**
```json
{
  "run_id": "8f8b89d2-97b1-419b-a0d7-27b0f69a1945",
  "policies": ["no_intervention", "targeted_driver_incentive", "rider_discount"],
  "incentive_amount_pct": 25.0,
  "discount_amount_pct": 20.0
}
```

---

## 5. Standard Error Format (PRD Section 12.1)

All API errors return a uniform structure:
```json
{
  "error_code": "VALIDATION_ERROR",
  "message": "Invalid request body or query parameters",
  "details": [
    {
      "loc": ["body", "duration_minutes"],
      "msg": "Input should be less than or equal to 480",
      "type": "less_than_equal"
    }
  ]
}
```
