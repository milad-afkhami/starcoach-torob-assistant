"""Stream the supplied CSV payloads into an atomic, immutable catalogue."""

import csv
import hashlib
import io
import itertools
import json
import math
import sqlite3
import time
import uuid
import zipfile
from collections import Counter
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path, PurePosixPath

from .normalize import normalize_text

KNOWN_HASHES = {
    "shops.csv": "1a292d6180e2a28cd0bbec57b1bb575a440e5afcc3ec3f5af5b1e13172aebaa1",
    "products.csv": "e4a9749529d1e032c1dc2c4e275a8793a1edd702a194cb8de9abafc0649cc9c9",
    "offers.csv": "664d256ed04b37cfb268d89eb605afda4a3b76179324b39d2dbaef21439f09b9",
}
HEADERS = {
    "shops.csv": {
        "address",
        "category_names",
        "contacts",
        "instagram",
        "lat",
        "location_label",
        "lon",
        "name",
        "payment_options",
        "shop_id",
        "supports_fast_delivery",
        "website_url",
        "weekly_hours",
    },
    "products.csv": {
        "brand_name",
        "category_name",
        "image_urls",
        "model",
        "persian_title",
        "product_id",
        "specs",
    },
    "offers.csv": {
        "description",
        "last_price_changed_at",
        "offer_id",
        "price_toman",
        "product_id",
        "seller_title",
        "shop_id",
        "warranty",
    },
}
JSON_FIELDS = {
    "category_names",
    "contacts",
    "payment_options",
    "weekly_hours",
    "image_urls",
    "specs",
    "supports_fast_delivery",
}
ARRAY_FIELDS = {"category_names", "contacts", "payment_options", "image_urls", "specs"}
SAFE_INTEGER = 2**53 - 1


class ImportFailure(ValueError):
    pass


@dataclass
class ImportReport:
    counts: dict
    missing: dict
    payload_hashes: dict
    archive_sha256: str
    duration_seconds: float
    rejected_rows: int = 0


def _digest(handle):
    digest = hashlib.sha256()
    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def _members(archive):
    found = {}
    for info in archive.infolist():
        path = PurePosixPath(info.filename)
        if path.is_absolute() or ".." in path.parts or "\\" in info.filename:
            raise ImportFailure("unsafe archive path")
        if info.is_dir() or "__MACOSX" in path.parts or path.name.startswith("._"):
            continue
        if path.name in HEADERS and info.filename in (path.name, "torob-dataset/" + path.name):
            if path.name in found:
                raise ImportFailure("ambiguous CSV member")
            if info.file_size > 512 * 1024 * 1024:
                raise ImportFailure("CSV exceeds bounded import size")
            found[path.name] = info
    if set(found) != set(HEADERS):
        raise ImportFailure("missing required CSV payload")
    return found


def _rows(archive, member, missing):
    with archive.open(member) as source:
        reader = csv.DictReader(io.TextIOWrapper(source, encoding="utf-8-sig", newline=""))
        if set(reader.fieldnames or []) != HEADERS[PurePosixPath(member.filename).name]:
            raise ImportFailure("unexpected/missing CSV header")
        for raw in reader:
            if None in raw or any(value is None for value in raw.values()):
                raise ImportFailure("malformed CSV row")
            row = {key: None if value == "null" else value for key, value in raw.items()}
            missing.update(key for key, value in row.items() if value is None)
            for field in JSON_FIELDS & row.keys():
                if row[field] is not None:
                    row[field] = json.loads(row[field])
                    if field in ARRAY_FIELDS and not isinstance(row[field], list):
                        raise ImportFailure("expected nested array")
                    if field == "weekly_hours" and not isinstance(row[field], dict):
                        raise ImportFailure("expected hours object")
            yield row


def _median(values):
    values = sorted(values)
    mid = len(values) // 2
    return Fraction(values[mid]) if len(values) % 2 else Fraction(values[mid - 1] + values[mid], 2)


def _flag_outliers(db):
    cursor = db.execute(
        "SELECT product_id,shop_id,price,offer_id FROM offers WHERE price_quality='normal' ORDER BY product_id"
    )
    flagged = []
    for _, group in itertools.groupby(cursor, key=lambda r: r[0]):
        rows = list(group)
        prices = {}
        for _, shop, price, _ in rows:
            prices.setdefault(shop, []).append(price)
        if len(prices) >= 3:
            median = _median([_median(v) for v in prices.values()])
            flagged.extend(
                (offer,) for _, _, price, offer in rows if price * 10 < median or price > median * 10
            )
    db.executemany("UPDATE offers SET price_quality='flagged' WHERE offer_id=?", flagged)


