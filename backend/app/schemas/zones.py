from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from app.schemas.alerts import RiskCategory


class LatLng(BaseModel):
    lat: float
    lng: float


class ZoneIntelligenceItem(BaseModel):
    zone_id: str
    zone_name: str
    zone_type: str
    description: str
    centroid: LatLng
    boundary: List[LatLng]
    baseline_demand: float
    baseline_supply: float
    current_demand: float
    current_supply: float
    supply_demand_ratio: float
    estimated_wait_time_minutes: float
    fare_pressure_index: float
    fulfillment_rate_pct: float
    risk_category: RiskCategory
    anomaly_score: float
    active_alerts_count: int
    dominant_signal: str
    recent_alert_summaries: List[str]


class ZoneIntelligenceSummary(BaseModel):
    total_zones: int
    investigate_zones: int
    watch_zones: int
    normal_zones: int
    system_avg_wait_time: float
    system_avg_fare_pressure: float
    overall_fulfillment_rate: float


class ZoneIntelligenceResponse(BaseModel):
    scenario_type: str
    run_id: Optional[str] = None
    timestamp: str
    zones: List[ZoneIntelligenceItem]
    summary: ZoneIntelligenceSummary
    disclaimer: str = (
        "Synthetic NYC TLC Demo Zones — Geocoded schematic centroids and boundaries "
        "for research prototype demonstration; not real-time GPS tracking."
    )
