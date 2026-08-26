import math
from typing import Tuple, List, Dict, Any
from shapely.geometry import shape, mapping, Polygon, Point
import numpy as np

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two points in kilometers."""
    R = 6371.0  # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2.0)**2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def calculate_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates forward initial bearing from point 1 to point 2 in degrees (0-360)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)
    
    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - \
        math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    
    bearing = math.degrees(math.atan2(y, x))
    return (bearing + 360.0) % 360.0

def angular_difference_deg(bearing1: float, bearing2: float) -> float:
    """Calculates minimum angular difference between two bearings in degrees (0 to 180)."""
    diff = abs((bearing1 - bearing2 + 180.0) % 360.0 - 180.0)
    return diff

def polygon_area_and_perimeter_km(geojson_geom: Dict[str, Any]) -> Tuple[float, float]:
    """
    Computes approximate geodesic area (sq km) and perimeter (km) for a GeoJSON polygon.
    Uses equirectangular projection centered on polygon centroid.
    """
    poly = shape(geojson_geom)
    centroid = poly.centroid
    lat_rad = math.radians(centroid.y)
    
    # Scale factors: 1 deg lat ~= 111.32 km, 1 deg lon ~= 111.32 * cos(lat) km
    km_per_deg_lat = 111.32
    km_per_deg_lon = 111.32 * math.cos(lat_rad)
    
    # Transform coordinates to km
    def to_km_coords(coords):
        return [(lon * km_per_deg_lon, lat * km_per_deg_lat) for lon, lat in coords]
    
    if poly.geom_type == 'Polygon':
        exterior_km = to_km_coords(poly.exterior.coords)
        poly_km = Polygon(exterior_km)
        area_sqkm = poly_km.area
        perimeter_km = poly_km.length
        return float(area_sqkm), float(perimeter_km)
    elif poly.geom_type == 'MultiPolygon':
        total_area = 0.0
        total_len = 0.0
        for p in poly.geoms:
            p_km = Polygon(to_km_coords(p.exterior.coords))
            total_area += p_km.area
            total_len += p_km.length
        return float(total_area), float(total_len)
    
    return 0.0, 0.0

def compute_uncertainty_ellipse_params(lats: np.ndarray, lons: np.ndarray, confidence: float = 0.95) -> Dict[str, float]:
    """
    Fits a bivariate Gaussian uncertainty ellipse (semi-major, semi-minor, rotation)
    to a set of particle coordinates.
    """
    if len(lats) < 3:
        return {
            "centroid_lat": float(np.mean(lats)),
            "centroid_lon": float(np.mean(lons)),
            "semi_major_km": 5.0,
            "semi_minor_km": 5.0,
            "rotation_deg": 0.0
        }
    
    mean_lat = float(np.mean(lats))
    mean_lon = float(np.mean(lons))
    
    # Project to km relative to centroid
    lat_rad = math.radians(mean_lat)
    km_per_deg_lat = 111.32
    km_per_deg_lon = 111.32 * math.cos(lat_rad)
    
    y_km = (lats - mean_lat) * km_per_deg_lat
    x_km = (lons - mean_lon) * km_per_deg_lon
    
    cov = np.cov(x_km, y_km)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    
    # 95% confidence chi-squared scale factor (~5.991)
    chi2_val = 5.991 if confidence >= 0.95 else 2.296
    
    order = eigenvalues.argsort()[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]
    
    semi_major = math.sqrt(max(1e-4, eigenvalues[0] * chi2_val))
    semi_minor = math.sqrt(max(1e-4, eigenvalues[1] * chi2_val))
    
    # Rotation angle
    angle_rad = math.atan2(eigenvectors[1, 0], eigenvectors[0, 0])
    rotation_deg = (math.degrees(angle_rad) + 360.0) % 360.0
    
    return {
        "centroid_lat": mean_lat,
        "centroid_lon": mean_lon,
        "semi_major_km": round(float(semi_major), 2),
        "semi_minor_km": round(float(semi_minor), 2),
        "rotation_deg": round(float(rotation_deg), 2)
    }
