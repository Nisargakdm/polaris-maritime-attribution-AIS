from datetime import datetime
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field

class GeoJSONGeometry(BaseModel):
    type: str
    coordinates: Any

class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: GeoJSONGeometry
    properties: Dict[str, Any] = Field(default_factory=dict)

class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature]

class SpillDetectionResult(BaseModel):
    detection_id: str
    satellite_mission: str
    acquisition_time: datetime
    oil_probability: float
    lookalike_probability: float
    detection_confidence: float
    surface_area_sqkm: float
    perimeter_km: float
    centroid_lat: float
    centroid_lon: float
    bounding_box: List[float]  # [min_lon, min_lat, max_lon, max_lat]
    polygon_geojson: Dict[str, Any]
    classes_detected: List[str]
    sar_intensity_mean_db: float
    speckle_snr_db: float

class DriftSimulationRequest(BaseModel):
    duration_hours: int = Field(default=48, ge=1, le=120)
    num_particles: int = Field(default=1200, ge=100, le=10000)
    wind_factor: float = Field(default=0.031, ge=0.01, le=0.06)
    stochastic_diffusion: bool = True
    time_step_minutes: int = Field(default=30, ge=5, le=120)

class ParticleStep(BaseModel):
    time_offset_hours: float
    timestamp: datetime
    lat: float
    lon: float
    status: str = "active"

class ParticleTrajectory(BaseModel):
    particle_id: int
    steps: List[ParticleStep]

class OriginUncertaintyEllipse(BaseModel):
    centroid_lat: float
    centroid_lon: float
    semi_major_km: float
    semi_minor_km: float
    rotation_deg: float
    time_offset_hours: float
    timestamp: datetime
    confidence_level: float = 0.95

class CurrentVector(BaseModel):
    lat: float
    lon: float
    u_mps: float
    v_mps: float
    speed_knots: float
    direction_deg: float

class DepthContour(BaseModel):
    depth_m: int
    coordinates: List[List[float]]  # List of [lat, lon] line coordinates

class IsoProbabilityRing(BaseModel):
    confidence_percent: int  # e.g. 75, 90, 95
    coordinates: List[List[float]]  # polygon ring coordinates

class DriftOriginEstimate(BaseModel):
    simulation_id: str
    duration_hours: int
    num_particles: int
    most_probable_origin_lat: float
    most_probable_origin_lon: float
    spatial_uncertainty_km: float
    origin_time_window_start: datetime
    origin_time_window_end: datetime
    most_probable_release_time: datetime
    ellipses: List[OriginUncertaintyEllipse]
    density_heatmap_grid: List[List[float]]  # [lat, lon, normalized_density]
    grid_bounds: List[float]  # [min_lat, min_lon, max_lat, max_lon]
    sample_trajectories: List[ParticleTrajectory]
    ocean_current_mean_mps: float
    wind_speed_mean_mps: float
    current_vectors: List[CurrentVector] = Field(default_factory=list)
    depth_contours: List[DepthContour] = Field(default_factory=list)
    probability_rings: List[IsoProbabilityRing] = Field(default_factory=list)

class VesselWaypoint(BaseModel):
    timestamp: datetime
    lat: float
    lon: float
    sog_knots: float  # Speed Over Ground
    cog_degrees: float  # Course Over Ground
    heading: Optional[float] = None
    nav_status: Optional[str] = "Under way using engine"

class AnomalyFlag(BaseModel):
    flag_type: str  # e.g. "LOITERING", "SPEED_DROP", "AIS_GAP", "COURSE_DEVIATION"
    severity: Literal["INFO", "LOW", "MEDIUM", "HIGH"]
    description: str
    timestamp: datetime
    lat: float
    lon: float

class VesselCandidate(BaseModel):
    mmsi: str
    vessel_name: str
    vessel_type: str
    flag_country: str
    imo: Optional[str] = None
    callsign: Optional[str] = None
    
    # Enhanced Maritime Specifications
    length_m: Optional[float] = 182.0
    beam_m: Optional[float] = 32.2
    draft_m: Optional[float] = 11.5
    dwt_tonnes: Optional[int] = 49990
    gross_tonnage: Optional[int] = 28500
    destination_port: Optional[str] = "CHENNAI [IN MAA]"
    eta: Optional[str] = "2026-08-27 18:00 UTC"
    classification_society: Optional[str] = "DNV / Indian Register of Shipping"
    engine_type: Optional[str] = "MAN B&W 6S50ME-C (9,480 kW)"
    owner_operator: Optional[str] = "Global Maritime Shipping Ltd."
    
    overall_score: float = Field(..., ge=0.0, le=1.0)
    priority_tier: Literal["HIGH", "MEDIUM", "LOW", "UNLIKELY"]
    sub_scores: Dict[str, float]
    score_weights_used: Dict[str, float]
    closest_approach_km: float
    time_of_closest_approach: datetime
    temporal_overlap_hours: float
    drift_alignment_deg: float
    anomaly_flags: List[AnomalyFlag]
    evidence_points: List[str]
    waypoints: List[VesselWaypoint]
    flagged_by_analyst: bool = False
    excluded_by_analyst: bool = False
    analyst_notes: Optional[str] = None

class AttributionWeightConfig(BaseModel):
    weight_spatial: float = 0.30
    weight_temporal: float = 0.25
    weight_trajectory: float = 0.20
    weight_anomaly: float = 0.15
    weight_vessel_type: float = 0.10
    penalty_ais_gap: float = 0.10

class EvidenceNode(BaseModel):
    id: str
    label: str
    node_type: str  # "SATELLITE", "SPILL", "ORIGIN", "DRIFT", "AIS_RECORD", "VESSEL"
    properties: Dict[str, Any]

class EvidenceEdge(BaseModel):
    source: str
    target: str
    relation: str
    confidence: float

class EvidenceGraph(BaseModel):
    nodes: List[EvidenceNode]
    edges: List[EvidenceEdge]

class CaseSummary(BaseModel):
    case_id: str
    title: str
    region: str
    incident_type: str
    satellite_mission: str
    detection_timestamp: datetime
    spill_area_sqkm: float
    status: str
    is_demo: bool = True
    data_sources: List[str]

class InvestigationDossier(BaseModel):
    case_id: str
    title: str
    generated_at: datetime
    provenance_hash_sha256: str
    analyst_name: str = "Chief Maritime Environmental Analyst"
    executive_summary: str
    satellite_evidence: SpillDetectionResult
    drift_analysis: DriftOriginEstimate
    ranked_candidates: List[VesselCandidate]
    evidence_graph: EvidenceGraph
    uncertainty_statement: str
    data_limitations: List[str]
    recommended_investigative_actions: List[str]
    legal_disclaimer: str

class AnalystReviewUpdate(BaseModel):
    mmsi: str
    flagged: Optional[bool] = None
    excluded: Optional[bool] = None
    notes: Optional[str] = None
