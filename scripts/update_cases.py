from pathlib import Path

code = """import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

from app.models.schemas import (
    CaseSummary, 
    SpillDetectionResult, 
    DriftOriginEstimate, 
    VesselCandidate,
    AttributionWeightConfig,
    AnalystReviewUpdate,
    InvestigationDossier,
    EvidenceGraph
)
from app.services.sar_preprocessor import SARPreprocessor
from app.services.unet_detector import UNetDetector
from app.services.geometry_extractor import GeometryExtractor
from app.services.drift_engine import LagrangianDriftEngine
from app.services.trajectory_analyzer import TrajectoryAnalyzer
from app.services.attribution_scorer import AttributionScorer
from app.services.evidence_graph import EvidenceGraphBuilder
from app.services.report_generator import ReportGenerator

from app.ais_providers.marine_cadastre import MarineCadastreProvider
from app.ais_providers.curated_indian_case import CuratedIndianCaseProvider
from app.ais_providers.synthetic_provider import SyntheticEvaluationProvider
from app.config import settings
from app.utils.logger import logger

class ExtendedAISProvider:
    \"\"\"Provides realistic candidate AIS data for regional benchmark cases.\"\"\"
    @staticmethod
    def get_candidates_for_case(case_id: str, t_obs: datetime, center_lat: float, center_lon: float) -> List[Dict[str, Any]]:
        t_start = t_obs - timedelta(hours=48)
        num_points = 24
        
        if case_id == "case_04_malacca_strait":
            defs = [
                {
                    "mmsi": "563001880",
                    "vessel_name": "MT STRAIT PIONEER",
                    "vessel_type": "VLCC Crude Oil Tanker",
                    "flag_country": "Singapore [SG]",
                    "imo": "9812450",
                    "callsign": "9V821",
                    "length_m": 333.0,
                    "beam_m": 60.0,
                    "draft_m": 20.5,
                    "dwt_tonnes": 305000,
                    "gross_tonnage": 160000,
                    "destination_port": "SINGAPORE EAST [SG SIN]",
                    "eta": "2026-08-26 14:00 UTC",
                    "classification_society": "American Bureau of Shipping (ABS)",
                    "engine_type": "MAN B&W 7G80ME-C9 (32,000 kW)",
                    "owner_operator": "Straits Tanker Management Pte",
                    "base_lat": 1.28,
                    "base_lon": 103.88,
                    "heading": 105.0,
                    "speed_profile": [13.5, 12.8, 3.8, 3.2, 5.5, 12.0],
                    "gap_minutes": 35
                },
                {
                    "mmsi": "353004120",
                    "vessel_name": "C/V PACIFIC LINK",
                    "vessel_type": "Container Ship (14,000 TEU)",
                    "flag_country": "Panama [PA]",
                    "imo": "9645102",
                    "callsign": "3FEQ2",
                    "length_m": 366.0,
                    "beam_m": 51.2,
                    "draft_m": 15.2,
                    "dwt_tonnes": 145000,
                    "gross_tonnage": 140000,
                    "destination_port": "TANJUNG PELEPAS [MY TPP]",
                    "eta": "2026-08-26 09:30 UTC",
                    "classification_society": "ClassNK (NKK)",
                    "engine_type": "Wartsila-Sulzer 12RTA96C (68,000 kW)",
                    "owner_operator": "Orient Express Maritime",
                    "base_lat": 1.35,
                    "base_lon": 103.95,
                    "heading": 110.0,
                    "speed_profile": [18.5, 18.2, 18.6, 18.4, 18.5, 18.3],
                    "gap_minutes": 0
                },
                {
                    "mmsi": "477002340",
                    "vessel_name": "MT MALACCA BREEZE",
                    "vessel_type": "Bunkering Tanker",
                    "flag_country": "Hong Kong [HK]",
                    "imo": "9288114",
                    "callsign": "VRKM8",
                    "length_m": 118.0,
                    "beam_m": 19.5,
                    "draft_m": 6.8,
                    "dwt_tonnes": 8500,
                    "gross_tonnage": 5200,
                    "destination_port": "SINGAPORE OPL",
                    "eta": "2026-08-26 12:00 UTC",
                    "classification_society": "Bureau Veritas (BV)",
                    "engine_type": "Daihatsu 6DKM-28 (2,600 kW)",
                    "owner_operator": "Bunker Marine Logistics",
                    "base_lat": 1.25,
                    "base_lon": 103.80,
                    "heading": 85.0,
                    "speed_profile": [8.0, 7.5, 4.2, 3.9, 7.2, 8.1],
                    "gap_minutes": 20
                },
                {
                    "mmsi": "566009812",
                    "vessel_name": "TUG BATAM RAPID",
                    "vessel_type": "Tug / Towing Vessel",
                    "flag_country": "Singapore [SG]",
                    "imo": "N/A",
                    "callsign": "9V551",
                    "length_m": 34.0,
                    "beam_m": 10.5,
                    "draft_m": 3.8,
                    "dwt_tonnes": 450,
                    "gross_tonnage": 380,
                    "destination_port": "BATAM HARBOUR",
                    "eta": "2026-08-26 16:00 UTC",
                    "classification_society": "IRS",
                    "engine_type": "Caterpillar 3516B (2,200 kW)",
                    "owner_operator": "Riau Towing Services",
                    "base_lat": 1.20,
                    "base_lon": 103.92,
                    "heading": 180.0,
                    "speed_profile": [6.2, 6.0, 6.1, 5.9, 6.3, 6.1],
                    "gap_minutes": 0
                }
            ]
        elif case_id == "case_05_mumbai_high":
            defs = [
                {
                    "mmsi": "419001890",
                    "vessel_name": "MT KONKAN PRIDE",
                    "vessel_type": "Crude Oil Tanker (Aframax)",
                    "flag_country": "India [IN]",
                    "imo": "9451120",
                    "callsign": "AVCP",
                    "length_m": 244.0,
                    "beam_m": 42.0,
                    "draft_m": 14.8,
                    "dwt_tonnes": 105000,
                    "gross_tonnage": 61000,
                    "destination_port": "MUMBAI JNPT [IN BOM]",
                    "eta": "2026-08-26 21:00 UTC",
                    "classification_society": "Indian Register of Shipping (IRS)",
                    "engine_type": "Hyundai-MAN B&W 6S60MC-C (13,560 kW)",
                    "owner_operator": "Shipping Corporation of India (SCI)",
                    "base_lat": 19.45,
                    "base_lon": 71.35,
                    "heading": 140.0,
                    "speed_profile": [12.8, 12.0, 4.1, 3.6, 6.0, 12.5],
                    "gap_minutes": 40
                },
                {
                    "mmsi": "419088440",
                    "vessel_name": "OSV SAGAR VIKAS",
                    "vessel_type": "Offshore Supply / Support Vessel",
                    "flag_country": "India [IN]",
                    "imo": "9512300",
                    "callsign": "AUVK",
                    "length_m": 68.0,
                    "beam_m": 16.0,
                    "draft_m": 5.2,
                    "dwt_tonnes": 2800,
                    "gross_tonnage": 2200,
                    "destination_port": "BOMBAY HIGH SOUTH RIG",
                    "eta": "2026-08-26 10:00 UTC",
                    "classification_society": "IRS",
                    "engine_type": "Bergen B32:40 (4,800 kW)",
                    "owner_operator": "ONGC Marine Logistics",
                    "base_lat": 19.38,
                    "base_lon": 71.28,
                    "heading": 220.0,
                    "speed_profile": [5.5, 5.0, 4.8, 5.2, 5.0, 5.3],
                    "gap_minutes": 0
                },
                {
                    "mmsi": "636018900",
                    "vessel_name": "C/V GULF COMMERCE",
                    "vessel_type": "Container Ship",
                    "flag_country": "Liberia [LR]",
                    "imo": "9388100",
                    "callsign": "A8MN2",
                    "length_m": 294.0,
                    "beam_m": 32.2,
                    "draft_m": 12.0,
                    "dwt_tonnes": 68000,
                    "gross_tonnage": 54000,
                    "destination_port": "MUNDRA [IN MUN]",
                    "eta": "2026-08-27 04:00 UTC",
                    "classification_society": "DNV",
                    "engine_type": "MAN B&W 8K90MC-C (36,500 kW)",
                    "owner_operator": "Oceanic Container Line",
                    "base_lat": 19.65,
                    "base_lon": 71.55,
                    "heading": 320.0,
                    "speed_profile": [16.5, 16.8, 16.4, 16.6, 16.7, 16.5],
                    "gap_minutes": 0
                }
            ]
        else: # case_06_bay_of_bengal_sagar
            defs = [
                {
                    "mmsi": "419002200",
                    "vessel_name": "MT GANGA DISCOVERY",
                    "vessel_type": "Product Tanker",
                    "flag_country": "India [IN]",
                    "imo": "9312004",
                    "callsign": "AVGD",
                    "length_m": 182.0,
                    "beam_m": 27.4,
                    "draft_m": 9.5,
                    "dwt_tonnes": 37000,
                    "gross_tonnage": 23500,
                    "destination_port": "HALDIA DOCK [IN HAL]",
                    "eta": "2026-08-26 15:00 UTC",
                    "classification_society": "IRS",
                    "engine_type": "MAN B&W 6S46MC-C (7,860 kW)",
                    "owner_operator": "Bengal Coast Maritime",
                    "base_lat": 21.45,
                    "base_lon": 88.08,
                    "heading": 355.0,
                    "speed_profile": [10.2, 9.8, 3.5, 3.1, 5.0, 9.5],
                    "gap_minutes": 30
                },
                {
                    "mmsi": "419008910",
                    "vessel_name": "M/V SAGAR RATNA",
                    "vessel_type": "General Cargo",
                    "flag_country": "India [IN]",
                    "imo": "9188200",
                    "callsign": "AUSR",
                    "length_m": 138.0,
                    "beam_m": 21.0,
                    "draft_m": 7.2,
                    "dwt_tonnes": 12000,
                    "gross_tonnage": 8900,
                    "destination_port": "KOLKATA PORT [IN CCU]",
                    "eta": "2026-08-26 18:30 UTC",
                    "classification_society": "IRS",
                    "engine_type": "Mak 8M32C (4,000 kW)",
                    "owner_operator": "Eastern Shipping Corp",
                    "base_lat": 21.35,
                    "base_lon": 88.15,
                    "heading": 350.0,
                    "speed_profile": [11.5, 11.2, 11.4, 11.6, 11.3, 11.5],
                    "gap_minutes": 0
                }
            ]

        results = []
        for v in defs:
            waypoints = []
            speeds = v["speed_profile"]
            start_lat = v["base_lat"] - 0.35
            start_lon = v["base_lon"] - 0.25
            lat_step = 0.70 / num_points
            lon_step = 0.50 / num_points
            
            for i in range(num_points):
                pt_time = t_start + timedelta(hours=(i * 48.0 / num_points))
                if v.get("gap_minutes", 0) > 0 and 11 <= i <= 12:
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

class CaseManager:
    \"\"\"Central orchestration service managing 6 diverse maritime cases.\"\"\"
    def __init__(self):
        self.cases_summary: Dict[str, CaseSummary] = {}
        self.cases_detections: Dict[str, SpillDetectionResult] = {}
        self.cases_drifts: Dict[str, DriftOriginEstimate] = {}
        self.cases_candidates: Dict[str, List[VesselCandidate]] = {}
        self.cases_weights: Dict[str, AttributionWeightConfig] = {}
        self.cases_evidence_graphs: Dict[str, EvidenceGraph] = {}
        
        self.unet_detector = UNetDetector()
        self.drift_engine = LagrangianDriftEngine()
        
        self.ais_providers = {
            "case_01_gulf_mexico": MarineCadastreProvider(),
            "case_02_ennore_india": CuratedIndianCaseProvider(),
            "case_03_synthetic_eval": SyntheticEvaluationProvider()
        }
        self._init_benchmark_cases()

    def _init_benchmark_cases(self):
        t_ref = datetime(2026, 8, 25, 6, 0, 0)
        
        # 1. Gulf of Mexico
        self.cases_summary["case_01_gulf_mexico"] = CaseSummary(
            case_id="case_01_gulf_mexico",
            title="Case 1: Gulf of Mexico Deepwater Transit (NOAA Benchmark)",
            region="Gulf of Mexico (US EEZ / Outer Continental Shelf)",
            incident_type="Hydrocarbon Discharge / Mineral Slick",
            satellite_mission="Sentinel-1A IW GRD",
            detection_timestamp=t_ref,
            spill_area_sqkm=14.85,
            status="ANALYZED",
            is_demo=True,
            data_sources=["Copernicus Sentinel-1 SAR", "CMEMS Reanalysis", "ERA5 Winds", "NOAA MarineCadastre AIS"]
        )

        # 2. Ennore Port / Coromandel
        self.cases_summary["case_02_ennore_india"] = CaseSummary(
            case_id="case_02_ennore_india",
            title="Case 2: Ennore Port / Coromandel Coast Slick (INCOIS Advisory)",
            region="Bay of Bengal / Chennai Coastal Zone (India EEZ)",
            incident_type="Vessel Bunker / Bilge Discharge",
            satellite_mission="Sentinel-1B IW GRD",
            detection_timestamp=t_ref - timedelta(days=2),
            spill_area_sqkm=9.42,
            status="ANALYZED",
            is_demo=True,
            data_sources=["Copernicus Sentinel-1 SAR", "INCOIS Ocean State Forecast", "INCOIS Public Advisory", "Curated Indian AIS"]
        )

        # 3. Arabian Sea Ground-Truth Evaluation
        self.cases_summary["case_03_synthetic_eval"] = CaseSummary(
            case_id="case_03_synthetic_eval",
            title="Case 3: Arabian Sea Controlled Attribution (Synthetic Ground Truth)",
            region="Arabian Sea International Transit Corridor",
            incident_type="Controlled Synthetic Discharge (Top-1 Verification)",
            satellite_mission="Sentinel-1A IW GRD (Simulated)",
            detection_timestamp=t_ref - timedelta(days=4),
            spill_area_sqkm=18.20,
            status="ANALYZED",
            is_demo=True,
            data_sources=["Simulated SAR Intensity", "CMEMS Reanalysis", "ERA5 Reanalysis", "Controlled Ground-Truth AIS Track"]
        )

        # 4. Malacca Strait / Singapore TSS Chokepoint
        self.cases_summary["case_04_malacca_strait"] = CaseSummary(
            case_id="case_04_malacca_strait",
            title="Case 4: Singapore Strait / Malacca TSS Chokepoint (Bunker Slick)",
            region="Malacca & Singapore Strait Traffic Separation Scheme (TSS)",
            incident_type="Bunker Tank Cleaning Discharge",
            satellite_mission="Sentinel-1A IW GRD",
            detection_timestamp=t_ref - timedelta(days=1),
            spill_area_sqkm=11.60,
            status="ANALYZED",
            is_demo=True,
            data_sources=["Copernicus Sentinel-1 SAR", "CMEMS Equatorial Currents", "ERA5 Winds", "MPA Singapore TSS AIS"]
        )

        # 5. Mumbai Offshore / Bombay High Platform Transit
        self.cases_summary["case_05_mumbai_high"] = CaseSummary(
            case_id="case_05_mumbai_high",
            title="Case 5: Mumbai Offshore / Bombay High Platform Transit (Arabian Sea)",
            region="Arabian Sea / Mumbai Offshore Basin (India EEZ)",
            incident_type="Crude Oil Carrier Hydrocarbon Discharge",
            satellite_mission="Sentinel-1B IW GRD",
            detection_timestamp=t_ref - timedelta(days=3),
            spill_area_sqkm=16.75,
            status="ANALYZED",
            is_demo=True,
            data_sources=["Copernicus Sentinel-1 SAR", "INCOIS Western EEZ Currents", "ERA5 Winds", "DG Shipping Feeds"]
        )

        # 6. Bay of Bengal Sagar Island Approach
        self.cases_summary["case_06_bay_of_bengal_sagar"] = CaseSummary(
            case_id="case_06_bay_of_bengal_sagar",
            title="Case 6: Bay of Bengal / Sagar Island Marine Sanctuary Approach",
            region="Bay of Bengal / Sundarbans Estuary Corridor (India EEZ)",
            incident_type="Coastal Product Tanker Bilge Release",
            satellite_mission="Sentinel-1A IW GRD",
            detection_timestamp=t_ref - timedelta(days=5),
            spill_area_sqkm=8.15,
            status="ANALYZED",
            is_demo=True,
            data_sources=["Copernicus Sentinel-1 SAR", "INCOIS Coastal Model", "ERA5 Winds", "Kolkata Port AIS"]
        )

        for cid in list(self.cases_summary.keys()):
            self._run_full_case_pipeline(cid)

    def _run_full_case_pipeline(self, case_id: str):
        summary = self.cases_summary[case_id]
        t_obs = summary.detection_timestamp
        
        # Determine center, current and wind forcing per regional case
        if case_id == "case_01_gulf_mexico":
            center_lat, center_lon = 28.38, -89.15
            bbox = [-89.30, 28.25, -89.00, 28.50]
            curr_u, curr_v, wind_u, wind_v = 0.24, -0.15, 4.2, -2.5
        elif case_id == "case_02_ennore_india":
            center_lat, center_lon = 13.32, 80.45
            bbox = [80.35, 13.20, 80.55, 13.45]
            curr_u, curr_v, wind_u, wind_v = -0.18, 0.28, -3.5, 5.0
        elif case_id == "case_03_synthetic_eval":
            center_lat, center_lon = 20.62, 69.10
            bbox = [68.95, 20.45, 69.25, 20.75]
            curr_u, curr_v, wind_u, wind_v = 0.20, 0.18, 5.0, 3.2
        elif case_id == "case_04_malacca_strait":
            center_lat, center_lon = 1.30, 103.88
            bbox = [103.75, 1.20, 104.05, 1.40]
            curr_u, curr_v, wind_u, wind_v = -0.32, 0.10, -2.8, 1.5
        elif case_id == "case_05_mumbai_high":
            center_lat, center_lon = 19.45, 71.35
            bbox = [71.15, 19.25, 71.55, 19.65]
            curr_u, curr_v, wind_u, wind_v = 0.15, -0.22, 3.8, -4.2
        else: # case_06_bay_of_bengal_sagar
            center_lat, center_lon = 21.45, 88.08
            bbox = [87.90, 21.30, 88.25, 21.60]
            curr_u, curr_v, wind_u, wind_v = -0.12, 0.20, -3.2, 4.0

        # SAR segmentation simulation
        synthetic_sar = np.random.normal(0.5, 0.12, (512, 512)).astype(np.float32)
        y, x = np.ogrid[:512, :512]
        dist_from_slick = ((x - 256) / 120.0)**2 + ((y - 256) / 35.0)**2
        spill_mask = (dist_from_slick < 1.0).astype(np.float32)
        synthetic_sar[spill_mask > 0] = np.random.normal(0.12, 0.04, int(np.sum(spill_mask)))
        
        norm_sar, sar_meta = SARPreprocessor.preprocess_sar_scene(synthetic_sar)
        class_mask, oil_probs, seg_metrics = self.unet_detector.segment_sar_scene(norm_sar, spill_mask)
        geo_result = GeometryExtractor.mask_to_geojson(oil_probs > 0.5, bbox=bbox)
        
        detection = SpillDetectionResult(
            detection_id=f"DET-{case_id.upper()}",
            satellite_mission=summary.satellite_mission,
            acquisition_time=t_obs,
            oil_probability=seg_metrics["oil_probability"],
            lookalike_probability=seg_metrics["lookalike_probability"],
            detection_confidence=seg_metrics["detection_confidence"],
            surface_area_sqkm=geo_result["area_sqkm"],
            perimeter_km=geo_result["perimeter_km"],
            centroid_lat=geo_result["centroid_lat"],
            centroid_lon=geo_result["centroid_lon"],
            bounding_box=bbox,
            polygon_geojson=geo_result["geojson"],
            classes_detected=["Sea Surface", "Oil Spill", "Look-alike"],
            sar_intensity_mean_db=sar_meta["mean_backscatter_db"],
            speckle_snr_db=sar_meta["speckle_snr_db"]
        )
        self.cases_detections[case_id] = detection

        # Reverse Drift
        drift = self.drift_engine.run_reverse_simulation(
            spill_geojson=detection.polygon_geojson,
            observation_time=t_obs,
            duration_hours=48,
            num_particles=1200,
            current_u_mps=curr_u,
            current_v_mps=curr_v,
            wind_u_mps=wind_u,
            wind_v_mps=wind_v
        )
        self.cases_drifts[case_id] = drift

        # Candidates retrieval
        if case_id in self.ais_providers:
            provider = self.ais_providers[case_id]
            vessels_raw = provider.query_candidates(bbox, drift.origin_time_window_start, t_obs, case_id)
        else:
            vessels_raw = ExtendedAISProvider.get_candidates_for_case(case_id, t_obs, center_lat, center_lon)

        weights = AttributionWeightConfig()
        self.cases_weights[case_id] = weights
        
        candidate_models = []
        for v_raw in vessels_raw:
            analysis = TrajectoryAnalyzer.analyze_vessel_track(
                waypoints_raw=v_raw["waypoints"],
                origin_lat=drift.most_probable_origin_lat,
                origin_lon=drift.most_probable_origin_lon,
                origin_time_start=drift.origin_time_window_start,
                origin_time_end=drift.origin_time_window_end,
                spill_centroid_lat=detection.centroid_lat,
                spill_centroid_lon=detection.centroid_lon,
                spatial_uncertainty_km=drift.spatial_uncertainty_km
            )
            cand = AttributionScorer.compute_candidate_score(
                vessel_raw=v_raw,
                trajectory_analysis=analysis,
                origin_lat=drift.most_probable_origin_lat,
                origin_lon=drift.most_probable_origin_lon,
                spatial_uncertainty_km=drift.spatial_uncertainty_km,
                origin_time_start=drift.origin_time_window_start,
                origin_time_end=drift.origin_time_window_end,
                most_probable_release_time=drift.most_probable_release_time,
                weights=weights
            )
            
            # Enrich with maritime specifications
            cand.length_m = v_raw.get("length_m", 182.0)
            cand.beam_m = v_raw.get("beam_m", 32.2)
            cand.draft_m = v_raw.get("draft_m", 11.5)
            cand.dwt_tonnes = v_raw.get("dwt_tonnes", 49990)
            cand.gross_tonnage = v_raw.get("gross_tonnage", 28500)
            cand.destination_port = v_raw.get("destination_port", "REGIONAL COMMERCIAL PORT")
            cand.eta = v_raw.get("eta", (t_obs + timedelta(hours=14)).strftime("%Y-%m-%d %H:%M UTC"))
            cand.classification_society = v_raw.get("classification_society", "DNV / Lloyd's Register")
            cand.engine_type = v_raw.get("engine_type", "MAN B&W Low-Speed Diesel")
            cand.owner_operator = v_raw.get("owner_operator", "Ocean Commercial Marine Corp")

            candidate_models.append(cand)

        ranked = AttributionScorer.rank_candidates(candidate_models)
        self.cases_candidates[case_id] = ranked
        self.cases_evidence_graphs[case_id] = EvidenceGraphBuilder.build_graph(case_id, detection, drift, ranked)
        logger.info(f"Initialized pipeline for {case_id}: {len(ranked)} candidate vessels scored.")

    def list_cases(self) -> List[CaseSummary]:
        return list(self.cases_summary.values())

    def get_case_summary(self, case_id: str) -> Optional[CaseSummary]:
        return self.cases_summary.get(case_id)

    def get_detection(self, case_id: str) -> Optional[SpillDetectionResult]:
        return self.cases_detections.get(case_id)

    def get_drift(self, case_id: str) -> Optional[DriftOriginEstimate]:
        return self.cases_drifts.get(case_id)

    def get_candidates(self, case_id: str) -> List[VesselCandidate]:
        return self.cases_candidates.get(case_id, [])

    def get_evidence_graph(self, case_id: str) -> Optional[EvidenceGraph]:
        return self.cases_evidence_graphs.get(case_id)

    def recompute_attribution(self, case_id: str, new_weights: AttributionWeightConfig) -> List[VesselCandidate]:
        self.cases_weights[case_id] = new_weights
        detection = self.cases_detections[case_id]
        drift = self.cases_drifts[case_id]
        existing_cands = self.cases_candidates.get(case_id, [])

        updated = []
        for cand in existing_cands:
            v_raw = {
                "mmsi": cand.mmsi,
                "vessel_name": cand.vessel_name,
                "vessel_type": cand.vessel_type,
                "flag_country": cand.flag_country,
                "imo": cand.imo,
                "callsign": cand.callsign,
                "length_m": cand.length_m,
                "beam_m": cand.beam_m,
                "draft_m": cand.draft_m,
                "dwt_tonnes": cand.dwt_tonnes,
                "gross_tonnage": cand.gross_tonnage,
                "destination_port": cand.destination_port,
                "eta": cand.eta,
                "classification_society": cand.classification_society,
                "engine_type": cand.engine_type,
                "owner_operator": cand.owner_operator
            }
            analysis = {
                "closest_approach_km": cand.closest_approach_km,
                "time_of_closest_approach": cand.time_of_closest_approach,
                "temporal_overlap_hours": cand.temporal_overlap_hours,
                "drift_alignment_deg": cand.drift_alignment_deg,
                "anomaly_flags": cand.anomaly_flags,
                "waypoints": cand.waypoints,
                "sog_mean": 12.0,
                "sog_min": 5.0
            }
            re_cand = AttributionScorer.compute_candidate_score(
                vessel_raw=v_raw,
                trajectory_analysis=analysis,
                origin_lat=drift.most_probable_origin_lat,
                origin_lon=drift.most_probable_origin_lon,
                spatial_uncertainty_km=drift.spatial_uncertainty_km,
                origin_time_start=drift.origin_time_window_start,
                origin_time_end=drift.origin_time_window_end,
                most_probable_release_time=drift.most_probable_release_time,
                weights=new_weights
            )
            re_cand.length_m = cand.length_m
            re_cand.beam_m = cand.beam_m
            re_cand.draft_m = cand.draft_m
            re_cand.dwt_tonnes = cand.dwt_tonnes
            re_cand.gross_tonnage = cand.gross_tonnage
            re_cand.destination_port = cand.destination_port
            re_cand.eta = cand.eta
            re_cand.classification_society = cand.classification_society
            re_cand.engine_type = cand.engine_type
            re_cand.owner_operator = cand.owner_operator
            
            re_cand.flagged_by_analyst = cand.flagged_by_analyst
            re_cand.excluded_by_analyst = cand.excluded_by_analyst
            re_cand.analyst_notes = cand.analyst_notes
            updated.append(re_cand)

        ranked = AttributionScorer.rank_candidates(updated)
        self.cases_candidates[case_id] = ranked
        self.cases_evidence_graphs[case_id] = EvidenceGraphBuilder.build_graph(case_id, detection, drift, ranked)
        return ranked

    def update_candidate_review(self, case_id: str, review: AnalystReviewUpdate) -> Optional[VesselCandidate]:
        candidates = self.cases_candidates.get(case_id, [])
        for c in candidates:
            if c.mmsi == review.mmsi:
                if review.flagged is not None:
                    c.flagged_by_analyst = review.flagged
                if review.excluded is not None:
                    c.excluded_by_analyst = review.excluded
                if review.notes is not None:
                    c.analyst_notes = review.notes
                return c
        return None

    def get_investigation_dossier(self, case_id: str) -> Optional[InvestigationDossier]:
        if case_id not in self.cases_summary:
            return None
        summary = self.cases_summary[case_id]
        detection = self.cases_detections[case_id]
        drift = self.cases_drifts[case_id]
        candidates = self.cases_candidates.get(case_id, [])
        ev_graph = self.cases_evidence_graphs.get(case_id)
        
        return ReportGenerator.generate_dossier(
            case_id=case_id,
            case_title=summary.title,
            detection=detection,
            drift=drift,
            candidates=candidates,
            evidence_graph=ev_graph
        )

case_manager = CaseManager()
"""

Path("backend/app/services/case_manager.py").write_text(code, encoding="utf-8")
print("case_manager.py successfully updated with 6 cases and enhanced vessel telemetry!")