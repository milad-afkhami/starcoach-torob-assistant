"""The build-stage database must be byte-identical or fail without replacing it."""

import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import pytest


def module():
    spec = importlib.util.spec_from_file_location(
        "unpack_catalogue", Path(__file__).parents[1] / "scripts/unpack_catalogue.py"
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def payload(tmp_path, data=b"complete SQLite bytes" * 1000):
    source = tmp_path / "catalogue.sqlite.xz"
    compressed = lzma.compress(data, preset=6)
    source.write_bytes(compressed)
    manifest = tmp_path / "catalogue-build.json"
    value = {
        "compression": "xz",
        "uncompressed_bytes": len(data),
        "uncompressed_sha256": hashlib.sha256(data).hexdigest(),
        "compressed_sha256": hashlib.sha256(compressed).hexdigest(),
    }
    manifest.write_text(json.dumps(value))
    return source, manifest, value


def test_streaming_restore_exact_hash_and_no_partial_artifact(tmp_path):
    source, manifest, value = payload(tmp_path)
    target = tmp_path / "restored.sqlite"
    result = module().restore(source, manifest, target)
    assert target.read_bytes() == b"complete SQLite bytes" * 1000
    assert result["sha256"] == value["uncompressed_sha256"]
    assert target.stat().st_mode & 0o777 == 0o444
    assert not list(tmp_path.glob("*.partial*"))


@pytest.mark.parametrize("fault", ["compressed_hash", "uncompressed_hash", "truncated", "trailing", "size"])
def test_corruption_cannot_replace_existing_database(tmp_path, fault):
    source, manifest, value = payload(tmp_path)
    if fault == "compressed_hash":
        source.write_bytes(source.read_bytes() + b"corrupt")
    elif fault == "uncompressed_hash":
        value["uncompressed_sha256"] = "0" * 64
    elif fault == "truncated":
        source.write_bytes(source.read_bytes()[:-5])
        value["compressed_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    elif fault == "trailing":
        source.write_bytes(source.read_bytes() + b"garbage")
        value["compressed_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    elif fault == "size":
        value["uncompressed_bytes"] -= 1
    manifest.write_text(json.dumps(value))
    target = tmp_path / "restored.sqlite"
    target.write_bytes(b"keep existing")
    with pytest.raises(ValueError):
        module().restore(source, manifest, target)
    assert target.read_bytes() == b"keep existing"
    assert not list(tmp_path.glob("*.partial*"))
