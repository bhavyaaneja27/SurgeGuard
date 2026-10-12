"""
SurgeGuard Assessment & Anomaly Alerts Endpoints (Phase 3).
Provides:
  - POST /api/v1/assessments/run/{run_id} : Assess a simulation run and generate explainable alerts
  - GET  /api/v1/assessments/run/{run_id} : Retrieve assessment history and timeline for a run
  - GET  /api/v1/assessments/run/{run_id}/step/{step_number} : Retrieve detailed step explanation
  - GET  /api/v1/alerts : List all flagged alerts across session runs with query filters
"""
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.alerts import (
    RiskCategory,
    RunAssessmentResponse,
    RunAssessmentSummary,
    StepAssessment,
)
from app.services.anomaly_detection import anomaly_detector
from app.services.persistence import persistence_service
from app.services.simulator import simulator_service

router = APIRouter(tags=["Assessments & Alerts"])


def _build_run_assessment_response(run_id: str) -> RunAssessmentResponse:
    """Helper to assess a simulation run and compile RunAssessmentResponse."""
    run = simulator_service.get_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation run '{run_id}' not found.",
        )

    steps = simulator_service.get_run_steps(run_id)
    if not steps:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No time-series steps found for simulation run '{run_id}'.",
        )

    assessments = anomaly_detector.assess_simulation_run(steps)

    scores = [a.score for a in assessments]
    max_score = round(max(scores), 2) if scores else 0.0
    mean_score = round(sum(scores) / len(scores), 2) if scores else 0.0

    normal_cnt = sum(1 for a in assessments if a.risk_category == "normal")
    watch_cnt = sum(1 for a in assessments if a.risk_category == "watch")
    investigate_cnt = sum(1 for a in assessments if a.risk_category == "investigate")

    if investigate_cnt > 0:
        peak_category: RiskCategory = "investigate"
    elif watch_cnt > 0:
        peak_category: RiskCategory = "watch"
    else:
        peak_category: RiskCategory = "normal"

    # Dominant interpretation among non-normal steps or overall
    non_normal = [a for a in assessments if a.risk_category != "normal"]
    if non_normal:
        dominant_interp = max(set(a.interpretation for a in non_normal), key=lambda x: [a.interpretation for a in non_normal].count(x))
    else:
        dominant_interp = "Normal equilibrium"

    alerts_only = [a for a in assessments if a.risk_category in ("watch", "investigate")]

    summary = RunAssessmentSummary(
        run_id=run_id,
        scenario_type=run.scenario_type,
        zone_id=run.zone_id,
        total_steps=len(assessments),
        normal_steps_count=normal_cnt,
        watch_steps_count=watch_cnt,
        investigate_steps_count=investigate_cnt,
        max_score=max_score,
        mean_score=mean_score,
        peak_risk_category=peak_category,
        dominant_interpretation=dominant_interp,
        model_version=anomaly_detector.model_version,
        assessed_at=datetime.now(timezone.utc).isoformat(),
    )

    response = RunAssessmentResponse(
        summary=summary,
        assessments=assessments,
        alerts_only=alerts_only,
    )

    persistence_service.save_run_assessment(run_id, response)
    return response


@router.post("/assessments/run/{run_id}", response_model=RunAssessmentResponse, status_code=status.HTTP_200_OK)
def assess_simulation_run(run_id: str) -> RunAssessmentResponse:
    """
    Execute Phase 3 contextual anomaly detection and explanation pipeline on simulation run.
    """
    return _build_run_assessment_response(run_id)


@router.get("/assessments/run/{run_id}", response_model=RunAssessmentResponse)
def get_run_assessment(run_id: str) -> RunAssessmentResponse:
    """
    Retrieve stored assessment history for a simulation run.
    Computes on-the-fly if not previously evaluated.
    """
    existing = persistence_service.get_run_assessment(run_id)
    if existing:
        return existing
    return _build_run_assessment_response(run_id)


@router.get("/assessments/run/{run_id}/step/{step_number}", response_model=StepAssessment)
def get_step_explanation(run_id: str, step_number: int) -> StepAssessment:
    """
    Retrieve detailed, auditable feature explanation and uncertainty indicator for a specific time step.
    """
    assessment_resp = persistence_service.get_run_assessment(run_id)
    if not assessment_resp:
        assessment_resp = _build_run_assessment_response(run_id)

    step_match = next((a for a in assessment_resp.assessments if a.step_number == step_number), None)
    if not step_match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Step {step_number} not found in assessment for run '{run_id}'.",
        )
    return step_match


@router.get("/alerts", response_model=List[StepAssessment])
def list_alerts(
    zone_id: Optional[str] = Query(None, description="Filter by zone ID"),
    risk_category: Optional[str] = Query(None, description="Filter by risk category ('watch' or 'investigate')"),
    min_score: float = Query(30.0, ge=0.0, le=100.0, description="Minimum risk score threshold"),
) -> List[StepAssessment]:
    """
    List all active anomaly alerts across session simulation runs.
    """
    all_assessments = persistence_service.list_run_assessments()
    alerts: List[StepAssessment] = []

    for run_resp in all_assessments:
        for a in run_resp.assessments:
            if a.score < min_score:
                continue
            if zone_id and a.zone_id != zone_id:
                continue
            if risk_category and a.risk_category != risk_category:
                continue
            alerts.append(a)

    return alerts
