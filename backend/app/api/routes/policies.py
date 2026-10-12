"""
SurgeGuard What-If Policy Lab Routes.
Provides:
  - POST /api/v1/policies/compare : Run counterfactual policy comparisons against baseline
  - GET  /api/v1/policies/compare/{run_id} : Run policy comparisons for an existing simulation run
  - GET  /api/v1/policies/export/{run_id} : Export policy comparison metrics as CSV or JSON
"""

import csv
import io
import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Response, status

from app.schemas.policy import (
    PolicyComparisonRequest,
    PolicyComparisonResponse,
)
from app.services.policy_simulator import policy_simulator

router = APIRouter(tags=["What-If Policy Lab"])


@router.post(
    "/policies/compare",
    response_model=PolicyComparisonResponse,
    status_code=status.HTTP_200_OK,
)
def compare_policies(payload: PolicyComparisonRequest) -> PolicyComparisonResponse:
    """
    Simulate and compare multiple operational interventions (driver incentive,
    rider discount, supply recovery support) against a reproducible Digital Twin baseline.
    """
    try:
        return policy_simulator.compare_policies(payload)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Policy comparison failed: {str(exc)}",
        )


@router.get(
    "/policies/compare/{run_id}",
    response_model=PolicyComparisonResponse,
)
def compare_policies_for_run(
    run_id: str,
    incentive_pct: float = Query(default=25.0, ge=5.0, le=100.0),
    discount_pct: float = Query(default=20.0, ge=5.0, le=50.0),
    recovery_pct: float = Query(default=30.0, ge=5.0, le=60.0),
) -> PolicyComparisonResponse:
    """
    Evaluate policy interventions using an existing simulation run as the baseline.
    """
    payload = PolicyComparisonRequest(
        run_id=run_id,
        incentive_amount_pct=incentive_pct,
        discount_amount_pct=discount_pct,
        recovery_support_pct=recovery_pct,
    )
    try:
        return policy_simulator.compare_policies(payload)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Policy comparison for run '{run_id}' failed: {str(exc)}",
        )


@router.get("/policies/export/{run_id}")
def export_policy_comparison(
    run_id: str,
    format: str = Query(default="csv", pattern="^(csv|json)$"),
    incentive_pct: float = Query(default=25.0, ge=5.0, le=100.0),
    discount_pct: float = Query(default=20.0, ge=5.0, le=50.0),
    recovery_pct: float = Query(default=30.0, ge=5.0, le=60.0),
):
    """
    Export policy comparison metrics and trade-offs as CSV or JSON.
    """
    payload = PolicyComparisonRequest(
        run_id=run_id,
        incentive_amount_pct=incentive_pct,
        discount_amount_pct=discount_pct,
        recovery_support_pct=recovery_pct,
    )
    result = policy_simulator.compare_policies(payload)

    if format == "json":
        data_str = result.model_dump_json(indent=2)
        return Response(
            content=data_str,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="policy_comparison_{run_id}.json"'},
        )

    # CSV output
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "run_id",
        "policy_type",
        "policy_name",
        "ride_requests",
        "available_drivers",
        "completed_rides",
        "unfulfilled_requests",
        "fulfillment_rate_pct",
        "average_wait_time_minutes",
        "fare_pressure_index",
        "peak_fare_pressure",
        "rides_delta_vs_baseline",
        "unfulfilled_delta",
        "wait_time_delta_mins",
        "fare_pressure_delta",
        "estimated_intervention_cost_usd",
        "cost_per_recovered_ride_usd",
    ])

    for comp in result.comparisons:
        m = comp.metrics
        d = comp.deltas_versus_baseline
        writer.writerow([
            result.run_id,
            comp.policy_type,
            comp.policy_name,
            m.ride_requests,
            m.available_drivers,
            m.completed_rides,
            m.unfulfilled_requests,
            m.fulfillment_rate_pct,
            m.average_wait_time_minutes,
            m.fare_pressure_index,
            m.peak_fare_pressure,
            d.rides_delta,
            d.unfulfilled_delta,
            d.wait_time_delta,
            d.fare_pressure_delta,
            m.estimated_intervention_cost,
            m.cost_per_recovered_ride or "",
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="policy_comparison_{run_id}.csv"'},
    )
