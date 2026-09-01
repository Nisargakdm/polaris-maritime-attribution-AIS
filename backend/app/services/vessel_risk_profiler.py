"""
vessel_risk_profiler.py — Behavioral Risk Profiling from Historical AIS Data
═══════════════════════════════════════════════════════════════════════════════

Computes a complementary "general behavioral risk indicator" from full historical
AIS records (not scoped to any single incident), representing patterns that may
warrant elevated monitoring priority.

IMPORTANT: This is a HEURISTIC PATTERN-BASED SCORE built ONLY from AIS behavioral
signals. It is NOT predictive certainty, NOT a mechanical/sensor assessment, and
does NOT substitute for actual vessel safety/inspection data (hull condition,
engine health, classification society records, etc.).

The score reflects:
  - Frequency of AIS transponder gaps (communication reliability issues)
  - Frequency of erratic speed changes (behavioral anomalies)
  - Frequency of loitering events (unusual dwell patterns)
  - Vessel age/type as supporting (non-determining) context

Risk Levels: INSUFFICIENT_DATA | LOW | MEDIUM | HIGH | ELEVATED
"""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import duckdb

from app.models.schemas import AnomalyFlag
from app.utils.logger import logger


class VesselRiskProfiler:
    """
    Analyzes historical AIS tracks to compute general behavioral risk indicators.
    """

    # Risk thresholds (configurable)
    CONFIG = {
        # Gap detection: gaps >= this many minutes are counted
        "gap_detection_minutes": 25,
        
        # Speed anomaly: SOG drops to < threshold% of rolling average
        "speed_drop_factor": 0.50,
        
        # Loitering: SOG < this many knots
        "loiter_sog_threshold": 4.0,
        
        # Minimum tracked history to compute risk (avoid spurious scores from <1hr data)
        "min_historical_hours": 24,
        
        # Thresholds for gap frequency (gaps per tracked hour)
        "gap_freq_high": 0.10,      # >= 0.10 gaps/hour -> HIGH risk
        "gap_freq_medium": 0.05,    # >= 0.05 gaps/hour -> MEDIUM risk
        
        # Thresholds for speed anomaly frequency
        "speed_anomaly_freq_high": 0.15,    # >= 0.15 events/hour -> HIGH
        "speed_anomaly_freq_medium": 0.08,  # >= 0.08 events/hour -> MEDIUM
        
        # Thresholds for loitering frequency
        "loiter_freq_high": 0.12,      # >= 0.12 loiter_events/hour -> HIGH
        "loiter_freq_medium": 0.06,    # >= 0.06 loiter_events/hour -> MEDIUM
        
        # Score weights (compositing behavioral signals)
        "weight_gap_frequency": 0.35,
        "weight_speed_anomaly": 0.35,
        "weight_loiter_frequency": 0.30,
    }

    @classmethod
    def compute_risk_profile(
        cls,
        mmsi: str,
        db_path: str = "data/db/polaris.duckdb"
    ) -> Dict[str, Any]:
        """
        Computes behavioral risk profile for a vessel from its FULL historical AIS track.

        Args:
            mmsi: Vessel MMSI identifier
            db_path: Path to DuckDB database

        Returns:
            {
                "mmsi": "419001890",
                "risk_level": "ELEVATED",  # or "HIGH", "MEDIUM", "LOW", "INSUFFICIENT_DATA"
                "risk_score": 0.68,  # 0-1 scale
                "historical_hours": 240.5,
                "data_sufficiency": {
                    "has_sufficient_data": true,
                    "min_required_hours": 24,
                    "actual_hours": 240.5,
                    "waypoint_count": 1245,
                    "reason": "..."
                },
                "gap_analysis": {
                    "total_gaps_detected": 15,
                    "gap_frequency_per_hour": 0.062,
                    "gap_severity": "MEDIUM",
                    "largest_gap_minutes": 65,
                    "description": "..."
                },
                "speed_anomaly_analysis": {
                    "anomalies_detected": 28,
                    "anomaly_frequency_per_hour": 0.117,
                    "anomaly_severity": "MEDIUM",
                    "description": "..."
                },
                "loiter_analysis": {
                    "loiter_events": 12,
                    "loiter_frequency_per_hour": 0.050,
                    "loiter_severity": "LOW",
                    "description": "..."
                },
                "vessel_context": {
                    "vessel_type": "Crude Oil Tanker",
                    "vessel_age_years": 8,
                    "note": "Context only — not a determining factor"
                },
                "risk_factors": [
                    "Recurring AIS gaps in vicinity of shipping routes",
                    "Moderate frequency of sharp speed reductions",
                    "Limited loitering activity"
                ],
                "limitations": [
                    "Based solely on AIS behavioral patterns — not hull condition, engine health, or inspection data",
                    "AIS data represents communication from vessel; gaps do not indicate intent or malfunction",
                    "Vessel age/type is supporting context only"
                ],
                "computed_at": "2026-08-30T12:34:56Z",
                "note": "Behavioral risk indicator for monitoring priority. Not predictive certainty."
            }
        """
        try:
            con = duckdb.connect(db_path, read_only=True)
        except Exception as e:
            logger.error(f"Failed to connect to DuckDB at {db_path}: {e}")
            return cls._insufficient_data_response(mmsi, "Database connection failed")

        # Query all AIS waypoints for this MMSI, sorted by timestamp
        try:
            query = f"""
                SELECT mmsi, timestamp, lat, lon, sog_knots, cog_degrees, vessel_type
                FROM ais_tracks
                WHERE mmsi = '{mmsi}'
                ORDER BY timestamp ASC
            """
            result = con.execute(query).fetchall()
            con.close()
        except Exception as e:
            logger.error(f"Failed to query AIS data for MMSI {mmsi}: {e}")
            return cls._insufficient_data_response(mmsi, "Database query failed")

        if not result:
            return cls._insufficient_data_response(mmsi, "No AIS records found")

        # Parse waypoints
        waypoints = []
        vessel_type = None
        for row in result:
            mmsi_rec, ts, lat, lon, sog, cog, v_type = row
            waypoints.append({
                "timestamp": ts,
                "lat": float(lat),
                "lon": float(lon),
                "sog_knots": float(sog),
                "cog_degrees": float(cog)
            })
            if v_type:
                vessel_type = str(v_type)

        waypoints.sort(key=lambda w: w["timestamp"])

        # Check data sufficiency
        if len(waypoints) < 3:
            return cls._insufficient_data_response(
                mmsi,
                f"Insufficient waypoints ({len(waypoints)} < 3)"
            )

        t_start = waypoints[0]["timestamp"]
        t_end = waypoints[-1]["timestamp"]
        
        if isinstance(t_start, str):
            t_start = datetime.fromisoformat(t_start.replace("Z", "+00:00"))
        if isinstance(t_end, str):
            t_end = datetime.fromisoformat(t_end.replace("Z", "+00:00"))
            
        historical_hours = (t_end - t_start).total_seconds() / 3600.0

        if historical_hours < cls.CONFIG["min_historical_hours"]:
            return cls._insufficient_data_response(
                mmsi,
                f"Insufficient history ({historical_hours:.1f}h < {cls.CONFIG['min_historical_hours']}h minimum)"
            )

        # Compute risk components
        gap_analysis = cls._analyze_gaps(waypoints, historical_hours)
        speed_analysis = cls._analyze_speed_anomalies(waypoints, historical_hours)
        loiter_analysis = cls._analyze_loitering(waypoints, historical_hours)

        # Composite risk score
        raw_score = (
            cls.CONFIG["weight_gap_frequency"] * gap_analysis["severity_score"] +
            cls.CONFIG["weight_speed_anomaly"] * speed_analysis["severity_score"] +
            cls.CONFIG["weight_loiter_frequency"] * loiter_analysis["severity_score"]
        )
        risk_score = float(np.clip(raw_score, 0.0, 0.95))

        # Determine risk level
        risk_level = cls._score_to_risk_level(risk_score)

        # Risk factors
        risk_factors = []
        if gap_analysis["severity"] in ["MEDIUM", "HIGH"]:
            risk_factors.append(f"Recurring AIS gaps ({gap_analysis['description']})")
        if speed_analysis["severity"] in ["MEDIUM", "HIGH"]:
            risk_factors.append(f"Erratic speed patterns ({speed_analysis['description']})")
        if loiter_analysis["severity"] in ["MEDIUM", "HIGH"]:
            risk_factors.append(f"Loitering behavior ({loiter_analysis['description']})")

        if not risk_factors:
            risk_factors.append("Behavioral patterns consistent with routine operations")

        response = {
            "mmsi": mmsi,
            "risk_level": risk_level,
            "risk_score": round(risk_score, 3),
            "historical_hours": round(historical_hours, 1),
            "waypoint_count": len(waypoints),
            "data_sufficiency": {
                "has_sufficient_data": True,
                "min_required_hours": cls.CONFIG["min_historical_hours"],
                "actual_hours": round(historical_hours, 1),
                "waypoint_count": len(waypoints),
                "reason": "Sufficient historical AIS data available for profiling"
            },
            "gap_analysis": {
                "total_gaps_detected": gap_analysis["count"],
                "gap_frequency_per_hour": round(gap_analysis["frequency"], 4),
                "gap_severity": gap_analysis["severity"],
                "largest_gap_minutes": gap_analysis["max_gap_minutes"],
                "description": gap_analysis["description"]
            },
            "speed_anomaly_analysis": {
                "anomalies_detected": speed_analysis["count"],
                "anomaly_frequency_per_hour": round(speed_analysis["frequency"], 4),
                "anomaly_severity": speed_analysis["severity"],
                "description": speed_analysis["description"]
            },
            "loiter_analysis": {
                "loiter_events": loiter_analysis["count"],
                "loiter_frequency_per_hour": round(loiter_analysis["frequency"], 4),
                "loiter_severity": loiter_analysis["severity"],
                "description": loiter_analysis["description"]
            },
            "vessel_context": {
                "vessel_type": vessel_type or "Unknown",
                "note": "Type/age are supporting context only — not determining factors"
            },
            "risk_factors": risk_factors,
            "limitations": [
                "Based solely on AIS behavioral patterns — not hull condition, engine health, classification data",
                "AIS gaps reflect transponder communication, not vessel intent or mechanical status",
                "Speed/course anomalies may reflect legitimate operational changes (navigation, weather, cargo ops)",
                "Limited to available historical AIS coverage and accuracy"
            ],
            "computed_at": datetime.utcnow().isoformat() + "Z",
            "note": "Behavioral risk indicator for elevated monitoring priority. Not predictive certainty."
        }

        return response

    @classmethod
    def _analyze_gaps(cls, waypoints: List[Dict], historical_hours: float) -> Dict[str, Any]:
        """Detects and analyzes AIS transponder gaps (silent periods)."""
        gaps = []
        for i in range(len(waypoints) - 1):
            dt_minutes = (waypoints[i+1]["timestamp"] - waypoints[i]["timestamp"]).total_seconds() / 60.0
            if dt_minutes >= cls.CONFIG["gap_detection_minutes"]:
                gaps.append(dt_minutes)

        count = len(gaps)
        frequency = count / max(historical_hours, 1.0)
        max_gap = max(gaps) if gaps else 0.0

        # Severity mapping
        if frequency >= cls.CONFIG["gap_freq_high"]:
            severity = "HIGH"
            severity_score = 0.85
            desc = f"{count} gaps detected (>= {cls.CONFIG['gap_detection_minutes']}m each)"
        elif frequency >= cls.CONFIG["gap_freq_medium"]:
            severity = "MEDIUM"
            severity_score = 0.55
            desc = f"{count} gaps detected, avg {np.mean(gaps):.0f}m"
        else:
            severity = "LOW"
            severity_score = 0.15
            desc = f"{count} minor gaps" if count > 0 else "No significant AIS gaps"

        return {
            "count": count,
            "frequency": frequency,
            "severity": severity,
            "severity_score": severity_score,
            "max_gap_minutes": float(max_gap),
            "description": desc
        }

    @classmethod
    def _analyze_speed_anomalies(cls, waypoints: List[Dict], historical_hours: float) -> Dict[str, Any]:
        """Detects erratic speed changes relative to rolling average."""
        sogs = [wp["sog_knots"] for wp in waypoints]
        if len(sogs) < 5:
            return {
                "count": 0,
                "frequency": 0.0,
                "severity": "LOW",
                "severity_score": 0.1,
                "description": "Insufficient data for speed anomaly analysis"
            }

        # Rolling average (5-point window)
        rolling_avg = np.convolve(sogs, np.ones(5) / 5, mode='valid')

        anomalies = []
        for i, ra in enumerate(rolling_avg):
            if ra > 3.0:  # Only flagged if vessel typically moving
                idx_in_full = i + 2  # Offset due to window size
                if idx_in_full < len(sogs):
                    sog = sogs[idx_in_full]
                    if sog < cls.CONFIG["speed_drop_factor"] * ra:
                        anomalies.append({
                            "sog": sog,
                            "expected": ra,
                            "factor": sog / ra if ra > 0 else 0
                        })

        count = len(anomalies)
        frequency = count / max(historical_hours, 1.0)

        if frequency >= cls.CONFIG["speed_anomaly_freq_high"]:
            severity = "HIGH"
            severity_score = 0.80
        elif frequency >= cls.CONFIG["speed_anomaly_freq_medium"]:
            severity = "MEDIUM"
            severity_score = 0.50
        else:
            severity = "LOW"
            severity_score = 0.15

        desc = f"{count} speed anomalies detected" if count > 0 else "Consistent speed profile"

        return {
            "count": count,
            "frequency": frequency,
            "severity": severity,
            "severity_score": severity_score,
            "description": desc
        }

    @classmethod
    def _analyze_loitering(cls, waypoints: List[Dict], historical_hours: float) -> Dict[str, Any]:
        """Detects low-speed loitering events."""
        loiter_count = sum(1 for wp in waypoints if wp["sog_knots"] < cls.CONFIG["loiter_sog_threshold"])
        frequency = loiter_count / max(len(waypoints), 1.0)

        # Frequency as events per hour (loiter waypoints / total hours)
        loiter_freq_per_hour = loiter_count / max(historical_hours, 1.0)

        if loiter_freq_per_hour >= cls.CONFIG["loiter_freq_high"]:
            severity = "HIGH"
            severity_score = 0.80
        elif loiter_freq_per_hour >= cls.CONFIG["loiter_freq_medium"]:
            severity = "MEDIUM"
            severity_score = 0.50
        else:
            severity = "LOW"
            severity_score = 0.15

        desc = f"{loiter_count} loiter waypoints" if loiter_count > 0 else "No significant loitering"

        return {
            "count": loiter_count,
            "frequency": loiter_freq_per_hour,
            "severity": severity,
            "severity_score": severity_score,
            "description": desc
        }

    @classmethod
    def _score_to_risk_level(cls, score: float) -> str:
        """Maps numerical risk score to categorical risk level."""
        if score >= 0.75:
            return "ELEVATED"
        elif score >= 0.60:
            return "HIGH"
        elif score >= 0.40:
            return "MEDIUM"
        else:
            return "LOW"

    @classmethod
    def _insufficient_data_response(cls, mmsi: str, reason: str) -> Dict[str, Any]:
        """Returns a standardized response when insufficient data is available."""
        return {
            "mmsi": mmsi,
            "risk_level": "INSUFFICIENT_DATA",
            "risk_score": None,
            "historical_hours": 0.0,
            "waypoint_count": 0,
            "data_sufficiency": {
                "has_sufficient_data": False,
                "min_required_hours": cls.CONFIG["min_historical_hours"],
                "actual_hours": 0.0,
                "waypoint_count": 0,
                "reason": reason
            },
            "gap_analysis": None,
            "speed_anomaly_analysis": None,
            "loiter_analysis": None,
            "vessel_context": None,
            "risk_factors": [],
            "limitations": [
                "Insufficient data for reliable risk profiling",
                "Vessel may have limited AIS history in database"
            ],
            "computed_at": datetime.utcnow().isoformat() + "Z",
            "note": f"Risk profile unavailable: {reason}. Please ensure vessel has >= {cls.CONFIG['min_historical_hours']}h of historical AIS data."
        }
