"""Build an atomic catalogue from the mandatory archive; hashes enforced by default."""

import argparse
import json
import resource
from dataclasses import asdict
from pathlib import Path
from torob.ingest import ingest_archive


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/catalogue.sqlite"))
    parser.add_argument("--manifest", type=Path, default=Path("docs/qa-evidence/catalogue-import.json"))
    args = parser.parse_args()
    report = ingest_archive(args.archive, args.output)
    expected = {"shops": 6476, "products": 225903, "offers": 331506}
    if report.counts != expected:
        raise SystemExit(f"Unexpected source counts: {report.counts}")
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
