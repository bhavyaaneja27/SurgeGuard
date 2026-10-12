import csv
import io
import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.data_generator import data_generator, SCENARIO_METADATA, ZONE_BASELINES

client = TestClient(app)

REQUIRED_RECORD_COLUMNS = [
    "timestamp",
    "zone_id",
    "scenario_id",
    "scenario_type",
    "random_seed",
    "ride_requests",
    "available_drivers",
    "completed_rides",
    "estimated_wait_time_minutes",
    "fare_pressure_index",
    "supply_demand_ratio",
    "context_type",
    "ground_truth_label",
]


def test_reproducibility_identical_seed():
    """
    Verify that identical parameters and seed produce exact identical time-series records.
    """
    records_1 = data_generator.generate_scenario_records(
        scenario_type="unusual_supply_drop",
        zone_id="zone_midtown_core",
        duration_minutes=60,
        event_intensity=0.8,
        seed=12345,
    )
    records_2 = data_generator.generate_scenario_records(
        scenario_type="unusual_supply_drop",
        zone_id="zone_midtown_core",
        duration_minutes=60,
        event_intensity=0.8,
        seed=12345,
    )

    assert len(records_1) == 60
    assert len(records_2) == 60
    for r1, r2 in zip(records_1, records_2):
        assert r1["ride_requests"] == r2["ride_requests"]
        assert r1["available_drivers"] == r2["available_drivers"]
        assert r1["completed_rides"] == r2["completed_rides"]
        assert r1["fare_pressure_index"] == r2["fare_pressure_index"]
        assert r1["estimated_wait_time_minutes"] == r2["estimated_wait_time_minutes"]
        assert r1["supply_demand_ratio"] == r2["supply_demand_ratio"]


def test_different_seeds_produce_different_traces():
    """
    Verify that varying seeds produce distinct stochastic paths.
    """
    records_a = data_generator.generate_scenario_records(
        scenario_type="normal_marketplace",
        duration_minutes=45,
        seed=101,
    )
    records_b = data_generator.generate_scenario_records(
        scenario_type="normal_marketplace",
        duration_minutes=45,
        seed=999,
    )
    # Check that not all steps are identical
    differences = sum(
        1 for ra, rb in zip(records_a, records_b) if ra["ride_requests"] != rb["ride_requests"]
    )
    assert differences > 0


def test_all_four_scenarios_generate_valid_ranges():
    """
    Verify all 4 scenario archetypes produce valid physical bounds and non-negative counts.
    """
    scenarios = ["normal_marketplace", "demand_led_surge", "natural_shortage", "unusual_supply_drop"]

    for sc in scenarios:
        records = data_generator.generate_scenario_records(
            scenario_type=sc,
            duration_minutes=60,
            event_intensity=0.75,
            seed=42,
        )
        assert len(records) == 60

        for r in records:
            # Check required columns from Section 3
            for col in REQUIRED_RECORD_COLUMNS:
                assert col in r, f"Missing required column '{col}' in scenario '{sc}'"

            # Check sensible ranges
            assert r["ride_requests"] >= 0.0
            assert r["available_drivers"] >= 0.0
            assert r["completed_rides"] >= 0
            assert r["completed_rides"] <= r["ride_requests"] + 1  # Cannot exceed demand
            assert r["estimated_wait_time_minutes"] >= 1.5
            assert r["fare_pressure_index"] >= 50.0
            assert r["supply_demand_ratio"] >= 0.0
            assert r["scenario_type"] == sc


def test_api_list_scenarios():
    """
    Verify GET /api/v1/scenarios returns all 4 scenarios with metadata.
    """
    response = client.get("/api/v1/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 4

    scenario_types = {s["scenario_type"] for s in data}
    assert "normal_marketplace" in scenario_types
    assert "demand_led_surge" in scenario_types
    assert "natural_shortage" in scenario_types
    assert "unusual_supply_drop" in scenario_types


def test_api_simulation_lifecycle():
    """
    Verify full simulation workflow:
    1. POST /api/v1/simulations
    2. GET /api/v1/simulations/{run_id}
    3. GET /api/v1/simulations/{run_id}/steps
    4. GET /api/v1/export/{run_id}?format=csv
    5. GET /api/v1/export/{run_id}?format=json
    """
    payload = {
        "scenario_type": "unusual_supply_drop",
        "zone_id": "zone_midtown_core",
        "duration_minutes": 60,
        "event_intensity": 0.8,
        "seed": 42,
    }
    post_res = client.post("/api/v1/simulations", json=payload)
    assert post_res.status_code == 201
    run_data = post_res.json()
    run_id = run_data["run_id"]

    assert run_data["status"] == "completed"
    assert run_data["scenario_type"] == "unusual_supply_drop"
    assert run_data["total_steps"] == 60
    assert "summary_metrics" in run_data
    assert run_data["summary_metrics"]["peak_fare_pressure"] > 100.0

    # Fetch summary
    get_res = client.get(f"/api/v1/simulations/{run_id}")
    assert get_res.status_code == 200
    assert get_res.json()["run_id"] == run_id

    # Fetch steps
    steps_res = client.get(f"/api/v1/simulations/{run_id}/steps")
    assert steps_res.status_code == 200
    steps = steps_res.json()
    assert len(steps) == 60
    assert steps[0]["step_number"] == 0
    assert "ride_requests" in steps[0]
    assert "available_drivers" in steps[0]

    # Export CSV
    csv_res = client.get(f"/api/v1/export/{run_id}?format=csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    reader = csv.reader(io.StringIO(csv_res.text))
    rows = list(reader)
    # Header + 60 records
    assert len(rows) == 61

    # Export JSON
    json_res = client.get(f"/api/v1/export/{run_id}?format=json")
    assert json_res.status_code == 200
    assert "application/json" in json_res.headers["content-type"]
    exported_records = json.loads(json_res.text)
    assert len(exported_records) == 60


def test_api_invalid_parameters():
    """
    Verify validation error handling (HTTP 422) for out-of-range or missing inputs.
    """
    # Duration below 30
    bad_payload = {
        "scenario_type": "normal_marketplace",
        "duration_minutes": 10,
    }
    response = client.post("/api/v1/simulations", json=bad_payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "VALIDATION_ERROR"
    assert "details" in data


def test_api_non_existent_run():
    """
    Verify 404 response for non-existent run ID with standard error shape.
    """
    response = client.get("/api/v1/simulations/invalid-run-uuid-12345")
    assert response.status_code == 404
    data = response.json()
    assert data["error_code"] == "HTTP_404"
