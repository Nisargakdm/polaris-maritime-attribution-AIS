# POLARIS: Probabilistic Maritime Pollution Attribution Engine
### Satellite Oil-Spill Detection + Lagrangian Reverse Drift + AIS Vessel Attribution
**Smart India Hackathon 2026 — Problem Statement SIH26143 (NTRO / Space Technology)**

---

## 1. Project Vision & Core Differentiation
Operational maritime surveillance systems (such as EMSA CleanSeaNet and India's INCOIS OOSA) detect oil slicks and manually cross-reference nearby vessel locations. However, ocean slicks drift continuously under surface currents and wind forcing, meaning the ship responsible for a discharge is rarely at the observed location hours later.

**POLARIS** establishes an end-to-end, scientifically defensible, uncertainty-aware forensic intelligence pipeline:

```
Satellite SAR Scene (Sentinel-1)
       ↓
SAR Calibration & Lee Speckle Filtering
       ↓
U-Net Semantic Segmentation (5-Class: Sea, Oil, Look-alike, Ship, Land)
       ↓
GeoJSON Polygon & Geodesic Surface Extent (km²)
       ↓
Stochastic Lagrangian Reverse Drift Hindcast (-48h)
       ↓
Probable Origin Probability Surface (2D KDE) + Origin Time-Window PDF
       ↓
Modular AIS Trajectory Extraction (4D Space-Time Query)
       ↓
Kinematic Anomaly Analysis (Loitering, Speed Drops, AIS Transponder Gaps)
       ↓
Explainable Multi-Factor Weighted Attribution Scoring
       ↓
Interactive GIS Dashboard + Maritime Pollution Investigation Brief
```

> **IMPORTANT LEGAL NOTICE**: POLARIS provides *probabilistic investigative decision support* to prioritize maritime assets for physical inspection and forensic sampling. It **never** claims definitive legal proof of guilt.

---

## 2. Key Features

- **Multi-Class SAR Segmentation**: Uses a U-Net architecture trained on Sentinel-1 SAR benchmarks to differentiate true mineral oil spills from natural biogenic slicks and low-wind look-alikes.
- **Physical Reverse Drift Engine**: Integrates ocean current vectors (Copernicus Marine CMEMS) and atmospheric wind fields (ERA5) backwards in time ($T_0 	o -48	ext{h}$) with stochastic turbulent diffusion.
- **Uncertainty Quantification**: Origin is output as a continuous 2D Kernel Density Estimation (KDE) probability heatmap and 95% confidence covariance ellipses rather than a fake single coordinate.
- **Provider-Agnostic AIS Architecture**: Interfaces with MarineCadastre (US open benchmark), curated INCOIS incident cases (Indian EEZ), and synthetic evaluation scenarios.
- **Explainable Attribution Scoring**: Transparent weighted scoring formula:
  $$\text{Score}(v) = \frac{w_1 S_{\text{spat}} + w_2 S_{\text{temp}} + w_3 S_{\text{traj}} + w_4 S_{\text{anom}} + w_5 S_{\text{type}} + p \cdot P_{\text{gap}}}{\sum w_i + p}$$
- **Interactive Temporal GIS Map**: Scrub backward through time ($-48	ext{h} 	o T_0$) to watch Lagrangian particles and vessel markers converge on the probable release zone.
- **Forensic Provenance Trail**: Generates SHA-256 cryptographic hashes across all input scenes, drift runs, and scoring matrices to maintain chain-of-custody for investigation briefs.

---

## 3. Technology Stack

- **Backend**: Python 3.10+, FastAPI, Uvicorn, Pydantic v2.
- **Deep Learning / CV**: PyTorch, Torchvision, OpenCV.
- **Geospatial & Ocean Physics**: Shapely, PyProj, NumPy, SciPy, NetworkX.
- **Frontend / GIS**: HTML5, Modern ES6 JavaScript, Tailwind CSS, Leaflet, Leaflet-Heat, Lucide Icons.

---

## 4. Installation & Local Execution

### Prerequisites
- Python 3.10+
- Modern Web Browser (Chrome, Edge, Firefox)

### Setup
```bash
# 1. Clone or navigate to the repository
cd polaris-maritime-attribution

# 2. Activate virtual environment
.\venv\Scripts\activate

# 3. Install requirements
pip install -r backend/requirements.txt
```

### Running the Application
```bash
# Start FastAPI backend server
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

Open your browser and navigate to:
- **Interactive GIS Dashboard**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive OpenAPI Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 5. Automated Testing & Validation
Run the full PyTest suite:
```bash
pytest backend/tests
```
Test suite coverage:
- `test_sar_geometry.py`: Verifies SAR calibration, Lee speckle filtering, and polygon vectorization.
- `test_drift_hindcast.py`: Verifies Lagrangian backward integration, particle conservation, and uncertainty ellipses.
- `test_attribution_scoring.py`: Evaluates ground-truth candidate recovery (Top-1 accuracy on synthetic benchmarks).
- `test_api_endpoints.py`: End-to-end validation of all FastAPI REST endpoints.

---

## 6. Preloaded Benchmark Cases

1. **Case 1: Gulf of Mexico (NOAA Benchmark)**
   - Sentinel-1 SAR acquisition over Mississippi Canyon transit corridor.
   - NOAA MarineCadastre historical AIS traffic + CMEMS currents + ERA5 winds.
2. **Case 2: Ennore Port / Coromandel Coast (INCOIS Advisory)**
   - Coromandel coastal zone incident calibrated with INCOIS public advisory data and DG Shipping shipping records.
3. **Case 3: Arabian Sea Ground-Truth Evaluation**
   - Controlled synthetic scenario with mathematically known discharge release at $T - 24	ext{h}$ to verify Top-1 recovery.

---

## 7. License & Compliance
All dependencies and data sources are 100% open-source or public domain. Full audit details are available in [`open_source_license_report.md`](open_source_license_report.md).
