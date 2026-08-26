from pathlib import Path

# 1. Update attribution_scorer.py
scorer_path = Path("backend/app/services/attribution_scorer.py")
scorer_code = '''import math
from datetime import datetime
from typing import List, Dict, Any
from app.models.schemas import VesselCandidate, AttributionWeightConfig, AnomalyFlag
from app.utils.logger import logger

class AttributionScorer:
    """
    Transparent, explainable weighted scoring engine for maritime pollution attribution.
    Evaluates candidate vessels against physical reverse-drift origin, time window,
    kinematic trajectory consistency, behavioral anomalies, and vessel type compatibility.
    """

    VESSEL_TYPE_SCORES = {
        "crude oil tanker": 1.00,
        "oil / chemical tanker": 0.95,
        "petroleum product / chemical tanker": 0.95,
        "product tanker": 0.90,
        "lpg / gas carrier": 0.70,
        "bulk carrier": 0.65,
        "container ship": 0.60,
        "general cargo": 0.60,
        "offshore supply vessel": 0.45,
        "tug / port operations": 0.35,
        "commercial fishing": 0.25,
        "mechanized fishing vessel": 0.25,
        "fishing vessel": 0.25,
        "passenger / ferry": 0.15
    }

    @classmethod
    def get_vessel_type_score(cls, vessel_type: str) -> float:
        v_lower = vessel_type.lower().strip()
        for key, val in cls.VESSEL_TYPE_SCORES.items():
            if key in v_lower:
                return val
        return 0.50

    @classmethod
    def compute_candidate_score(
        cls,
        vessel_raw: Dict[str, Any],
        trajectory_analysis: Dict[str, Any],
        origin_lat: float,
        origin_lon: float,
        spatial_uncertainty_km: float,
        origin_time_start: datetime,
        origin_time_end: datetime,
        most_probable_release_time: datetime,
        weights: AttributionWeightConfig = AttributionWeightConfig()
    ) -> VesselCandidate:
        cpa_km = trajectory_analysis["closest_approach_km"]
        tca = trajectory_analysis["time_of_closest_approach"]
        overlap_hours = trajectory_analysis["temporal_overlap_hours"]
        align_deg = trajectory_analysis["drift_alignment_deg"]
        anomalies: List[AnomalyFlag] = trajectory_analysis["anomaly_flags"]
        
        # 1. Spatial Compatibility Score
        sigma_spat = max(10.0, spatial_uncertainty_km)
        spatial_score = math.exp(-0.5 * ((cpa_km / sigma_spat) ** 2))
        
        # 2. Temporal Compatibility Score
        total_window_hours = max(4.0, (origin_time_end - origin_time_start).total_seconds() / 3600.0)
        dt_hours = abs((tca - most_probable_release_time).total_seconds()) / 3600.0
        sigma_temp = total_window_hours * 0.4
        temporal_score = math.exp(-0.5 * ((dt_hours / max(sigma_temp, 2.0)) ** 2))
        
        # 3. Trajectory / Drift Alignment Score
        rad_diff = math.radians(align_deg)
        trajectory_score = max(0.0, math.cos(rad_diff))
        
        # 4. Behavioral Anomaly Score
        anomaly_score = 0.10
        for anom in anomalies:
            if anom.flag_type == "LOITERING":
                anomaly_score += 0.50
            elif anom.flag_type == "SPEED_DROP":
                anomaly_score += 0.35
            elif anom.flag_type == "COURSE_DEVIATION":
                anomaly_score += 0.20
            elif anom.flag_type == "AIS_GAP":
                anomaly_score += 0.30
        anomaly_score = min(1.0, anomaly_score)
        
        # 5. Vessel Type Compatibility Score
        v_type = vessel_raw.get("vessel_type", "Unknown")
        type_score = cls.get_vessel_type_score(v_type)
        
        # 6. AIS Gap Factor
        has_gap = any(anom.flag_type == "AIS_GAP" for anom in anomalies) or vessel_raw.get("gap_minutes", 0) > 20
        gap_factor = 0.85 if has_gap else 0.0
        
        w_sum = (
            weights.weight_spatial +
            weights.weight_temporal +
            weights.weight_trajectory +
            weights.weight_anomaly +
            weights.weight_vessel_type
        )
        
        raw_composite = (
            weights.weight_spatial * spatial_score +
            weights.weight_temporal * temporal_score +
            weights.weight_trajectory * trajectory_score +
            weights.weight_anomaly * anomaly_score +
            weights.weight_vessel_type * type_score +
            weights.penalty_ais_gap * gap_factor
        ) / max(w_sum + weights.penalty_ais_gap, 1e-4)
        
        overall_score = round(float(max(0.05, min(0.99, raw_composite))), 3)
        
        # Priority classification
        if overall_score >= 0.70:
            priority = "HIGH"
        elif overall_score >= 0.50:
            priority = "MEDIUM"
        elif overall_score >= 0.30:
            priority = "LOW"
        else:
            priority = "UNLIKELY"
            
        evidence_points = []
        if cpa_km <= spatial_uncertainty_km:
            evidence_points.append(f"Direct entry into probable origin zone (CPA {cpa_km} km <= {spatial_uncertainty_km} km uncertainty boundary).")
        else:
            evidence_points.append(f"Proximate navigation to origin area (CPA: {cpa_km} km).")
            
        tca_str = tca.strftime('%H:%M UTC')
        if dt_hours <= 3.0:
            evidence_points.append(f"High temporal overlap: presence within {round(dt_hours, 1)}h of peak estimated discharge window ({tca_str}).")
        else:
            evidence_points.append(f"Temporal proximity: passed origin area at {tca_str} ({round(dt_hours, 1)}h from peak).")
            
        if align_deg <= 35.0:
            evidence_points.append(f"Strong trajectory compatibility: vessel course aligned with ocean drift direction ({align_deg} deg deviation).")
            
        if type_score >= 0.90:
            evidence_points.append(f"High cargo compatibility: classified as {v_type} (capable of carrying bulk hydrocarbon cargo).")
            
        for anom in anomalies:
            evidence_points.append(f"Behavioral Anomaly ({anom.flag_type}): {anom.description}")
            
        sub_scores = {
            "spatial_compatibility": round(float(spatial_score), 3),
            "temporal_compatibility": round(float(temporal_score), 3),
            "trajectory_consistency": round(float(trajectory_score), 3),
            "behavioral_anomaly": round(float(anomaly_score), 3),
            "vessel_compatibility": round(float(type_score), 3),
            "ais_gap_factor": round(float(gap_factor), 3)
        }
        
        weights_dict = {
            "weight_spatial": weights.weight_spatial,
            "weight_temporal": weights.weight_temporal,
            "weight_trajectory": weights.weight_trajectory,
            "weight_anomaly": weights.weight_anomaly,
            "weight_vessel_type": weights.weight_vessel_type,
            "penalty_ais_gap": weights.penalty_ais_gap
        }

        return VesselCandidate(
            mmsi=str(vessel_raw.get("mmsi", "")),
            vessel_name=str(vessel_raw.get("vessel_name", "UNKNOWN VESSEL")),
            vessel_type=v_type,
            flag_country=str(vessel_raw.get("flag_country", "Unknown")),
            imo=str(vessel_raw.get("imo", "N/A")),
            callsign=str(vessel_raw.get("callsign", "N/A")),
            overall_score=overall_score,
            priority_tier=priority,
            sub_scores=sub_scores,
            score_weights_used=weights_dict,
            closest_approach_km=cpa_km,
            time_of_closest_approach=tca,
            temporal_overlap_hours=overlap_hours,
            drift_alignment_deg=align_deg,
            anomaly_flags=anomalies,
            evidence_points=evidence_points,
            waypoints=trajectory_analysis["waypoints"],
            flagged_by_analyst=False,
            excluded_by_analyst=False,
            analyst_notes=None
        )

    @classmethod
    def rank_candidates(cls, candidates: List[VesselCandidate]) -> List[VesselCandidate]:
        return sorted(candidates, key=lambda c: c.overall_score, reverse=True)
'''
scorer_path.write_text(scorer_code, encoding="utf-8")

