"""Private size-bounded source packages, read from frozen no-follow file descriptors."""

import argparse
import gzip
import hashlib
import io
import json
import lzma
import os
import secrets
import stat
import sys
import tarfile
import zipfile
from contextlib import ExitStack, contextmanager
from pathlib import Path

MAX_SOURCE_BYTES = 128_000_000
CHUNK = 1024 * 1024


def absolute(path):
    return Path(os.path.abspath(path))


def digest_handle(handle):
    handle.seek(0)
    value = hashlib.file_digest(handle, "sha256").hexdigest()
    handle.seek(0)
    return value


def digest(path):
    with FrozenInput(path) as source:
        return source.checksum


def directory(path, *, create=False):
    """Walk each parent with openat/O_NOFOLLOW; never resolve through a symlink."""
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    first = os.fstat(descriptor)
    chain = [(first.st_dev, first.st_ino)]
    try:
        for name in absolute(path).parts[1:]:
            if create:
                try:
                    os.mkdir(name, 0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
            info = os.fstat(descriptor)
            chain.append((info.st_dev, info.st_ino))
        return descriptor, chain
    except Exception:
        os.close(descriptor)
        raise


def regular(path):
    parent = None
    try:
        parent, chain = directory(path.parent)
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            os.close(descriptor)
            raise ValueError("Deployment inputs must be regular files")
        return os.fdopen(descriptor, "rb"), chain
    except OSError as error:
        raise ValueError("Symlinks or changed deployment input path") from error
    finally:
        if parent is not None:
            os.close(parent)


def identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mode, info.st_mtime_ns, info.st_ctime_ns)


class FrozenInput:
    def __init__(self, path):
        self.path = absolute(path)

    def __enter__(self):
        self.handle, self.parents = regular(self.path)
        try:
            self.info = os.fstat(self.handle.fileno())
            self.identity = identity(self.info)
            self.checksum = digest_handle(self.handle)
            self.verify()
            return self
        except Exception:
            self.handle.close()
            raise

    def verify(self):
        handle, chain = regular(self.path)
        with handle as current:
            if chain != self.parents or identity(os.fstat(current.fileno())) != self.identity:
                raise ValueError("Deployment input identity changed during packaging")
        if identity(os.fstat(self.handle.fileno())) != self.identity or digest_handle(self.handle) != self.checksum:
            raise ValueError("Deployment input bytes changed during packaging")

    def __exit__(self, *_):
        self.handle.close()


def guard_destination(destination, inputs, reserved=()):
    destination = absolute(destination)
    if destination in {source.path for source in inputs} | {absolute(path) for path in reserved}:
        raise ValueError("Destination aliases a deployment input")
    parent = None
    try:
        parent, _ = directory(destination.parent)
        info = os.stat(destination.name, dir_fd=parent, follow_symlinks=False)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("Destination must be a regular file, never a symlink")
        if any((info.st_dev, info.st_ino) == source.identity[:2] for source in inputs):
            raise ValueError("Destination aliases a deployment input inode")
    except FileNotFoundError:
        pass
    except OSError as error:
        raise ValueError("Unsafe destination parent path") from error
    finally:
        if parent is not None:
            os.close(parent)


@contextmanager
def atomic_output(destination, inputs, reserved=()):
    """Exclusive random temporary + dir-fd rename; no predictable wb target or path reopen."""
    destination = absolute(destination)
    guard_destination(destination, inputs, reserved)
    for source in inputs:
        source.verify()
    parent = None
    temporary = None
    created = False
    try:
        parent, parents = directory(destination.parent, create=True)
        temporary = "." + destination.name + "." + secrets.token_hex(16) + ".tmp"
        descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        created = True
        with os.fdopen(descriptor, "w+b") as output:
            yield output
            output.flush()
            os.fsync(output.fileno())
        for source in inputs:
            source.verify()
        current, chain = directory(destination.parent)
        os.close(current)
        if chain != parents:
            raise ValueError("Destination parent changed during packaging")
        guard_destination(destination, inputs, reserved)
        os.replace(temporary, destination.name, src_dir_fd=parent, dst_dir_fd=parent)
        temporary = None
    except OSError as error:
        raise ValueError("Unsafe or changed packaging path") from error
    finally:
        if parent is not None:
            if temporary is not None and created:
                try:
                    os.unlink(temporary, dir_fd=parent)
                except FileNotFoundError:
                    pass
            os.close(parent)


