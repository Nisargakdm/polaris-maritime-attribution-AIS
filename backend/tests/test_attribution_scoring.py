import pytest
from datetime import datetime, timedelta
from app.services.attribution_scorer import AttributionScorer
from app.services.trajectory_analyzer import TrajectoryAnalyzer
from app.models.schemas import AttributionWeightConfig

def test_synthetic_ground_truth_recovery():
    """Verifies that the deliberate discharge candidate ranks #1 (Top-1 Recovery)."""
    t0 = datetime(2026, 8, 20, 14, 0, 0)
    origin_lat, origin_lon = 20.40, 68.80
    t_release = t0 - timedelta(hours=24)
    t_start = t0 - timedelta(hours=48)
    
    # 1. Culprit vessel (passes right through origin at release time with slowdown & gap)
    culprit_wps = [
        {"timestamp": t0 - timedelta(hours=36), "lat": 20.10, "lon": 68.50, "sog_knots": 14.0, "cog_degrees": 115.0},
        {"timestamp": t_release, "lat": 20.41, "lon": 68.81, "sog_knots": 3.5, "cog_degrees": 115.0}, # CPA < 2km & speed drop
        {"timestamp": t0 - timedelta(hours=12), "lat": 20.70, "lon": 69.10, "sog_knots": 13.8, "cog_degrees": 115.0}
    ]
    culprit_vessel = {
        "mmsi": "355912001",
        "vessel_name": "MT AURORA EXPLORER",
        "vessel_type": "Crude Oil Tanker",
        "flag_country": "Panama [PA]",
        "gap_minutes": 45
    }
    
    # 2. Innocent cargo vessel (passes 50km away at steady speed)
    innocent_wps = [
        {"timestamp": t0 - timedelta(hours=36), "lat": 20.90, "lon": 68.30, "sog_knots": 16.5, "cog_degrees": 120.0},
        {"timestamp": t_release, "lat": 21.00, "lon": 68.70, "sog_knots": 16.5, "cog_degrees": 120.0},
        {"timestamp": t0 - timedelta(hours=12), "lat": 21.10, "lon": 69.10, "sog_knots": 16.5, "cog_degrees": 120.0}
    ]
    innocent_vessel = {
        "mmsi": "477192800",
        "vessel_name": "M/V GLOBAL TRADER",
        "vessel_type": "Container Ship",
        "flag_country": "Hong Kong [HK]",
        "gap_minutes": 0
    }
    
    weights = AttributionWeightConfig()
    
    # Analyze and score culprit
    culprit_analysis = TrajectoryAnalyzer.analyze_vessel_track(
        waypoints_raw=culprit_wps,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        origin_time_start=t_start,
        origin_time_end=t0,
        spill_centroid_lat=20.60,
        spill_centroid_lon=69.00,
        spatial_uncertainty_km=15.0
    )
    cand_culprit = AttributionScorer.compute_candidate_score(
        vessel_raw=culprit_vessel,
        trajectory_analysis=culprit_analysis,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        spatial_uncertainty_km=15.0,
        origin_time_start=t_start,
        origin_time_end=t0,
        most_probable_release_time=t_release,
        weights=weights
    )
    
    # Analyze and score innocent
    innocent_analysis = TrajectoryAnalyzer.analyze_vessel_track(
        waypoints_raw=innocent_wps,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        origin_time_start=t_start,
        origin_time_end=t0,
        spill_centroid_lat=20.60,
        spill_centroid_lon=69.00,
        spatial_uncertainty_km=15.0
    )
    cand_innocent = AttributionScorer.compute_candidate_score(
        vessel_raw=innocent_vessel,
        trajectory_analysis=innocent_analysis,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        spatial_uncertainty_km=15.0,
        origin_time_start=t_start,
        origin_time_end=t0,
        most_probable_release_time=t_release,
        weights=weights
    )
    
    ranked = AttributionScorer.rank_candidates([cand_innocent, cand_culprit])
    
    # Ground-truth verification: Culprit MUST rank #1 with significantly higher score
    assert ranked[0].mmsi == "355912001"
    assert ranked[0].overall_score > ranked[1].overall_score
    assert ranked[0].priority_tier == "HIGH"
