"""
SurgeGuard City Map & Zone Intelligence Routes.
Provides:
  - GET /api/v1/zones : List spatial demo zones
  - GET /api/v1/zones/intelligence : Aggregated zone intelligence, risk categories, and wait times
  - GET /api/v1/zones/{zone_id} : Specific zone operational intelligence
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.simulation import ScenarioType
from app.schemas.zones import (
    ZoneIntelligenceItem,
    ZoneIntelligenceResponse,
)
from app.services.zone_service import zone_service, ZONE_SPATIAL_METADATA

router = APIRouter(tags=["City Map & Zone Intelligence"])


@router.get("/zones/intelligence", response_model=ZoneIntelligenceResponse)
def get_zone_intelligence(
    scenario_type: ScenarioType = Query(
        default="unusual_supply_drop",
        description="Scenario archetype to assess across zones"
    ),
    run_id: Optional[str] = Query(
        default=None,
        description="Optional simulation run ID for contextual zone overlay"
    ),
) -> ZoneIntelligenceResponse:
    """
    Fetch zone-level demand, supply, wait times, fare pressure,
    and contextual anomaly detector outputs across NYC TLC demo zones.
    """
    return zone_service.get_zone_intelligence(
        scenario_type=scenario_type,
        run_id=run_id,
    )


@router.get("/zones", response_model=List[dict])
def list_zones():
    """
    List all NYC TLC demo zones with centroids and boundary coordinates.
    """
    zones_list = []
    for z_id, meta in ZONE_SPATIAL_METADATA.items():
        zones_list.append({
            "zone_id": z_id,
            "zone_name": meta["zone_name"],
            "zone_type": meta["zone_type"],
            "description": meta["description"],
            "centroid": meta["centroid"],
            "boundary": meta["boundary"],
        })
    return zones_list


@router.get("/zones/{zone_id}", response_model=ZoneIntelligenceItem)
def get_single_zone_intelligence(
    zone_id: str,
    scenario_type: ScenarioType = Query(default="unusual_supply_drop"),
    run_id: Optional[str] = Query(default=None),
) -> ZoneIntelligenceItem:
    """
    Retrieve operational intelligence for a specific zone.
    """
    if zone_id not in ZONE_SPATIAL_METADATA:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone '{zone_id}' not found in registered demo zones.",
        )
    resp = zone_service.get_zone_intelligence(
        scenario_type=scenario_type,
        run_id=run_id,
    )
    for z in resp.zones:
        if z.zone_id == zone_id:
            return z
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Zone '{zone_id}' data not found.",
    )
