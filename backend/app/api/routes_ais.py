from fastapi import APIRouter, HTTPException
from typing import List
from app.models.schemas import VesselCandidate
from app.services.case_manager import case_manager

router = APIRouter(prefix="/ais", tags=["AIS"])

@router.get("/candidates/{case_id}", response_model=List[VesselCandidate])
async def get_ais_candidates(case_id: str):
    """Returns candidate vessels and full waypoints within the origin-space window."""
    candidates = case_manager.get_candidates(case_id)
    if not candidates:
        raise HTTPException(status_code=404, detail=f"No AIS candidates found for case '{case_id}'.")
    return candidates
