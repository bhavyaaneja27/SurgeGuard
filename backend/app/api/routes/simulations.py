from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Response, status

from app.schemas.simulation import (
    ScenarioDefinition,
    SimulationCreateRequest,
    SimulationRunResponse,
    SimulationStepRecord,
)
from app.services.simulator import simulator_service

router = APIRouter(tags=["Simulations"])


@router.get("/scenarios", response_model=List[ScenarioDefinition])
def list_scenarios() -> List[ScenarioDefinition]:
    """
    List available built-in scenario archetypes with descriptions and parameter guidelines.
    """
    return simulator_service.get_available_scenarios()


@router.post("/simulations", response_model=SimulationRunResponse, status_code=status.HTTP_201_CREATED)
def create_simulation(payload: SimulationCreateRequest) -> SimulationRunResponse:
    """
    Execute a deterministic simulation run for the selected scenario and zone.
    Returns the simulation run summary and aggregate metrics.
    """
    run_response, _ = simulator_service.run_simulation(payload)
    return run_response


@router.get("/simulations/{run_id}", response_model=SimulationRunResponse)
def get_simulation_summary(run_id: str) -> SimulationRunResponse:
    """
    Retrieve metadata, operational metrics, and status for a completed simulation run.
    """
    run = simulator_service.get_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation run '{run_id}' not found.",
        )
    return run


@router.get("/simulations/{run_id}/steps", response_model=List[SimulationStepRecord])
def get_simulation_steps(run_id: str) -> List[SimulationStepRecord]:
    """
    Retrieve full time-series records (ride requests, available drivers, wait time,
    fare pressure, etc.) for timeline scrubbing and charts.
    """
    steps = simulator_service.get_run_steps(run_id)
    if steps is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation run '{run_id}' not found.",
        )
    return [SimulationStepRecord(**s) for s in steps]


@router.get("/export/{run_id}")
@router.get("/simulations/{run_id}/export")
def export_simulation_data(
    run_id: str,
    format: str = Query(default="csv", pattern="^(csv|json)$", description="Export format ('csv' or 'json')")
):
    """
    Download simulation time-series dataset as a CSV or JSON file for Colab experiments and model training.
    """
    try:
        content, media_type, filename = simulator_service.export_run_data(run_id, format_type=format)
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation run '{run_id}' not found for export.",
        )
