import os
from pathlib import Path

static_dir = Path("backend/app/static")
css_dir = static_dir / "css"
js_dir = static_dir / "js"
css_dir.mkdir(parents=True, exist_ok=True)
js_dir.mkdir(parents=True, exist_ok=True)

print("Directories verified:", static_dir)
