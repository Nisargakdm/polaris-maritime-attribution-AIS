import networkx as nx
from typing import List, Dict, Any
from app.models.schemas import (
    SpillDetectionResult, 
    DriftOriginEstimate, 
    VesselCandidate, 
    EvidenceGraph, 
    EvidenceNode, 
    EvidenceEdge
)
from app.utils.logger import logger

class EvidenceGraphBuilder:
    """
    Constructs a directed evidentiary provenance graph using NetworkX.
    Maps relationships between satellite SAR detections, physical drift hindcasts,
    probabilistic origin ellipses, AIS tracks, and ranked candidate vessels.
    """

    @classmethod
    def build_graph(
        cls,
        case_id: str,
        detection: SpillDetectionResult,
        drift: DriftOriginEstimate,
        candidates: List[VesselCandidate]
    ) -> EvidenceGraph:
        G = nx.DiGraph()
        nodes: List[EvidenceNode] = []
        edges: List[EvidenceEdge] = []

        # 1. Satellite Observation Node
        sat_id = f"SAT-{detection.satellite_mission}"
        nodes.append(EvidenceNode(
            id=sat_id,
            label=f"{detection.satellite_mission} SAR Scene",
            node_type="SATELLITE",
            properties={
                "mission": detection.satellite_mission,
                "acquisition": detection.acquisition_time.isoformat(),
                "snr_db": detection.speckle_snr_db
            }
        ))

        # 2. Spill Polygon Node
        spill_id = f"SPILL-{detection.detection_id}"
        nodes.append(EvidenceNode(
            id=spill_id,
            label=f"Oil Spill ({detection.surface_area_sqkm} km²)",
            node_type="SPILL",
            properties={
                "area_sqkm": detection.surface_area_sqkm,
                "confidence": detection.detection_confidence,
                "oil_prob": detection.oil_probability
            }
        ))
        edges.append(EvidenceEdge(
            source=sat_id,
            target=spill_id,
            relation="DETECTS_SEGMENTATION",
            confidence=detection.detection_confidence
        ))

        # 3. Drift Simulation Node
        drift_id = f"DRIFT-{drift.simulation_id}"
        nodes.append(EvidenceNode(
            id=drift_id,
            label=f"Lagrangian Hindcast (-{drift.duration_hours}h)",
            node_type="DRIFT",
            properties={
                "particles": drift.num_particles,
                "current_mps": drift.ocean_current_mean_mps,
                "wind_mps": drift.wind_speed_mean_mps
            }
        ))
        edges.append(EvidenceEdge(
            source=spill_id,
            target=drift_id,
            relation="SEEDED_HINDCAST",
            confidence=0.95
        ))

        # 4. Probable Origin Node
        origin_id = f"ORIGIN-{case_id}"
        nodes.append(EvidenceNode(
            id=origin_id,
            label=f"Origin Zone (±{drift.spatial_uncertainty_km} km)",
            node_type="ORIGIN",
            properties={
                "lat": drift.most_probable_origin_lat,
                "lon": drift.most_probable_origin_lon,
                "release_window_start": drift.origin_time_window_start.isoformat(),
                "release_window_end": drift.origin_time_window_end.isoformat()
            }
        ))
        edges.append(EvidenceEdge(
            source=drift_id,
            target=origin_id,
            relation="ESTIMATES_PROBABLE_SOURCE",
            confidence=0.88
        ))

        # 5. Candidate Vessel Nodes and Evidentiary Links
        for cand in candidates:
            vessel_id = f"VESSEL-{cand.mmsi}"
            nodes.append(EvidenceNode(
                id=vessel_id,
                label=f"{cand.vessel_name} ({cand.vessel_type})",
                node_type="VESSEL",
                properties={
                    "mmsi": cand.mmsi,
                    "flag": cand.flag_country,
                    "score": cand.overall_score,
                    "priority": cand.priority_tier
                }
            ))

            # Vessel to Origin link (Spatial/Temporal Intersect)
            spat_conf = cand.sub_scores.get("spatial_compatibility", 0.5)
            edges.append(EvidenceEdge(
                source=vessel_id,
                target=origin_id,
                relation=f"INTERSECTS_ORIGIN_ZONE (CPA {cand.closest_approach_km}km)",
                confidence=spat_conf
            ))

            # Vessel to Spill link (Attribution compatibility)
            edges.append(EvidenceEdge(
                source=vessel_id,
                target=spill_id,
                relation=f"COMPATIBILITY_SCORE ({int(cand.overall_score*100)}%)",
                confidence=cand.overall_score
            ))

            # Anomaly nodes if present
            for idx, anom in enumerate(cand.anomaly_flags):
                anom_id = f"ANOM-{cand.mmsi}-{idx}"
                nodes.append(EvidenceNode(
                    id=anom_id,
                    label=f"Anomaly: {anom.flag_type}",
                    node_type="ANOMALY",
                    properties={
                        "severity": anom.severity,
                        "description": anom.description
                    }
                ))
                edges.append(EvidenceEdge(
                    source=vessel_id,
                    target=anom_id,
                    relation="EXHIBITS_BEHAVIOR",
                    confidence=0.90
                ))

        return EvidenceGraph(nodes=nodes, edges=edges)
