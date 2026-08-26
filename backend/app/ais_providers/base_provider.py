from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.models.schemas import VesselCandidate, VesselWaypoint

class BaseAISProvider(ABC):
    """
    Abstract Base Class for AIS data providers.
    Ensures modularity across MarineCadastre (US), INCOIS/Indian curated,
    Synthetic evaluation scenarios, and optional real-time feeds.
    """

    @abstractmethod
    def get_provider_name(self) -> str:
        """Returns the human-readable name of the AIS provider."""
        pass

    @abstractmethod
    def get_data_coverage_statement(self) -> str:
        """Returns disclaimer and coverage metadata for this source."""
        pass

    @abstractmethod
    def query_candidates(
        self,
        bounding_box: List[float],  # [min_lat, min_lon, max_lat, max_lon]
        time_window_start: datetime,
        time_window_end: datetime,
        case_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves raw vessel trajectory records within the 4D spatiotemporal window.
        Returns list of vessel raw records with waypoints.
        """
        pass
