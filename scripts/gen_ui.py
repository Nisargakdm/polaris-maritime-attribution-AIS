from pathlib import Path
html_path = Path("backend/app/static/index.html")
js_path = Path("backend/app/static/js/app.js")
html_path.parent.mkdir(parents=True, exist_ok=True)
js_path.parent.mkdir(parents=True, exist_ok=True)
print("Ready to assemble UI files.")
