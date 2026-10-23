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


def csv_repo(tmp_path):
    root = tmp_path / 'repo'
    for name, value in {
        'Dockerfile': 'XZBUILD', 'Dockerfile.csv-source': 'CSVBUILD',
        'requirements.lock': 'fixture', 'backend/torob/__init__.py': '',
        'backend/torob/ingest.py': 'fixture', 'backend/torob/normalize.py': 'fixture',
        'backend/torob/api.py': 'fixture', 'scripts/build_catalogue.py': 'fixture',
        'scripts/container_entrypoint.py': 'fixture', 'frontend/dist/index.html': 'frozen UI',
        '.env': 'SECRET', 'data/state.sqlite': 'PRIVATE', 'data/catalogue.sqlite': 'OLD_DB',
        'data/catalogue.sqlite.xz': 'OLD_XZ',
    }.items():
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(value)
    return root


def trusted_zip(tmp_path, monkeypatch):
    import hashlib
    import zipfile
    from catalogue_fixtures import archive
    from torob import ingest

    source = archive(tmp_path)
    with zipfile.ZipFile(source) as z:
        hashes = {name: hashlib.sha256(z.read(name)).hexdigest() for name in ingest.KNOWN_HASHES}
    monkeypatch.setattr(ingest, 'KNOWN_HASHES', hashes)
    return source, hashes


