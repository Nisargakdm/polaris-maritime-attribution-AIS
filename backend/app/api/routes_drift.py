from fastapi import APIRouter, HTTPException
from app.models.schemas import DriftOriginEstimate, DriftSimulationRequest
from app.services.case_manager import case_manager

router = APIRouter(prefix="/drift", tags=["Drift"])

@router.get("/{case_id}", response_model=DriftOriginEstimate)
async def get_drift_simulation(case_id: str):
    """Returns backward Lagrangian particle simulation, uncertainty ellipses, and KDE heatmap."""
    drift = case_manager.get_drift(case_id)
    if not drift:
        raise HTTPException(status_code=404, detail=f"No drift hindcast found for case '{case_id}'.")
    return drift

@router.post("/{case_id}/re-simulate", response_model=DriftOriginEstimate)
async def resimulate_drift(case_id: str, config: DriftSimulationRequest):
    """Re-runs backward drift simulation with custom particle count, duration, or wind factor."""
    detection = case_manager.get_detection(case_id)
    summary = case_manager.get_case_summary(case_id)
    if not detection or not summary:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    
    # Re-run simulation with custom parameters
    drift = case_manager.drift_engine.run_reverse_simulation(
        spill_geojson=detection.polygon_geojson,
        observation_time=summary.detection_timestamp,
        duration_hours=config.duration_hours,
        num_particles=config.num_particles
    )
    case_manager.cases_drifts[case_id] = drift
    return drift
