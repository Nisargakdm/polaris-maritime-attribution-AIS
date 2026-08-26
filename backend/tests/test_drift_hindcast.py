import pytest
from datetime import datetime, timedelta
from shapely.geometry import Polygon, mapping
from app.services.drift_engine import LagrangianDriftEngine
from app.utils.geo_utils import haversine_distance_km, calculate_bearing_deg, compute_uncertainty_ellipse_params

def test_haversine_and_bearing():
    # Chennai to Ennore Port (~20 km North)
    d = haversine_distance_km(13.0827, 80.2707, 13.2500, 80.3200)
    assert 15.0 < d < 25.0
    
    bearing = calculate_bearing_deg(13.0827, 80.2707, 13.2500, 80.3200)
    assert 0.0 <= bearing <= 360.0

def test_lagrangian_drift_hindcast():
    engine = LagrangianDriftEngine(wind_factor=0.031, diffusion_coeff=1.0)
    
    poly = Polygon([(-89.2, 28.3), (-89.1, 28.3), (-89.1, 28.4), (-89.2, 28.4), (-89.2, 28.3)])
    spill_geojson = mapping(poly)
    t0 = datetime(2026, 4, 18, 12, 0, 0)
    
    drift = engine.run_reverse_simulation(
        spill_geojson=spill_geojson,
        observation_time=t0,
        duration_hours=24,
        num_particles=200,
        time_step_minutes=30
    )
    
    assert drift.num_particles == 200
    assert drift.duration_hours == 24
    assert len(drift.ellipses) > 0
    assert drift.spatial_uncertainty_km > 0
    assert drift.origin_time_window_start < t0
    assert len(drift.density_heatmap_grid) > 0
