"""Import invariants: complete atomic data, exact money, real hashes, no unsafe archive members."""

import json
import sqlite3
import pytest
from catalogue_fixtures import archive, records, HEADERS


def ingest(tmp_path, rows=None, prefix="", **kw):
    from torob.ingest import ingest_archive

    return ingest_archive(
        archive(tmp_path, rows, prefix, **kw), tmp_path / "catalogue.sqlite", expected_hashes={}
    )


@pytest.mark.parametrize(
    "raw,want",
    [
        ("گوشي ۱۲۸ ك", "گوشی 128 ک"),
        ("  A07   RAM ", "a07 ram"),
        ("كیف\u200cگوشي", "کیف گوشی"),
        ("١٢٣٤٥٦٧٨٩٠", "1234567890"),
        ("کِتاب", "کتاب"),
    ],
)
def test_normalize_preserves_display_separately(raw, want):
    from torob.normalize import normalize_text

    assert normalize_text(raw) == want


def test_complete_joined_catalogue_and_nulls(tmp_path):
    report = ingest(tmp_path)
    assert report.counts == {"shops": 3, "products": 2, "offers": 3}
    with sqlite3.connect(tmp_path / "catalogue.sqlite") as db:
        assert (
            db.execute(
                "select count(*) from offers join shops using(shop_id) join products using(product_id)"
            ).fetchone()[0]
            == 3
        )
        raw = json.loads(db.execute('select data from products where product_id="p1"').fetchone()[0])
        assert raw["persian_title"] == "گوشي سامسونگ A07 ۱۲۸"
        assert raw["specs"][0]["value"] == "۱۲۸ گیگ"
        assert db.execute('select price,price_quality from offers where offer_id="o1"').fetchone() == (
            100,
            "normal",
        )
        assert (
            json.loads(db.execute('select data from offers where offer_id="o1"').fetchone()[0])["warranty"]
            is None
        )
    assert report.missing["offers"]["warranty"] == 3
    assert set(report.payload_hashes) == {"shops.csv", "products.csv", "offers.csv"}


def test_wrapped_and_root_payload_hashes_match(tmp_path):
    a = ingest(tmp_path)
    b = ingest(
        tmp_path,
        prefix="torob-dataset/",
        extras={"__MACOSX/torob-dataset/._shops.csv": "ignored", "torob-dataset/README.txt": "notes"},
    )
    assert a.counts == b.counts and a.payload_hashes == b.payload_hashes


def test_exact_large_money_flagged_not_rounded(tmp_path):
    rows = records()
    rows["offers.csv"][0]["price_toman"] = 499258940504558912
    ingest(tmp_path, rows)
    with sqlite3.connect(tmp_path / "catalogue.sqlite") as db:
        p, q, raw = db.execute('select price,price_quality,data from offers where offer_id="o1"').fetchone()
    assert p == 499258940504558912 and q == "flagged"
    assert json.loads(raw)["price_toman"] == "499258940504558912"


def test_price_outlier_compares_distinct_shops(tmp_path):
    rows = records()
    rows["offers.csv"][2]["price_toman"] = 100000
    rows["offers.csv"].append({**rows["offers.csv"][0], "offer_id": "duplicate-shop", "price_toman": 1})
    ingest(tmp_path, rows)
    with sqlite3.connect(tmp_path / "catalogue.sqlite") as db:
        assert db.execute('select price_quality from offers where offer_id="o3"').fetchone()[0] == "flagged"


