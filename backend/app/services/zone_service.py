"""
Zone Intelligence Service.
Aggregates spatial marketplace metrics, supply/demand imbalances,
and contextual anomaly detector outputs across NYC TLC demo zones.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.logging import logger
from app.schemas.alerts import RiskCategory
from app.schemas.simulation import ScenarioType, SimulationCreateRequest
from app.schemas.zones import (
    LatLng,
    ZoneIntelligenceItem,
    ZoneIntelligenceResponse,
    ZoneIntelligenceSummary,
)
from app.services.anomaly_detection import anomaly_detector
from app.services.data_generator import ZONE_BASELINES
from app.services.simulator import simulator_service

# Geocoded TLC Demo Zones definitions
ZONE_SPATIAL_METADATA: Dict[str, Dict[str, Any]] = {
    "zone_midtown_core": {
        "zone_name": "Midtown Core",
        "zone_type": "Commercial & Transit Hub",
        "description": "High-density commercial core with rapid turnover and severe vulnerability to sudden driver drop-offs.",
        "centroid": {"lat": 40.7549, "lng": -73.9840},
        "boundary": [
            {"lat": 40.7640, "lng": -73.9920},
            {"lat": 40.7660, "lng": -73.9740},
            {"lat": 40.7450, "lng": -73.9700},
            {"lat": 40.7430, "lng": -73.9890},
        ],
    },
    "zone_downtown_financial": {
        "zone_name": "Downtown Financial",
        "zone_type": "Commuter & Corporate Hub",
        "description": "Financial district with sharp morning and evening commute peaks and sensitive corporate travel.",
        "centroid": {"lat": 40.7075, "lng": -74.0090},
        "boundary": [
            {"lat": 40.7160, "lng": -74.0170},
            {"lat": 40.7180, "lng": -74.0020},
            {"lat": 40.6990, "lng": -74.0050},
            {"lat": 40.7010, "lng": -74.0200},
        ],
    },
    "zone_airport_terminal": {
        "zone_name": "Airport Terminal",
        "zone_type": "Staged Queue Transit Hub",
        "description": "Airport staging lot with long inbound passenger queues, high fare sensitivity, and fixed dispatch holding areas.",
        "centroid": {"lat": 40.6413, "lng": -73.7781},
        "boundary": [
            {"lat": 40.6550, "lng": -73.7940},
            {"lat": 40.6580, "lng": -73.7620},
            {"lat": 40.6270, "lng": -73.7600},
            {"lat": 40.6240, "lng": -73.7920},
        ],
    },
    "zone_uptown_residential": {
        "zone_name": "Uptown Residential",
        "zone_type": "Dispersed Residential",
        "description": "Dispersed residential neighborhood with steady local mobility, lower density, and broader pickup radii.",
        "centroid": {"lat": 40.8075, "lng": -73.9626},
        "boundary": [
            {"lat": 40.8200, "lng": -73.9720},
            {"lat": 40.8230, "lng": -73.9500},
            {"lat": 40.7950, "lng": -73.9530},
            {"lat": 40.7920, "lng": -73.9740},
        ],
    },
}


class ZoneIntelligenceService:
    """
    Coordinates spatial intelligence queries across all TLC demo zones.
    """

    def __init__(self):
        logger.info("Initialized ZoneIntelligenceService")

    def get_zone_intelligence(
        self,
        scenario_type: ScenarioType = "unusual_supply_drop",
        selected_zone_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> ZoneIntelligenceResponse:
        """
        Calculates zone-level operational metrics and anomaly detections for all zones.
        """
        zone_items: List[ZoneIntelligenceItem] = []
        tot_investigate = 0
        tot_watch = 0
        tot_normal = 0
        sum_wait = 0.0
        sum_fare = 0.0
        sum_fulfill = 0.0

        for zone_id, meta in ZONE_SPATIAL_METADATA.items():
            baseline_cfg = ZONE_BASELINES.get(zone_id, {
                "baseline_demand": 100.0,
                "baseline_supply": 110.0,
            })
            base_d = baseline_cfg["baseline_demand"]
            base_s = baseline_cfg["baseline_supply"]

            # If a run_id was provided and matches this zone, use its steps;
            # otherwise generate a deterministic run for this zone under the scenario.
            if run_id:
                existing_run = simulator_service.get_run(run_id)
                if existing_run and existing_run.zone_id == zone_id:
                    steps = simulator_service.get_run_steps(run_id) or []
                else:
                    # Generate deterministic zone steps under the scenario
                    sim_req = SimulationCreateRequest(
                        scenario_type=scenario_type,
                        zone_id=zone_id,
                        duration_minutes=120,
                        event_intensity=0.75,
                        seed=42,
                    )
                    _, steps = simulator_service.run_simulation(sim_req)
            else:
                sim_req = SimulationCreateRequest(
                    scenario_type=scenario_type,
                    zone_id=zone_id,
                    duration_minutes=120,
                    event_intensity=0.75,
                    seed=42,
                )
                _, steps = simulator_service.run_simulation(sim_req)

            if steps:
                # Assess steps through the contextual anomaly detector
                assessments = anomaly_detector.assess_simulation_run(steps)
                scores = [a.score for a in assessments]
                max_score = round(max(scores), 2) if scores else 0.0

                investigate_cnt = sum(1 for a in assessments if a.risk_category == "investigate")
                watch_cnt = sum(1 for a in assessments if a.risk_category == "watch")

                if investigate_cnt > 0:
                    risk_cat: RiskCategory = "investigate"
                elif watch_cnt > 0:
                    risk_cat: RiskCategory = "watch"
                else:
                    risk_cat = "normal"

                active_alerts = [
                    f"Step {a.step_number}: {a.interpretation} (score: {a.score})"
                    for a in assessments
                    if a.risk_category in ("watch", "investigate")
                ][:4]

                # Dominant signal
                flagged = [a for a in assessments if a.risk_category != "normal"]
                if flagged:
                    dom_sig = flagged[0].interpretation
                else:
                    dom_sig = "Stable Equilibrium"

                # Peak or critical step for current conditions
                crit_steps = [s for s in steps if s["fare_pressure_index"] >= 130.0 or s["estimated_wait_time_minutes"] >= 6.0]
                sample_step = crit_steps[0] if crit_steps else steps[len(steps) // 2]

                curr_d = float(sample_step["ride_requests"])
                curr_s = float(sample_step["available_drivers"])
                ratio = float(sample_step["supply_demand_ratio"])
                wt = float(sample_step["estimated_wait_time_minutes"])
                fp = float(sample_step["fare_pressure_index"])
                total_reqs = sum(s["ride_requests"] for s in steps)
                total_comp = sum(s["completed_rides"] for s in steps)
                fulfill_pct = round((total_comp / max(1, total_reqs)) * 100.0, 1)
            else:
                curr_d = base_d
                curr_s = base_s
                ratio = 1.1
                wt = 3.5
                fp = 100.0
                fulfill_pct = 95.0
                risk_cat = "normal"
                max_score = 15.0
                investigate_cnt = 0
                watch_cnt = 0
                active_alerts = []
                dom_sig = "Stable Baseline"

            if risk_cat == "investigate":
                tot_investigate += 1
            elif risk_cat == "watch":
                tot_watch += 1
            else:
                tot_normal += 1

            sum_wait += wt
            sum_fare += fp
            sum_fulfill += fulfill_pct

            zone_items.append(
                ZoneIntelligenceItem(
                    zone_id=zone_id,
                    zone_name=meta["zone_name"],
                    zone_type=meta["zone_type"],
                    description=meta["description"],
                    centroid=LatLng(**meta["centroid"]),
                    boundary=[LatLng(**pt) for pt in meta["boundary"]],
                    baseline_demand=base_d,
                    baseline_supply=base_s,
                    current_demand=curr_d,
                    current_supply=curr_s,
                    supply_demand_ratio=ratio,
                    estimated_wait_time_minutes=wt,
                    fare_pressure_index=fp,
                    fulfillment_rate_pct=fulfill_pct,
                    risk_category=risk_cat,
                    anomaly_score=max_score,
                    active_alerts_count=investigate_cnt + watch_cnt,
                    dominant_signal=dom_sig,
                    recent_alert_summaries=active_alerts,
                )
            )

        n = len(zone_items)
        summary = ZoneIntelligenceSummary(
            total_zones=n,
            investigate_zones=tot_investigate,
            watch_zones=tot_watch,
            normal_zones=tot_normal,
            system_avg_wait_time=round(sum_wait / max(1, n), 1),
            system_avg_fare_pressure=round(sum_fare / max(1, n), 1),
            overall_fulfillment_rate=round(sum_fulfill / max(1, n), 1),
        )

        return ZoneIntelligenceResponse(
            scenario_type=scenario_type,
            run_id=run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            zones=zone_items,
            summary=summary,
        )


zone_service = ZoneIntelligenceService()
