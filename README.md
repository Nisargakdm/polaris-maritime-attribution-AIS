# POLARIS: Probabilistic Maritime Pollution Attribution Engine

### Satellite Oil-Spill Detection · Lagrangian Drift Reconstruction & Prediction · AIS Vessel Attribution · Behavioral Risk Profiling

**Smart India Hackathon 2026 — Problem Statement SIH26143 (NTRO / Space Technology)**

> **IMPORTANT LEGAL NOTICE**: POLARIS provides *probabilistic investigative decision support* to prioritize maritime assets for physical inspection and forensic sampling. It **never** claims definitive legal proof of guilt. All scores are heuristic indicators based on available AIS and SAR data only.

---

## Table of Contents

1. [Project Vision](#1-project-vision)
2. [System Architecture & Pipeline](#2-system-architecture--pipeline)
3. [Key Features](#3-key-features)
4. [Technology Stack](#4-technology-stack)
5. [Installation & Running](#5-installation--running)
6. [API Reference](#6-api-reference)
7. [U-Net Model Training](#7-u-net-sar-model-training)
8. [AIS Database](#8-ais-database)
9. [Vessel Risk Profiler](#9-vessel-behavioral-risk-profiler)
10. [Dashboard Interface](#10-dashboard-interface)
11. [Test Suite](#11-test-suite)
12. [Preloaded Scenarios](#12-preloaded-scenarios)
13. [Current Prototype Status](#13-current-prototype-status)
14. [License & Compliance](#14-license--compliance)

---

## 1. Project Vision

Operational maritime surveillance systems (EMSA CleanSeaNet, India's INCOIS OOSA) detect oil slicks and manually cross-reference nearby vessel locations. This approach systematically misses the responsible vessel: ocean slicks drift continuously under surface currents and wind, meaning the ship responsible for a discharge is rarely at the observed spill location hours later.

**POLARIS** addresses this gap with an end-to-end, physically grounded, uncertainty-aware forensic intelligence pipeline that reconstructs where a slick originated rather than simply where it was observed.

---

## 2. System Architecture & Pipeline

```
Satellite SAR Scene (Sentinel-1 / PALSAR)
        │
        ▼
SAR Calibration + Lee Speckle Filtering
        │
        ▼
U-Net Semantic Segmentation
(Binary: Background vs. Oil-Spill)
        │
        ▼
GeoJSON Polygon Extraction + Geodesic Area (km²)
        │
        ├──────────────────────────────────────┐
        ▼                                      ▼
Backward Lagrangian Drift              Forward Lagrangian Drift
Hindcast (–48h)                        Prediction (+48h)
Particles: 1200 / Timestep: 30min      Particles: 300 / Timestep: 30min
Stochastic diffusion, windage=0.031    Same physics, positive time integration
        │                                      │
        ▼                                      ▼
Origin Zone Estimate                   Predicted Future Trajectory
(2D KDE heatmap, 95% CI ellipses,      (uncertainty grows with time horizon)
 release time window PDF)
        │
        ▼
AIS Spatiotemporal Query
(filtered by ORIGIN location + release time window,
 not the visible spill location)
        │
        ▼
Kinematic Anomaly Analysis per Vessel
(SPEED_DROP, LOITERING, AIS_GAP, COURSE_DEVIATION)
        │
        ▼
Explainable Multi-Factor Attribution Score
Score(v) = w1·Sspatial + w2·Stemporal + w3·Strajectory + w4·Sanomaly + w5·Stype − p·Pgap
        │
        ├──────────────────────────────────────┐
        ▼                                      ▼
Ranked Vessel Shortlist              General Behavioral Risk Profile
(incident-specific correlation)      (per-vessel, full AIS history,
                                      independent of any incident)
        │
        ▼
Interactive GIS Dashboard + Investigation Brief
```

**Forcing data note:** The current prototype uses simplified constant ocean current and wind vectors. Fields labeled `"forcing_data_source": "simplified_constant"` in API responses reflect this. Full operational deployment requires live CMEMS ocean current + ERA5/ECMWF wind forecast integration.

---

## 3. Key Features

### SAR Detection
- **Binary U-Net segmentation** trained on the Deep-SAR Oil Spill Segmentation dataset (8,070 PALSAR/Sentinel-1 image-mask pairs, 256×256 px)
- Lee speckle filter, dB-scale calibration, percentile normalization
- GeoJSON polygon vectorization with geodesic area and centroid extraction
- Oil probability, look-alike probability, and detection confidence reported per scene

### Drift Engine
- **Backward drift (origin reconstruction):** 1,200 particles seeded in the observed spill polygon, advected backward 48 hours under `u_drift = −(u_current + 0.031·u_wind)` with stochastic diffusion
- **Forward drift (future prediction):** 300 particles advected forward from the observed spill, same physics without sign inversion; uncertainty ellipses grow with time horizon
- Outputs: origin centroid, 95% CI covariance ellipses at 6-hour intervals, 2D KDE heatmap, iso-probability rings (75/90/95%), sample trajectories for animation
- API exposes backward-only, forward-only, or combined endpoints

### AIS Correlation
- AIS queries filter vessels by the **reconstructed origin location and release time window** — not the visible spill position
- DuckDB embedded database for fast spatio-temporal queries on `ais_tracks`
- Kinematic anomaly detection: `SPEED_DROP`, `LOITERING`, `AIS_GAP`, `COURSE_DEVIATION`
- Attribution scorer computes CPA-to-origin, temporal overlap, trajectory consistency, anomaly index, vessel type compatibility
- Configurable scoring weights; re-ranking via POST endpoint without restarting server

### Vessel Behavioral Risk Profiler
- **Independently computed** from full historical AIS track (not incident-scoped)
- Metrics: AIS gap frequency (gaps/hour), speed anomaly frequency, loitering frequency
- Risk levels: `LOW` / `MEDIUM` / `HIGH` / `ELEVATED` / `INSUFFICIENT_DATA`
- Clearly framed as AIS-behavioral-pattern heuristic — not hull/engine/inspection data
- Exposed via `GET /api/ais/vessels/{mmsi}/risk-profile`; also embedded in vessel candidate responses

### Dashboard & Evidence
- Three-panel GIS dashboard: investigation workflow sidebar, Leaflet map, vessel ranking sidebar
- Vessel cards show **both** incident correlation score (%) and general risk indicator badge side by side
- Evidence graph (nodes + edges), investigation brief (Markdown + SHA-256 provenance hash)
- Analyst actions: flag candidate, exclude candidate, notes
- Timeline scrubber: animate vessel positions and drift particles across the 48-hour hindcast window
- Layer toggles: spill polygon, origin heatmap, uncertainty ellipses, bathymetric contours, current vectors, AIS tracks, drift particles

---

## 4. Technology Stack

| Layer | Libraries |
|---|---|
| Backend API | Python 3.10+, FastAPI, Uvicorn, Pydantic v2 |
| Deep Learning | PyTorch 2.x, Torchvision, OpenCV |
| Geospatial | Shapely, PyProj, NumPy, SciPy |
| Database | DuckDB (embedded, no server required) |
| Graph / Reporting | NetworkX, Jinja2 |
| Frontend | HTML5, ES6, Tailwind CSS, Leaflet 1.9, Leaflet-Heat, Lucide Icons |

---

## 5. Installation & Running

### Prerequisites
- Python 3.10+
- Modern browser (Chrome, Edge, Firefox)

### Setup

```bash
# 1. Clone / navigate to the repository
cd polaris-maritime-attribution

# 2. Activate virtual environment (Windows)
.\venv\Scripts\activate

# 3. Install dependencies
pip install -r backend/requirements.txt
```

### Start the server

```bash
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

Then open:
- **Dashboard:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **API docs (Swagger UI):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

On startup, the server automatically initializes all six preloaded scenario pipelines (SAR detection → backward drift → AIS candidates → attribution scoring). This takes approximately 15–20 seconds.

---

## 6. API Reference

All routes are prefixed under `/api/`.

### Cases
| Method | Route | Description |
|---|---|---|
| GET | `/api/cases` | List all preloaded scenarios |
| GET | `/api/cases/{case_id}` | Single case summary |

### Detection
| Method | Route | Description |
|---|---|---|
| GET | `/api/detection/{case_id}` | SAR segmentation result: polygon, area, confidence, probabilities |

### Drift
| Method | Route | Description |
|---|---|---|
| GET | `/api/drift/{case_id}` | Backward drift hindcast: origin estimate, ellipses, heatmap, trajectories |
| GET | `/api/drift/{case_id}/forward-prediction` | Forward drift prediction: future trajectory, growing uncertainty. Query params: `duration_hours` (default 48), `num_particles` (default 300) |
| GET | `/api/drift/{case_id}/combined` | Both backward and forward results in one response |
| POST | `/api/drift/{case_id}/re-simulate` | Re-run backward drift with custom particle count / duration |

### Attribution
| Method | Route | Description |
|---|---|---|
| GET | `/api/attribution/{case_id}` | Ranked vessel candidates with sub-scores, waypoints, anomaly flags, and general risk profile |
| POST | `/api/attribution/{case_id}/recompute` | Re-rank candidates with new scoring weights (body: `AttributionWeightConfig`) |
| POST | `/api/attribution/{case_id}/review` | Analyst flag / exclude action on a candidate |

### AIS / Vessel Risk
| Method | Route | Description |
|---|---|---|
| GET | `/api/ais/candidates/{case_id}` | Raw AIS candidate list for a case |
| GET | `/api/ais/vessels/{mmsi}/risk-profile` | General behavioral risk profile from full historical AIS track |

### Report & Evidence
| Method | Route | Description |
|---|---|---|
| GET | `/api/report/{case_id}` | Full investigation dossier JSON (evidence graph, ranked candidates, SHA-256 hash) |
| GET | `/api/report/{case_id}/markdown` | Investigation brief as plain Markdown |

---

## 7. U-Net SAR Model Training

The training pipeline lives entirely in `scripts/train_unet.py` as a standalone script (no FastAPI dependency).

### Dataset structure

```
data/raw/archive/
  images/images/
    train/   palsar_0.png … palsar_N.png   (8,070 total pairs)
    val/
  masks/masks/
    train/   palsar_0.png …
    val/
data/processed/sar_cache/   ← preprocessed memory-mapped arrays (auto-built)
data/models/
  model.pth                 ← saved best checkpoint
  metrics.json              ← test-set evaluation metrics
```

### Training

```bash
# Full training run
python scripts/train_unet.py --epochs 30 --batch-size 8

# Fast prototype run (1000 samples, 8 epochs)
python scripts/train_unet.py --epochs 8 --batch-size 8 --max-samples 1000

# Smoke test (3 epochs, 50 samples)
python scripts/train_unet.py --epochs 3 --batch-size 8 --max-samples 50
```

Training uses a preprocessing cache (`data/processed/sar_cache/`) so SAR calibration and speckle filtering only run once. On CPU with `--max-samples 1000`, expect ~25 minutes per epoch.

### Current model metrics (prototype checkpoint)

From `data/models/metrics.json` (1 epoch, 800 training samples, CPU):

| Metric | Value |
|---|---|
| Val IoU (best epoch) | 0.5084 |
| Test IoU (oil class) | see metrics.json |
| Architecture | SimpleUNet, binary (num_classes=2) |
| Note | Interim prototype. Full multi-class (5-class) training requires a labeled multi-class dataset. |

### Google Colab (GPU training)

For faster multi-epoch training on a free T4 GPU:

1. Open `scripts/train_unet_colab.ipynb` in [Google Colab](https://colab.research.google.com/)
2. Enable GPU: **Runtime → Change runtime type → T4 GPU**
3. Upload `data/raw/archive/` to Google Drive at `MyDrive/polaris/archive/`
4. Run the notebook — weights and metrics save back to Drive
5. Download `model.pth` and `metrics.json` to `data/models/`

---

## 8. AIS Database

POLARIS uses DuckDB (`data/db/polaris.duckdb`) for vessel trajectory storage and spatio-temporal queries.

### Initialize schema

```bash
python scripts/build_ais_db.py
```

### Ingest a real AIS CSV

```bash
python scripts/build_ais_db.py --csv data/raw/ais/noaa_gulf_ais.csv --incident-id INC-DEMO-001
```

Expected CSV columns (mapped automatically): `MMSI`, `BaseDateTime`, `LAT`, `LON`, `SOG`, `COG`, `VesselType`.

### Fetch NOAA MarineCadastre data

A helper script is provided for downloading NOAA public AIS data:

```bash
python scripts/fetch_noaa_ais.py
```

See the script's header comments for bounding box and time window configuration.

### Schema

The `ais_tracks` table stores: `mmsi`, `timestamp`, `lat`, `lon`, `sog_knots`, `cog_degrees`, `vessel_type`, `incident_id`.

**Note on current prototype:** The six preloaded demo cases use programmatically generated AIS candidate data (via `case_manager.py`), not the DuckDB database directly. The database pipeline is wired and functional — populating it with real AIS CSVs will cause the vessel risk profiler to return scored profiles rather than `INSUFFICIENT_DATA`.

---

## 9. Vessel Behavioral Risk Profiler

`backend/app/services/vessel_risk_profiler.py`

Computes a general behavioral risk indicator for any vessel from its **full historical AIS track** — completely independent of any specific incident.

### Scoring components

| Component | Weight | What it measures |
|---|---|---|
| AIS gap frequency | 0.35 | Gaps ≥ 25 minutes per tracked hour |
| Speed anomaly frequency | 0.35 | Sharp SOG drops vs. rolling 5-point average |
| Loitering frequency | 0.30 | Waypoints with SOG < 4 knots per tracked hour |

### Risk levels

| Level | Score range | Meaning |
|---|---|---|
| `LOW` | 0.00 – 0.39 | Behavioral patterns consistent with routine operations |
| `MEDIUM` | 0.40 – 0.59 | Moderate anomaly frequency, warrants elevated monitoring |
| `HIGH` | 0.60 – 0.74 | Recurring anomalies across historical track |
| `ELEVATED` | 0.75 – 0.95 | High anomaly frequency across full history |
| `INSUFFICIENT_DATA` | — | Fewer than 24h of historical AIS coverage available |

### Limitations (displayed in dashboard and API response)

- Based **solely on AIS behavioral patterns** — not hull condition, engine health, or classification society records
- AIS transponder gaps reflect communication, not vessel intent or mechanical status
- Speed/course anomalies may reflect legitimate operations (weather, navigation, cargo)
- Requires ≥ 24h of historical AIS coverage to compute; returns `INSUFFICIENT_DATA` otherwise

---

## 10. Dashboard Interface

The single-page GIS dashboard (`backend/app/static/index.html`) is a three-column layout locked to the browser viewport.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  HEADER: POLARIS | Historical/Simulation Mode badge | Scenario selector  │
│           SAR Active | Evidence Graph | Weights | Investigation Brief    │
│  DISCLAIMER: forensic decision support notice                            │
├──────────────────┬──────────────────────────────┬───────────────────────┤
│  LEFT SIDEBAR    │  GIS MAP (Leaflet, fills all  │  RIGHT SIDEBAR        │
│  (scrollable)    │  remaining height)            │  (scrollable)         │
│                  │                               │                       │
│  Investigation   │  Layer toggles overlay        │  VESSEL RANKING       │
│  Workflow (6     │  Basemap switcher             │  Ranked cards, each   │
│  pipeline steps) │  Zoom shortcuts               │  showing:             │
│                  │                               │  · Incident score %   │
│  Spill Detection │  GIS Symbology legend:        │  · Risk badge         │
│  Evidence        │  · Oil slick (red)            │                       │
│  (SAR metadata)  │  · Origin zone (amber)        │  Attribution Weights  │
│                  │  · Heatmap gradient           │  strip + Edit         │
│  Drift           │  · Vessel tier colors         │                       │
│  Reconstruction  │  · Track line styles          │  SELECTED VESSEL      │
│  (origin coords, │  · Drift particles            │  · Name + tier badge  │
│   uncertainty,   │                               │  · Score Summary:     │
│   forcing note)  │  Timeline scrubber (–48h→T0)  │    Incident Corr. %   │
│                  │  animate particles + vessels  │    General Risk badge │
│  AIS Source &    │                               │  · Identity grid      │
│  Coverage        │                               │  · Tech specs         │
│                  │                               │  · SOG sparkline      │
│                  │                               │  · Sub-score bars     │
│                  │                               │  · Evidence points    │
│                  │                               │  · Anomaly flags      │
│                  │                               │  · Risk breakdown     │
│                  │                               │    (when available)   │
│                  │                               │  · Flag / Exclude     │
└──────────────────┴──────────────────────────────┴───────────────────────┘
```

Every panel has a labeled header and a `?` tooltip explaining what it shows and which API route feeds it. The layout uses CSS `height: 100%` + `min-height: 0` flex guards so neither sidebar nor the page scrolls at the page level — only sidebars scroll internally.

---

## 11. Test Suite

```bash
pytest backend/tests -v
```

| Test file | What it validates |
|---|---|
| `test_sar_geometry.py` | SAR preprocessor (Lee filter, calibration), geometry extractor (polygon area, centroid), U-Net inference shape |
| `test_drift_hindcast.py` | Lagrangian integration (particle conservation, backward time progression, haversine/bearing math) |
| `test_attribution_scoring.py` | Ground-truth Top-1 candidate recovery on a synthetic controlled scenario |
| `test_api_endpoints.py` | End-to-end HTTP responses for all major routes |

All 7 tests pass on a clean install.

Additional integration scripts (not part of the pytest suite):

```bash
python backend/test_drift_forward_integration.py  # forward drift physics + uncertainty growth
python backend/test_api_drift_endpoints.py         # all three drift API endpoints live
python backend/test_risk_profiler_integration.py   # risk profiler edge cases + config validation
python backend/verify_ui.py                        # static asset + API content checks (requires server running)
```

---

## 12. Preloaded Scenarios

Six scenarios initialize automatically on server startup. All use programmatically generated AIS candidate data and simplified constant ocean forcing.

| Case | Region | Key feature demonstrated |
|---|---|---|
| `case_01_gulf_mexico` | Gulf of Mexico, Mississippi Canyon | NOAA MarineCadastre AIS benchmark; deepwater transit corridor |
| `case_02_ennore_india` | Ennore Port, Coromandel Coast | Indian EEZ scenario; INCOIS advisory calibration |
| `case_03_synthetic_eval` | Arabian Sea | Controlled ground-truth: discharge at T–24h, Top-1 recovery verified |
| `case_04_malacca_strait` | Singapore Strait / Malacca TSS | High-traffic chokepoint; bunkering slick scenario |
| `case_05_mumbai_high` | Mumbai Offshore / Bombay High | Offshore platform corridor; ONGC operational zone |
| `case_06_bay_of_bengal_sagar` | Bay of Bengal / Sagar Island | Marine sanctuary proximity; coastal impact sensitivity |

---

## 13. Current Prototype Status

This section is honest about what is fully wired versus what uses simplified stand-ins.

### Fully operational

- SAR preprocessing pipeline (Lee filter, calibration, normalization)
- U-Net segmentation inference (`data/models/model.pth`, num_classes=2)
- GeoJSON polygon extraction and geodesic area computation
- Backward Lagrangian drift (1,200 particles, 48h, stochastic diffusion, KDE heatmap)
- Forward Lagrangian drift prediction (300 particles, 48h, growing uncertainty)
- AIS candidate generation and DuckDB query pipeline (schema + ingestion scripts ready)
- Attribution scoring (all 5 sub-scores + gap penalty, configurable weights, live recompute)
- Trajectory analyzer (anomaly detection: SPEED_DROP, LOITERING, AIS_GAP, COURSE_DEVIATION)
- Vessel behavioral risk profiler (gap/speed/loitering frequency from full AIS history)
- Evidence graph builder and report generator
- Full GIS dashboard with all panels, tooltips, legend, simulation badge, risk profile badges

### Simplified / prototype stand-ins

| Component | Current state | What's needed for production |
|---|---|---|
| Ocean/wind forcing | Constant vectors per case | Live CMEMS ocean current + ECMWF/ERA5 wind API integration |
| AIS data for demo cases | Programmatically generated candidate vessels | Real AIS CSV ingestion via `build_ais_db.py` |
| U-Net model | 1-epoch prototype (Val IoU ~0.51, binary only) | Multi-epoch GPU training; 5-class labeled dataset |
| Vessel risk profiles | `INSUFFICIENT_DATA` for demo cases (no 24h+ AIS history in DB) | Populated DuckDB from real historical AIS feeds |
| Coastline impact layer | Not implemented | Port/coastline proximity analysis for forward drift |

---

## 14. License & Compliance

All dependencies and data sources are open-source or public domain. See [`open_source_license_report.md`](open_source_license_report.md) for the full audit.
