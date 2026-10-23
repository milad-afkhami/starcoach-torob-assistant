"""Build an atomic catalogue from the mandatory archive; hashes enforced by default."""

import argparse
import json
import resource
import hashlib
import sqlite3
from dataclasses import asdict
from pathlib import Path
from torob.ingest import ingest_archive


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/catalogue.sqlite"))
    parser.add_argument("--manifest", type=Path, default=Path("docs/qa-evidence/catalogue-import.json"))
    parser.add_argument("--source-manifest", type=Path)
    args = parser.parse_args()
    if args.source_manifest:
        source = json.loads(args.source_manifest.read_text())
        with args.archive.open("rb") as incoming:
            actual = hashlib.file_digest(incoming, "sha256").hexdigest()
        if source.get("compression") != "zip" or actual != source.get("archive_sha256"):
            raise SystemExit("Source ZIP manifest/hash mismatch")
    report = ingest_archive(args.archive, args.output)
    expected = {"shops": 6476, "products": 225903, "offers": 331506}
    if report.counts != expected:
        raise SystemExit(f"Unexpected source counts: {report.counts}")
    if args.source_manifest and (report.payload_hashes != source.get("payload_hashes") or report.counts != source.get("expected_counts")):
        raise SystemExit("Source payload/count manifest mismatch")
    with sqlite3.connect(f"file:{args.output}?mode=ro", uri=True) as db:
        if db.execute("PRAGMA quick_check").fetchone() != ("ok",):
            raise SystemExit("Catalogue integrity check failed")
        if db.execute("SELECT count(*) FROM product_search").fetchone()[0] != expected["products"]:
            raise SystemExit("Catalogue FTS count mismatch")
    manifest = {
        **asdict(report),
        "database_bytes": args.output.stat().st_size,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