def ingest_archive(zip_path: Path, destination: Path, *, expected_hashes=None) -> ImportReport:
    started = time.monotonic()
    zip_path, destination = Path(zip_path), Path(destination)
    expected_hashes = KNOWN_HASHES if expected_hashes is None else expected_hashes
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".building-" + uuid.uuid4().hex)
    counts, missing, hashes = {}, {}, {}
    db = None
    try:
        with zip_path.open("rb") as f:
            archive_hash = _digest(f)
        with zipfile.ZipFile(zip_path) as archive:
            members = _members(archive)
            for name, member in members.items():
                with archive.open(member) as f:
                    hashes[name] = _digest(f)
                if name in expected_hashes and hashes[name] != expected_hashes[name]:
                    raise ImportFailure(f"checksum mismatch: {name}")
            db = sqlite3.connect(temporary)
            db.execute("PRAGMA foreign_keys=ON")
            db.executescript("""
              CREATE TABLE shops(shop_id TEXT PRIMARY KEY NOT NULL, lat REAL, lon REAL, data TEXT NOT NULL);
              CREATE TABLE products(product_id TEXT PRIMARY KEY NOT NULL,title TEXT,category TEXT,data TEXT NOT NULL);
              CREATE TABLE offers(offer_id TEXT PRIMARY KEY NOT NULL,
                product_id TEXT NOT NULL REFERENCES products(product_id),
                shop_id TEXT NOT NULL REFERENCES shops(shop_id),price INTEGER,price_quality TEXT,data TEXT NOT NULL);
              CREATE VIRTUAL TABLE product_search USING fts5(product_id UNINDEXED,text,tokenize='unicode61 remove_diacritics 2');
              CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT);
            """)
            csv.field_size_limit(4 * 1024 * 1024)
            for name in ("shops.csv", "products.csv", "offers.csv"):
                table = name[:-4]
                counter, count = Counter(), 0
                for row in _rows(archive, members[name], counter):
                    key = {"shops": "shop_id", "products": "product_id", "offers": "offer_id"}[table]
                    if not row.get(key):
                        raise ImportFailure("missing primary identifier")
                    if table == "shops":
                        coords = []
                        for field, maximum in (("lat", 90), ("lon", 180)):
                            value = None if row[field] in (None, "") else float(row[field])
                            if value is not None and (not math.isfinite(value) or abs(value) > maximum):
                                raise ImportFailure("invalid coordinates")
                            row[field] = value
                            coords.append(value)
                        db.execute(
                            "INSERT INTO shops VALUES(?,?,?,?)",
                            (row[key], *coords, json.dumps(row, ensure_ascii=False)),
                        )
                    elif table == "products":
                        db.execute(
                            "INSERT INTO products VALUES(?,?,?,?)",
                            (
                                row[key],
                                row["persian_title"],
                                row["category_name"],
                                json.dumps(row, ensure_ascii=False),
                            ),
                        )
                        spec_text = " ".join(
                            str(v.get("value", "")) for v in (row["specs"] or []) if isinstance(v, dict)
                        )
                        text = " ".join(
                            str(row.get(k) or "")
                            for k in ("persian_title", "brand_name", "category_name", "model")
                        )
                        db.execute(
                            "INSERT INTO product_search VALUES(?,?)",
                            (row[key], normalize_text(text + " " + spec_text)),
                        )
                    else:
                        price = None if row["price_toman"] in (None, "") else int(row["price_toman"])
                        if price is not None and not 0 <= price <= 2**63 - 1:
                            raise ImportFailure("price outside exact integer range")
                        quality = (
                            "missing"
                            if price is None
                            else "flagged"
                            if price == 0 or price > SAFE_INTEGER
                            else "normal"
                        )
                        db.execute(
                            "INSERT INTO offers VALUES(?,?,?,?,?,?)",
                            (
                                row[key],
                                row["product_id"],
                                row["shop_id"],
                                price,
                                quality,
                                json.dumps(row, ensure_ascii=False),
                            ),
                        )
                    count += 1
                counts[table], missing[table] = count, dict(counter)
            db.executescript("""
              CREATE INDEX offer_product ON offers(product_id);
              CREATE INDEX offer_shop ON offers(shop_id);
              CREATE INDEX offer_price ON offers(price);
              CREATE INDEX product_category ON products(category);
              CREATE INDEX shop_coordinates ON shops(lat,lon);
            """)
            if db.execute(
                "SELECT shop_id FROM offers GROUP BY shop_id HAVING COUNT(DISTINCT product_id)>300 LIMIT 1"
            ).fetchone():
                raise ImportFailure("shop exceeds source product cap")
            _flag_outliers(db)
            report = ImportReport(counts, missing, hashes, archive_hash, round(time.monotonic() - started, 3))
            db.execute("INSERT INTO metadata VALUES('manifest',?)", (json.dumps(asdict(report)),))
            db.commit()
            if db.execute("PRAGMA foreign_key_check").fetchone():
                raise ImportFailure("broken references")
            db.close()
            db = None
            temporary.replace(destination)
            return report
    except (ValueError, OSError, sqlite3.Error, zipfile.BadZipFile, csv.Error, OverflowError) as exc:
        raise ImportFailure(str(exc)) from exc
    finally:
        if db is not None:
            db.close()
        temporary.unlink(missing_ok=True)