def prepare_catalogue(root, source, inputs):
    compressed, manifest = root / "data/catalogue.sqlite.xz", root / "data/catalogue-build.json"
    guard_destination(compressed, inputs, [manifest])
    guard_destination(manifest, inputs, [compressed])
    if compressed.exists() and manifest.exists():
        with FrozenInput(compressed) as cache, FrozenInput(manifest) as metadata:
            try:
                saved = json.load(metadata.handle)
            except json.JSONDecodeError:
                saved = None
            cache.verify()
            metadata.verify()
            expected = {
                "compression": "xz", "xz_preset": 6, "uncompressed_sha256": source.checksum,
                "uncompressed_bytes": source.info.st_size, "compressed_sha256": cache.checksum,
                "compressed_bytes": cache.info.st_size,
            }
            if saved == expected:
                return saved
    with atomic_output(compressed, inputs, [manifest]) as output:
        with lzma.LZMAFile(output, "wb", preset=6) as zipped:
            source.handle.seek(0)
            for chunk in iter(lambda: source.handle.read(CHUNK), b""):
                zipped.write(chunk)
        compressed_hash, compressed_bytes = digest_handle(output), os.fstat(output.fileno()).st_size
    value = {
        "compression": "xz", "xz_preset": 6,
        "uncompressed_bytes": source.info.st_size, "uncompressed_sha256": source.checksum,
        "compressed_sha256": compressed_hash, "compressed_bytes": compressed_bytes,
    }
    with atomic_output(manifest, inputs, [compressed]) as output:
        output.write(json.dumps(value, indent=2).encode() + b"\n")
    return value


def inspect_source_zip(source):
    backend = str(Path(__file__).resolve().parents[1] / "backend")
    if backend not in sys.path:
        sys.path.insert(0, backend)
    from torob.ingest import KNOWN_HASHES, _members, _digest

    try:
        source.handle.seek(0)
        with zipfile.ZipFile(source.handle) as archive:
            hashes = {}
            for name, member in _members(archive).items():
                with archive.open(member) as incoming:
                    hashes[name] = _digest(incoming)
                if hashes[name] != KNOWN_HASHES[name]:
                    raise ValueError(f"Source payload checksum mismatch: {name}")
    except zipfile.BadZipFile as error:
        raise ValueError("Invalid source ZIP") from error
    source.verify()
    return {
        "compression": "zip", "archive_sha256": source.checksum,
        "compressed_bytes": source.info.st_size, "payload_hashes": hashes,
        "expected_counts": {"shops": 6476, "products": 225903, "offers": 331506},
    }


def runtime_paths(root, source_zip):
    required = ["Dockerfile.csv-source" if source_zip is not None else "Dockerfile", "requirements.lock",
                "scripts/container_entrypoint.py", "frontend/dist/index.html",
                "scripts/build_catalogue.py" if source_zip is not None else "scripts/unpack_catalogue.py"]
    files = [root / name for name in required]
    backend = list((root / "backend/torob").glob("*.py"))
    if not backend:
        raise ValueError("Build frontend/catalogue and lock dependencies before packaging")
    files.extend(backend)
    nodes = list((root / "frontend/dist").rglob("*"))
    if any(path.is_symlink() for path in nodes):
        raise ValueError("Symlinks are not deployment inputs")
    files.extend(p for p in nodes if not p.is_dir())
    return sorted(set(files))


