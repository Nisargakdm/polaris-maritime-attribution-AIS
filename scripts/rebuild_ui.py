import re

with open(r'd:\Test\polaris-maritime-attribution\backend\app\static\index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Expand Dashboard Width
html = html.replace('class="w-80 bg-navy-900 border-r', 'class="w-[32%] bg-navy-900 border-r')

# 2. Rename Left Sidebar original sections
html = html.replace('<span>Investigation Workflow</span>', '<span>INVESTIGATION</span>')
html = html.replace('<span>Satellite Detection Evidence</span>', '<span>SATELLITE DATA</span>')
html = html.replace('<span>Ocean Drift & Hydrodynamics</span>', '<span>ANALYSIS</span>')

# 3. Extract MAP LAYERS overlays from the map and prepare them for insertion
map_layers_match = re.search(r'<div class="absolute top-3 left-3 z-10 flex flex-col space-y-2 max-w-xs">(.*?)<div class="flex items-center space-x-1 bg-navy-900', html, re.DOTALL)
if not map_layers_match:
    print("Could not find map layers")
    exit(1)
map_layers_content = map_layers_match.group(1)

# Remove the map_layers absolute block from the map
html = html.replace(map_layers_content, '')
# Also remove the wrapper
html = html.replace('<div class="absolute top-3 left-3 z-10 flex flex-col space-y-2 max-w-xs">\n                \n                <div class="flex items-center space-x-1 bg-navy-900', '<div class="absolute top-3 left-3 z-10 flex items-center space-x-1 bg-navy-900')

# Also extract GIS Symbology from map
symbology_match = re.search(r'<div class="absolute bottom-16 left-3 z-10 bg-navy-900/90 backdrop-blur-md border border-navy-700/80 rounded-lg shadow-xl p-2.5 text-\[10px\] space-y-1">(.*?)</div>\s*<div class="absolute bottom-16 right-3', html, re.DOTALL)
symbology_content = symbology_match.group(1)

# Remove the symbology block
html = re.sub(r'<div class="absolute bottom-16 left-3 z-10 bg-navy-900/90 backdrop-blur-md border border-navy-700/80 rounded-lg shadow-xl p-2.5 text-\[10px\] space-y-1">.*?</div>\s*<div class="absolute bottom-16 right-3', '<div class="absolute bottom-16 right-3', html, flags=re.DOTALL)

# Format MAP LAYERS for sidebar
map_layers_sidebar = """
            <div class="p-3 border-b border-navy-700/50 space-y-2">
                <div class="accordion-header cursor-pointer select-none font-bold text-slate-300 text-[10px] uppercase tracking-wider mb-1 flex items-center justify-between" onclick="toggleAccordion('map-layers')">
                    <span>MAP LAYERS</span>
                    <div class="flex items-center">
                        <i data-lucide="layers" class="w-3 h-3 text-cyan-400 mr-2"></i>
                        <span class="text-cyan-400 text-[10px] toggle-icon" id="icon-map-layers">▼</span>
                    </div>
                </div>
                <div id="content-map-layers" class="accordion-content hidden space-y-2 mt-2">
                    <div>
                        <div class="font-bold text-[9px] uppercase tracking-wider text-slate-400 mb-1">Basemap Style</div>
                        <div class="grid grid-cols-2 gap-1 text-[10px]">
                            <button id="btn-basemap-dark" class="px-2 py-1 rounded bg-ocean-600/30 text-ocean-300 border border-ocean-500/50 font-semibold transition">Tactical Dark</button>
                            <button id="btn-basemap-sat" class="px-2 py-1 rounded bg-navy-850 hover:bg-navy-750 text-slate-300 border border-navy-700 transition">Satellite</button>
                            <button id="btn-basemap-topo" class="px-2 py-1 rounded bg-navy-850 hover:bg-navy-750 text-slate-300 border border-navy-700 transition">Ocean Topo</button>
                            <button id="btn-basemap-light" class="px-2 py-1 rounded bg-navy-850 hover:bg-navy-750 text-slate-300 border border-navy-700 transition">Light Marine</button>
                        </div>
                    </div>
                    <div>
                        <div class="font-bold text-[9px] uppercase tracking-wider text-slate-400 mb-1 mt-2">Forensic Layers</div>
                        <label class="flex items-center space-x-2 text-slate-200 cursor-pointer hover:text-white"><input type="checkbox" id="layer-spill" checked class="rounded border-slate-700 text-ocean-600 focus:ring-0"><span>Observed Spill Polygon</span></label>
                        <label class="flex items-center space-x-2 text-slate-200 cursor-pointer hover:text-white"><input type="checkbox" id="layer-origin-heat" checked class="rounded border-slate-700 text-ocean-600 focus:ring-0"><span>Origin Probability Heatmap</span></label>
                        <label class="flex items-center space-x-2 text-slate-200 cursor-pointer hover:text-white"><input type="checkbox" id="layer-contours" checked class="rounded border-slate-700 text-ocean-600 focus:ring-0"><span class="text-cyan-300">Bathymetric Contours (50-2000m)</span></label>
                        <label class="flex items-center space-x-2 text-slate-200 cursor-pointer hover:text-white"><input type="checkbox" id="layer-current-vectors" checked class="rounded border-slate-700 text-ocean-600 focus:ring-0"><span class="text-cyan-300">Ocean Current Streamlines</span></label>
                        <label class="flex items-center space-x-2 text-slate-200 cursor-pointer hover:text-white"><input type="checkbox" id="layer-ellipses" checked class="rounded border-slate-700 text-ocean-600 focus:ring-0"><span>Uncertainty Ellipses (95%)</span></label>
                        <label class="flex items-center space-x-2 text-slate-200 cursor-pointer hover:text-white"><input type="checkbox" id="layer-prob-rings" checked class="rounded border-slate-700 text-ocean-600 focus:ring-0"><span>Iso-Probability Rings (75-95%)</span></label>
                        <label class="flex items-center space-x-2 text-slate-200 cursor-pointer hover:text-white"><input type="checkbox" id="layer-particles" checked class="rounded border-slate-700 text-ocean-600 focus:ring-0"><span>Lagrangian Drift Particles</span></label>
                        <label class="flex items-center space-x-2 text-slate-200 cursor-pointer hover:text-white"><input type="checkbox" id="layer-ais-tracks" checked class="rounded border-slate-700 text-ocean-600 focus:ring-0"><span>AIS Vessel Trajectories</span></label>
                    </div>
                    <div>
                        <div class="font-bold text-[9px] uppercase tracking-wider text-slate-400 mb-1 mt-2">GIS Symbology</div>
                        <div class="flex items-center space-x-2"><span class="w-3 h-3 rounded bg-red-900/80 border border-red-500"></span><span class="text-slate-300">Observed Oil Slick</span></div>
                        <div class="flex items-center space-x-2"><span class="w-3 h-3 rounded bg-amber-500/50 border border-amber-400"></span><span class="text-slate-300">Probable Origin Zone</span></div>
                        <div class="flex items-center space-x-2"><span class="w-3 h-0.5 bg-cyan-400"></span><span class="text-slate-300">Depth Contour (Isobath)</span></div>
                        <div class="flex items-center space-x-2"><span class="w-3 h-0.5 bg-red-400"></span><span class="text-slate-300">High-Priority Vessel Track</span></div>
                        <div class="flex items-center space-x-2"><span class="w-3 h-0.5 bg-slate-500"></span><span class="text-slate-300">Normal Vessel Track</span></div>
                    </div>
                </div>
            </div>
"""

# 4. Extract Right Sidebar
right_sidebar_match = re.search(r'<!-- Right Sidebar -->(.*?)</div>\s*<div id="modal-weights"', html, re.DOTALL)
right_sidebar = right_sidebar_match.group(1)

# Remove Right Sidebar completely
html = re.sub(r'\s*<!-- Right Sidebar -->.*?</div>\s*<div id="modal-weights"', '\n    </div>\n    <div id="modal-weights"', html, flags=re.DOTALL)

# Modify Right Sidebar to become VESSEL & AIS and ALERTS
vessel_ais = right_sidebar.replace('<aside class="w-96 bg-navy-900 border-l border-navy-700/50 flex flex-col z-10 shrink-0 overflow-y-auto custom-scroll text-xs">', '')
vessel_ais = vessel_ais.replace('<span>Candidate Shortlist</span>', '<span>VESSEL & AIS</span>')

# Extract ALERTS
alerts_match = re.search(r'(<div class="space-y-1\.5">\s*<h5 class="accordion-header.*?Kinematic Anomaly Signatures.*?</div>\s*</div>\s*</div>\s*<div class="pt-2 border-t.*?Analyst Review Actions.*?</div>\s*</div>)', vessel_ais, re.DOTALL)
alerts_content = alerts_match.group(1)

# Remove ALERTS from vessel_ais
vessel_ais = vessel_ais.replace(alerts_content, '')
# Note: we need to wrap ALERTS properly
alerts_sidebar = alerts_content.replace('<span>Kinematic Anomaly Signatures</span>', '<span>ALERTS</span>')
alerts_sidebar = f'''
            <div class="p-3 border-b border-navy-700/50 space-y-2">
{alerts_sidebar}
            </div>
'''

# 5. Inject everything into the Left Sidebar
# Find the insertion point (before AIS Source & Coverage)
insertion_point = r'            <div class="p-3 space-y-1\.5 mt-auto">'
replacement = f'''{vessel_ais}{map_layers_sidebar}{alerts_sidebar}
            <div class="p-3 space-y-1.5 mt-auto">'''

html = re.sub(insertion_point, replacement, html)

with open(r'd:\Test\polaris-maritime-attribution\backend\app\static\index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Done")
