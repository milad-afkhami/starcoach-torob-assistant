"""Restore the complete private catalogue during image build, with bounded memory."""

import argparse
import hashlib
import json
import lzma
import os
import resource
from pathlib import Path

CHUNK = 1024 * 1024
DECODER_MEMORY_LIMIT = 64 * 1024 * 1024
MAX_CATALOGUE_BYTES = 1024 * 1024 * 1024


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def restore(source: Path, manifest_path: Path, destination: Path):
    source, manifest_path, destination = Path(source), Path(manifest_path), Path(destination)
    value = json.loads(manifest_path.read_text())
    size = value.get("uncompressed_bytes")
    if value.get("compression") != "xz" or type(size) is not int or not 0 < size <= MAX_CATALOGUE_BYTES:
        raise ValueError("Invalid bounded catalogue manifest")
    if digest(source) != value.get("compressed_sha256"):
        raise ValueError("Compressed catalogue hash mismatch")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + f".partial-{os.getpid()}")
    actual_size, checksum = 0, hashlib.sha256()
    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_XZ, memlimit=DECODER_MEMORY_LIMIT)
    try:
        with source.open("rb") as incoming, temporary.open("xb") as output:
            while not decoder.eof:
                chunk = incoming.read(CHUNK) if decoder.needs_input else b""
                if decoder.needs_input and not chunk:
                    raise ValueError("Truncated catalogue archive")
                data = decoder.decompress(chunk, max_length=CHUNK)
                actual_size += len(data)
                if actual_size > size:
                    raise ValueError("Restored catalogue exceeds manifest size")
                checksum.update(data)
                output.write(data)
            if decoder.unused_data or incoming.read(1):
                raise ValueError("Unexpected trailing catalogue bytes")
        if actual_size != size or checksum.hexdigest() != value.get("uncompressed_sha256"):
            raise ValueError("Restored catalogue size/hash mismatch")
        temporary.chmod(0o444)
        temporary.replace(destination)
    except lzma.LZMAError as error:
        raise ValueError("Invalid or excessive-memory catalogue archive") from error
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "uncompressed_bytes": actual_size,
        "sha256": checksum.hexdigest(),
        "compressed_sha256": value["compressed_sha256"],
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(restore(args.source, args.manifest, args.output), indent=2))
