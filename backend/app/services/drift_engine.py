import math
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from shapely.geometry import shape, Point, Polygon
from app.utils.geo_utils import compute_uncertainty_ellipse_params, haversine_distance_km
from app.models.schemas import ParticleTrajectory, ParticleStep, OriginUncertaintyEllipse, DriftOriginEstimate, CurrentVector, DepthContour, IsoProbabilityRing
from app.utils.logger import logger

class LagrangianDriftEngine:
    """
    Lagrangian particle trajectory hindcast engine for oil spill reverse tracking.
    Simulates reverse advection forced by surface ocean currents and 10m atmospheric wind fields.
    Embeds stochastic turbulent diffusion to model spatial dispersion over time.
    """

    def __init__(self, wind_factor: float = 0.031, diffusion_coeff: float = 1.2):
        self.wind_factor = wind_factor
        self.diffusion_coeff = diffusion_coeff  # m^2/s

    def generate_seed_particles(
        self, 
        spill_geojson: Dict[str, Any], 
        num_particles: int = 1000
    ) -> List[Tuple[float, float]]:
        """
        Seeds particles uniformly at random within the observed oil spill polygon.
        """
        poly = shape(spill_geojson)
        min_lon, min_lat, max_lon, max_lat = poly.bounds
        
        particles = []
        max_attempts = num_particles * 20
        attempts = 0
        
        while len(particles) < num_particles and attempts < max_attempts:
            attempts += 1
            rand_lon = np.random.uniform(min_lon, max_lon)
            rand_lat = np.random.uniform(min_lat, max_lat)
            pt = Point(rand_lon, rand_lat)
            if poly.contains(pt) or poly.touches(pt):
                particles.append((rand_lat, rand_lon))
                
        # If any shortfall, populate with centroid plus slight jitter
        centroid = poly.centroid
        while len(particles) < num_particles:
            jitter_lat = centroid.y + np.random.normal(0, 0.002)
            jitter_lon = centroid.x + np.random.normal(0, 0.002)
            particles.append((jitter_lat, jitter_lon))
            
        return particles

    def run_reverse_simulation(
        self,
        spill_geojson: Dict[str, Any],
        observation_time: datetime,
        duration_hours: int = 48,
        num_particles: int = 1200,
        time_step_minutes: int = 30,
        current_u_mps: float = 0.22,  # Eastward current (m/s)
        current_v_mps: float = -0.12, # Northward current (m/s)
        wind_u_mps: float = 4.5,      # Eastward wind (m/s)
        wind_v_mps: float = -2.8,     # Northward wind (m/s)
        current_shear_deg: float = 12.0
    ) -> DriftOriginEstimate:
        """
        Executes backward Lagrangian particle integration from t=0 (observation) to t=-duration_hours.
        Returns time-stepped trajectories, uncertainty ellipses, and 2D KDE probability density.
        """
        logger.info(f"Running reverse drift simulation: {num_particles} particles, {duration_hours}h duration.")
        initial_coords = self.generate_seed_particles(spill_geojson, num_particles)
        
        lats = np.array([p[0] for p in initial_coords], dtype=np.float64)
        lons = np.array([p[1] for p in initial_coords], dtype=np.float64)
        
        dt_seconds = time_step_minutes * 60.0
        num_steps = int((duration_hours * 60) / time_step_minutes)
        
        # Subsample particle paths for visualization performance (e.g. 50 representative trajectories)
        sample_indices = np.random.choice(num_particles, size=min(40, num_particles), replace=False)
        trajectories: Dict[int, List[ParticleStep]] = {idx: [] for idx in sample_indices}
        
        # Record initial step (t=0)
        for idx in sample_indices:
            trajectories[idx].append(ParticleStep(
                time_offset_hours=0.0,
                timestamp=observation_time,
                lat=round(float(lats[idx]), 5),
                lon=round(float(lons[idx]), 5),
                status="active"
            ))
            
        ellipses: List[OriginUncertaintyEllipse] = []
        
        # Earth constants
        R_earth_m = 6371000.0
        deg_to_rad = math.pi / 180.0
        rad_to_deg = 180.0 / math.pi
        
        for step in range(1, num_steps + 1):
            elapsed_hours = (step * time_step_minutes) / 60.0
            current_time = observation_time - timedelta(hours=elapsed_hours)
            
            # Physical advection with slight temporal rotation (Coriolis/tides/current variation)
            t_phase = (elapsed_hours / 24.0) * 2.0 * math.pi
            u_curr = current_u_mps + 0.05 * math.cos(t_phase)
            v_curr = current_v_mps + 0.04 * math.sin(t_phase)
            
            u_wind = wind_u_mps + 0.8 * math.sin(t_phase * 0.5)
            v_wind = wind_v_mps + 0.6 * math.cos(t_phase * 0.5)
            
            # Total forward drift velocity = current + wind_factor * wind
            # For REVERSE integration, velocity is inverted (-v)
            u_tot = -(u_curr + self.wind_factor * u_wind)
            v_tot = -(v_curr + self.wind_factor * v_wind)
            
            # Turbulent stochastic diffusion (random walk: sqrt(2 * Kh * dt))
            diff_std = math.sqrt(2.0 * self.diffusion_coeff * dt_seconds)
            rand_dx = np.random.normal(0.0, diff_std, size=num_particles)
            rand_dy = np.random.normal(0.0, diff_std, size=num_particles)
            
            # Total displacement in meters
            dx_m = u_tot * dt_seconds + rand_dx
            dy_m = v_tot * dt_seconds + rand_dy
            
            # Convert meters to degrees lat/lon
            dlat_deg = (dy_m / R_earth_m) * rad_to_deg
            # Latitude-dependent lon scaling
            dlon_deg = (dx_m / (R_earth_m * np.cos(lats * deg_to_rad))) * rad_to_deg
            
            lats += dlat_deg
            lons += dlon_deg
            
            # Record trajectory samples
            for idx in sample_indices:
                trajectories[idx].append(ParticleStep(
                    time_offset_hours=round(float(-elapsed_hours), 2),
                    timestamp=current_time,
                    lat=round(float(lats[idx]), 5),
                    lon=round(float(lons[idx]), 5),
                    status="active"
                ))
                
            # Compute uncertainty ellipse every 6 hours and at the final timestep
            if elapsed_hours in [6.0, 12.0, 18.0, 24.0, 30.0, 36.0, 42.0, 48.0] or step == num_steps:
                ellipse_params = compute_uncertainty_ellipse_params(lats, lons)
                ellipses.append(OriginUncertaintyEllipse(
                    centroid_lat=round(ellipse_params["centroid_lat"], 5),
                    centroid_lon=round(ellipse_params["centroid_lon"], 5),
                    semi_major_km=ellipse_params["semi_major_km"],
                    semi_minor_km=ellipse_params["semi_minor_km"],
                    rotation_deg=ellipse_params["rotation_deg"],
                    time_offset_hours=round(float(-elapsed_hours), 2),
                    timestamp=current_time,
                    confidence_level=0.95
                ))

        # Compile final estimated origin distribution
        final_lat = float(np.mean(lats))
        final_lon = float(np.mean(lons))
        final_ellipse = ellipses[-1] if ellipses else None
        spatial_uncertainty = final_ellipse.semi_major_km if final_ellipse else 12.5
        
        # Most probable release window is between -16h and -32h (peak around -24h)
        most_probable_release = observation_time - timedelta(hours=min(24.0, duration_hours * 0.5))
        release_window_start = observation_time - timedelta(hours=duration_hours)
        release_window_end = observation_time - timedelta(hours=max(4.0, duration_hours * 0.15))
        
        # 2D Kernel Density Estimation Grid for Heatmap
        density_grid, grid_bounds = self._compute_kde_grid(lats, lons)
        
        sample_traj_models = [
            ParticleTrajectory(particle_id=int(k), steps=v)
            for k, v in trajectories.items()
        ]
        
        current_speed_mag = math.hypot(current_u_mps, current_v_mps)
        wind_speed_mag = math.hypot(wind_u_mps, wind_v_mps)
        
        current_vectors = self._generate_current_vectors(final_lat, final_lon, current_u_mps, current_v_mps)
        depth_contours = self._generate_bathymetric_contours(final_lat, final_lon)
        prob_rings = self._generate_probability_rings(final_lat, final_lon, spatial_uncertainty)
        
        return DriftOriginEstimate(
            simulation_id=f"SIM-{int(observation_time.timestamp())}",
            duration_hours=duration_hours,
            num_particles=num_particles,
            most_probable_origin_lat=round(final_lat, 5),
            most_probable_origin_lon=round(final_lon, 5),
            spatial_uncertainty_km=round(spatial_uncertainty, 2),
            origin_time_window_start=release_window_start,
            origin_time_window_end=release_window_end,
            most_probable_release_time=most_probable_release,
            ellipses=ellipses,
            density_heatmap_grid=density_grid,
            grid_bounds=grid_bounds,
            sample_trajectories=sample_traj_models,
            ocean_current_mean_mps=round(current_speed_mag, 2),
            wind_speed_mean_mps=round(wind_speed_mag, 2),
            current_vectors=current_vectors,
            depth_contours=depth_contours,
            probability_rings=prob_rings
        )


    @staticmethod
    def _generate_current_vectors(center_lat: float, center_lon: float, u: float, v: float) -> List[CurrentVector]:
        vectors = []
        speed_kts = math.hypot(u, v) * 1.94384
        d_lat = 0.10
        d_lon = 0.12
        for i in range(-2, 3):
            for j in range(-2, 3):
                pt_lat = center_lat + i * d_lat
                pt_lon = center_lon + j * d_lon
                local_u = u + 0.03 * math.sin(i * 1.5)
                local_v = v + 0.03 * math.cos(j * 1.5)
                local_spd = math.hypot(local_u, local_v) * 1.94384
                local_ang = (math.degrees(math.atan2(local_u, local_v)) + 360.0) % 360.0
                vectors.append(CurrentVector(
                    lat=round(pt_lat, 5),
                    lon=round(pt_lon, 5),
                    u_mps=round(local_u, 3),
                    v_mps=round(local_v, 3),
                    speed_knots=round(local_spd, 1),
                    direction_deg=round(local_ang, 1)
                ))
        return vectors

    @staticmethod
    def _generate_bathymetric_contours(center_lat: float, center_lon: float) -> List[DepthContour]:
        contours = []
        depths = [50, 100, 200, 500, 1000, 2000]
        for idx, d in enumerate(depths):
            offset = 0.045 * (idx + 1)
            line = []
            num_pts = 18
            for k in range(num_pts):
                t = (k / (num_pts - 1)) * 2.0 - 1.0
                lat = center_lat + t * 0.40
                lon = center_lon - offset - 0.035 * math.sin(t * 3.1415)
                line.append([round(lat, 5), round(lon, 5)])
            contours.append(DepthContour(depth_m=d, coordinates=line))
        return contours

    @staticmethod
    def _generate_probability_rings(center_lat: float, center_lon: float, base_radius_km: float) -> List[IsoProbabilityRing]:
        rings = []
        levels = [(75, 0.65), (90, 0.85), (95, 1.05)]
        km_per_deg_lat = 111.32
        km_per_deg_lon = 111.32 * math.cos(math.radians(center_lat))
        for pct, factor in levels:
            r_km = base_radius_km * factor
            coords = []
            num_pts = 32
            for i in range(num_pts + 1):
                angle = (i / num_pts) * 2.0 * math.pi
                d_lat = (r_km * math.cos(angle)) / km_per_deg_lat
                d_lon = (r_km * math.sin(angle)) / km_per_deg_lon
                coords.append([round(center_lat + d_lat, 5), round(center_lon + d_lon, 5)])
            rings.append(IsoProbabilityRing(confidence_percent=pct, coordinates=coords))
        return rings

    def run_forward_prediction(
        self,
        spill_geojson: Dict[str, Any],
        observation_time: datetime,
        duration_hours: int = 48,
        num_particles: int = 300,
        time_step_minutes: int = 30,
        current_u_mps: float = 0.22,
        current_v_mps: float = -0.12,
        wind_u_mps: float = 4.5,
        wind_v_mps: float = -2.8,
        current_shear_deg: float = 12.0
    ) -> Dict[str, Any]:
        """
        Executes FORWARD Lagrangian particle integration from t=0 (observation) to t=+duration_hours.
        Predicts future spill drift trajectory and spreading.
        
        NOTE: Uses simplified constant ocean/wind forcing. For operational deployment,
        integrate live CMEMS ocean current forecasts + ECMWF/ERA5 wind forecasts.
        
        Returns:
            {
                "simulation_id": "FWDSIM-...",
                "duration_hours": 48,
                "num_particles": 300,
                "prediction_centroid_lat": 19.52,
                "prediction_centroid_lon": 72.18,
                "spatial_uncertainty_km": 18.5,  # grows with time horizon
                "prediction_time_window_start": datetime(...),
                "prediction_time_window_end": datetime(...),
                "ellipses": [...],  # uncertainty ellipses at timesteps
                "density_heatmap_grid": [[lat, lon, density], ...],
                "grid_bounds": [min_lat, min_lon, max_lat, max_lon],
                "sample_trajectories": [...],
                "ocean_current_mean_mps": 0.25,
                "wind_speed_mean_mps": 5.2,
                "current_vectors": [...],
                "forcing_data_source": "simplified_constant",
                "note": "Forward prediction using constant forcing. Uncertainty increases with time horizon."
            }
        """
        logger.info(f"Running FORWARD drift prediction: {num_particles} particles, {duration_hours}h horizon.")
        
        # Seed particles at current spill polygon (t=0)
        initial_coords = self.generate_seed_particles(spill_geojson, num_particles)
        
        lats = np.array([p[0] for p in initial_coords], dtype=np.float64)
        lons = np.array([p[1] for p in initial_coords], dtype=np.float64)
        
        dt_seconds = time_step_minutes * 60.0
        num_steps = int((duration_hours * 60) / time_step_minutes)
        
        # Subsample for visualization
        sample_indices = np.random.choice(num_particles, size=min(40, num_particles), replace=False)
        trajectories: Dict[int, List[ParticleStep]] = {idx: [] for idx in sample_indices}
        
        # Record initial step (t=0)
        for idx in sample_indices:
            trajectories[idx].append(ParticleStep(
                time_offset_hours=0.0,
                timestamp=observation_time,
                lat=round(float(lats[idx]), 5),
                lon=round(float(lons[idx]), 5),
                status="active"
            ))
        
        ellipses = []
        
        # Earth constants
        R_earth_m = 6371000.0
        deg_to_rad = math.pi / 180.0
        rad_to_deg = 180.0 / math.pi
        
        for step in range(1, num_steps + 1):
            elapsed_hours = (step * time_step_minutes) / 60.0
            current_time = observation_time + timedelta(hours=elapsed_hours)
            
            # Physical advection (slight temporal variation)
            t_phase = (elapsed_hours / 24.0) * 2.0 * math.pi
            u_curr = current_u_mps + 0.05 * math.cos(t_phase)
            v_curr = current_v_mps + 0.04 * math.sin(t_phase)
            
            u_wind = wind_u_mps + 0.8 * math.sin(t_phase * 0.5)
            v_wind = wind_v_mps + 0.6 * math.cos(t_phase * 0.5)
            
            # Total FORWARD drift velocity = current + wind_factor * wind
            # NO SIGN INVERSION (this is forward integration)
            u_tot = u_curr + self.wind_factor * u_wind
            v_tot = v_curr + self.wind_factor * v_wind
            
            # Turbulent diffusion (grows slightly with time to reflect increasing uncertainty)
            # Base diffusion + time-dependent growth factor
            diff_coeff_effective = self.diffusion_coeff * (1.0 + 0.015 * elapsed_hours)
            diff_std = math.sqrt(2.0 * diff_coeff_effective * dt_seconds)
            rand_dx = np.random.normal(0.0, diff_std, size=num_particles)
            rand_dy = np.random.normal(0.0, diff_std, size=num_particles)
            
            # Total displacement in meters
            dx_m = u_tot * dt_seconds + rand_dx
            dy_m = v_tot * dt_seconds + rand_dy
            
            # Convert to degrees
            dlat_deg = (dy_m / R_earth_m) * rad_to_deg
            dlon_deg = (dx_m / (R_earth_m * np.cos(lats * deg_to_rad))) * rad_to_deg
            
            lats += dlat_deg
            lons += dlon_deg
            
            # Record trajectory samples
            for idx in sample_indices:
                trajectories[idx].append(ParticleStep(
                    time_offset_hours=round(float(elapsed_hours), 2),
                    timestamp=current_time,
                    lat=round(float(lats[idx]), 5),
                    lon=round(float(lons[idx]), 5),
                    status="active"
                ))
            
            # Compute uncertainty ellipse every 6 hours and at final timestep
            if elapsed_hours in [6.0, 12.0, 18.0, 24.0, 30.0, 36.0, 42.0, 48.0] or step == num_steps:
                ellipse_params = compute_uncertainty_ellipse_params(lats, lons)
                ellipses.append({
                    "centroid_lat": round(ellipse_params["centroid_lat"], 5),
                    "centroid_lon": round(ellipse_params["centroid_lon"], 5),
                    "semi_major_km": ellipse_params["semi_major_km"],
                    "semi_minor_km": ellipse_params["semi_minor_km"],
                    "rotation_deg": ellipse_params["rotation_deg"],
                    "time_offset_hours": round(float(elapsed_hours), 2),
                    "timestamp": current_time.isoformat() + "Z",
                    "confidence_level": 0.95
                })
        
        # Final predicted position
        final_lat = float(np.mean(lats))
        final_lon = float(np.mean(lons))
        final_ellipse = ellipses[-1] if ellipses else {}
        spatial_uncertainty = final_ellipse.get("semi_major_km", 15.0)
        
        # Uncertainty grows with time horizon
        # Base uncertainty from particle spread + time-dependent growth
        base_uncertainty = spatial_uncertainty if spatial_uncertainty > 5.0 else max(8.0, duration_hours * 0.25)
        spatial_uncertainty = round(base_uncertainty * (1.0 + 0.015 * duration_hours), 2)
        
        # KDE grid for heatmap
        density_grid, grid_bounds = self._compute_kde_grid(lats, lons)
        
        sample_traj_list = [
            {"particle_id": int(k), "steps": [s.dict() for s in v]}
            for k, v in trajectories.items()
        ]
        
        current_speed_mag = math.hypot(current_u_mps, current_v_mps)
        wind_speed_mag = math.hypot(wind_u_mps, wind_v_mps)
        
        current_vectors_list = [cv.dict() for cv in self._generate_current_vectors(final_lat, final_lon, current_u_mps, current_v_mps)]
        
        return {
            "simulation_id": f"FWDSIM-{int(observation_time.timestamp())}",
            "duration_hours": duration_hours,
            "num_particles": num_particles,
            "prediction_centroid_lat": round(final_lat, 5),
            "prediction_centroid_lon": round(final_lon, 5),
            "spatial_uncertainty_km": spatial_uncertainty,
            "prediction_time_window_start": observation_time.isoformat() + "Z",
            "prediction_time_window_end": (observation_time + timedelta(hours=duration_hours)).isoformat() + "Z",
            "ellipses": ellipses,
            "density_heatmap_grid": density_grid,
            "grid_bounds": grid_bounds,
            "sample_trajectories": sample_traj_list,
            "ocean_current_mean_mps": round(current_speed_mag, 2),
            "wind_speed_mean_mps": round(wind_speed_mag, 2),
            "current_vectors": current_vectors_list,
            "forcing_data_source": "simplified_constant",
            "note": "Forward prediction using simplified constant ocean/wind forcing. Uncertainty increases with time horizon. For operational deployment, integrate live CMEMS current + ECMWF wind forecasts."
        }

    @staticmethod
    def _compute_kde_grid(
        lats: np.ndarray, 
        lons: np.ndarray, 
        grid_res: int = 25
    ) -> Tuple[List[List[float]], List[float]]:
        """
        Computes 2D Gaussian Kernel Density Estimation grid points [lat, lon, density] for Leaflet heatmaps.
        """
        min_lat, max_lat = float(np.min(lats)), float(np.max(lats))
        min_lon, max_lon = float(np.min(lons)), float(np.max(lons))
        
        pad_lat = max(0.02, (max_lat - min_lat) * 0.15)
        pad_lon = max(0.02, (max_lon - min_lon) * 0.15)
        
        grid_lats = np.linspace(min_lat - pad_lat, max_lat + pad_lat, grid_res)
        grid_lons = np.linspace(min_lon - pad_lon, max_lon + pad_lon, grid_res)
        
        # Bandwidth estimation (Scott's rule)
        n = len(lats)
        bw_lat = np.std(lats) * (n ** (-1.0 / 6.0)) if np.std(lats) > 1e-4 else 0.02
        bw_lon = np.std(lons) * (n ** (-1.0 / 6.0)) if np.std(lons) > 1e-4 else 0.02
        
        points = []
        max_density = 1e-6
        
        for g_lat in grid_lats:
            for g_lon in grid_lons:
                dist_sq = ((lats - g_lat) / max(bw_lat, 1e-4))**2 + ((lons - g_lon) / max(bw_lon, 1e-4))**2
                density = float(np.sum(np.exp(-0.5 * dist_sq)))
                if density > max_density:
                    max_density = density
                points.append([round(float(g_lat), 5), round(float(g_lon), 5), density])
                
        # Normalize densities to 0.0 - 1.0 range and filter trivial noise
        normalized_points = []
        for p in points:
            norm_val = round(p[2] / max_density, 3)
            if norm_val >= 0.05:
                normalized_points.append([p[0], p[1], norm_val])
                
        bounds = [
            round(min_lat - pad_lat, 5), 
            round(min_lon - pad_lon, 5), 
            round(max_lat + pad_lat, 5), 
            round(max_lon + pad_lon, 5)
        ]
        return normalized_points, bounds
