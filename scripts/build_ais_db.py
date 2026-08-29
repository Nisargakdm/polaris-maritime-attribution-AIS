"""
scripts/build_ais_db.py
─────────────────────────────────────────────────────────────────────────────
POLARIS — Phase 2 / Step 3: AIS Database Bootstrap Script
Sets up an embedded DuckDB database at data/db/polaris.duckdb with the
canonical AIS vessel tracking schema.

This is a STANDALONE script — it does NOT import from the FastAPI app.

USAGE
─────
    # Create / re-create the schema only (no data ingestion):
    python scripts/build_ais_db.py

    # Ingest a real AIS CSV once it is available:
    python scripts/build_ais_db.py --csv path/to/ais_data.csv --incident-id INC001

CSV FORMAT EXPECTED
───────────────────
The CSV must contain these columns (exact names, case-insensitive):
    mmsi, vessel_name, ts, lat, lon, sog_knots, cog_degrees, heading,
    nav_status, vessel_type

The --incident-id argument tags every row with the incident identifier.

REAL DATA PLACEHOLDER
─────────────────────
    ┌─────────────────────────────────────────────────────────────────────┐
    │  DROP YOUR HISTORICAL AIS CSV HERE:                                 │
    │    data/raw/ais/<incident_id>_ais.csv                               │
    │                                                                     │
    │  Then run:                                                          │
    │    python scripts/build_ais_db.py \\                                │
    │        --csv data/raw/ais/<incident_id>_ais.csv \\                  │
    │        --incident-id <incident_id>                                  │
    │                                                                     │
    │  Expected source: MarineCadastre, INCOIS AIS archive, or           │
    │  DG Shipping historical records for the relevant incident window.   │
    └─────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import duckdb
except ImportError:
    sys.exit(
        "ERROR: duckdb is not installed.\n"
        "Install it with:\n"
        "  venv\\Scripts\\pip install duckdb"
    )

# ─── CONFIG ──────────────────────────────────────────────────────────────────

DB_PATH = Path("data/db/polaris.duckdb")

# ─── SCHEMA ──────────────────────────────────────────────────────────────────

CREATE_AIS_TABLE = """
CREATE TABLE IF NOT EXISTS ais_tracks (
    incident_id  VARCHAR,     -- Links to incident_config.json incident_id
    mmsi         VARCHAR,     -- Maritime Mobile Service Identity (9-digit string)
    vessel_name  VARCHAR,
    ts           TIMESTAMP,   -- UTC timestamp of AIS message
    lat          DOUBLE,      -- Latitude (WGS-84, decimal degrees)
    lon          DOUBLE,      -- Longitude (WGS-84, decimal degrees)
    sog_knots    DOUBLE,      -- Speed Over Ground (knots)
    cog_degrees  DOUBLE,      -- Course Over Ground (degrees true, 0–360)
    heading      DOUBLE,      -- True heading (degrees, 0–360; 511 = not available)
    nav_status   VARCHAR,     -- AIS navigational status string
    vessel_type  VARCHAR      -- AIS vessel type description
);
"""

CREATE_INCIDENTS_TABLE = """
CREATE TABLE IF NOT EXISTS incidents (
    incident_id    VARCHAR PRIMARY KEY,
    name           VARCHAR,
    mode           VARCHAR,   -- 'historical' or 'live'
    detection_time TIMESTAMP,
    case_source    VARCHAR,
    notes          VARCHAR
);
"""


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def init_db(db_path: Path) -> duckdb.DuckDBPyConnection:
    """Open (or create) the DuckDB database and ensure schema exists."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    con.execute(CREATE_AIS_TABLE)
    con.execute(CREATE_INCIDENTS_TABLE)
    print(f"  [OK] Database schema verified: {db_path.resolve()}")
    return con


def ingest_csv(
    con: duckdb.DuckDBPyConnection,
    csv_path: Path,
    incident_id: str,
) -> None:
    """
    Load an AIS CSV into ais_tracks, tagging every row with incident_id.

    The CSV is read by DuckDB's native CSV reader (handles large files
    efficiently without loading everything into memory).
    """
    if not csv_path.exists():
        sys.exit(f"ERROR: CSV file not found: {csv_path}")

    # Preview column names
    preview = con.execute(
        f"SELECT * FROM read_csv_auto('{csv_path}', header=True) LIMIT 1"
    ).description
    csv_cols = {d[0].lower() for d in preview}

    required = {
        "mmsi", "vessel_name", "ts", "lat", "lon",
        "sog_knots", "cog_degrees", "heading", "nav_status", "vessel_type",
    }
    missing = required - csv_cols
    if missing:
        sys.exit(
            f"ERROR: CSV is missing required columns: {missing}\n"
            f"Found columns: {csv_cols}"
        )

    # Insert with incident_id injected as a literal
    con.execute(f"""
        INSERT INTO ais_tracks
        SELECT
            '{incident_id}'  AS incident_id,
            CAST(mmsi        AS VARCHAR),
            CAST(vessel_name AS VARCHAR),
            CAST(ts          AS TIMESTAMP),
            CAST(lat         AS DOUBLE),
            CAST(lon         AS DOUBLE),
            CAST(sog_knots   AS DOUBLE),
            CAST(cog_degrees AS DOUBLE),
            CAST(heading     AS DOUBLE),
            CAST(nav_status  AS VARCHAR),
            CAST(vessel_type AS VARCHAR)
        FROM read_csv_auto('{csv_path}', header=True)
    """)

    row_count = con.execute(
        f"SELECT COUNT(*) FROM ais_tracks WHERE incident_id = '{incident_id}'"
    ).fetchone()[0]
    print(f"  [OK] Ingested {row_count:,} AIS rows for incident '{incident_id}'.")


def print_summary(con: duckdb.DuckDBPyConnection) -> None:
    """Print a brief summary of the current database contents."""
    print("\n  -- Database Summary ------------------------------------------------")
    result = con.execute("""
        SELECT incident_id, COUNT(*) AS rows,
               MIN(ts) AS first_ts, MAX(ts) AS last_ts,
               COUNT(DISTINCT mmsi) AS unique_vessels
        FROM ais_tracks
        GROUP BY incident_id
        ORDER BY incident_id
    """).fetchall()

    if not result:
        print("  ais_tracks: (empty — no AIS data ingested yet)")
    else:
        for row in result:
            print(
                f"  incident={row[0]:15s}  rows={row[1]:>7,}  "
                f"vessels={row[4]:>4}  "
                f"window={row[2]} → {row[3]}"
            )
    print()


# ─── MAIN ────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="POLARIS — AIS DuckDB database setup and ingestion"
    )
    p.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Path to historical AIS CSV to ingest (optional — skipped if not provided).",
    )
    p.add_argument(
        "--incident-id",
        type=str,
        default=None,
        help="Incident identifier to tag ingested rows (required when --csv is given).",
    )
    p.add_argument(
        "--db",
        type=Path,
        default=DB_PATH,
        help=f"Path to DuckDB file (default: {DB_PATH}).",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    print(f"\n{'='*60}")
    print(f"  POLARIS — AIS Database Setup")
    print(f"{'='*60}")

    con = init_db(args.db)

    if args.csv is not None:
        if args.incident_id is None:
            sys.exit(
                "ERROR: --incident-id is required when --csv is provided.\n"
                "Example: --incident-id INC001"
            )
        print(f"\n  Ingesting CSV: {args.csv}")
        ingest_csv(con, args.csv, args.incident_id)

    print_summary(con)
    con.close()
    print(f"  Database path: {args.db.resolve()}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
