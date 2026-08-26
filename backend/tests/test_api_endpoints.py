from starlette.testclient import TestClient
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
