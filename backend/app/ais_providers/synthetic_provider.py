from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.ais_providers.base_provider import BaseAISProvider
from app.utils.logger import logger

class SyntheticEvaluationProvider(BaseAISProvider):
    """
    Synthetic Controlled Scenario Provider with mathematically known ground-truth.
    Used for objective evaluation of Top-1 / Top-3 candidate ranking recovery.
    """

    def get_provider_name(self) -> str:
        return "Controlled Synthetic Ground-Truth Scenario Provider"

    def get_data_coverage_statement(self) -> str:
        return (
            "Synthetic controlled benchmark environment. "
            "Known ground truth: Candidate MMSI 355912001 discharged simulated slick at T - 24.0 hours."
        )

    def query_candidates(
        self,
        bounding_box: List[float],
        time_window_start: datetime,
        time_window_end: datetime,
        case_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        # Origin center: Lat 20.40, Lon 68.80 (Arabian Sea international lane)
        candidates = [
            {
                "mmsi": "355912001",
                "vessel_name": "MT AURORA EXPLORER",
                "vessel_type": "Crude Oil Tanker",
                "flag_country": "Panama [PA]",
                "imo": "9558110",
                "callsign": "3FEQ8",
                "base_lat": 20.42,
                "base_lon": 68.79,
                "heading": 115.0,
                "speed_profile": [14.0, 13.5, 3.8, 3.4, 6.2, 13.8], # Obvious speed drop near origin
                "gap_minutes": 45, # Transponder gap during discharge window
                "is_ground_truth_culprit": True
            },
            {
                "mmsi": "477192800",
                "vessel_name": "M/V GLOBAL TRADER",
                "vessel_type": "Container Ship",
                "flag_country": "Hong Kong [HK]",
                "imo": "9487122",
                "callsign": "VRKM3",
                "base_lat": 20.65,
                "base_lon": 68.95,
                "heading": 120.0,
                "speed_profile": [16.5, 16.6, 16.4, 16.5, 16.7, 16.5],
                "gap_minutes": 0,
                "is_ground_truth_culprit": False
            },
            {
                "mmsi": "636091220",
                "vessel_name": "MT PACIFIC GUARDIAN",
                "vessel_type": "Product Tanker",
                "flag_country": "Liberia [LR]",
                "imo": "9621004",
                "callsign": "A8XJ5",
                "base_lat": 20.05,
                "base_lon": 68.45,
                "heading": 110.0,
                "speed_profile": [13.2, 13.1, 13.0, 13.3, 13.2, 13.1],
                "gap_minutes": 0,
                "is_ground_truth_culprit": False
            },
            {
                "mmsi": "316001240",
                "vessel_name": "F/V SEA BREEZE",
                "vessel_type": "Fishing Vessel",
                "flag_country": "India [IN]",
                "imo": "N/A",
                "callsign": "N/A",
                "base_lat": 20.80,
                "base_lon": 69.20,
                "heading": 270.0,
                "speed_profile": [4.0, 3.8, 4.1, 3.9, 4.0, 4.2],
                "gap_minutes": 0,
                "is_ground_truth_culprit": False
            }
        ]
        
        return self._generate_interpolated_waypoints(candidates, time_window_start, time_window_end)

    def _generate_interpolated_waypoints(
        self, 
        vessel_defs: List[Dict[str, Any]], 
        t_start: datetime, 
        t_end: datetime
    ) -> List[Dict[str, Any]]:
        duration_hours = max(1.0, (t_end - t_start).total_seconds() / 3600.0)
        num_points = 24
        results = []
        for v in vessel_defs:
            waypoints = []
            speeds = v["speed_profile"]
            start_lat = v["base_lat"] - 0.40
            start_lon = v["base_lon"] - 0.40
            lat_step = 0.80 / num_points
            lon_step = 0.80 / num_points
            
            for i in range(num_points):
                pt_time = t_start + timedelta(hours=(i * duration_hours / num_points))
                if v.get("gap_minutes", 0) > 0 and 11 <= i <= 13:
                    continue
                s_idx = min(len(speeds) - 1, int((i / num_points) * len(speeds)))
                cur_lat = start_lat + i * lat_step
                cur_lon = start_lon + i * lon_step
                waypoints.append({
                    "timestamp": pt_time,
                    "lat": round(cur_lat, 5),
                    "lon": round(cur_lon, 5),
                    "sog_knots": round(speeds[s_idx], 1),
                    "cog_degrees": round(v["heading"], 1),
                    "heading": round(v["heading"], 1),
                    "nav_status": "Under way using engine"
                })
            v_dict = dict(v)
            v_dict["waypoints"] = waypoints
            results.append(v_dict)
        return results
