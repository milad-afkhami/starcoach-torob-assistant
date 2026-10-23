"""Private upload bundles must never scoop up development secrets or state."""

import importlib.util
import tarfile
from pathlib import Path
import pytest


def module():
    path = Path(__file__).parents[1] / "scripts/package_deployment.py"
    spec = importlib.util.spec_from_file_location("package_deployment", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_bundle_contains_only_allowlisted_runtime_inputs(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    for name in [
        "Dockerfile",
        "requirements.lock",
        "scripts/unpack_catalogue.py",
        "scripts/container_entrypoint.py",
        "backend/torob/api.py",
        "frontend/dist/index.html",
        "data/catalogue.sqlite",
        ".env",
        "data/state.sqlite",
        "backend/torob/__pycache__/secret.pyc",
        "frontend/src/secret.ts",
    ]:
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("fixture")
    out = tmp_path / "upload.tar.gz"
    module().package(root, out)
    with tarfile.open(out) as archive:
        import lzma
        import json
        import hashlib

        raw = archive.extractfile("data/catalogue.sqlite.xz").read()
        assert lzma.decompress(raw) == b"fixture"
        manifest = json.load(archive.extractfile("data/catalogue-build.json"))
        assert manifest["uncompressed_sha256"] == hashlib.sha256(b"fixture").hexdigest()
        assert manifest["uncompressed_bytes"] == 7
        assert set(archive.getnames()) == {
            "Dockerfile",
            "requirements.lock",
            "backend/torob/api.py",
            "frontend/dist/index.html",
            "data/catalogue.sqlite.xz",
            "data/catalogue-build.json",
            "scripts/unpack_catalogue.py",
            "scripts/container_entrypoint.py",
        }


def test_bundle_rejects_symlink_and_missing_frontend(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    for name in [
        "Dockerfile",
        "requirements.lock",
        "backend/torob/api.py",
        "scripts/unpack_catalogue.py",
        "scripts/container_entrypoint.py",
        "data/catalogue.sqlite",
        ".env",
    ]:
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("fixture")
    with pytest.raises(ValueError):
        module().package(root, tmp_path / "out.tar.gz")
    (root / "frontend/dist").mkdir(parents=True)
    (root / "frontend/dist/index.html").symlink_to(root / ".env")
    with pytest.raises(ValueError, match="Symlinks"):
        module().package(root, tmp_path / "out.tar.gz")


def test_package_reports_exact_restored_catalogue_and_enforces_source_limit(tmp_path):
    root = tmp_path / "repo"
    for name in [
        "Dockerfile",
        "requirements.lock",
        "backend/torob/api.py",
        "scripts/unpack_catalogue.py",
        "scripts/container_entrypoint.py",
        "data/catalogue.sqlite",
        "frontend/dist/index.html",
    ]:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"bounded complete payload" * 100)
    result = module().package(root, tmp_path / "upload.tar.gz")
    assert result["catalogue"]["uncompressed_bytes"] == 2400
    assert result["catalogue"]["compression"] == "xz"
    assert result["max_source_bytes"] == 128_000_000
    assert result["bytes"] < 128_000_000
    with pytest.raises(ValueError, match="source.*limit"):
        module().package(root, tmp_path / "too-small.tar.gz", max_source_bytes=10)
    assert not (tmp_path / "too-small.tar.gz").exists()


def test_compressed_cache_is_revalidated_and_source_change_is_never_hidden(tmp_path):
    import lzma
    import hashlib

    root = tmp_path / "repo"
    for name in [
        "Dockerfile",
        "requirements.lock",
        "backend/torob/api.py",
        "scripts/unpack_catalogue.py",
        "scripts/container_entrypoint.py",
        "data/catalogue.sqlite",
        "frontend/dist/index.html",
    ]:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"original payload")
    out = tmp_path / "upload.tar.gz"
    module().package(root, out)
    cached = root / "data/catalogue.sqlite.xz"
    cached.write_bytes(b"corrupt cache")
    repaired = module().package(root, out)
    assert lzma.decompress(cached.read_bytes()) == b"original payload"
    assert repaired["catalogue"]["uncompressed_sha256"] == hashlib.sha256(b"original payload").hexdigest()
    (root / "data/catalogue.sqlite").write_bytes(b"changed complete payload")
    updated = module().package(root, out)
    assert (
        updated["catalogue"]["uncompressed_sha256"] == hashlib.sha256(b"changed complete payload").hexdigest()
    )
    assert lzma.decompress(cached.read_bytes()) == b"changed complete payload"
