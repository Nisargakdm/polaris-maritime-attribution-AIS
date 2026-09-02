"""
Bug-fix verification script for POLARIS dashboard.
Run from project root with server already running on port 8765.
"""
import urllib.request, json, sys
BASE = "http://127.0.0.1:8765"
errors = []

def ok(label): print(f"  OK   {label}")
def fail(label, reason=""):
    print(f"  FAIL {label}{': ' + reason if reason else ''}")
    errors.append(label)

def get_json(path):
    with urllib.request.urlopen(BASE + path, timeout=15) as r:
        return json.loads(r.read().decode())

def get_text(path):
    with urllib.request.urlopen(BASE + path, timeout=10) as r:
        return r.read().decode()

print("\n── Bug 1: Evidence Graph ──────────────────────────────────")
# New dedicated endpoint must exist and return real data
try:
    g = get_json("/api/cases/case_01_gulf_mexico/evidence-graph")
    nodes = g.get("nodes", [])
    edges = g.get("edges", [])
    if len(nodes) >= 4:
        ok(f"GET /api/cases/.../evidence-graph: {len(nodes)} nodes, {len(edges)} edges")
    else:
        fail("evidence-graph node count too low", f"got {len(nodes)}")
    # Check expected node types
    types = {n["node_type"] for n in nodes}
    for expected in ["SATELLITE", "SPILL", "DRIFT", "ORIGIN", "VESSEL"]:
        if expected in types:
            ok(f"  node_type={expected} present")
        else:
            fail(f"  node_type={expected} missing")
    # Check edges have confidence
    if edges and "confidence" in edges[0]:
        ok(f"  edges have confidence field (sample: {edges[0]['confidence']})")
    else:
        fail("  edges missing confidence")
except Exception as e:
    fail("GET /api/cases/.../evidence-graph", str(e))

# JS must use new endpoint, not /api/report/
js = get_text("/static/js/app.js")
if "cases/${currentCaseId}/evidence-graph" in js:
    ok("app.js openGraphModal fetches /api/cases/.../evidence-graph")
else:
    fail("app.js openGraphModal still fetches old endpoint")

# JS must NOT use classList.add('hidden') for modals
bad_patterns = [
    'modal-graph").classList.add("hidden")',
    'modal-report").classList.add("hidden")',
    'modal-weights").classList.add("hidden")',
]
for bp in bad_patterns:
    if bp in js:
        fail(f"app.js still uses classList.add hidden: {bp[:50]}")
    else:
        ok(f"app.js: no stale classList.add hidden ({bp[:30]}...)")

# Modals must use polaris-modal class, not hidden+flex
html = get_text("/")
for modal_id in ("modal-graph", "modal-report", "modal-weights"):
    if f'id="{modal_id}" class="polaris-modal"' in html:
        ok(f"  {modal_id} uses polaris-modal class")
    else:
        fail(f"  {modal_id} NOT using polaris-modal class")

# CSS must define polaris-modal
css = get_text("/static/css/styles.css")
if ".polaris-modal" in css and 'data-open="true"' in css:
    ok("styles.css defines .polaris-modal with data-open pattern")
else:
    fail("styles.css missing .polaris-modal or data-open rule")

print("\n── Bug 2/3: Sidebar scroll fix ────────────────────────────")
if "#sidebar-left" in css and "overflow-y: auto" in css:
    ok("styles.css: #sidebar-left has overflow-y:auto")
else:
    fail("styles.css: #sidebar-left overflow-y:auto missing")
if "#sidebar-right" in css and "overflow-y: auto" in css:
    ok("styles.css: #sidebar-right has overflow-y:auto")
else:
    fail("styles.css: #sidebar-right overflow-y:auto missing")
if "min-height: 0" in css:
    ok("styles.css: min-height:0 present for flex scroll guard")
else:
    fail("styles.css: min-height:0 missing")

print("\n── Bug 4: Map layer overlay scroll ────────────────────────")
if 'id="map-layer-panel"' in html:
    ok("index.html: map-layer-panel id present")
else:
    fail("index.html: map-layer-panel id missing")
if "#map-layer-panel" in css:
    ok("styles.css: #map-layer-panel rule present")
else:
    fail("styles.css: #map-layer-panel rule missing")

print("\n── Bug 5: Root layout – no page scroll ────────────────────")
if "html, body" in css and "overflow: hidden" in css:
    ok("styles.css: html,body overflow:hidden")
else:
    fail("styles.css: html,body overflow:hidden missing")
if "#content-row" in css and "min-height: 0" in css:
    ok("styles.css: #content-row has min-height:0")
else:
    fail("styles.css: #content-row min-height:0 missing")

print("\n── Bug 6: Font size floor ─────────────────────────────────")
if "font-size: 13px" in css:
    ok("styles.css: body font-size bumped to 13px")
else:
    fail("styles.css: body font-size 13px missing")
if ".text-xs" in css and "12px" in css:
    ok("styles.css: text-xs floor at 12px")
else:
    fail("styles.css: text-xs 12px floor missing")
if r".text-\[10px\]" in css and "11px" in css:
    ok("styles.css: text-[10px] floor at 11px")
else:
    fail(r"styles.css: .text-\[10px\] floor missing")

print("\n── Existing tests still pass ──────────────────────────────")
try:
    cases = get_json("/api/cases")
    ok(f"GET /api/cases: {len(cases)} cases")
    det = get_json("/api/detection/case_01_gulf_mexico")
    ok(f"GET /api/detection: confidence={det['detection_confidence']:.2f}")
    dft = get_json("/api/drift/case_01_gulf_mexico")
    ok(f"GET /api/drift: origin=({dft['most_probable_origin_lat']:.3f},{dft['most_probable_origin_lon']:.3f})")
    att = get_json("/api/attribution/case_01_gulf_mexico")
    ok(f"GET /api/attribution: {len(att)} candidates, top score={att[0]['overall_score']:.2f}")
    g4 = get_json("/api/cases/case_04_malacca_strait/evidence-graph")
    ok(f"GET /api/cases/case_04/evidence-graph: {len(g4['nodes'])} nodes")
except Exception as e:
    fail("regression check", str(e))

print()
print("=" * 60)
if errors:
    print(f"FAILED — {len(errors)} issue(s):")
    for e in errors: print(f"  - {e}")
    sys.exit(1)
else:
    print("ALL BUG-FIX CHECKS PASSED")
print("=" * 60)
