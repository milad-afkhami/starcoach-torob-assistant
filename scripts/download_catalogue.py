"""One pinned public organizer archive, fetched only during the private Docker build."""

import argparse
import hashlib
import json
import ssl
import time
import urllib.request
from pathlib import Path
from package_deployment import FrozenInput, atomic_output, guard_destination
from torob.ingest import KNOWN_HASHES, _members, _digest
import zipfile

SOURCE_URL = "https://startech.s3.ir-central1.arvanstorage.ir/starcoach-dataset-v16-cap300-csv.zip?versionId="
ARCHIVE_SHA256 = "b0afb47b2b70f65c6d8ec07b7423dcc49efc71cd7a27e95606fb81da008c210d"
ARCHIVE_BYTES = 60176276
MAX_SECONDS = 180


def source_manifest():
    return {
        "compression": "zip",
        "source_url": SOURCE_URL,
        "archive_sha256": ARCHIVE_SHA256,
        "compressed_bytes": ARCHIVE_BYTES,
        "payload_hashes": dict(KNOWN_HASHES),
        "expected_counts": {"shops": 6476, "products": 225903, "offers": 331506},
    }


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        raise ValueError("Organizer download redirect refused")


def download(destination, *, opener=None):
    if opener is None:
        client = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPSHandler(context=ssl.create_default_context()),
            NoRedirect(),
        )
        opener = client.open
    request = urllib.request.Request(
        SOURCE_URL, headers={"User-Agent": "TorobCatalogueBuild/1.0", "Accept": "application/zip"}
    )
    started = time.monotonic()
    checksum = hashlib.sha256()
    size = 0
    with atomic_output(destination, []) as output:
        with opener(request, timeout=15) as response:
            if response.status != 200 or response.geturl() != SOURCE_URL:
                raise ValueError("Organizer URL/status mismatch")
            length = response.headers.get("Content-Length")
            if length is not None and int(length) != ARCHIVE_BYTES:
                raise ValueError("Organizer archive length mismatch")
            while True:
                if time.monotonic() - started > MAX_SECONDS:
                    raise ValueError("Organizer download deadline exceeded")
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > ARCHIVE_BYTES:
                    raise ValueError("Organizer archive exceeds pinned size")
                checksum.update(chunk)
                output.write(chunk)
        if size != ARCHIVE_BYTES or checksum.hexdigest() != ARCHIVE_SHA256:
            raise ValueError("Organizer archive size/hash mismatch")
        output.flush()
        output.seek(0)
        with zipfile.ZipFile(output) as archive:
            for name, member in _members(archive).items():
                with archive.open(member) as incoming:
                    if _digest(incoming) != KNOWN_HASHES[name]:
                        raise ValueError("Organizer payload hash mismatch")
    return source_manifest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    guard_destination(args.manifest, [], [args.output])
    result = download(args.output)
    with FrozenInput(args.output) as source:
        with atomic_output(args.manifest, [source]) as output:
            output.write(json.dumps(result, indent=2).encode() + b"\n")
    print(json.dumps(result, indent=2))
