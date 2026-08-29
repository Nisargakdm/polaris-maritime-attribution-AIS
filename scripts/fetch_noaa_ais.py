"""
scripts/fetch_noaa_ais.py
==============================================================================
POLARIS -- Download and extract real historical NOAA MarineCadastre AIS data
Filters records for the Gulf of Mexico incident region and outputs a CSV
matching the DuckDB polaris schema.
==============================================================================
"""

import os
import csv
import io
import zipfile
import urllib.request
from pathlib import Path

NOAA_URL = "https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2023/AIS_2023_01_01.zip"
OUTPUT_DIR = Path("data/raw/ais")
OUTPUT_CSV = OUTPUT_DIR / "noaa_gulf_ais.csv"

# Bounding box for Gulf of Mexico Mississippi Canyon / Deepwater corridor
LAT_MIN, LAT_MAX = 27.5, 29.5
LON_MIN, LON_MAX = -90.5, -88.0

def fetch_and_filter():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Connecting to NOAA MarineCadastre: {NOAA_URL} ...", flush=True)
    
    req = urllib.request.Request(NOAA_URL, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    
    print("Downloading NOAA AIS zip package (streaming) ...", flush=True)
    with urllib.request.urlopen(req, timeout=120) as resp:
        zip_bytes = io.BytesIO(resp.read())
    
    print("Extracting and filtering Gulf of Mexico vessel tracks ...", flush=True)
    total_scanned = 0
    matched_rows = []
    
    with zipfile.ZipFile(zip_bytes) as zf:
        csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
        if not csv_names:
            print("Error: No CSV found inside zip archive.", flush=True)
            return
        
        with zf.open(csv_names[0]) as csv_file:
            reader = csv.DictReader(io.TextIOWrapper(csv_file, encoding="utf-8"))
            for row in reader:
                total_scanned += 1
                try:
                    lat = float(row.get("LAT", 0))
                    lon = float(row.get("LON", 0))
                except (ValueError, TypeError):
                    continue
                
                # Check spatial bounding box
                if LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX:
                    v_name = (row.get("VesselName") or "").strip()
                    if not v_name:
                        v_name = f"VESSEL-{row.get('MMSI', 'UNKNOWN')}"
                    
                    matched_rows.append({
                        "mmsi": row.get("MMSI", ""),
                        "vessel_name": v_name,
                        "ts": row.get("BaseDateTime", "").replace("T", " "),
                        "lat": lat,
                        "lon": lon,
                        "sog_knots": float(row.get("SOG") or 0.0),
                        "cog_degrees": float(row.get("COG") or 0.0),
                        "heading": float(row.get("Heading") or 511.0),
                        "nav_status": row.get("Status") or "under way using engine",
                        "vessel_type": row.get("VesselType") or "Commercial Vessel",
                    })
                
                if len(matched_rows) >= 5000:
                    # Keep a focused set of tracks for fast processing
                    break

    print(f"Scanned {total_scanned:,} AIS records | Filtered {len(matched_rows):,} Gulf of Mexico records.", flush=True)
    
    # Write output CSV
    fieldnames = [
        "mmsi", "vessel_name", "ts", "lat", "lon",
        "sog_knots", "cog_degrees", "heading", "nav_status", "vessel_type"
    ]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(matched_rows)
    
    print(f"Saved real NOAA AIS records -> {OUTPUT_CSV.resolve()}", flush=True)

if __name__ == "__main__":
    fetch_and_filter()
