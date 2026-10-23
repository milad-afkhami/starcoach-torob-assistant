"""Build a private, size-bounded source upload with the complete compressed catalogue."""

import argparse
import hashlib
import json
import lzma
import os
import tarfile
from pathlib import Path

MAX_SOURCE_BYTES = 128_000_000  # Conservative decimal bound for Liara's reported128MB limit.
CHUNK = 1024 * 1024


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def prepare_catalogue(root: Path):
    source = root / "data/catalogue.sqlite"
    compressed = root / "data/catalogue.sqlite.xz"
    manifest = root / "data/catalogue-build.json"
    for path in (source, compressed, manifest):
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("Symlinks are not deployment inputs")
    source_hash, size = digest(source), source.stat().st_size
    if compressed.is_file() and manifest.is_file():
        try:
            saved = json.loads(manifest.read_text())
            if (
                saved.get("compression") == "xz"
                and saved.get("uncompressed_sha256") == source_hash
                and saved.get("uncompressed_bytes") == size
                and saved.get("compressed_sha256") == digest(compressed)
            ):
                return saved
        except (ValueError, OSError):
            pass
    temporary = compressed.with_name(compressed.name + ".partial")
    actual_hash = hashlib.sha256()
    try:
        with source.open("rb") as incoming, lzma.open(temporary, "wb", preset=6) as output:
            temporary.chmod(0o600)
            for chunk in iter(lambda: incoming.read(CHUNK), b""):
                actual_hash.update(chunk)
                output.write(chunk)
        if actual_hash.hexdigest() != source_hash or source.stat().st_size != size:
            raise ValueError("Catalogue changed during compression")
        value = {
            "compression": "xz",
            "xz_preset": 6,
            "uncompressed_bytes": size,
            "uncompressed_sha256": source_hash,
            "compressed_sha256": digest(temporary),
            "compressed_bytes": temporary.stat().st_size,
        }
        temporary.replace(compressed)
        manifest.write_text(json.dumps(value, indent=2) + "\n")
        manifest.chmod(0o600)
        return value
    finally:
        temporary.unlink(missing_ok=True)


def package(root: Path, destination: Path, *, max_source_bytes=MAX_SOURCE_BYTES):
    root = root.resolve()
    required = [
        "Dockerfile",
        "requirements.lock",
        "scripts/unpack_catalogue.py",
        "scripts/container_entrypoint.py",
        "data/catalogue.sqlite",
        "frontend/dist/index.html",
    ]
    files = [root / name for name in required]
    files.extend((root / "backend/torob").glob("*.py"))
    files.extend(p for p in (root / "frontend/dist").rglob("*") if not p.is_dir())
    if any(not p.is_file() for p in files) or not any((root / "backend/torob").glob("*.py")):
        raise ValueError("Build frontend/catalogue and lock dependencies before packaging")
    files = sorted(set(files))
    for path in files:
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("Symlinks are not deployment inputs")
    catalogue = prepare_catalogue(root)
    files.remove(root / "data/catalogue.sqlite")
    files.extend(root / name for name in ("data/catalogue.sqlite.xz", "data/catalogue-build.json"))
    files = sorted(files)
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
        if temporary.stat().st_size > max_source_bytes:
            raise ValueError(f"Private source exceeds upload limit of{max_source_bytes}bytes")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "artifact": str(destination.resolve()),
        "bytes": destination.stat().st_size,
        "sha256": digest(destination),
        "members": [str(p.relative_to(root)) for p in files],
        "private_catalogue_included": True,
        "credentials_included": False,
        "max_source_bytes": max_source_bytes,
        "catalogue": catalogue,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/deployment-xz.tar.gz"))
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    report = package(args.root, args.output)
    Path("docs/qa-evidence/deployment-artifact.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "members"}, indent=2))