def package(root: Path, destination: Path, *, max_source_bytes=MAX_SOURCE_BYTES, source_zip: Path | None = None):
    root, destination = absolute(root), absolute(destination)
    files = runtime_paths(root, source_zip)
    reserved = [root / "data/catalogue.sqlite.xz", root / "data/catalogue-build.json"] if source_zip is None else []
    with ExitStack() as stack:
        frozen = [stack.enter_context(FrozenInput(path)) for path in files]
        catalogue_source = stack.enter_context(FrozenInput(source_zip if source_zip is not None else root / "data/catalogue.sqlite"))
        frozen.append(catalogue_source)
        # Existing XZ cache files are inputs to the cache decision too. Reject output
        # aliases before a corrupt cache can cause any regeneration writes.
        with ExitStack() as cache_stack:
            cache_inputs = [cache_stack.enter_context(FrozenInput(path)) for path in reserved if path.exists() or path.is_symlink()]
            guard_destination(destination, frozen + cache_inputs, reserved)
        entries = [(source, "Dockerfile" if source.path == root / "Dockerfile.csv-source" else str(source.path.relative_to(root))) for source in frozen[:-1]]
        extra = None
        if source_zip is not None:
            catalogue = inspect_source_zip(catalogue_source)
            extra = json.dumps(catalogue, indent=2).encode() + b"\n"
            entries.append((catalogue_source, "data/catalogue-source.zip"))
        else:
            catalogue = prepare_catalogue(root, catalogue_source, frozen)
            for name in ("data/catalogue.sqlite.xz", "data/catalogue-build.json"):
                source = stack.enter_context(FrozenInput(root / name))
                frozen.append(source)
                entries.append((source, name))
            if entries[-2][0].checksum != catalogue["compressed_sha256"]:
                raise ValueError("Compressed cache changed during packaging")
            if json.load(entries[-1][0].handle) != catalogue:
                raise ValueError("Catalogue cache manifest changed during packaging")
        with atomic_output(destination, frozen, reserved) as output:
            with gzip.GzipFile(filename="", fileobj=output, mode="wb", mtime=0) as zipped:
                with tarfile.open(fileobj=zipped, mode="w") as archive:
                    for source, name in sorted(entries, key=lambda item: item[1]):
                        info = tarfile.TarInfo(name)
                        info.size, info.mode, info.mtime = source.info.st_size, 0o644, source.info.st_mtime
                        source.handle.seek(0)
                        archive.addfile(info, source.handle)
                    if extra is not None:
                        info = tarfile.TarInfo("data/catalogue-source.json")
                        info.size, info.mode = len(extra), 0o644
                        archive.addfile(info, io.BytesIO(extra))
            output.flush()
            artifact_bytes = os.fstat(output.fileno()).st_size
            artifact_hash = digest_handle(output)
            if artifact_bytes > max_source_bytes:
                raise ValueError(f"Private source exceeds upload limit of{max_source_bytes}bytes")
    return {
        "artifact": str(destination), "bytes": artifact_bytes, "sha256": artifact_hash,
        "members": sorted([name for _, name in entries] + (["data/catalogue-source.json"] if extra is not None else [])),
        "private_catalogue_included": True, "credentials_included": False,
        "max_source_bytes": max_source_bytes, "catalogue": catalogue,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/deployment-xz.tar.gz"))
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--source-zip", type=Path, help="Original full private CSV ZIP; alternate build-stage import mode")
    parser.add_argument("--report", type=Path, default=Path("docs/qa-evidence/deployment-artifact.json"))
    args = parser.parse_args()
    root = absolute(args.root)
    paths = runtime_paths(root, args.source_zip) + [absolute(args.source_zip) if args.source_zip is not None else root / "data/catalogue.sqlite"]
    cache_paths = [root / "data/catalogue.sqlite.xz", root / "data/catalogue-build.json"] if args.source_zip is None else []
    # Validate the report destination too, before cache generation or artifact writes.
    with ExitStack() as stack:
        originals = [stack.enter_context(FrozenInput(path)) for path in paths + cache_paths if path.exists() or path.is_symlink()]
        guard_destination(args.report, originals, [args.output, *cache_paths])
    report = package(args.root, args.output, source_zip=args.source_zip)
    with ExitStack() as stack:
        inputs = [stack.enter_context(FrozenInput(path)) for path in [*paths, *cache_paths, absolute(args.output)]]
        with atomic_output(args.report, inputs) as output:
            output.write(json.dumps(report, indent=2).encode() + b"\n")
    print(json.dumps({key: value for key, value in report.items() if key != "members"}, indent=2))
