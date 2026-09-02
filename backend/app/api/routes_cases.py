from fastapi import APIRouter, HTTPException
from typing import List
from app.models.schemas import CaseSummary, EvidenceGraph
from app.services.case_manager import case_manager

router = APIRouter(prefix="/cases", tags=["Cases"])

@router.get("", response_model=List[CaseSummary])
async def list_cases():
    """Returns all preloaded benchmark and active investigation cases."""
    return case_manager.list_cases()

@router.get("/{case_id}", response_model=CaseSummary)
async def get_case(case_id: str):
    """Retrieves metadata summary for a specific case."""
    summary = case_manager.get_case_summary(case_id)
    if not summary:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    return summary

@router.get("/{case_id}/evidence-graph", response_model=EvidenceGraph)
async def get_evidence_graph(case_id: str):
    """
    Returns the forensic evidentiary linkage graph for a case.
    Nodes: SATELLITE, SPILL, DRIFT, ORIGIN, VESSEL, ANOMALY.
    Edges: directed provenance relationships with confidence scores.
    """
    graph = case_manager.get_evidence_graph(case_id)
    if not graph:
        raise HTTPException(status_code=404, detail=f"No evidence graph found for case '{case_id}'.")
    return graph
