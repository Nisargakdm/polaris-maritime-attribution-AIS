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

## 5. U-Net SAR Oil-Spill Model Training (Phase 2)

The project includes an end-to-end U-Net segmentation pipeline trained on Sentinel-1 & PALSAR SAR imagery (Deep-SAR dataset).

### Dataset Location
Raw imagery and binary ground-truth masks are structured at:
- `data/raw/archive/images/images/{train,val}/*.png` (256x256 SAR scenes)
- `data/raw/archive/masks/masks/{train,val}/*.png` (256x256 binary masks)

### Option A: Local Training (with Preprocessing Cache)
To train locally using the standalone training script:
```bash
# Run standalone training (with automatic deterministic SAR preprocessing cache):
python scripts/train_unet.py --epochs 30 --batch-size 8

# Quick 3-epoch smoke test:
python scripts/train_unet.py --epochs 3 --batch-size 8
```
Outputs are automatically saved to:
- Trained model weights: `data/models/model.pth`
- Test-set evaluation metrics: `data/models/metrics.json`

### Option B: High-Speed GPU Training via Google Colab
For fast multi-epoch training on free T4 GPUs:
1. Open `scripts/train_unet_colab.ipynb` in [Google Colab](https://colab.research.google.com/).
2. Enable GPU under **Runtime** -> **Change runtime type** -> **T4 GPU**.
3. Upload `data/raw/archive/` to your Google Drive (`MyDrive/polaris/archive/`).
4. Execute the notebook. Model weights (`model.pth`) and verified test metrics (`metrics.json`) will be saved directly back to Google Drive.
5. Download both files to `data/models/` in your local workspace.

---

## 6. AIS Vessel Data & DuckDB Storage (Phase 2)

POLARIS uses an embedded DuckDB database (`data/db/polaris.duckdb`) for fast historical vessel trajectory spatio-temporal hindcast queries.

### Initialize Schema
```bash
# Creates table schema without fake data:
python scripts/build_ais_db.py
```

### Ingest Historical AIS Records
When historical AIS CSV data is available:
```bash
# Drop CSV in data/raw/ais/<incident_id>_ais.csv and run:
python scripts/build_ais_db.py --csv data/raw/ais/sample_incident_ais.csv --incident-id INC-2026-001
```

### Incident Config Template
Standardized incident metadata templates are stored at `data/incidents/incident_config.json`.

---

## 7. Automated Testing & Validation
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

## 8. Preloaded Benchmark Cases

1. **Case 1: Gulf of Mexico (NOAA Benchmark)**
   - Sentinel-1 SAR acquisition over Mississippi Canyon transit corridor.
   - NOAA MarineCadastre historical AIS traffic + CMEMS currents + ERA5 winds.
2. **Case 2: Ennore Port / Coromandel Coast (INCOIS Advisory)**
   - Coromandel coastal zone incident calibrated with INCOIS public advisory data and DG Shipping shipping records.
3. **Case 3: Arabian Sea Ground-Truth Evaluation**
   - Controlled synthetic scenario with mathematically known discharge release at $T - 24\text{h}$ to verify Top-1 recovery.

---

## 9. License & Compliance
All dependencies and data sources are 100% open-source or public domain. Full audit details are available in [`open_source_license_report.md`](open_source_license_report.md).
