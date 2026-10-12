from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_policy_comparison_baseline_and_interventions():
    payload = {
        "scenario_type": "unusual_supply_drop",
        "zone_id": "zone_midtown_core",
        "duration_minutes": 120,
        "event_intensity": 0.75,
        "seed": 42,
        "policies": [
            "no_intervention",
            "targeted_driver_incentive",
            "rider_discount",
            "supply_recovery_support",
        ],
        "incentive_amount_pct": 25.0,
        "discount_amount_pct": 20.0,
        "recovery_support_pct": 30.0,
    }
    response = client.post("/api/v1/policies/compare", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["baseline_policy"] == "no_intervention"
    assert len(data["comparisons"]) == 4

    # Baseline comparison checks
    base_comp = data["comparisons"][0]
    assert base_comp["policy_type"] == "no_intervention"
    assert base_comp["metrics"]["estimated_intervention_cost"] == 0.0
    assert base_comp["deltas_versus_baseline"]["rides_delta"] == 0

    # Targeted driver incentive checks
    inc_comp = next(c for c in data["comparisons"] if c["policy_type"] == "targeted_driver_incentive")
    assert inc_comp["metrics"]["simulated_driver_incentive_cost"] > 0
    assert inc_comp["metrics"]["available_drivers"] > base_comp["metrics"]["available_drivers"]
    # Supply recovery support checks
    rec_comp = next(c for c in data["comparisons"] if c["policy_type"] == "supply_recovery_support")
    assert rec_comp["metrics"]["estimated_intervention_cost"] > 0

    # Rider discount checks (in supply drop, unfulfilled requests remain high or increase)
    disc_comp = next(c for c in data["comparisons"] if c["policy_type"] == "rider_discount")
    assert disc_comp["metrics"]["simulated_rider_discount_cost"] > 0
    assert disc_comp["metrics"]["ride_requests"] > base_comp["metrics"]["ride_requests"]


def test_policy_export_csv():
    # First create a simulation run
    sim_res = client.post(
        "/api/v1/simulations",
        json={
            "scenario_type": "unusual_supply_drop",
            "zone_id": "zone_midtown_core",
            "duration_minutes": 60,
            "event_intensity": 0.75,
            "seed": 42,
        },
    )
    assert sim_res.status_code == 201
    run_id = sim_res.json()["run_id"]

    # Export policy comparison CSV
    export_res = client.get(f"/api/v1/policies/export/{run_id}?format=csv")
    assert export_res.status_code == 200
    assert "text/csv" in export_res.headers["content-type"]
    assert "policy_type" in export_res.text
    assert "targeted_driver_incentive" in export_res.text


def test_zone_intelligence_endpoint():
    response = client.get("/api/v1/zones/intelligence?scenario_type=unusual_supply_drop")
    assert response.status_code == 200
    data = response.json()
    assert "zones" in data
    assert len(data["zones"]) == 4
    zone_ids = [z["zone_id"] for z in data["zones"]]
    assert "zone_midtown_core" in zone_ids
    assert "zone_downtown_financial" in zone_ids

    midtown = next(z for z in data["zones"] if z["zone_id"] == "zone_midtown_core")
    assert midtown["centroid"]["lat"] > 0
    assert len(midtown["boundary"]) >= 4
    assert midtown["risk_category"] in ("normal", "watch", "investigate")


def test_zones_list_endpoint():
    response = client.get("/api/v1/zones")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 4
