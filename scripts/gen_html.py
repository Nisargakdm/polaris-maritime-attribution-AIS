from pathlib import Path

content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>POLARIS — Probabilistic Maritime Pollution Attribution Engine</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        navy: { 900: '#0b1329', 800: '#111e38', 700: '#1e2e4f', 600: '#2b3f66' },
                        slate: { 850: '#172033', 950: '#0a0f1d' },
                        ocean: { 500: '#0ea5e9', 600: '#0284c7' }
                    }
                }
            }
        }
    </script>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <link rel="stylesheet" href="/static/css/styles.css">
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col font-sans overflow-hidden select-none">
    <header class="bg-navy-900 border-b border-slate-800 px-4 py-2.5 flex items-center justify-between z-30 shrink-0">
        <div class="flex items-center space-x-3">
            <div class="flex items-center justify-center w-8 h-8 rounded bg-ocean-600/20 border border-ocean-500/40 text-ocean-400">
                <i data-lucide="compass" class="w-5 h-5"></i>
            </div>
            <div>
                <div class="flex items-center space-x-2">
                    <span class="font-bold tracking-wider text-base text-slate-100">POLARIS</span>
                    <span class="text-[10px] uppercase tracking-widest px-1.5 py-0.5 rounded bg-ocean-500/10 text-ocean-400 border border-ocean-500/20 font-semibold">Attribution Engine</span>
                </div>
                <p class="text-[11px] text-slate-400">Probabilistic Maritime Pollution Decision Support &bull; SIH26143</p>
            </div>
        </div>
        <div class="flex items-center space-x-3">
            <div class="flex items-center space-x-2 bg-navy-800/80 border border-slate-700/60 rounded px-3 py-1.5 shadow-sm">
                <i data-lucide="folder-git-2" class="w-4 h-4 text-ocean-400"></i>
                <span class="text-xs text-slate-400 font-medium">Case:</span>
                <select id="case-selector" class="bg-transparent text-xs text-slate-200 font-semibold focus:outline-none cursor-pointer pr-2">
                    <option value="case_01_gulf_mexico">Case 1: Gulf of Mexico (NOAA Benchmark)</option>
                    <option value="case_02_ennore_india">Case 2: Ennore Port / Coromandel Coast (INCOIS Advisory)</option>
                    <option value="case_03_synthetic_eval">Case 3: Arabian Sea Ground-Truth Evaluation</option>
                </select>
            </div>
            <div class="hidden md:flex items-center space-x-1 text-xs px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>SAR Engine Active</span>
            </div>
        </div>
        <div class="flex items-center space-x-2">
            <button id="btn-open-weights" class="flex items-center space-x-1.5 text-xs bg-navy-800 hover:bg-navy-700 border border-slate-700 px-3 py-1.5 rounded transition text-slate-200" title="Configure Attribution Weights">
                <i data-lucide="sliders" class="w-3.5 h-3.5 text-slate-300"></i>
                <span>Scoring Weights</span>
            </button>
            <button id="btn-open-report" class="flex items-center space-x-1.5 text-xs bg-ocean-600 hover:bg-ocean-500 text-white font-medium px-3.5 py-1.5 rounded shadow transition" title="View Full Investigation Dossier">
                <i data-lucide="file-text" class="w-3.5 h-3.5"></i>
                <span>Investigation Brief</span>
            </button>
        </div>
    </header>

    <div class="bg-navy-900/90 border-b border-amber-500/20 px-4 py-1 flex items-center justify-between text-[11px] text-amber-300/90 z-20 shrink-0">
        <div class="flex items-center space-x-1.5 truncate">
            <i data-lucide="shield-alert" class="w-3.5 h-3.5 text-amber-400 shrink-0"></i>
            <span class="font-semibold uppercase tracking-wider text-[10px] text-amber-400">Forensic Decision Support:</span>
            <span class="truncate">This platform provides probabilistic investigative leads based on available satellite, drift physics, and AIS telemetry. It does not constitute definitive proof of legal liability.</span>
        </div>
        <div class="hidden lg:flex items-center space-x-2 text-[10px] text-slate-400 shrink-0 ml-4">
            <span id="provenance-hash-display" class="font-mono text-slate-500 truncate max-w-xs">SHA-256: calculating...</span>
        </div>
    </div>

    <div class="flex-1 flex overflow-hidden relative">
        <aside class="w-80 bg-navy-900/95 border-r border-slate-800 flex flex-col z-10 shrink-0 overflow-y-auto custom-scroll text-xs">
            <div class="p-3 border-b border-slate-800/80">
                <h3 class="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2 flex items-center justify-between">
                    <span>Attribution Workflow</span>
                    <span class="text-[10px] text-emerald-400">6/6 COMPLETE</span>
                </h3>
                <div class="space-y-1.5 text-[11px]">
                    <div class="flex items-center justify-between text-slate-300">
                        <span class="flex items-center space-x-1.5"><i data-lucide="check-circle-2" class="w-3.5 h-3.5 text-emerald-400"></i><span>1. Sentinel-1 SAR Preprocessing</span></span>
                        <span class="text-[10px] text-slate-500">Lee Filter</span>
                    </div>
                    <div class="flex items-center justify-between text-slate-300">
                        <span class="flex items-center space-x-1.5"><i data-lucide="check-circle-2" class="w-3.5 h-3.5 text-emerald-400"></i><span>2. U-Net 5-Class Segmentation</span></span>
                        <span class="text-[10px] text-emerald-400 font-mono" id="meta-oil-prob">84.2%</span>
                    </div>
                    <div class="flex items-center justify-between text-slate-300">
                        <span class="flex items-center space-x-1.5"><i data-lucide="check-circle-2" class="w-3.5 h-3.5 text-emerald-400"></i><span>3. GeoJSON Polygon Vectorization</span></span>
                        <span class="text-[10px] text-slate-400 font-mono" id="meta-spill-area">14.8 km²</span>
                    </div>
                    <div class="flex items-center justify-between text-slate-300">
                        <span class="flex items-center space-x-1.5"><i data-lucide="check-circle-2" class="w-3.5 h-3.5 text-emerald-400"></i><span>4. Lagrangian Backward Drift</span></span>
                        <span class="text-[10px] text-slate-400 font-mono">-48.0h</span>
                    </div>
                    <div class="flex items-center justify-between text-slate-300">
                        <span class="flex items-center space-x-1.5"><i data-lucide="check-circle-2" class="w-3.5 h-3.5 text-emerald-400"></i><span>5. AIS Spatiotemporal Correlation</span></span>
                        <span class="text-[10px] text-slate-400 font-mono" id="meta-candidate-count">5 Ships</span>
                    </div>
                    <div class="flex items-center justify-between text-slate-300">
                        <span class="flex items-center space-x-1.5"><i data-lucide="check-circle-2" class="w-3.5 h-3.5 text-emerald-400"></i><span>6. Explainable Weighted Scoring</span></span>
                        <span class="text-[10px] text-emerald-400 font-semibold">Ranked</span>
                    </div>
                </div>
            </div>

            <div class="p-3 border-b border-slate-800/80 space-y-2">
                <h3 class="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between">
                    <span>Satellite SAR Evidence</span>
                    <span id="meta-mission" class="text-ocean-400 font-mono text-[10px]">Sentinel-1A</span>
                </h3>
                <div class="bg-navy-800/60 rounded p-2 border border-slate-800 space-y-1.5">
                    <div class="flex justify-between text-slate-300"><span class="text-slate-400">Acquisition UTC:</span><span id="meta-acq-time" class="font-mono text-slate-200">2026-04-18 06:30</span></div>
                    <div class="flex justify-between text-slate-300"><span class="text-slate-400">Observed Centroid:</span><span id="meta-centroid" class="font-mono text-slate-200">28.380°N, -89.150°E</span></div>
                    <div class="flex justify-between text-slate-300"><span class="text-slate-400">Surface Extent:</span><span id="meta-extent" class="font-mono text-slate-200">14.85 km²</span></div>
                    <div class="flex justify-between text-slate-300"><span class="text-slate-400">Detection Confidence:</span><span id="meta-confidence" class="font-mono text-emerald-400 font-bold">88.4%</span></div>
                    <div class="flex justify-between text-slate-300"><span class="text-slate-400">Look-alike Probability:</span><span id="meta-lookalike" class="font-mono text-slate-400">9.1% (Low)</span></div>
                    <div class="flex justify-between text-slate-300"><span class="text-slate-400">Backscatter SNR:</span><span id="meta-snr" class="font-mono text-slate-300">12.4 dB</span></div>
                </div>
            </div>

            <div class="p-3 border-b border-slate-800/80 space-y-2">
                <h3 class="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between">
                    <span>Ocean Drift & Uncertainty</span>
                    <span class="text-ocean-400 text-[10px]">CMEMS + ERA5</span>
                </h3>
                <div class="bg-navy-800/60 rounded p-2 border border-slate-800 space-y-1.5">
                    <div class="flex justify-between text-slate-300"><span class="text-slate-400">Probable Origin:</span><span id="meta-origin-coord" class="font-mono text-slate-200">28.182°N, -89.418°E</span></div>
                    <div class="flex justify-between text-slate-300"><span class="text-slate-400">Estimated Window:</span><span id="meta-origin-window" class="font-mono text-slate-200">14:00 – 19:30 UTC</span></div>
                    <div class="flex justify-between text-slate-300"><span class="text-slate-400">Spatial Uncertainty:</span><span id="meta-spatial-unc" class="font-mono text-amber-400 font-semibold">±14.2 km</span></div>
                    <div class="flex justify-between text-slate-300"><span class="text-slate-400">Surface Currents:</span><span id="meta-currents" class="font-mono text-slate-300">0.28 m/s (CMEMS)</span></div>
                    <div class="flex justify-between text-slate-300"><span class="text-slate-400">10m Wind Forcing:</span><span id="meta-winds" class="font-mono text-slate-300">4.9 m/s (ERA5)</span></div>
                </div>
            </div>

            <div class="p-3 space-y-1.5 mt-auto">
                <h4 class="text-[10px] font-bold uppercase tracking-wider text-slate-400">AIS Data Source & Limitations</h4>
                <p id="meta-ais-statement" class="text-[11px] text-slate-400 leading-relaxed bg-navy-800/40 p-2 rounded border border-slate-800">
                    Source: NOAA MarineCadastre US Waters benchmark data. Unrestricted public domain access.
                </p>
            </div>
        </aside>

        <main class="flex-1 flex flex-col relative bg-slate-950">
            <div class="absolute top-3 left-3 z-10 flex flex-col space-y-2">
                <div class="bg-navy-900/90 backdrop-blur border border-slate-700/80 rounded shadow-lg p-2 text-xs space-y-1.5">
                    <div class="font-semibold text-slate-300 text-[10px] uppercase tracking-wider mb-1 flex items-center justify-between">
                        <span>Map Layers</span>
                        <i data-lucide="layers" class="w-3 h-3 text-slate-400"></i>
                    </div>
                    <label class="flex items-center space-x-2 text-slate-200 cursor-pointer hover:text-white">
                        <input type="checkbox" id="layer-spill" checked class="rounded border-slate-700 text-ocean-600 focus:ring-0">
                        <span>Observed Spill Polygon</span>
                    </label>
                    <label class="flex items-center space-x-2 text-slate-200 cursor-pointer hover:text-white">
                        <input type="checkbox" id="layer-origin-heat" checked class="rounded border-slate-700 text-ocean-600 focus:ring-0">
                        <span>Origin Probability Heatmap</span>
                    </label>
                    <label class="flex items-center space-x-2 text-slate-200 cursor-pointer hover:text-white">
                        <input type="checkbox" id="layer-ellipses" checked class="rounded border-slate-700 text-ocean-600 focus:ring-0">
                        <span>Uncertainty Ellipses (95%)</span>
                    </label>
                    <label class="flex items-center space-x-2 text-slate-200 cursor-pointer hover:text-white">
                        <input type="checkbox" id="layer-particles" checked class="rounded border-slate-700 text-ocean-600 focus:ring-0">
                        <span>Drift Hindcast Particles</span>
                    </label>
                    <label class="flex items-center space-x-2 text-slate-200 cursor-pointer hover:text-white">
                        <input type="checkbox" id="layer-ais-tracks" checked class="rounded border-slate-700 text-ocean-600 focus:ring-0">
                        <span>AIS Vessel Trajectories</span>
                    </label>
                </div>
                <div class="flex space-x-1 bg-navy-900/90 backdrop-blur border border-slate-700/80 rounded p-1 shadow-lg">
                    <button id="btn-fit-spill" class="px-2 py-1 bg-navy-800 hover:bg-navy-700 rounded text-[11px] text-slate-200 font-medium transition">Spill</button>
                    <button id="btn-fit-origin" class="px-2 py-1 bg-navy-800 hover:bg-navy-700 rounded text-[11px] text-slate-200 font-medium transition">Origin</button>
                    <button id="btn-fit-all" class="px-2 py-1 bg-navy-800 hover:bg-navy-700 rounded text-[11px] text-slate-200 font-medium transition">All</button>
                </div>
            </div>

            <div class="absolute bottom-16 left-3 z-10 bg-navy-900/90 backdrop-blur border border-slate-700/80 rounded shadow-lg p-2.5 text-[11px] space-y-1">
                <div class="font-bold text-[10px] uppercase tracking-wider text-slate-400 mb-1">GIS Legend</div>
                <div class="flex items-center space-x-2"><span class="w-3 h-3 rounded bg-red-900/80 border border-red-500"></span><span class="text-slate-300">Observed Spill Polygon</span></div>
                <div class="flex items-center space-x-2"><span class="w-3 h-3 rounded bg-amber-500/50 border border-amber-400"></span><span class="text-slate-300">Probable Origin Zone</span></div>
                <div class="flex items-center space-x-2"><span class="w-3 h-1 bg-cyan-400"></span><span class="text-slate-300">Backward Particle Path</span></div>
                <div class="flex items-center space-x-2"><span class="w-3 h-1 bg-red-400"></span><span class="text-slate-300">High-Priority Vessel Track</span></div>
                <div class="flex items-center space-x-2"><span class="w-3 h-1 bg-slate-500"></span><span class="text-slate-300">Normal Vessel Track</span></div>
            </div>

            <div id="gis-map" class="flex-1 w-full h-full z-0"></div>

            <div class="bg-navy-900 border-t border-slate-800 px-4 py-2 flex items-center space-x-4 z-10 shrink-0">
                <div class="flex items-center space-x-2">
                    <button id="btn-play-pause" class="w-8 h-8 rounded bg-ocean-600 hover:bg-ocean-500 text-white flex items-center justify-center transition shadow">
                        <i data-lucide="play" class="w-4 h-4" id="play-icon"></i>
                    </button>
                    <button id="btn-step-back" class="w-7 h-7 rounded bg-navy-800 hover:bg-navy-700 text-slate-300 flex items-center justify-center transition"><i data-lucide="skip-back" class="w-3.5 h-3.5"></i></button>
                    <button id="btn-step-forward" class="w-7 h-7 rounded bg-navy-800 hover:bg-navy-700 text-slate-300 flex items-center justify-center transition"><i data-lucide="skip-forward" class="w-3.5 h-3.5"></i></button>
                </div>
                <div class="flex-1 flex flex-col space-y-1">
                    <div class="flex justify-between items-center text-[11px]">
                        <span class="font-mono text-slate-400">-48.0h (Hindcast Start)</span>
                        <span id="timeline-current-label" class="font-mono font-bold text-ocean-400 bg-ocean-500/10 px-2 py-0.5 rounded border border-ocean-500/20">T - 0.0h (Observation)</span>
                        <span class="font-mono text-slate-400">T 0.0h (Observation)</span>
                    </div>
                    <input type="range" id="timeline-slider" min="-48" max="0" step="0.5" value="0" class="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-ocean-500">
                </div>
                <div class="flex items-center space-x-1 text-xs">
                    <span class="text-[10px] text-slate-400">Speed:</span>
                    <button id="btn-speed-1x" class="px-2 py-0.5 rounded bg-ocean-600/30 text-ocean-300 border border-ocean-500/40 text-[10px] font-bold">1x</button>
                    <button id="btn-speed-2x" class="px-2 py-0.5 rounded bg-navy-800 hover:bg-navy-700 text-slate-300 text-[10px]">2x</button>
                </div>
            </div>
        </main>

        <aside class="w-96 bg-navy-900/95 border-l border-slate-800 flex flex-col z-10 shrink-0 overflow-y-auto custom-scroll text-xs">
            <div class="p-3 border-b border-slate-800">
                <div class="flex items-center justify-between mb-1">
                    <h3 class="text-[11px] font-bold uppercase tracking-wider text-slate-300 flex items-center space-x-1.5">
                        <i data-lucide="ship" class="w-4 h-4 text-ocean-400"></i>
                        <span>Candidate Vessel Shortlist</span>
                    </h3>
                    <span class="text-[10px] text-slate-400" id="candidate-header-count">5 Vessels</span>
                </div>
                <p class="text-[11px] text-slate-400">Ranked by spatial, temporal, trajectory, and behavioral compatibility.</p>
            </div>

            <div class="p-2 border-b border-slate-800">
                <div class="space-y-1.5" id="candidate-list-container"></div>
            </div>

            <div class="p-3 flex-1 space-y-3" id="evidence-panel-container">
                <div class="flex items-center justify-between border-b border-slate-800 pb-2">
                    <div>
                        <span class="text-[10px] font-bold uppercase tracking-wider text-ocean-400">Active Candidate Profile</span>
                        <h4 id="detail-vessel-name" class="text-sm font-bold text-slate-100">MT GULF VOYAGER</h4>
                    </div>
                    <span id="detail-priority-badge" class="px-2 py-0.5 rounded text-[10px] font-bold bg-red-500/20 text-red-400 border border-red-500/30">HIGH PRIORITY</span>
                </div>

                <div class="grid grid-cols-2 gap-2 bg-navy-800/60 p-2.5 rounded border border-slate-800 text-[11px]">
                    <div><span class="text-slate-400 block text-[10px]">MMSI / IMO</span><span id="detail-mmsi-imo" class="font-mono text-slate-200">367184920 / 9421882</span></div>
                    <div><span class="text-slate-400 block text-[10px]">Vessel Type</span><span id="detail-vessel-type" class="text-slate-200">Oil / Chemical Tanker</span></div>
                    <div><span class="text-slate-400 block text-[10px]">Flag State</span><span id="detail-flag" class="text-slate-200">United States [US]</span></div>
                    <div><span class="text-slate-400 block text-[10px]">Closest Approach (CPA)</span><span id="detail-cpa" class="font-mono text-amber-400 font-semibold">2.4 km</span></div>
                </div>

                <div class="space-y-2">
                    <h5 class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Compatibility Sub-Scores</h5>
                    <div class="space-y-1.5 text-[11px]">
                        <div>
                            <div class="flex justify-between text-slate-300 mb-0.5"><span>Spatial Proximity</span><span id="score-spatial-val" class="font-mono">92%</span></div>
                            <div class="w-full bg-slate-800 rounded-full h-1.5"><div id="score-spatial-bar" class="bg-ocean-500 h-1.5 rounded-full" style="width: 92%"></div></div>
                        </div>
                        <div>
                            <div class="flex justify-between text-slate-300 mb-0.5"><span>Temporal Overlap</span><span id="score-temporal-val" class="font-mono">88%</span></div>
                            <div class="w-full bg-slate-800 rounded-full h-1.5"><div id="score-temporal-bar" class="bg-ocean-500 h-1.5 rounded-full" style="width: 88%"></div></div>
                        </div>
                        <div>
                            <div class="flex justify-between text-slate-300 mb-0.5"><span>Trajectory Drift Consistency</span><span id="score-traj-val" class="font-mono">95%</span></div>
                            <div class="w-full bg-slate-800 rounded-full h-1.5"><div id="score-traj-bar" class="bg-emerald-500 h-1.5 rounded-full" style="width: 95%"></div></div>
                        </div>
                        <div>
                            <div class="flex justify-between text-slate-300 mb-0.5"><span>Behavioral Anomaly Index</span><span id="score-anom-val" class="font-mono text-amber-400">65%</span></div>
                            <div class="w-full bg-slate-800 rounded-full h-1.5"><div id="score-anom-bar" class="bg-amber-500 h-1.5 rounded-full" style="width: 65%"></div></div>
                        </div>
                        <div>
                            <div class="flex justify-between text-slate-300 mb-0.5"><span>Vessel / Cargo Compatibility</span><span id="score-type-val" class="font-mono">95%</span></div>
                            <div class="w-full bg-slate-800 rounded-full h-1.5"><div id="score-type-bar" class="bg-ocean-500 h-1.5 rounded-full" style="width: 95%"></div></div>
                        </div>
                    </div>
                </div>

                <div class="space-y-1.5">
                    <h5 class="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-1"><i data-lucide="help-circle" class="w-3 h-3 text-ocean-400"></i><span>Key Evidentiary Points</span></h5>
                    <ul id="detail-evidence-list" class="space-y-1 text-[11px] text-slate-300 bg-navy-800/40 p-2.5 rounded border border-slate-800 list-disc list-inside"></ul>
                </div>

                <div class="space-y-1.5">
                    <h5 class="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-1"><i data-lucide="alert-triangle" class="w-3 h-3 text-amber-400"></i><span>Detected Anomaly Signatures</span></h5>
                    <div id="detail-anomaly-container" class="space-y-1"></div>
                </div>

                <div class="pt-2 border-t border-slate-800 space-y-2">
                    <h5 class="text-[10px] font-bold uppercase tracking-wider text-slate-400">Analyst Review Actions</h5>
                    <div class="flex space-x-2">
                        <button id="btn-flag-candidate" class="flex-1 py-1.5 px-2 bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded text-[11px] font-medium transition flex items-center justify-center space-x-1"><i data-lucide="flag" class="w-3 h-3"></i><span>Flag Lead</span></button>
                        <button id="btn-exclude-candidate" class="flex-1 py-1.5 px-2 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded text-[11px] font-medium transition flex items-center justify-center space-x-1"><i data-lucide="user-x" class="w-3 h-3"></i><span>Exclude</span></button>
                    </div>
                </div>
            </div>
        </aside>
    </div>

    <!-- Modal: Scoring Weight Customizer -->
    <div id="modal-weights" class="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 hidden flex items-center justify-center p-4">
        <div class="bg-navy-900 border border-slate-700 rounded-lg shadow-2xl max-w-md w-full p-5 space-y-4">
            <div class="flex items-center justify-between border-b border-slate-800 pb-3">
                <div class="flex items-center space-x-2">
                    <i data-lucide="sliders" class="w-4 h-4 text-ocean-400"></i>
                    <h3 class="font-bold text-slate-100 text-sm">Attribution Scoring Weights</h3>
                </div>
                <button id="btn-close-weights" class="text-slate-400 hover:text-white"><i data-lucide="x" class="w-4 h-4"></i></button>
            </div>
            <p class="text-xs text-slate-400">Adjust the relative influence of physical, temporal, and behavioral parameters.</p>
            <div class="space-y-3 text-xs">
                <div>
                    <div class="flex justify-between text-slate-300 mb-1"><span>Spatial Proximity (w1)</span><span id="slider-val-spatial" class="font-mono text-ocean-400">0.30</span></div>
                    <input type="range" id="slider-weight-spatial" min="0.0" max="1.0" step="0.05" value="0.30" class="w-full h-1.5 bg-slate-700 rounded appearance-none accent-ocean-500">
                </div>
                <div>
                    <div class="flex justify-between text-slate-300 mb-1"><span>Temporal Overlap (w2)</span><span id="slider-val-temporal" class="font-mono text-ocean-400">0.25</span></div>
                    <input type="range" id="slider-weight-temporal" min="0.0" max="1.0" step="0.05" value="0.25" class="w-full h-1.5 bg-slate-700 rounded appearance-none accent-ocean-500">
                </div>
                <div>
                    <div class="flex justify-between text-slate-300 mb-1"><span>Trajectory Alignment (w3)</span><span id="slider-val-trajectory" class="font-mono text-ocean-400">0.20</span></div>
                    <input type="range" id="slider-weight-trajectory" min="0.0" max="1.0" step="0.05" value="0.20" class="w-full h-1.5 bg-slate-700 rounded appearance-none accent-ocean-500">
                </div>
                <div>
                    <div class="flex justify-between text-slate-300 mb-1"><span>Behavioral Anomaly (w4)</span><span id="slider-val-anomaly" class="font-mono text-ocean-400">0.15</span></div>
                    <input type="range" id="slider-weight-anomaly" min="0.0" max="1.0" step="0.05" value="0.15" class="w-full h-1.5 bg-slate-700 rounded appearance-none accent-ocean-500">
                </div>
                <div>
                    <div class="flex justify-between text-slate-300 mb-1"><span>Vessel Type (w5)</span><span id="slider-val-type" class="font-mono text-ocean-400">0.10</span></div>
                    <input type="range" id="slider-weight-type" min="0.0" max="1.0" step="0.05" value="0.10" class="w-full h-1.5 bg-slate-700 rounded appearance-none accent-ocean-500">
                </div>
                <div>
                    <div class="flex justify-between text-slate-300 mb-1"><span>AIS Silence Gap Penalty</span><span id="slider-val-gap" class="font-mono text-red-400">0.10</span></div>
                    <input type="range" id="slider-weight-gap" min="0.0" max="0.30" step="0.05" value="0.10" class="w-full h-1.5 bg-slate-700 rounded appearance-none accent-red-500">
                </div>
            </div>
            <div class="flex justify-end space-x-2 pt-2 border-t border-slate-800">
                <button id="btn-reset-weights" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs">Reset Defaults</button>
                <button id="btn-apply-weights" class="px-4 py-1.5 bg-ocean-600 hover:bg-ocean-500 text-white rounded text-xs font-semibold">Apply & Recompute</button>
            </div>
        </div>
    </div>

    <!-- Modal: Full Investigation Dossier -->
    <div id="modal-report" class="fixed inset-0 bg-slate-950/85 backdrop-blur-md z-50 hidden flex items-center justify-center p-6">
        <div class="bg-navy-900 border border-slate-700 rounded-lg shadow-2xl max-w-3xl w-full max-h-[85vh] flex flex-col">
            <div class="p-4 border-b border-slate-800 flex items-center justify-between shrink-0">
                <div class="flex items-center space-x-2">
                    <i data-lucide="file-check" class="w-5 h-5 text-ocean-400"></i>
                    <div>
                        <h3 class="font-bold text-slate-100 text-sm">Maritime Pollution Investigation Brief</h3>
                        <p class="text-[10px] text-slate-400 font-mono" id="modal-report-hash">SHA-256: calculating...</p>
                    </div>
                </div>
                <div class="flex items-center space-x-2">
                    <button id="btn-copy-markdown" class="px-2.5 py-1 bg-navy-800 hover:bg-navy-700 border border-slate-700 rounded text-xs text-slate-300 flex items-center space-x-1"><i data-lucide="copy" class="w-3.5 h-3.5"></i><span>Copy Markdown</span></button>
                    <button id="btn-close-report" class="text-slate-400 hover:text-white p-1"><i data-lucide="x" class="w-5 h-5"></i></button>
                </div>
            </div>
            <div class="p-6 overflow-y-auto custom-scroll text-slate-200 text-xs leading-relaxed space-y-4 font-mono select-text whitespace-pre-wrap" id="report-content-body"></div>
            <div class="p-3 border-t border-slate-800 bg-navy-950 flex justify-between items-center text-[10px] text-slate-400 shrink-0">
                <span>POLARIS Automated Forensic Intelligence Export</span>
                <span class="text-amber-400/90 font-semibold">Strict Decision Support Only &bull; Not Final Adjudication</span>
            </div>
        </div>
    </div>

    <script src="/static/js/app.js"></script>
</body>
</html>
"""

Path("backend/app/static/index.html").write_text(content, encoding="utf-8")
print("Written backend/app/static/index.html successfully!")
