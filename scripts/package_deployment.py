"""Build a private Liara source-upload artifact from an explicit runtime allowlist."""

import argparse
import hashlib
import json
import os
import tarfile
from pathlib import Path


def package(root: Path, destination: Path):
    root = root.resolve()
    required = ["Dockerfile", "requirements.lock", "data/catalogue.sqlite", "frontend/dist/index.html"]
    files = [root / name for name in required]
    files.extend((root / "backend/torob").glob("*.py"))
    files.extend(p for p in (root / "frontend/dist").rglob("*") if not p.is_dir())
    if any(not p.is_file() for p in files) or not any((root / "backend/torob").glob("*.py")):
        raise ValueError("Build frontend/catalogue and lock dependencies before packaging")
    files = sorted(set(files))
    for path in files:
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("Symlinks are not deployment inputs")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".partial")
    try:
        with temporary.open("wb") as output:
            os.chmod(temporary, 0o600)
            with tarfile.open(fileobj=output, mode="w:gz") as archive:
                for path in files:
                    info = archive.gettarinfo(str(path), arcname=str(path.relative_to(root)))
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mode = 0o644
                    with path.open("rb") as source:
                        archive.addfile(info, source)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "artifact": str(destination.resolve()),
        "bytes": destination.stat().st_size,
        "sha256": hashlib.file_digest(destination.open("rb"), "sha256").hexdigest(),
        "members": [str(p.relative_to(root)) for p in files],
        "private_catalogue_included": True,
        "credentials_included": False,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=Path("data/deployment.tar.gz"))
    p.add_argument("--root", type=Path, default=Path("."))
    a = p.parse_args()
    report = package(a.root, a.output)
    Path("docs/qa-evidence/deployment-artifact.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "members"}, indent=2))
