from fastapi import APIRouter, HTTPException
from typing import Dict, Any
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

@router.get("/{case_id}/forward-prediction")
async def get_forward_prediction(
    case_id: str,
    duration_hours: int = 48,
    num_particles: int = 300
) -> Dict[str, Any]:
    """
    Returns FORWARD drift prediction from current spill location into future.
    
    Computes where the oil slick is likely to drift over the next duration_hours
    using the same Lagrangian physics as backward drift, but with forward time integration.
    
    Uncertainty grows with time horizon.
    
    Args:
        case_id: Incident identifier
        duration_hours: Future prediction window (default: 48h)
        num_particles: Particle count (default: 300 for performance)
    
    Returns:
        {
            "simulation_id": "FWDSIM-...",
            "duration_hours": 48,
            "num_particles": 300,
            "prediction_centroid_lat": ...,
            "prediction_centroid_lon": ...,
            "spatial_uncertainty_km": ...,  # grows with time
            "prediction_time_window_start": "...",
            "prediction_time_window_end": "...",
            "ellipses": [...],
            "density_heatmap_grid": [[lat, lon, density], ...],
            "grid_bounds": [...],
            "sample_trajectories": [...],
            "forcing_data_source": "simplified_constant",
            "note": "Forward prediction with simplified forcing. Uncertainty increases over time."
        }
    """
    detection = case_manager.get_detection(case_id)
    summary = case_manager.get_case_summary(case_id)
    if not detection or not summary:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    
    # Run forward prediction
    forward_result = case_manager.drift_engine.run_forward_prediction(
        spill_geojson=detection.polygon_geojson,
        observation_time=summary.detection_timestamp,
        duration_hours=duration_hours,
        num_particles=num_particles
    )
    
    return forward_result

@router.get("/{case_id}/combined")
async def get_combined_drift(case_id: str) -> Dict[str, Any]:
    """
    Returns BOTH backward (origin reconstruction) and forward (future prediction) drift results.
    
    Useful for showing full temporal context: where did the spill come from, and where is it going.
    """
    # Get backward drift (already computed during case initialization)
    drift_backward = case_manager.get_drift(case_id)
    if not drift_backward:
        raise HTTPException(status_code=404, detail=f"No drift hindcast found for case '{case_id}'.")
    
    # Compute forward prediction
    detection = case_manager.get_detection(case_id)
    summary = case_manager.get_case_summary(case_id)
    if not detection or not summary:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    
    drift_forward = case_manager.drift_engine.run_forward_prediction(
        spill_geojson=detection.polygon_geojson,
        observation_time=summary.detection_timestamp,
        duration_hours=48,
        num_particles=300
    )
    
    return {
        "case_id": case_id,
        "observation_time": summary.detection_timestamp.isoformat() + "Z",
        "spill_centroid_lat": detection.centroid_lat,
        "spill_centroid_lon": detection.centroid_lon,
        "backward_drift": drift_backward.dict(),
        "forward_prediction": drift_forward,
        "note": "Backward drift shows reconstructed origin; forward prediction shows likely future trajectory."
    }

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
