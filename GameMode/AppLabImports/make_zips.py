"""Build Arduino App Lab import zips for the App Lab apps in this folder.

Each zip holds one app folder (app.yaml at <AppName>/app.yaml), which is the
layout App Lab's Import app accepts. Private files (.studio with access code,
Claude key and conversations) are never included.

Run from anywhere:  python make_zips.py
"""

import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECTS = HERE.parent
SKIP = {".studio", "__pycache__", ".cache", ".git", "highscores.json"}

for app in sorted(PROJECTS.iterdir()):
    if not (app / "app.yaml").is_file():
        continue
    target = HERE / f"{app.name}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(app.rglob("*")):
            rel = f.relative_to(app)
            if f.is_file() and not SKIP.intersection(rel.parts) and f.name not in (".gitignore", "highscores.json"):
                z.write(f, f.relative_to(PROJECTS).as_posix())
    print(f"{target.name}: {len(z.namelist())} files")
