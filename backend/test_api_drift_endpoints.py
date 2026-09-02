#!/usr/bin/env python
"""
End-to-end API test for drift endpoints.
Tests that the FastAPI routes work correctly.
"""

import sys
sys.path.insert(0, ".")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_backward_drift_endpoint():
    """Test GET /api/drift/{case_id} returns backward drift."""
    print("\n[1/3] Testing backward drift endpoint...")
    response = client.get("/api/drift/case_04_malacca_strait")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.json()
    assert "most_probable_origin_lat" in data, "Missing origin latitude"
    assert "spatial_uncertainty_km" in data, "Missing spatial uncertainty"
    assert data["duration_hours"] > 0, "Duration should be positive"
    
    print(f"  ✓ Backward drift endpoint working")
    print(f"    Origin: ({data['most_probable_origin_lat']:.5f}, {data['most_probable_origin_lon']:.5f})")
    print(f"    Uncertainty: {data['spatial_uncertainty_km']} km")
    print(f"    Duration: {data['duration_hours']}h backward")

def test_forward_prediction_endpoint():
    """Test GET /api/drift/{case_id}/forward-prediction returns forward drift."""
    print("\n[2/3] Testing forward prediction endpoint...")
    response = client.get("/api/drift/case_04_malacca_strait/forward-prediction?duration_hours=48&num_particles=200")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.json()
    assert "prediction_centroid_lat" in data, "Missing prediction centroid"
    assert "spatial_uncertainty_km" in data, "Missing spatial uncertainty"
    assert data["duration_hours"] == 48, "Duration mismatch"
    assert data["num_particles"] == 200, "Particle count mismatch"
    assert data["forcing_data_source"] == "simplified_constant", "Forcing source should be documented"
    
    print(f"  ✓ Forward prediction endpoint working")
    print(f"    Predicted position: ({data['prediction_centroid_lat']:.5f}, {data['prediction_centroid_lon']:.5f})")
    print(f"    Uncertainty: {data['spatial_uncertainty_km']} km")
    print(f"    Duration: {data['duration_hours']}h forward")
    print(f"    Forcing: {data['forcing_data_source']}")

def test_combined_endpoint():
    """Test GET /api/drift/{case_id}/combined returns both backward and forward."""
    print("\n[3/3] Testing combined drift endpoint...")
    response = client.get("/api/drift/case_04_malacca_strait/combined")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.json()
    assert "backward_drift" in data, "Missing backward drift"
    assert "forward_prediction" in data, "Missing forward prediction"
    assert "spill_centroid_lat" in data, "Missing spill centroid"
    
    backward = data["backward_drift"]
    forward = data["forward_prediction"]
    
    print(f"  ✓ Combined endpoint working")
    print(f"    Spill (t=0): ({data['spill_centroid_lat']:.5f}, {data['spill_centroid_lon']:.5f})")
    print(f"    Origin (t=-{backward['duration_hours']}h): ({backward['most_probable_origin_lat']:.5f}, {backward['most_probable_origin_lon']:.5f})")
    print(f"    Predicted (t=+{forward['duration_hours']}h): ({forward['prediction_centroid_lat']:.5f}, {forward['prediction_centroid_lon']:.5f})")

if __name__ == "__main__":
    print("=" * 70)
    print("  DRIFT API ENDPOINTS — END-TO-END TEST")
    print("=" * 70)
    
    try:
        test_backward_drift_endpoint()
        test_forward_prediction_endpoint()
        test_combined_endpoint()
        
        print("\n" + "=" * 70)
        print("  ALL API TESTS PASSED")
        print("=" * 70)
        print("\nEndpoints ready for frontend integration:")
        print("  - GET /api/drift/{case_id}")
        print("  - GET /api/drift/{case_id}/forward-prediction")
        print("  - GET /api/drift/{case_id}/combined")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAIL] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
