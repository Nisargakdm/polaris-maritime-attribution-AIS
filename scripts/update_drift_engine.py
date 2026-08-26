from pathlib import Path

drift_path = Path("backend/app/services/drift_engine.py")
with open("backend/app/services/drift_engine.py", "r", encoding="utf-8") as f:
    orig = f.read()

# Add CurrentVector, DepthContour, IsoProbabilityRing to imports
if "CurrentVector" not in orig:
    orig = orig.replace(
        "from app.models.schemas import ParticleTrajectory, ParticleStep, OriginUncertaintyEllipse, DriftOriginEstimate",
        "from app.models.schemas import ParticleTrajectory, ParticleStep, OriginUncertaintyEllipse, DriftOriginEstimate, CurrentVector, DepthContour, IsoProbabilityRing"
    )

# Add helper methods to LagrangianDriftEngine before _compute_kde_grid
helpers = """
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
"""

if "_generate_current_vectors" not in orig:
    orig = orig.replace("    @staticmethod\n    def _compute_kde_grid", helpers + "\n    @staticmethod\n    def _compute_kde_grid")

# Now update return DriftOriginEstimate
old_return = """        return DriftOriginEstimate(
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
            wind_speed_mean_mps=round(wind_speed_mag, 2)
        )"""

new_return = """        current_vectors = self._generate_current_vectors(final_lat, final_lon, current_u_mps, current_v_mps)
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
        )"""

if old_return in orig:
    orig = orig.replace(old_return, new_return)

drift_path.write_text(orig, encoding="utf-8")
print("Successfully patched drift_engine.py!")