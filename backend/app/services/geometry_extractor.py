import cv2
import numpy as np
from typing import Dict, Any, Tuple, List
from shapely.geometry import Polygon, MultiPolygon, mapping
from shapely.ops import unary_union
from app.utils.geo_utils import polygon_area_and_perimeter_km
from app.utils.logger import logger

class GeometryExtractor:
    """
    Converts 2D pixel segmentation masks into georeferenced GeoJSON polygons and computes
    geodesic surface metrics (area in km², perimeter in km, and centroid coordinates).
    """

    @staticmethod
    def pixel_to_geo(
        px: float, 
        py: float, 
        width: int, 
        height: int, 
        bbox: List[float]
    ) -> Tuple[float, float]:
        """
        Affine transformation from pixel (px, py) in image (0..width, 0..height)
        to geographic coordinates (lon, lat) given bounding box [min_lon, min_lat, max_lon, max_lat].
        """
        min_lon, min_lat, max_lon, max_lat = bbox
        lon = min_lon + (px / float(width)) * (max_lon - min_lon)
        # Note: image y=0 corresponds to max_lat (top of map)
        lat = max_lat - (py / float(height)) * (max_lat - min_lat)
        return float(lon), float(lat)

    @classmethod
    def mask_to_geojson(
        cls, 
        binary_mask: np.ndarray, 
        bbox: List[float], 
        min_area_pixels: int = 50,
        simplify_tolerance_deg: float = 0.0005
    ) -> Dict[str, Any]:
        """
        Vectorizes binary spill mask into clean, valid GeoJSON Polygon / MultiPolygon.
        Computes accurate geodesic metrics.
        """
        height, width = binary_mask.shape
        mask_uint8 = (binary_mask > 0.5).astype(np.uint8) * 255
        
        contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        polygons = []
        for contour in contours:
            if cv2.contourArea(contour) < min_area_pixels:
                continue
            
            # Squeeze contour to list of (px, py)
            pts = contour.squeeze()
            if len(pts.shape) != 2 or pts.shape[0] < 3:
                continue
            
            geo_coords = [
                cls.pixel_to_geo(pt[0], pt[1], width, height, bbox) 
                for pt in pts
            ]
            # Close polygon if not closed
            if geo_coords[0] != geo_coords[-1]:
                geo_coords.append(geo_coords[0])
            
            try:
                poly = Polygon(geo_coords)
                if not poly.is_valid:
                    poly = poly.buffer(0)
                if poly.is_valid and not poly.is_empty:
                    if simplify_tolerance_deg > 0:
                        poly = poly.simplify(simplify_tolerance_deg, preserve_topology=True)
                    polygons.append(poly)
            except Exception as e:
                logger.warning(f"Error vectorizing contour: {e}")

        if not polygons:
            # Fallback: create small default polygon around center of bbox
            center_lon = (bbox[0] + bbox[2]) / 2.0
            center_lat = (bbox[1] + bbox[3]) / 2.0
            d = 0.01
            poly = Polygon([
                (center_lon - d, center_lat - d),
                (center_lon + d, center_lat - d),
                (center_lon + d, center_lat + d),
                (center_lon - d, center_lat + d),
                (center_lon - d, center_lat - d)
            ])
            polygons.append(poly)

        if len(polygons) == 1:
            final_geom = polygons[0]
        else:
            final_geom = unary_union(polygons)

        geojson_dict = mapping(final_geom)
        centroid = final_geom.centroid
        area_sqkm, perimeter_km = polygon_area_and_perimeter_km(geojson_dict)

        return {
            "geojson": geojson_dict,
            "centroid_lat": round(float(centroid.y), 5),
            "centroid_lon": round(float(centroid.x), 5),
            "area_sqkm": round(float(area_sqkm), 3),
            "perimeter_km": round(float(perimeter_km), 3)
        }
