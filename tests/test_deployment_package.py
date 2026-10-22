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
        assert set(archive.getnames()) == {
            "Dockerfile",
            "requirements.lock",
            "backend/torob/api.py",
            "frontend/dist/index.html",
            "data/catalogue.sqlite",
        }


def test_bundle_rejects_symlink_and_missing_frontend(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    for name in ["Dockerfile", "requirements.lock", "backend/torob/api.py", "data/catalogue.sqlite"]:
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("fixture")
    with pytest.raises(ValueError):
        module().package(root, tmp_path / "out.tar.gz")
    (root / "frontend/dist").mkdir(parents=True)
    (root / "frontend/dist/index.html").symlink_to(root / ".env")
    with pytest.raises(ValueError):
        module().package(root, tmp_path / "out.tar.gz")
