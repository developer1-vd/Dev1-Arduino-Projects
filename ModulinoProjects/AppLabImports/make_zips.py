"""Build Arduino App Lab import zips for every *App folder in ModulinoProjects.

App Lab's import expects app.yaml at archive.zip/app.yaml or
archive.zip/<root_dir>/app.yaml, so each zip holds one app folder:

    ButtonBuzzerLevelsApp.zip
      ButtonBuzzerLevelsApp/app.yaml
      ButtonBuzzerLevelsApp/sketch/sketch.ino
      ...

Run from anywhere:  python make_zips.py
"""

import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECTS = HERE.parent

for app in sorted(PROJECTS.glob("*App")):
    if not (app / "app.yaml").is_file():
        continue
    target = HERE / f"{app.name}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(app.rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts:
                z.write(f, f.relative_to(PROJECTS).as_posix())
    print(f"{target.name}: {len(z.namelist())} files")
