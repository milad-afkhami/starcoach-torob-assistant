import importlib.util
import io
import hashlib
import sys
from pathlib import Path
import pytest
from catalogue_fixtures import archive
from torob import ingest


def module():
    sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "download_catalogue_test", Path(__file__).parents[1] / "scripts/download_catalogue.py"
    )
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class Response(io.BytesIO):
    status = 200

    def __init__(self, data, url, length):
        super().__init__(data)
        self.url = url
        self.headers = {"Content-Length": str(length)}

    def geturl(self):
        return self.url


def fixture(tmp_path, monkeypatch):
    import zipfile

    m = module()
    source = archive(tmp_path)
    data = source.read_bytes()
    with zipfile.ZipFile(source) as z:
        hashes = {n: hashlib.sha256(z.read(n)).hexdigest() for n in ingest.KNOWN_HASHES}
    monkeypatch.setattr(ingest, "KNOWN_HASHES", hashes)
    monkeypatch.setattr(m, "KNOWN_HASHES", hashes)
    monkeypatch.setattr(m, "ARCHIVE_SHA256", hashlib.sha256(data).hexdigest())
    monkeypatch.setattr(m, "ARCHIVE_BYTES", len(data))
    return m, data


def test_exact_pinned_stream_preserves_payload_and_uses_no_auth(tmp_path, monkeypatch):
    m, data = fixture(tmp_path, monkeypatch)
    calls = []

    def opener(request, timeout):
        calls.append(request)
        return Response(data, m.SOURCE_URL, len(data))

    out = tmp_path / "download.zip"
    result = m.download(out, opener=opener)
    assert out.read_bytes() == data and out.stat().st_mode & 0o777 == 0o600
    assert calls[0].full_url == m.SOURCE_URL
    assert not {"authorization", "cookie", "proxy-authorization"} & {k.lower() for k in calls[0].headers}
    assert result["archive_sha256"] == hashlib.sha256(data).hexdigest()


@pytest.mark.parametrize("kind", ["wrong_hash", "truncated", "oversize", "redirect", "status"])
def test_invalid_transfer_preserves_old_archive_and_removes_temporary(tmp_path, monkeypatch, kind):
    m, data = fixture(tmp_path, monkeypatch)
    out = tmp_path / "download.zip"
    out.write_bytes(b"accepted old")
    body = data[:-1] if kind == "truncated" else data + b"x" if kind == "oversize" else data
    if kind == "wrong_hash":
        monkeypatch.setattr(m, "ARCHIVE_SHA256", "0" * 64)

    def opener(request, timeout):
        response = Response(body, "https://example.com/" if kind == "redirect" else m.SOURCE_URL, len(body))
        if kind == "status":
            response.status = 503
        return response

    with pytest.raises(ValueError):
        m.download(out, opener=opener)
    assert out.read_bytes() == b"accepted old"
    assert not list(tmp_path.glob(".download.zip.*.tmp"))


def test_symlink_destination_refused_without_network(tmp_path, monkeypatch):
    m, _ = fixture(tmp_path, monkeypatch)
    secret = tmp_path / "secret"
    secret.write_bytes(b"keep")
    out = tmp_path / "download.zip"
    out.symlink_to(secret)
    with pytest.raises(ValueError):
        m.download(out, opener=lambda *_: pytest.fail("network must not start"))
    assert secret.read_bytes() == b"keep"
