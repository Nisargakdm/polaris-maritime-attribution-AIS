#!/usr/bin/env python
"""
Integration test for vessel_risk_profiler.py
Tests that the risk profiler gracefully handles edge cases and computes expected output.
"""

import sys
from datetime import datetime
from app.services.vessel_risk_profiler import VesselRiskProfiler

def test_insufficient_data():
    """Test that risk profiler returns INSUFFICIENT_DATA for vessels not in database."""
    print("\n[TEST] Querying risk profile for non-existent MMSI...")
    result = VesselRiskProfiler.compute_risk_profile("999999999", db_path="data/db/polaris.duckdb")
    
    assert result["mmsi"] == "999999999", "MMSI mismatch"
    assert result["risk_level"] == "INSUFFICIENT_DATA", f"Expected INSUFFICIENT_DATA, got {result['risk_level']}"
    assert result["risk_score"] is None, "Risk score should be None for insufficient data"
    assert not result["data_sufficiency"]["has_sufficient_data"], "Should flag insufficient data"
    
    print("  ✓ Correctly returned INSUFFICIENT_DATA response")
    print(f"  Reason: {result['data_sufficiency']['reason']}")
    return True

def test_response_structure():
    """Test that response has all expected fields."""
    print("\n[TEST] Checking response structure...")
    result = VesselRiskProfiler.compute_risk_profile("000000000", db_path="data/db/polaris.duckdb")
    
    required_fields = [
        "mmsi", "risk_level", "risk_score", "historical_hours", "waypoint_count",
        "data_sufficiency", "gap_analysis", "speed_anomaly_analysis", "loiter_analysis",
        "vessel_context", "risk_factors", "limitations", "computed_at", "note"
    ]
    
    for field in required_fields:
        assert field in result, f"Missing required field: {field}"
    
    print(f"  ✓ All required fields present")
    return True

def test_data_sufficiency_thresholds():
    """Test that the CONFIG thresholds are reasonable."""
    print("\n[TEST] Checking configuration thresholds...")
    cfg = VesselRiskProfiler.CONFIG
    
    assert cfg["min_historical_hours"] >= 1, "Minimum history should be >= 1 hour"
    assert cfg["gap_freq_high"] > cfg["gap_freq_medium"], "HIGH threshold should exceed MEDIUM"
    assert cfg["gap_freq_medium"] > 0, "MEDIUM threshold should be positive"
    
    # Check weights sum to approximately 1.0
    weight_sum = (
        cfg["weight_gap_frequency"] +
        cfg["weight_speed_anomaly"] +
        cfg["weight_loiter_frequency"]
    )
    assert 0.95 <= weight_sum <= 1.05, f"Weights should sum to ~1.0, got {weight_sum}"
    
    print(f"  ✓ Config thresholds validated")
    print(f"    Min history: {cfg['min_historical_hours']}h")
    print(f"    Weight sum: {weight_sum:.2f}")
    return True

def test_risk_level_mapping():
    """Test that score-to-risk-level mapping is correct."""
    print("\n[TEST] Checking risk level mapping...")
    
    test_cases = [
        (0.05, "LOW"),
        (0.35, "MEDIUM"),
        (0.55, "MEDIUM"),
        (0.65, "HIGH"),
        (0.78, "ELEVATED"),
        (0.95, "ELEVATED"),
    ]
    
    for score, expected_level in test_cases:
        level = VesselRiskProfiler._score_to_risk_level(score)
        assert level == expected_level, f"Score {score} -> got {level}, expected {expected_level}"
    
    print(f"  ✓ Risk level mapping correct for {len(test_cases)} test cases")
    return True

def main():
    print("=" * 70)
    print("  VESSEL RISK PROFILER — INTEGRATION TEST")
    print("=" * 70)
    
    try:
        test_data_sufficiency_thresholds()
        test_risk_level_mapping()
        test_response_structure()
        test_insufficient_data()
        
        print("\n" + "=" * 70)
        print("  ALL TESTS PASSED")
        print("=" * 70)
        print("\nNOTE: Full end-to-end test requires AIS data in DuckDB.")
        print("      Once data is ingested via build_ais_db.py, risk profiles can be computed.")
        return 0
    except AssertionError as e:
        print(f"\n[FAIL] {e}")
        return 1
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
