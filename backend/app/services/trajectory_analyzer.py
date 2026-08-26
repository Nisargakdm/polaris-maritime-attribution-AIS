import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import numpy as np
from app.utils.geo_utils import haversine_distance_km, calculate_bearing_deg, angular_difference_deg
from app.models.schemas import VesselWaypoint, AnomalyFlag
from app.utils.logger import logger

class TrajectoryAnalyzer:
    """
    Analyzes AIS vessel tracks to detect spatiotemporal proximity, trajectory alignment,
    and behavioral kinematic anomalies (speed dips, loitering, transponder gaps).
    """

    @classmethod
    def analyze_vessel_track(
        cls,
        waypoints_raw: List[Dict[str, Any]],
        origin_lat: float,
        origin_lon: float,
        origin_time_start: datetime,
        origin_time_end: datetime,
        spill_centroid_lat: float,
        spill_centroid_lon: float,
        spatial_uncertainty_km: float = 15.0
    ) -> Dict[str, Any]:
        """
        Extracts spatiotemporal and kinematic compatibility metrics for a candidate vessel.
        """
        if not waypoints_raw:
            return {
                "closest_approach_km": 999.0,
                "time_of_closest_approach": origin_time_start,
                "temporal_overlap_hours": 0.0,
                "drift_alignment_deg": 180.0,
                "anomaly_flags": [],
                "waypoints": [],
                "sog_mean": 0.0,
                "sog_min": 0.0
            }

        waypoints = [
            VesselWaypoint(**wp) if isinstance(wp, dict) else wp 
            for wp in waypoints_raw
        ]
        waypoints.sort(key=lambda x: x.timestamp)

        # 1. Compute Closest Point of Approach (CPA) and Time (TCA)
        min_dist_km = 9999.0
        tca = waypoints[0].timestamp
        cpa_wp = waypoints[0]
        
        distances_to_origin = []
        for wp in waypoints:
            d = haversine_distance_km(wp.lat, wp.lon, origin_lat, origin_lon)
            distances_to_origin.append((d, wp))
            if d < min_dist_km:
                min_dist_km = d
                tca = wp.timestamp
                cpa_wp = wp

        # 2. Temporal Overlap calculation
        # Fraction of time vessel was within spatial threshold (e.g. 2.0 * spatial_uncertainty)
        # during the estimated release time window
        proximity_threshold_km = max(20.0, spatial_uncertainty_km * 1.5)
        overlap_seconds = 0.0
        
        for i in range(len(waypoints) - 1):
            wp1 = waypoints[i]
            wp2 = waypoints[i+1]
            d_mid = haversine_distance_km((wp1.lat + wp2.lat)/2.0, (wp1.lon + wp2.lon)/2.0, origin_lat, origin_lon)
            t_mid = wp1.timestamp + (wp2.timestamp - wp1.timestamp)/2.0
            
            if d_mid <= proximity_threshold_km and (origin_time_start <= t_mid <= origin_time_end):
                overlap_seconds += max(0.0, (wp2.timestamp - wp1.timestamp).total_seconds())

        overlap_hours = round(overlap_seconds / 3600.0, 2)

        # 3. Drift trajectory alignment
        # Bearing from estimated origin to observed spill centroid
        drift_direction_deg = calculate_bearing_deg(origin_lat, origin_lon, spill_centroid_lat, spill_centroid_lon)
        # Vessel course at closest approach
        vessel_cog = cpa_wp.cog_degrees
        alignment_diff_deg = angular_difference_deg(vessel_cog, drift_direction_deg)

        # 4. Kinematic Anomaly Detection
        anomalies: List[AnomalyFlag] = []
        sogs = [wp.sog_knots for wp in waypoints]
        sog_mean = float(np.mean(sogs)) if sogs else 10.0
        sog_min = float(np.min(sogs)) if sogs else 10.0

        # Check for significant speed drops near origin
        for wp in waypoints:
            d = haversine_distance_km(wp.lat, wp.lon, origin_lat, origin_lon)
            if d <= proximity_threshold_km:
                if sog_mean > 8.0 and wp.sog_knots < 0.5 * sog_mean:
                    anomalies.append(AnomalyFlag(
                        flag_type="SPEED_DROP",
                        severity="MEDIUM",
                        description=f"Significant speed reduction ({wp.sog_knots} kts vs normal {round(sog_mean, 1)} kts) within {round(d, 1)} km of origin.",
                        timestamp=wp.timestamp,
                        lat=wp.lat,
                        lon=wp.lon
                    ))
                    break

        # Check for loitering behavior
        loiter_count = sum(1 for wp in waypoints if wp.sog_knots < 4.0 and haversine_distance_km(wp.lat, wp.lon, origin_lat, origin_lon) <= proximity_threshold_km)
        if loiter_count >= 2:
            anomalies.append(AnomalyFlag(
                flag_type="LOITERING",
                severity="HIGH",
                description=f"Loitering signature detected: persistent low speed navigation (<4 kts) near probable origin zone.",
                timestamp=tca,
                lat=cpa_wp.lat,
                lon=cpa_wp.lon
            ))

        # Check for AIS transponder gap (silence)
        for i in range(len(waypoints) - 1):
            dt_min = (waypoints[i+1].timestamp - waypoints[i].timestamp).total_seconds() / 60.0
            if dt_min >= 25.0:
                mid_lat = (waypoints[i].lat + waypoints[i+1].lat) / 2.0
                mid_lon = (waypoints[i].lon + waypoints[i+1].lon) / 2.0
                d_gap = haversine_distance_km(mid_lat, mid_lon, origin_lat, origin_lon)
                if d_gap <= proximity_threshold_km * 1.5:
                    anomalies.append(AnomalyFlag(
                        flag_type="AIS_GAP",
                        severity="MEDIUM",
                        description=f"AIS transponder silence detected ({int(dt_min)} min gap) during origin transit window ({round(d_gap, 1)} km from origin).",
                        timestamp=waypoints[i].timestamp,
                        lat=mid_lat,
                        lon=mid_lon
                    ))
                    break

        return {
            "closest_approach_km": round(float(min_dist_km), 2),
            "time_of_closest_approach": tca,
            "temporal_overlap_hours": overlap_hours,
            "drift_alignment_deg": round(float(alignment_diff_deg), 1),
            "anomaly_flags": anomalies,
            "waypoints": waypoints,
            "sog_mean": round(sog_mean, 1),
            "sog_min": round(sog_min, 1)
        }
