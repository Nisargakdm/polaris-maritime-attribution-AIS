#!/usr/bin/env python
"""
Integration test for forward drift prediction feature.
Tests that forward prediction works correctly alongside existing backward drift.
"""

import sys
from datetime import datetime, timedelta
sys.path.insert(0, ".")

from app.services.drift_engine import LagrangianDriftEngine

def test_forward_prediction():
    """Test forward drift prediction produces expected output structure."""
    print("\n" + "=" * 70)
    print("  FORWARD DRIFT PREDICTION — INTEGRATION TEST")
    print("=" * 70)
    
    # Create test spill polygon (simple square)
    spill_geojson = {
        "type": "Polygon",
        "coordinates": [[
            [72.00, 19.00],
            [72.02, 19.00],
            [72.02, 19.02],
            [72.00, 19.02],
            [72.00, 19.00]
        ]]
    }
    
    engine = LagrangianDriftEngine(wind_factor=0.031, diffusion_coeff=1.2)
    t_obs = datetime(2026, 8, 26, 12, 0, 0)
    
    print("\n[1/5] Running forward prediction (48h, 300 particles)...")
    result = engine.run_forward_prediction(
        spill_geojson=spill_geojson,
        observation_time=t_obs,
        duration_hours=48,
        num_particles=300,
        current_u_mps=0.22,
        current_v_mps=-0.12,
        wind_u_mps=4.5,
        wind_v_mps=-2.8
    )
    
    print(f"  ✓ Simulation completed")
    print(f"    Simulation ID: {result['simulation_id']}")
    print(f"    Particles: {result['num_particles']}")
    print(f"    Duration: {result['duration_hours']}h")
    
    print("\n[2/5] Checking prediction centroid...")
    pred_lat = result["prediction_centroid_lat"]
    pred_lon = result["prediction_centroid_lon"]
    print(f"  ✓ Predicted position: ({pred_lat:.5f}, {pred_lon:.5f})")
    
    # Forward drift should move particles in positive time direction
    # With positive u_current and windage, expect eastward drift
    initial_lon = 72.01  # center of test polygon
    assert pred_lon > initial_lon - 0.5, f"Predicted lon {pred_lon} seems unreasonable"
    print(f"    Drift from initial: {pred_lon - initial_lon:.3f}° lon")
    
    print("\n[3/5] Checking uncertainty growth...")
    uncertainty = result["spatial_uncertainty_km"]
    print(f"  ✓ Spatial uncertainty: {uncertainty:.2f} km")
    
    # Uncertainty should be reasonable (not trivially small or absurdly large)
    assert 5.0 < uncertainty < 100.0, f"Uncertainty {uncertainty} km is unreasonable"
    
    # Check ellipses show increasing spread
    ellipses = result["ellipses"]
    print(f"  ✓ Uncertainty ellipses computed: {len(ellipses)} timesteps")
    
    if len(ellipses) >= 2:
        early_ellipse = ellipses[0]
        late_ellipse = ellipses[-1]
        early_radius = early_ellipse["semi_major_km"]
        late_radius = late_ellipse["semi_major_km"]
        print(f"    Early (t={early_ellipse['time_offset_hours']}h): {early_radius:.1f} km")
        print(f"    Late (t={late_ellipse['time_offset_hours']}h): {late_radius:.1f} km")
        
        # Later uncertainty should be >= early (may grow due to diffusion)
        # Allow small tolerance for statistical noise
        assert late_radius >= early_radius * 0.95, "Uncertainty should not shrink significantly over time"
    
    print("\n[4/5] Checking required fields...")
    required_fields = [
        "simulation_id", "duration_hours", "num_particles",
        "prediction_centroid_lat", "prediction_centroid_lon",
        "spatial_uncertainty_km", "prediction_time_window_start",
        "prediction_time_window_end", "ellipses", "density_heatmap_grid",
        "grid_bounds", "sample_trajectories", "ocean_current_mean_mps",
        "wind_speed_mean_mps", "current_vectors", "forcing_data_source", "note"
    ]
    
    for field in required_fields:
        assert field in result, f"Missing required field: {field}"
    
    print(f"  ✓ All {len(required_fields)} required fields present")
    
    print("\n[5/5] Checking trajectories and heatmap...")
    trajectories = result["sample_trajectories"]
    print(f"  ✓ Sample trajectories: {len(trajectories)} particles")
    
    assert len(trajectories) > 0, "Should have at least one trajectory"
    
    first_traj = trajectories[0]
    steps = first_traj["steps"]
    print(f"    First trajectory: {len(steps)} steps")
    
    # Check time progression is forward
    if len(steps) >= 2:
        t0 = steps[0]["time_offset_hours"]
        t1 = steps[1]["time_offset_hours"]
        assert t1 > t0, f"Time should progress forward: {t0} -> {t1}"
        print(f"    Time progression: {t0}h -> {t1}h (forward ✓)")
    
    heatmap = result["density_heatmap_grid"]
    print(f"  ✓ Heatmap grid points: {len(heatmap)}")
    assert len(heatmap) > 0, "Heatmap should have points"
    
    # Check forcing data source is documented
    forcing_source = result["forcing_data_source"]
    print(f"\n  Forcing data source: {forcing_source}")
    assert forcing_source == "simplified_constant", "Should document simplified forcing"
    
    print("\n" + "=" * 70)
    print("  ALL TESTS PASSED — FORWARD PREDICTION WORKING")
    print("=" * 70)
    print("\nNOTE: Forward prediction uses same physics as backward drift,")
    print("      but with positive time integration and growing uncertainty.")
    return 0


def test_backward_still_works():
    """Verify backward drift still works (regression check)."""
    print("\n[REGRESSION CHECK] Verifying backward drift still works...")
    
    spill_geojson = {
        "type": "Polygon",
        "coordinates": [[
            [72.00, 19.00],
            [72.02, 19.00],
            [72.02, 19.02],
            [72.00, 19.02],
            [72.00, 19.00]
        ]]
    }
    
    engine = LagrangianDriftEngine()
    t_obs = datetime(2026, 8, 26, 12, 0, 0)
    
    result = engine.run_reverse_simulation(
        spill_geojson=spill_geojson,
        observation_time=t_obs,
        duration_hours=24,
        num_particles=200
    )
    
    print(f"  ✓ Backward drift: {result.num_particles} particles, {result.duration_hours}h")
    print(f"    Origin: ({result.most_probable_origin_lat:.5f}, {result.most_probable_origin_lon:.5f})")
    
    # Check trajectories have negative time offsets
    if result.sample_trajectories:
        first_traj = result.sample_trajectories[0]
        if len(first_traj.steps) >= 2:
            t0 = first_traj.steps[0].time_offset_hours
            t_last = first_traj.steps[-1].time_offset_hours
            assert t_last < t0, f"Backward drift should have negative progression: {t0} -> {t_last}"
            print(f"    Time progression: {t0}h -> {t_last}h (backward ✓)")
    
    print("  ✓ Backward drift regression check passed")
    return 0


if __name__ == "__main__":
    try:
        test_backward_still_works()
        test_forward_prediction()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAIL] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