# 2. Update backend/tests/test_api_endpoints.py using Starlette TestClient
test_api_path = Path("backend/tests/test_api_endpoints.py")
test_api_code = '''from starlette.testclient import TestClient
from app.main import app

def test_health_and_cases():
    client = TestClient(app)
    
    # 1. Health check
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
    
    # 2. List cases
    res_cases = client.get("/api/cases")
    assert res_cases.status_code == 200
    cases = res_cases.json()
    assert len(cases) >= 3
    
    # 3. Get specific case detection
    cid = cases[0]["case_id"]
    res_det = client.get(f"/api/detection/{cid}")
    assert res_det.status_code == 200
    det = res_det.json()
    assert "surface_area_sqkm" in det
    assert "polygon_geojson" in det
    
    # 4. Get drift simulation
    res_drift = client.get(f"/api/drift/{cid}")
    assert res_drift.status_code == 200
    drift = res_drift.json()
    assert drift["num_particles"] > 0
    
    # 5. Get attribution ranking
    res_cand = client.get(f"/api/attribution/{cid}")
    assert res_cand.status_code == 200
    cands = res_cand.json()
    assert len(cands) > 0
    assert cands[0]["overall_score"] >= cands[-1]["overall_score"]
    
    # 6. Get report dossier
    res_rep = client.get(f"/api/report/{cid}")
    assert res_rep.status_code == 200
    rep = res_rep.json()
    assert "provenance_hash_sha256" in rep
    assert "legal_disclaimer" in rep
    
    # 7. Recompute with weights
    new_weights = {
        "weight_spatial": 0.40,
        "weight_temporal": 0.20,
        "weight_trajectory": 0.20,
        "weight_anomaly": 0.10,
        "weight_vessel_type": 0.10,
        "penalty_ais_gap": 0.05
    }
    res_recomp = client.post(f"/api/attribution/{cid}/recompute", json=new_weights)
    assert res_recomp.status_code == 200
    recomp_cands = res_recomp.json()
    assert len(recomp_cands) == len(cands)
'''
test_api_path.write_text(test_api_code, encoding="utf-8")
print("Patched attribution_scorer.py and test_api_endpoints.py successfully!")