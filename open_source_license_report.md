# POLARIS: Open-Source Software & Data License Compliance Report
## Smart India Hackathon 2026 — SIH26143 (NTRO)

### 1. Executive Summary
This document provides a comprehensive license, access, and redistribution audit for all datasets, machine learning models, physical simulation frameworks, and software libraries utilized in the **POLARIS** (*Probabilistic Ocean-Lagrangian Attribution & Remote-sensing Intelligence System*) platform.

---

### 2. Dataset & Oceanographic Forcing License Audit

| Component | Source / Provider | License / Terms | Free / Open? | Restrictions & Attribution Requirements | Verification Status |
|---|---|---|---|---|---|
| **Sentinel-1 SAR Imagery** | ESA / Copernicus Data Space Ecosystem (CDSE) | Open Access Policy (Regulation EU 377/2014) | **Yes (Free)** | Free for academic, government, and commercial use. Mandatory citation: *"Contains modified Copernicus Sentinel data [year]"*. | **VERIFIED OPEN** |
| **Ocean Physics Reanalysis (Currents/Waves)** | Copernicus Marine Service (CMEMS) (`PHY_001_030`) | Copernicus Marine Open License (SLA) | **Yes (Free)** | Free open access upon free user registration. Cite CMEMS service in technical briefings. | **VERIFIED OPEN** |
| **Atmospheric Forcing (ERA5 Winds)** | ECMWF / Copernicus Climate Data Store (CDS) | Open CDS Licence | **Yes (Free)** | Free open data access via cdsapi. Attribution to ECMWF/Copernicus CDS required. | **VERIFIED OPEN** |
| **Historical AIS (US & Atlantic Benchmarks)** | NOAA Office for Coastal Management & BOEM MarineCadastre | US Federal Public Domain | **Yes (Free)** | Unrestricted public domain data. Free for unlimited redistribution and modification. | **VERIFIED OPEN** |
| **Oil Spill Detection Dataset (OSD)** | Krestenitis et al. (MKLab/CERTH) | Academic / Research Use | **Yes (Free)** | Freely benchmarked across academic literature. Used strictly for model evaluation and validation. | **VERIFIED RESEARCH** |
| **Indian Ocean Coastal Incident Data** | INCOIS (Indian National Centre for Ocean Information Services) | Government Open Public Data | **Yes (Free)** | Derived from public incident case advisories (Ennore Port 2017 & Kerala Coast). | **VERIFIED OPEN** |

---

### 3. Software Dependencies & Libraries Audit

| Software Library | Version | License | Commercial / Academic Use | Copyleft / Linking Terms | Status |
|---|---|---|---|---|---|
| **FastAPI** | 0.111.0+ | MIT | Permissive | Direct use permitted | **COMPLIANT** |
| **Uvicorn** | 0.30.0+ | BSD-3-Clause | Permissive | Direct use permitted | **COMPLIANT** |
| **PyTorch / Torchvision** | 2.0.1+ | Modified BSD | Permissive | Direct use permitted | **COMPLIANT** |
| **OpenDrift / OpenOil** | 1.11.0+ | GPL-2.0 | Copyleft (Open Source) | Complete system source is open; 100% compliant | **COMPLIANT** |
| **Shapely** | 2.1.0+ | BSD-3-Clause | Permissive | Direct use permitted | **COMPLIANT** |
| **PyProj** | 3.7.0+ | MIT | Permissive | Direct use permitted | **COMPLIANT** |
| **OpenCV** | 4.8.1+ | Apache-2.0 | Permissive | Direct use permitted | **COMPLIANT** |
| **NetworkX** | 3.4.0+ | BSD-3-Clause | Permissive | Direct use permitted | **COMPLIANT** |
| **Leaflet / Leaflet.heat** | 1.9.4 / 0.2.0 | BSD-2-Clause | Permissive | Direct use permitted | **COMPLIANT** |
| **Tailwind CSS** | 3.4.0+ | MIT | Permissive | Direct use permitted | **COMPLIANT** |

---

### 4. Statement on Indian Territorial AIS Coverage
Nationwide live Indian AIS data is not published on unrestricted open web feeds for national security and commercial confidentiality reasons (managed by DG Shipping / Indian Coast Guard). For SIH26143 demonstration and algorithm benchmarking, POLARIS utilizes:
1. MarineCadastre historical datasets for global ground-truth validation.
2. Curated public INCOIS incident case advisories for Indian EEZ operational scenarios.
3. Synthetic controlled scenarios for mathematical Top-1 / Top-3 candidate recovery verification.

*Production deployment within Indian waters would connect directly to an authorized DG Shipping / Indian Coast Guard AIS gateway under standard inter-agency data sharing agreements.*
