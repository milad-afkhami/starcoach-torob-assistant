"""Private CSV build manifests fail before touching an existing catalogue."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest


@pytest.mark.parametrize('change', [{'archive_sha256': '0' * 64}, {'compression': 'xz'}])
def test_source_manifest_mismatch_preserves_catalogue_before_import(tmp_path, change):
    root = Path(__file__).parents[1]
    source = tmp_path / 'source.zip'
    source.write_bytes(b'private fixture bytes')
    manifest = tmp_path / 'source.json'
    manifest.write_text(json.dumps({'compression': 'zip', 'archive_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), **change}))
    target = tmp_path / 'catalogue.sqlite'
    target.write_bytes(b'previous accepted database')
    result = subprocess.run([
        sys.executable, str(root / 'scripts/build_catalogue.py'), '--archive', str(source),
        '--source-manifest', str(manifest), '--output', str(target), '--manifest', str(tmp_path / 'report.json'),
    ], env={**os.environ, 'PYTHONPATH': str(root / 'backend')}, capture_output=True, text=True)
    assert result.returncode != 0
    assert 'Source ZIP manifest/hash mismatch' in result.stderr
    assert target.read_bytes() == b'previous accepted database'
    assert not (tmp_path / 'report.json').exists()
