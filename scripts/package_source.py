"""Package source, fixtures, prompts and reports, excluding all local secrets/databases."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT.parent / "India-Company-Compliance-Backend-v0.1.0.zip"
EXCLUDED = {".local", ".venv", "__pycache__", ".pytest_cache", ".git", "build", "dist"}
files = []
for path in ROOT.rglob("*"):
    if not path.is_file():
        continue
    relative = path.relative_to(ROOT)
    if any(part in EXCLUDED or part.endswith(".egg-info") for part in relative.parts):
        continue
    if path.name in {".env", ".coverage", "http-smoke-server.log"} or path.suffix in {".pyc", ".sqlite3"}:
        continue
    if ".sqlite3-" in path.name or path.name == "credentials.json":
        continue
    files.append(path)
files.sort()
manifest = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in files:
        archive.write(path, ROOT.name + "/" + path.relative_to(ROOT).as_posix())
    archive.writestr(ROOT.name + "/SOURCE-SHA256.json", json.dumps(manifest, indent=2))
with zipfile.ZipFile(OUTPUT) as archive:
    assert archive.testzip() is None
    for name, sha in manifest.items():
        data = archive.read(ROOT.name + "/" + name)
        assert hashlib.sha256(data).hexdigest() == sha
        if name.endswith(".py"):
            compile(data, name, "exec")
        if name.endswith(".json"):
            json.loads(data)
print(json.dumps({"file": str(OUTPUT), "files": len(files) + 1, "bytes": OUTPUT.stat().st_size,
                  "sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest()}))