def test_csv_mode_keeps_complete_original_zip_and_only_private_allowlisted_inputs(tmp_path, monkeypatch):
    import hashlib
    import json

    root = csv_repo(tmp_path)
    source, hashes = trusted_zip(tmp_path, monkeypatch)
    out = tmp_path / 'csv-source.tar.gz'
    report = module().package(root, out, source_zip=source)
    with tarfile.open(out) as archive:
        assert archive.extractfile('Dockerfile').read() == b'CSVBUILD'
        assert archive.extractfile('data/catalogue-source.zip').read() == source.read_bytes()
        manifest = json.load(archive.extractfile('data/catalogue-source.json'))
        assert manifest['archive_sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
        assert manifest['payload_hashes'] == hashes
        assert set(archive.getnames()) == {
            'Dockerfile', 'requirements.lock', 'backend/torob/__init__.py',
            'backend/torob/ingest.py', 'backend/torob/normalize.py', 'backend/torob/api.py',
            'scripts/build_catalogue.py', 'scripts/container_entrypoint.py',
            'frontend/dist/index.html', 'data/catalogue-source.zip', 'data/catalogue-source.json',
        }
    assert report['catalogue']['compression'] == 'zip'
    assert report['bytes'] < 128_000_000
    assert out.stat().st_mode & 0o777 == 0o600
    assert (root / 'data/catalogue.sqlite').read_text() == 'OLD_DB'
    assert (root / 'data/catalogue.sqlite.xz').read_text() == 'OLD_XZ'


@pytest.mark.parametrize('kind', ['bad_hash', 'bad_zip', 'symlink_zip', 'symlink_parent', 'symlink_ui_dir'])
def test_csv_mode_rejects_untrusted_or_symlink_inputs_before_publishing(tmp_path, monkeypatch, kind):
    import zipfile

    root = csv_repo(tmp_path)
    source, _ = trusted_zip(tmp_path, monkeypatch)
    if kind == 'bad_hash':
        with zipfile.ZipFile(source) as z:
            contents = {name: z.read(name) for name in z.namelist()}
        with zipfile.ZipFile(source, 'w') as z:
            for name, data in contents.items():
                z.writestr(name, b'unexpected data' if name == 'products.csv' else data)
    elif kind == 'bad_zip':
        source.write_bytes(b'not a zip')
    elif kind == 'symlink_zip':
        link = tmp_path / 'linked.zip'
        link.symlink_to(source)
        source = link
    elif kind == 'symlink_parent':
        link = tmp_path / 'linked-dir'
        link.symlink_to(source.parent, target_is_directory=True)
        source = link / source.name
    elif kind == 'symlink_ui_dir':
        secret = root / 'private'
        secret.mkdir()
        (secret / 'secret.txt').write_text('SECRET')
        (root / 'frontend/dist/linked').symlink_to(secret, target_is_directory=True)
    out = tmp_path / 'new.tar.gz'
    with pytest.raises(ValueError):
        module().package(root, out, source_zip=source)
    assert not out.exists()


def test_csv_mode_size_failure_preserves_previous_artifact(tmp_path, monkeypatch):
    root = csv_repo(tmp_path)
    source, _ = trusted_zip(tmp_path, monkeypatch)
    out = tmp_path / 'new.tar.gz'
    out.write_bytes(b'previous accepted artifact')
    with pytest.raises(ValueError, match='source.*limit'):
        module().package(root, out, source_zip=source, max_source_bytes=10)
    assert out.read_bytes() == b'previous accepted artifact'
    assert not out.with_suffix('.gz.partial').exists()


def test_csv_change_during_tar_write_rejects_new_output_and_preserves_previous(tmp_path, monkeypatch):
    root = csv_repo(tmp_path)
    source, _ = trusted_zip(tmp_path, monkeypatch)
    original = tarfile.TarFile.addfile

    def mutate(archive, info, fileobj=None):
        original(archive, info, fileobj)
        if info.name == 'data/catalogue-source.zip':
            source.write_bytes(b'changed during write')

    monkeypatch.setattr(tarfile.TarFile, 'addfile', mutate)
    out = tmp_path / 'previous.tar.gz'
    out.write_bytes(b'accepted previous')
    with pytest.raises(ValueError, match='changed during packaging'):
        module().package(root, out, source_zip=source)
    assert out.read_bytes() == b'accepted previous'


@pytest.mark.parametrize('mode', ['zip', 'xz'])
def test_untrusted_predictable_partial_never_overwrites_its_target(tmp_path, monkeypatch, mode):
    root = csv_repo(tmp_path)
    (root / 'scripts/unpack_catalogue.py').write_text('fixture')
    source, _ = trusted_zip(tmp_path, monkeypatch)
    out = tmp_path / 'output.tar.gz'
    sentinel = tmp_path / 'outside-secret'
    sentinel.write_bytes(b'DO NOT OVERWRITE')
    out.with_suffix('.gz.partial').symlink_to(sentinel)
    module().package(root, out, **({'source_zip': source} if mode == 'zip' else {}))
    assert sentinel.read_bytes() == b'DO NOT OVERWRITE'
    assert out.is_file() and not out.is_symlink()


@pytest.mark.parametrize('mode', ['zip', 'xz'])
@pytest.mark.parametrize('kind', ['source', 'runtime', 'hardlink', 'symlink', 'parent_symlink'])
def test_destination_cannot_alias_any_input_before_cache_or_output_writes(tmp_path, monkeypatch, mode, kind):
    import os

    root = csv_repo(tmp_path)
    (root / 'scripts/unpack_catalogue.py').write_text('fixture')
    source, _ = trusted_zip(tmp_path, monkeypatch)
    target = source if mode == 'zip' else root / 'data/catalogue.sqlite'
    before_source = target.read_bytes()
    before_cache = (root / 'data/catalogue.sqlite.xz').read_bytes()
    before_api = (root / 'backend/torob/api.py').read_bytes()
    if kind == 'source':
        out = target
    elif kind == 'runtime':
        out = root / 'backend/torob/api.py'
    elif kind == 'hardlink':
        out = tmp_path / 'hardlinked-output'
        os.link(target, out)
    elif kind == 'symlink':
        out = tmp_path / 'linked-output'
        out.symlink_to(target)
    else:
        link = tmp_path / 'linked-parent'
        link.symlink_to(target.parent, target_is_directory=True)
        out = link / target.name
    with pytest.raises(ValueError):
        module().package(root, out, **({'source_zip': source} if mode == 'zip' else {}))
    assert target.read_bytes() == before_source
    assert (root / 'data/catalogue.sqlite.xz').read_bytes() == before_cache
    assert (root / 'backend/torob/api.py').read_bytes() == before_api


@pytest.mark.parametrize('mode', ['zip', 'xz'])
@pytest.mark.parametrize('kind', ['symlink', 'same_size_inplace', 'parent_swap'])
def test_runtime_input_identity_and_bytes_are_frozen_until_publish(tmp_path, monkeypatch, mode, kind):
    root = csv_repo(tmp_path)
    (root / 'scripts/unpack_catalogue.py').write_text('fixture')
    source, _ = trusted_zip(tmp_path, monkeypatch)
    api = root / 'backend/torob/api.py'
    sentinel = tmp_path / 'outside'
    sentinel.mkdir()
    for path in (root / 'backend/torob').glob('*.py'):
        (sentinel / path.name).write_bytes(b'SECRET!')
    original = tarfile.TarFile.addfile
    altered = False

    def swap(archive, info, fileobj=None):
        nonlocal altered
        if info.name == 'backend/torob/api.py' and not altered:
            altered = True
            if kind == 'symlink':
                api.unlink()
                api.symlink_to(sentinel / 'api.py')
            elif kind == 'same_size_inplace':
                api.write_bytes(b'SECRET!')
            else:
                parent = api.parent
                parent.rename(root / 'backend/old-torob')
                parent.symlink_to(sentinel, target_is_directory=True)
        original(archive, info, fileobj)

    monkeypatch.setattr(tarfile.TarFile, 'addfile', swap)
    out = tmp_path / 'output.tar.gz'
    out.write_bytes(b'previous accepted artifact')
    with pytest.raises(ValueError):
        module().package(root, out, **({'source_zip': source} if mode == 'zip' else {}))
    assert altered
    assert out.read_bytes() == b'previous accepted artifact'
    assert (sentinel / 'api.py').read_bytes() == b'SECRET!'


@pytest.mark.parametrize('mode', ['zip', 'xz'])
def test_exclusive_temp_collision_never_changes_preexisting_node_or_target(tmp_path, monkeypatch, mode):
    root = csv_repo(tmp_path)
    (root / 'scripts/unpack_catalogue.py').write_text('fixture')
    source, _ = trusted_zip(tmp_path, monkeypatch)
    packer = module()
    monkeypatch.setattr(packer.secrets, 'token_hex', lambda _: 'controlled-collision')
    out = tmp_path / 'output.tar.gz'
    out.write_bytes(b'previous accepted artifact')
    sentinel = tmp_path / 'sentinel'
    sentinel.write_bytes(b'private sentinel')
    collision = tmp_path / '.output.tar.gz.controlled-collision.tmp'
    collision.symlink_to(sentinel)
    with pytest.raises(ValueError):
        packer.package(root, out, **({'source_zip': source} if mode == 'zip' else {}))
    assert out.read_bytes() == b'previous accepted artifact'
    assert sentinel.read_bytes() == b'private sentinel'
    assert collision.is_symlink()


@pytest.mark.parametrize('name', ['catalogue.sqlite.xz', 'catalogue-build.json'])
def test_destination_alias_to_existing_xz_cache_is_rejected_before_regeneration(tmp_path, name):
    import os

    root = csv_repo(tmp_path)
    (root / 'scripts/unpack_catalogue.py').write_text('fixture')
    cache = root / 'data' / name
    cache.write_bytes(b'old invalid cache')
    out = tmp_path / 'hardlinked-output'
    os.link(cache, out)
    before = {p: p.read_bytes() for p in (root / 'data').iterdir()}
    with pytest.raises(ValueError):
        module().package(root, out)
    assert {p: p.read_bytes() for p in (root / 'data').iterdir()} == before


def test_cli_report_alias_is_rejected_before_any_package_or_cache_write(tmp_path):
    import subprocess
    import sys

    root = csv_repo(tmp_path)
    (root / 'scripts/unpack_catalogue.py').write_text('fixture')
    source = root / 'data/catalogue.sqlite'
    before = source.read_bytes()
    out = tmp_path / 'output.tar.gz'
    script = Path(__file__).parents[1] / 'scripts/package_deployment.py'
    result = subprocess.run([sys.executable, str(script), '--root', str(root), '--output', str(out), '--report', str(source)], capture_output=True, text=True)
    assert result.returncode != 0 and 'aliases' in result.stderr
    assert source.read_bytes() == before
    assert not out.exists()
    assert (root / 'data/catalogue.sqlite.xz').read_bytes() == b'OLD_XZ'


def test_remote_mode_is_small_explicit_and_has_no_catalogue_or_secrets(tmp_path, monkeypatch):
    import urllib.request
    root = csv_repo(tmp_path)
    (root / 'Dockerfile.remote-source').write_text('PINNED BUILD')
    (root / 'scripts/download_catalogue.py').write_text('pinned downloader')
    (root / 'scripts/package_deployment.py').write_text('safe writer')
    monkeypatch.setattr(urllib.request.OpenerDirector, 'open', lambda *_args, **_kwargs: pytest.fail('Packaging must not perform network requests'))
    out = tmp_path / 'remote.tar.gz'
    report = module().package(root, out, remote_source=True)
    with tarfile.open(out) as archive:
        names = archive.getnames()
        assert archive.extractfile('Dockerfile').read() == b'PINNED BUILD'
        assert not any(name.endswith(('.zip', '.sqlite', '.xz')) for name in names)
        assert '.env' not in names and 'data/state.sqlite' not in names
        assert 'scripts/download_catalogue.py' in names
        assert 'scripts/package_deployment.py' in names
    assert report['catalogue']['archive_sha256'] == 'b0afb47b2b70f65c6d8ec07b7423dcc49efc71cd7a27e95606fb81da008c210d'
    assert report['catalogue']['source_url'].startswith('https://startech.s3.ir-central1.arvanstorage.ir/')
    assert report['private_catalogue_included'] is False and report['complete_catalogue_build'] is True
    with pytest.raises(ValueError, match='one explicit'):
        module().package(root, out, remote_source=True, source_zip=tmp_path / 'other.zip')
