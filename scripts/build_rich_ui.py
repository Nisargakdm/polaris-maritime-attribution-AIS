from pathlib import Path

# 1. Enhanced styles.css
css_code = """/* POLARIS High-Tech Maritime Forensic GIS Dashboard */
@import url("https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap");

:root {
    --bg-dark: #070d1d;
    --card-bg: rgba(13, 23, 46, 0.95);
    --border-color: rgba(30, 47, 84, 0.85);
    --accent-cyan: #06b6d4;
    --accent-blue: #38bdf8;
    --accent-amber: #f59e0b;
    --accent-red: #ef4444;
    --accent-emerald: #10b981;
}

body {
    font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: radial-gradient(circle at 50% 0%, #0c1836 0%, #060b17 100%);
}

code, pre, .font-mono {
    font-family: "JetBrains Mono", monospace;
}

/* Custom Sleek Scrollbar */
.custom-scroll::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
.custom-scroll::-webkit-scrollbar-track {
    background: #070d1d;
}
.custom-scroll::-webkit-scrollbar-thumb {
    background: #1e2f54;
    border-radius: 4px;
}
.custom-scroll::-webkit-scrollbar-thumb:hover {
    background: #0284c7;
}

/* Glassmorphism & High-tech Borders */
.glass-panel {
    background: var(--card-bg);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--border-color);
}

.glow-border {
    box-shadow: 0 0 15px rgba(6, 182, 212, 0.15);
}

/* Leaflet Container & Overrides */
.leaflet-container {
    background: #050a14 !important;
    font-family: inherit;
}

.leaflet-control-zoom {
    border: 1px solid #1e2f54 !important;
    border-radius: 8px !important;
    overflow: hidden;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6) !important;
}

.leaflet-control-zoom a {
    background-color: #0d172e !important;
    color: #94a3b8 !important;
    border-bottom: 1px solid #1e2f54 !important;
}

.leaflet-control-zoom a:hover {
    background-color: #1e2f54 !important;
    color: #38bdf8 !important;
}

.leaflet-popup-content-wrapper {
    background: #0d172e !important;
    color: #f8fafc !important;
    border: 1px solid #1e2f54 !important;
    border-radius: 8px !important;
    box-shadow: 0 12px 30px rgba(0, 0, 0, 0.75) !important;
}

.leaflet-popup-tip {
    background: #0d172e !important;
    border: 1px solid #1e2f54 !important;
}

/* Vessel Markers */
.vessel-marker {
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.vessel-marker:hover {
    transform: scale(1.3);
    z-index: 1000 !important;
}

/* Origin Pulse Radar Effect */
.origin-pulse {
    animation: origin-beacon 2s infinite cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes origin-beacon {
    0% {
        box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.85);
    }
    70% {
        box-shadow: 0 0 0 20px rgba(245, 158, 11, 0);
    }
    100% {
        box-shadow: 0 0 0 0 rgba(245, 158, 11, 0);
    }
}

/* Flash Animation when Weights Apply */
.flash-update {
    animation: flash-highlight 1.2s ease-out;
}

@keyframes flash-highlight {
    0% {
        box-shadow: 0 0 0 4px rgba(6, 182, 212, 0.7);
        border-color: #06b6d4;
    }
    100% {
        box-shadow: none;
    }
}

/* Depth Contour Labels */
.contour-label {
    background: rgba(7, 13, 29, 0.85);
    border: 1px solid rgba(56, 189, 248, 0.3);
    color: #38bdf8;
    font-size: 9px;
    font-family: "JetBrains Mono", monospace;
    padding: 1px 4px;
    border-radius: 3px;
}

/* Current Vector Arrow Icon */
.current-arrow {
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0.65;
    transition: opacity 0.2s ease;
}
.current-arrow:hover {
    opacity: 1.0;
}
"""

Path("backend/app/static/css/styles.css").write_text(css_code, encoding="utf-8")
print("styles.css successfully updated with rich maritime theme!")