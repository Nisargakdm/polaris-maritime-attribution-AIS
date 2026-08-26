from fastapi import APIRouter, HTTPException
from typing import List
from app.models.schemas import VesselCandidate, AttributionWeightConfig, AnalystReviewUpdate, EvidenceGraph
from app.services.case_manager import case_manager

router = APIRouter(prefix="/attribution", tags=["Attribution"])

@router.get("/{case_id}", response_model=List[VesselCandidate])
async def get_ranked_attribution(case_id: str):
    """Returns ranked candidate vessels with granular score breakdowns and evidence points."""
    candidates = case_manager.get_candidates(case_id)
    if not candidates:
        raise HTTPException(status_code=404, detail=f"No attribution found for case '{case_id}'.")
    return candidates

@router.post("/{case_id}/recompute", response_model=List[VesselCandidate])
async def recompute_attribution(case_id: str, weights: AttributionWeightConfig):
    """Recomputes candidate rankings and scores with updated analyst weights."""
    if case_id not in case_manager.cases_summary:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    return case_manager.recompute_attribution(case_id, weights)

@router.post("/{case_id}/review", response_model=VesselCandidate)
async def update_analyst_review(case_id: str, review: AnalystReviewUpdate):
    """Updates human analyst flags (flag, exclude, notes) for a candidate vessel."""
    updated = case_manager.update_candidate_review(case_id, review)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Vessel with MMSI '{review.mmsi}' not found in case '{case_id}'.")
    return updated

@router.get("/{case_id}/evidence-graph", response_model=EvidenceGraph)
async def get_evidence_graph(case_id: str):
    """Returns directed NetworkX evidentiary provenance graph."""
    graph = case_manager.get_evidence_graph(case_id)
    if not graph:
        raise HTTPException(status_code=404, detail=f"Evidence graph for case '{case_id}' not found.")
    return graph
