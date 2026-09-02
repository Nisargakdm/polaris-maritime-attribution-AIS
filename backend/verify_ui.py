"""
Verification script for POLARIS dashboard UI changes.
Run from project root with venv activated:
    python backend/verify_ui.py
"""
import urllib.request
import json
import sys

BASE = "http://127.0.0.1:8000"
errors = []


def get(path, label):
    try:
        with urllib.request.urlopen(BASE + path, timeout=15) as r:
            body = r.read().decode()
            data = json.loads(body)
            if isinstance(data, list):
                print(f"  OK   {label}: list({len(data)} items)")
            elif isinstance(data, dict):
                keys = list(data.keys())[:6]
                print(f"  OK   {label}: {keys}")
            return data
    except Exception as e:
        print(f"  FAIL {label}: {e}")
        errors.append(label)
        return None


def get_text(path, label):
    try:
        with urllib.request.urlopen(BASE + path, timeout=10) as r:
            return r.read().decode()
    except Exception as e:
        print(f"  FAIL {label}: {e}")
        errors.append(label)
        return ""


# ── Static assets ──────────────────────────────────────────────────────────────
print("\n── Static assets ──")

css = get_text("/static/css/styles.css", "styles.css")
checks = {
    "html/body height:100%": "height: 100%",
    "#app-root rule":        "#app-root",
    "#content-row rule":     "#content-row",
    "#sidebar-left rule":    "#sidebar-left",
    ".risk-badge class":     ".risk-badge",
    "#sim-mode-badge":       "#sim-mode-badge",
    ".panel-info tooltip":   ".panel-info",
}
all_ok = True
for name, needle in checks.items():
    found = needle in css
    status = "OK  " if found else "MISS"
    if not found:
        all_ok = False
        errors.append(f"CSS: {name}")
    print(f"    {status}  styles.css -> {name}")

js = get_text("/static/js/app.js", "app.js")
js_checks = {
    "detail-risk-badge-slot":  "detail-risk-badge-slot",
    "detail-risk-breakdown":   "detail-risk-breakdown",
    "detail-overall-score":    "detail-overall-score",
    "risk-badge class render": "risk-badge",
    "riskLevel mapping":       "riskLevel",
    "general_risk_profile ref":"general_risk_profile",
}
for name, needle in js_checks.items():
    found = needle in js
    status = "OK  " if found else "MISS"
    if not found:
        errors.append(f"JS: {name}")
    print(f"    {status}  app.js -> {name}")

html = get_text("/", "index.html (root)")
html_checks = {
    "id=app-root":              'id="app-root"',
    "id=content-row":           'id="content-row"',
    "id=sidebar-left":          'id="sidebar-left"',
    "id=sidebar-right":         'id="sidebar-right"',
    "id=sim-mode-badge":        'id="sim-mode-badge"',
    "detail-risk-badge-slot":   "detail-risk-badge-slot",
    "detail-overall-score":     "detail-overall-score",
    "Vessel Ranking heading":   "Vessel Ranking",
    "Extended legend (tiers)":  "High-priority vessel",
    "Heatmap gradient swatch":  "linear-gradient",
    "panel-info tooltip class": "panel-info",
    "panel-header class":       "panel-header",
    "Spill Detection Evidence": "Spill Detection Evidence",
    "Drift Reconstruction":     "Drift Reconstruction",
    "AIS Source heading":       "AIS Source",
    "forcing disclaimer":       "Simplified constant forcing",
}
for name, needle in html_checks.items():
    found = needle in html
    status = "OK  " if found else "MISS"
    if not found:
        errors.append(f"HTML: {name}")
    print(f"    {status}  index.html -> {name}")

# ── API routes ─────────────────────────────────────────────────────────────────
print("\n── API routes ──")
get("/api/cases",                                      "GET /api/cases")
det = get("/api/detection/case_01_gulf_mexico",        "GET /api/detection/case_01")
dft = get("/api/drift/case_01_gulf_mexico",            "GET /api/drift/case_01")
att = get("/api/attribution/case_01_gulf_mexico",      "GET /api/attribution/case_01")
get("/api/attribution/case_04_malacca_strait",         "GET /api/attribution/case_04")
get("/api/drift/case_01_gulf_mexico/forward-prediction","GET /api/drift/forward-prediction")
get("/api/drift/case_01_gulf_mexico/combined",          "GET /api/drift/combined")

# ── Data shape spot-checks ─────────────────────────────────────────────────────
print("\n── Data shape checks ──")

if det:
    ok = all(k in det for k in ("polygon_geojson","centroid_lat","centroid_lon","detection_confidence"))
    print(f"  {'OK  ' if ok else 'FAIL'} detection has required fields")
    if not ok: errors.append("detection shape")

if dft:
    ok = all(k in dft for k in ("most_probable_origin_lat","spatial_uncertainty_km","ellipses","sample_trajectories"))
    print(f"  {'OK  ' if ok else 'FAIL'} drift has required fields")
    if not ok: errors.append("drift shape")

if att and isinstance(att, list) and len(att) > 0:
    v = att[0]
    ok = all(k in v for k in ("mmsi","vessel_name","overall_score","priority_tier","sub_scores","waypoints"))
    print(f"  {'OK  ' if ok else 'FAIL'} attribution[0] has required fields (mmsi={v.get('mmsi','?')})")
    # Check if risk profile field exists in response (may be null if DB empty)
    has_rp_field = "general_risk_profile" in v
    rp_val = v.get("general_risk_profile")
    print(f"  {'OK  ' if has_rp_field else 'MISS'} attribution[0] has general_risk_profile field "
          f"({'null — no AIS history in DB' if rp_val is None else rp_val.get('risk_level','?')})")
    if not has_rp_field:
        errors.append("attribution missing general_risk_profile field")
    if not ok: errors.append("attribution shape")

# ── Result ─────────────────────────────────────────────────────────────────────
print()
print("=" * 60)
if errors:
    print(f"FAILED — {len(errors)} issue(s):")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("ALL CHECKS PASSED")
print("=" * 60)
