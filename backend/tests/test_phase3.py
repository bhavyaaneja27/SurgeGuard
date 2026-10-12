"""
SurgeGuard Phase 3 Unit & API Tests:
Tests:
  - Demand-conditioned scoring (Cases 1, 2, 3, 4)
  - Fixed-baseline supply deviation persistence
  - Explanation correctness and uncertainty handling
  - FastAPI endpoints for simulation run assessment and step explanation
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.anomaly_detection import AnomalyDetector
from app.services.explanations import ExplanationBuilder
from app.services.data_generator import data_generator
from app.schemas.alerts import StepAssessment, RunAssessmentResponse

client = TestClient(app)


def test_demand_conditioning_cases():
    """Verify that demand behavior distinguishes Case 1 (withholding) from Case 2 (natural shortage)."""
    det = AnomalyDetector()

    # Case 1: Supply plunge (-45%) with flat demand (+0%)
    rec_c1 = {
        "step_number": 54,
        "timestamp": "2026-10-12T18:00:00Z",
        "zone_id": "zone_midtown_core",
        "ride_requests": 120.0,
        "available_drivers": 65.0,  # ~50% drop vs 135 expected
        "fare_pressure_index": 160.0,
        "supply_demand_ratio": 65.0 / 120.0,
    }
    feat_c1 = {
        "supply_drop_pct": 0.12,
        "supply_demand_ratio": 65.0 / 120.0,
        "fare_pressure_delta": 60.0,
        "demand_change_pct": 0.0,
    }
    a_c1 = det.assess_step(rec_c1, feat_c1, sustained_shortage_duration=6)
    assert a_c1.score >= 55.0, f"Case 1 should have high risk score, got {a_c1.score}"
    assert a_c1.risk_category in ("watch", "investigate")
    assert a_c1.interpretation == "Unusual shortage — investigate"
    assert len(a_c1.supporting_reasons) > 0

    # Case 2: Supply plunge (-45%) with surging demand (+40%) (Natural shortage)
    rec_c2 = {
        "step_number": 54,
        "timestamp": "2026-10-12T18:00:00Z",
        "zone_id": "zone_midtown_core",
        "ride_requests": 170.0,  # +42% surge vs 120 expected
        "available_drivers": 65.0,
        "fare_pressure_index": 180.0,
        "supply_demand_ratio": 65.0 / 170.0,
    }
    feat_c2 = {
        "supply_drop_pct": 0.12,
        "supply_demand_ratio": 65.0 / 170.0,
        "fare_pressure_delta": 80.0,
        "demand_change_pct": 0.42,
    }
    a_c2 = det.assess_step(rec_c2, feat_c2, sustained_shortage_duration=6)
    # Natural shortage should be attenuated compared to Case 1
    assert a_c2.score < a_c1.score, "Natural shortage score should be lower than artificial withholding"
    assert a_c2.interpretation == "Likely natural shortage"
    assert any("demand" in r.lower() or "surged" in r.lower() for r in a_c2.weakening_reasons)


def test_fixed_baseline_supply_deviation():
    """Verify that sustained supply drops maintain deviation from expected baseline."""
    det = AnomalyDetector()

    # Even after rolling window adapts (rolling supply_drop_pct = 0.0),
    # fixed baseline supply deficit remains high.
    rec = {
        "step_number": 60,
        "timestamp": "2026-10-12T18:00:00Z",
        "zone_id": "zone_midtown_core",
        "ride_requests": 120.0,
        "available_drivers": 70.0,  # Below baseline ~135
        "fare_pressure_index": 150.0,
        "supply_demand_ratio": 70.0 / 120.0,
    }
    # Rolling feature has adapted and is 0
    feat_adapted = {
        "supply_drop_pct": 0.0,
        "supply_demand_ratio": 70.0 / 120.0,
        "fare_pressure_delta": 0.0,
        "demand_change_pct": 0.0,
    }
    assessment = det.assess_step(rec, feat_adapted, sustained_shortage_duration=10)
    # Must still register supply deficit from expected baseline
    assert assessment.baseline_comparison.supply_delta_pct > 0.30
    assert assessment.score > 30.0


def test_explanation_structure_and_disclaimer():
    """Verify that explanations contain all PRD required fields and prototype disclaimers."""
    builder = ExplanationBuilder()
    det = AnomalyDetector()

    recs = data_generator.generate_scenario_records("unusual_supply_drop", seed=44)
    assessments = det.assess_simulation_run(recs)
    peak = max(assessments, key=lambda a: a.score)

    assert peak.caveat is not None
    assert "RESEARCH PROTOTYPE DISCLAIMER" in peak.caveat or "synthetic" in peak.caveat.lower()
    assert len(peak.top_signals) > 0
    assert peak.demand_trend is not None
    assert peak.uncertainty in ("low", "medium", "high")


def test_api_assessments_workflow():
    """Integration test for POST /api/v1/assessments/run/{id} and GET endpoints."""
    # 1. Create a simulation run
    sim_payload = {
        "scenario_type": "unusual_supply_drop",
        "zone_id": "zone_midtown_core",
        "duration_minutes": 60,
        "event_intensity": 0.75,
        "seed": 42,
    }
    sim_res = client.post("/api/v1/simulations", json=sim_payload)
    assert sim_res.status_code == 201
    run_id = sim_res.json()["run_id"]

    # 2. Assess the simulation run
    assess_res = client.post(f"/api/v1/assessments/run/{run_id}")
    assert assess_res.status_code == 200
    data = assess_res.json()

    assert "summary" in data
    assert "assessments" in data
    assert "alerts_only" in data
    assert data["summary"]["run_id"] == run_id
    assert len(data["assessments"]) == 60

    # 3. Retrieve assessment via GET
    get_res = client.get(f"/api/v1/assessments/run/{run_id}")
    assert get_res.status_code == 200
    assert get_res.json()["summary"]["run_id"] == run_id

    # 4. Retrieve specific step explanation
    step_res = client.get(f"/api/v1/assessments/run/{run_id}/step/30")
    assert step_res.status_code == 200
    step_data = step_res.json()
    assert step_data["step_number"] == 30
    assert "top_signals" in step_data
    assert "baseline_comparison" in step_data

    # 5. List alerts
    alerts_res = client.get("/api/v1/alerts")
    assert alerts_res.status_code == 200
    assert isinstance(alerts_res.json(), list)
