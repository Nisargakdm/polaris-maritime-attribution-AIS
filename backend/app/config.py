import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "POLARIS - Probabilistic Maritime Pollution Attribution Engine"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    CASES_DIR: Path = DATA_DIR / "cases"
    MODELS_DIR: Path = DATA_DIR / "models"
    STATIC_DIR: Path = Path(__file__).resolve().parent / "static"
    
    # Drift default configurations
    DEFAULT_WIND_DRIFT_FACTOR: float = 0.031  # ~3.1% standard windage factor for oil
    DEFAULT_DIFFUSION_COEFFICIENT: float = 1.0  # m^2/s horizontal diffusion
    DEFAULT_ENSEMBLE_PARTICLES: int = 1500
    
    # Attribution default weights
    WEIGHT_SPATIAL: float = 0.30
    WEIGHT_TEMPORAL: float = 0.25
    WEIGHT_TRAJECTORY: float = 0.20
    WEIGHT_ANOMALY: float = 0.15
    WEIGHT_VESSEL_TYPE: float = 0.10
    PENALTY_AIS_GAP: float = 0.10
    
    LEGAL_DISCLAIMER: str = (
        "CONFIDENTIAL INVESTIGATION DECISION SUPPORT: This system provides probabilistic "
        "investigative decision support and is not legal proof of responsibility. "
        "Candidate rankings are mathematical compatibility scores based on available "
        "satellite, oceanographic hindcasts, and AIS telemetry."
    )

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
