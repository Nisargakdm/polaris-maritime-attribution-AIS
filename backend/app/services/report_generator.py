import hashlib
import json
from datetime import datetime
from typing import List, Dict, Any
from app.models.schemas import (
    SpillDetectionResult, 
    DriftOriginEstimate, 
    VesselCandidate, 
    InvestigationDossier, 
    EvidenceGraph
)
from app.config import settings
from app.utils.logger import logger

class ReportGenerator:
    """
    Generates structured, authoritative Maritime Pollution Investigation Briefs
    with cryptographic provenance tracking and strict decision-support guardrails.
    """

    @staticmethod
    def calculate_provenance_hash(
        case_id: str,
        detection: SpillDetectionResult,
        drift: DriftOriginEstimate,
        candidates: List[VesselCandidate]
    ) -> str:
        """
        Computes SHA-256 hash over all evidentiary inputs to guarantee forensic data integrity.
        """
        hash_payload = {
            "case_id": case_id,
            "satellite": detection.satellite_mission,
            "acquisition_time": detection.acquisition_time.isoformat(),
            "spill_centroid": [detection.centroid_lat, detection.centroid_lon],
            "spill_area": detection.surface_area_sqkm,
            "simulation_id": drift.simulation_id,
            "origin_centroid": [drift.most_probable_origin_lat, drift.most_probable_origin_lon],
            "candidate_scores": [
                {"mmsi": c.mmsi, "score": c.overall_score, "cpa": c.closest_approach_km}
                for c in candidates
            ]
        }
        raw_str = json.dumps(hash_payload, sort_keys=True)
        return hashlib.sha256(raw_str.encode('utf-8')).hexdigest()

    @classmethod
    def generate_dossier(
        cls,
        case_id: str,
        case_title: str,
        detection: SpillDetectionResult,
        drift: DriftOriginEstimate,
        candidates: List[VesselCandidate],
        evidence_graph: EvidenceGraph,
        analyst_notes: str = None
    ) -> InvestigationDossier:
        """
        Builds complete Investigation Dossier object.
        """
        provenance_hash = cls.calculate_provenance_hash(case_id, detection, drift, candidates)
        now_time = datetime.utcnow()
        
        top_candidate = candidates[0] if candidates else None
        
        # 1. Executive summary text
        exec_summary = (
            f"On {detection.acquisition_time.strftime('%d %b %Y at %H:%M UTC')}, a probable mineral oil slick "
            f"covering approximately {detection.surface_area_sqkm} km² was detected in {detection.satellite_mission} SAR imagery "
            f"at coordinates {detection.centroid_lat:.4f}°N, {detection.centroid_lon:.4f}°E. "
            f"Backward Lagrangian drift modeling (forced by Copernicus Marine surface currents and ERA5 wind fields) "
            f"estimates that the discharge originated {drift.spatial_uncertainty_km} km upstream between "
            f"{drift.origin_time_window_start.strftime('%H:%M UTC')} and {drift.origin_time_window_end.strftime('%H:%M UTC')}. "
            f"Spatiotemporal AIS correlation identified {len(candidates)} candidate vessels within the 95% uncertainty envelope. "
        )
        if top_candidate and top_candidate.overall_score >= 0.70:
            exec_summary += (
                f"The highest-priority investigative lead is vessel '{top_candidate.vessel_name}' (MMSI: {top_candidate.mmsi}, "
                f"Flag: {top_candidate.flag_country}), exhibiting a composite compatibility score of {int(top_candidate.overall_score*100)}% "
                f"due to spatial proximity (CPA {top_candidate.closest_approach_km} km), temporal window coincidence, and kinematic profile."
            )
        else:
            exec_summary += "No single candidate vessel exhibited decisive priority; multiple vessels present moderate compatibility."

        uncertainty_stmt = (
            f"Physical reverse-drift uncertainty is quantified at ±{drift.spatial_uncertainty_km} km spatial radius (95% confidence) "
            f"and ±{(drift.origin_time_window_end - drift.origin_time_window_start).total_seconds()/7200.0:.1f} hours temporal duration. "
            "Attribution scores represent mathematical compatibility based on available sensors and are subject to environmental "
            "forcing variance and AIS coverage density."
        )

        data_limitations = [
            "Sentinel-1 SAR spatial resolution (~20m) cannot resolve micro-sheens < 0.1 mm thickness.",
            "AIS transponder silence may represent transmission packet loss rather than intentional deactivation.",
            "Surface current forcing resolution (~1/12°) does not capture unresolved sub-mesoscale coastal eddies."
        ]

        recommended_actions = [
            "Initiate Port State Control (PSC) targeted physical inspection upon arrival of top-ranked candidate vessel(s).",
            "Collect fuel oil and bilge slop samples for GC-MS hydrocarbon chromatographic fingerprinting.",
            "Subpoena voyage data recorder (VDR) logs and official Oil Record Book (Part I & II) entries.",
            "Request high-resolution optical / follow-up SAR tasking over suspected trajectory corridors."
        ]

        return InvestigationDossier(
            case_id=case_id,
            title=case_title,
            generated_at=now_time,
            provenance_hash_sha256=provenance_hash,
            analyst_name="POLARIS Maritime Forensic Unit",
            executive_summary=exec_summary,
            satellite_evidence=detection,
            drift_analysis=drift,
            ranked_candidates=candidates,
            evidence_graph=evidence_graph,
            uncertainty_statement=uncertainty_stmt,
            data_limitations=data_limitations,
            recommended_investigative_actions=recommended_actions,
            legal_disclaimer=settings.LEGAL_DISCLAIMER
        )

    @classmethod
    def format_markdown_report(cls, dossier: InvestigationDossier) -> str:
        """Formats dossier into standard Markdown brief."""
        md = []
        md.append(f"# MARITIME POLLUTION INVESTIGATION BRIEF")
        md.append(f"**Case Reference:** {dossier.case_id} — *{dossier.title}*")
        md.append(f"**Date Generated:** {dossier.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        md.append(f"**Cryptographic Provenance (SHA-256):** `{dossier.provenance_hash_sha256}`\n")
        md.append("---\n")
        
        md.append("## 1. EXECUTIVE SUMMARY")
        md.append(dossier.executive_summary + "\n")
        
        md.append("## 2. SATELLITE OIL SPILL DETECTION")
        det = dossier.satellite_evidence
        md.append(f"- **Mission & Sensor:** {det.satellite_mission} (C-band SAR)")
        md.append(f"- **Acquisition Timestamp:** {det.acquisition_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        md.append(f"- **Spill Surface Extent:** {det.surface_area_sqkm:.2f} km² (Perimeter: {det.perimeter_km:.2f} km)")
        md.append(f"- **Observed Slick Centroid:** {det.centroid_lat:.5f}°N, {det.centroid_lon:.5f}°E")
        md.append(f"- **Model Probabilities:** Oil Probability = {det.oil_probability*100:.1f}%, Look-alike = {det.lookalike_probability*100:.1f}%")
        md.append(f"- **Detection Confidence:** {det.detection_confidence*100:.1f}%\n")
        
        md.append("## 3. HYDRODYNAMIC REVERSE-DRIFT HINDCAST")
        dr = dossier.drift_analysis
        md.append(f"- **Hindcast Duration:** {dr.duration_hours} hours backward integration ({dr.num_particles:,} Lagrangian particles)")
        md.append(f"- **Estimated Origin Centroid:** {dr.most_probable_origin_lat:.5f}°N, {dr.most_probable_origin_lon:.5f}°E")
        md.append(f"- **Estimated Discharge Window:** {dr.origin_time_window_start.strftime('%d %b %H:%M UTC')} to {dr.origin_time_window_end.strftime('%d %b %H:%M UTC')}")
        md.append(f"- **Peak Probability Release Time:** {dr.most_probable_release_time.strftime('%d %b %H:%M UTC')}")
        md.append(f"- **Spatial Uncertainty Radius:** ±{dr.spatial_uncertainty_km:.1f} km (95% confidence covariance)")
        md.append(f"- **Environmental Forcing:** Surface Currents: {dr.ocean_current_mean_mps:.2f} m/s | 10m Wind: {dr.wind_speed_mean_mps:.1f} m/s\n")
        
        md.append("## 4. RANKED CANDIDATE VESSEL ATTRIBUTION")
        md.append("| Rank | Vessel Name | MMSI | Type | Flag | Score | Priority | CPA (km) | Anomaly Flags |")
        md.append("|---|---|---|---|---|---|---|---|---|")
        for idx, c in enumerate(dossier.ranked_candidates, 1):
            anom_str = ", ".join(a.flag_type for a in c.anomaly_flags) if c.anomaly_flags else "None"
            md.append(f"| #{idx} | **{c.vessel_name}** | `{c.mmsi}` | {c.vessel_type} | {c.flag_country} | **{int(c.overall_score*100)}%** | `{c.priority_tier}` | {c.closest_approach_km:.1f} | {anom_str} |")
        md.append("\n")
        
        md.append("## 5. GRANULAR EVIDENTIARY BREAKDOWN (TOP CANDIDATES)")
        for idx, c in enumerate(dossier.ranked_candidates[:3], 1):
            md.append(f"### Candidate #{idx}: {c.vessel_name} (MMSI: {c.mmsi})")
            md.append(f"- **Overall Score:** {c.overall_score:.3f} ({int(c.overall_score*100)}%) — **Priority: {c.priority_tier}**")
            md.append(f"- **Sub-Scores:**")
            md.append(f"  - Spatial Proximity: {c.sub_scores.get('spatial_compatibility', 0):.2f}")
            md.append(f"  - Temporal Window Overlap: {c.sub_scores.get('temporal_compatibility', 0):.2f}")
            md.append(f"  - Trajectory Drift Alignment: {c.sub_scores.get('trajectory_consistency', 0):.2f}")
            md.append(f"  - Behavioral Anomaly Index: {c.sub_scores.get('behavioral_anomaly', 0):.2f}")
            md.append(f"  - Vessel Type Compatibility: {c.sub_scores.get('vessel_compatibility', 0):.2f}")
            md.append(f"  - AIS Gap Penalty: {c.sub_scores.get('ais_gap_factor', 0):.2f}")
            md.append(f"- **Key Evidence Points:**")
            for pt in c.evidence_points:
                md.append(f"  - {pt}")
            md.append("")
            
        md.append("## 6. UNCERTAINTY & SENSOR BOUNDS")
        md.append(dossier.uncertainty_statement + "\n")
        
        md.append("## 7. RECOMMENDED INVESTIGATIVE ACTIONS")
        for act in dossier.recommended_investigative_actions:
            md.append(f"- [ ] {act}")
        md.append("\n")
        
        md.append("## 8. LEGAL & ETHICAL NOTICE")
        md.append(f"> [!IMPORTANT]\n> {dossier.legal_disclaimer}\n")
        
        return "\n".join(md)