@pytest.mark.parametrize(
    "kind",
    [
        "duplicate_offer",
        "orphan_shop",
        "orphan_product",
        "invalid_json",
        "bad_price",
        "missing_header",
        "duplicate_product",
    ],
)
def test_bad_import_preserves_previous_database(tmp_path, kind):
    from torob.ingest import ImportFailure, ingest_archive

    ingest(tmp_path)
    before = (tmp_path / "catalogue.sqlite").read_bytes()
    rows = records()
    headers = None
    if kind == "duplicate_offer":
        rows["offers.csv"].append(rows["offers.csv"][0])
    elif kind == "orphan_shop":
        rows["offers.csv"][0]["shop_id"] = "missing"
    elif kind == "orphan_product":
        rows["offers.csv"][0]["product_id"] = "missing"
    elif kind == "invalid_json":
        rows["shops.csv"][0]["weekly_hours"] = "{bad"
    elif kind == "bad_price":
        rows["offers.csv"][0]["price_toman"] = "1.5"
    elif kind == "missing_header":
        headers = {"offers.csv": [h for h in HEADERS["offers.csv"] if h != "shop_id"]}
    elif kind == "duplicate_product":
        rows["products.csv"].append(rows["products.csv"][0])
    with pytest.raises(ImportFailure):
        ingest_archive(
            archive(tmp_path, rows, header_override=headers),
            tmp_path / "catalogue.sqlite",
            expected_hashes={},
        )
    assert (tmp_path / "catalogue.sqlite").read_bytes() == before
    assert not list(tmp_path.glob("*.building-*"))


@pytest.mark.parametrize(
    "member", ["../shops.csv", "/shops.csv", "torob-dataset/../../x", "torob-dataset/../x"]
)
def test_unsafe_archive_path_rejected(tmp_path, member):
    from torob.ingest import ImportFailure

    with pytest.raises(ImportFailure):
        ingest(tmp_path, extras={member: "bad"})


def test_ambiguous_csv_and_hash_mismatch_rejected(tmp_path):
    from torob.ingest import ImportFailure, ingest_archive

    with pytest.raises(ImportFailure):
        ingest(tmp_path, extras={"torob-dataset/shops.csv": "ambiguous"})
    with pytest.raises(ImportFailure, match="checksum"):
        ingest_archive(
            archive(tmp_path), tmp_path / "catalogue.sqlite", expected_hashes={"shops.csv": "wrong"}
        )


def test_missing_zero_and_negative_prices(tmp_path):
    from torob.ingest import ImportFailure

    rows = records()
    rows["offers.csv"][0]["price_toman"] = None
    rows["offers.csv"][1]["price_toman"] = 0
    ingest(tmp_path, rows)
    with sqlite3.connect(tmp_path / "catalogue.sqlite") as db:
        assert db.execute("select price,price_quality from offers order by offer_id").fetchall() == [
            (None, "missing"),
            (0, "flagged"),
            (300, "normal"),
        ]
    rows["offers.csv"][0]["price_toman"] = -1
    with pytest.raises(ImportFailure):
        ingest(tmp_path, rows)


def test_missing_product_title_is_preserved_not_fabricated_or_dropped(tmp_path):
    rows = records()
    rows["products.csv"][0]["persian_title"] = None
    report = ingest(tmp_path, rows)
    assert report.counts["products"] == 2 and report.missing["products"]["persian_title"] == 1
    with sqlite3.connect(tmp_path / "catalogue.sqlite") as db:
        title, raw = db.execute('select title,data from products where product_id="p1"').fetchone()
    assert title is None and json.loads(raw)["persian_title"] is None


@pytest.mark.parametrize("field,value", [("lat", "nan"), ("lat", "91"), ("lon", "181"), ("lon", "inf")])
def test_invalid_coordinate_does_not_enter_catalogue(tmp_path, field, value):
    from torob.ingest import ImportFailure

    rows = records()
    rows["shops.csv"][0][field] = value
    with pytest.raises(ImportFailure):
        ingest(tmp_path, rows)


def test_shop_product_cap_and_bad_nested_shape(tmp_path):
    from torob.ingest import ImportFailure

    rows = records()
    rows["products.csv"] = [{**rows["products.csv"][0], "product_id": f"p{n}"} for n in range(301)]
    rows["offers.csv"] = [
        {**rows["offers.csv"][0], "product_id": f"p{n}", "offer_id": f"o{n}"} for n in range(301)
    ]
    with pytest.raises(ImportFailure, match="cap"):
        ingest(tmp_path, rows)
    rows = records()
    rows["products.csv"][0]["specs"] = {"not": "an array"}
    with pytest.raises(ImportFailure, match="array"):
        ingest(tmp_path, rows)
