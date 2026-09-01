from fastapi import APIRouter, HTTPException
from typing import List
from app.models.schemas import VesselCandidate, VesselRiskProfile
from app.services.case_manager import case_manager
from app.services.vessel_risk_profiler import VesselRiskProfiler

router = APIRouter(prefix="/ais", tags=["AIS"])

@router.get("/candidates/{case_id}", response_model=List[VesselCandidate])
async def get_ais_candidates(case_id: str):
    """Returns candidate vessels and full waypoints within the origin-space window."""
    candidates = case_manager.get_candidates(case_id)
    if not candidates:
        raise HTTPException(status_code=404, detail=f"No AIS candidates found for case '{case_id}'.")
    return candidates

@router.get("/vessels/{mmsi}/risk-profile", response_model=VesselRiskProfile)
async def get_vessel_risk_profile(mmsi: str):
    """
    Computes and returns behavioral risk profile for a vessel from its FULL historical AIS track.
    
    Risk profile is based ONLY on AIS behavioral patterns (transponder gaps, speed anomalies,
    loitering frequency) and is NOT predictive certainty or equivalent to safety inspections.
    Use for elevated monitoring priority only.
    
    Args:
        mmsi: Vessel MMSI identifier
        
    Returns:
        VesselRiskProfile with risk_level (INSUFFICIENT_DATA|LOW|MEDIUM|HIGH|ELEVATED),
        component breakdowns, risk factors, and explicit data limitations.
    """
    try:
        profile = VesselRiskProfiler.compute_risk_profile(mmsi)
        
        # Convert dict response to Pydantic model
        if profile["computed_at"]:
            from datetime import datetime
            if isinstance(profile["computed_at"], str):
                profile["computed_at"] = datetime.fromisoformat(profile["computed_at"].replace("Z", "+00:00"))
        
        return VesselRiskProfile(**profile)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compute risk profile for MMSI {mmsi}: {str(e)}"
        )
