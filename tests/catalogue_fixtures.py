import csv
import io
import json
import zipfile

HEADERS = {
    "shops.csv": [
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
    ],
    "products.csv": [
        "brand_name",
        "category_name",
        "image_urls",
        "model",
        "persian_title",
        "product_id",
        "specs",
    ],
    "offers.csv": [
        "description",
        "last_price_changed_at",
        "offer_id",
        "price_toman",
        "product_id",
        "seller_title",
        "shop_id",
        "warranty",
    ],
}


def records():
    shops = [
        {
            "shop_id": f"s{i}",
            "name": f"فروشگاه {i}",
            "address": f"طبقه اول واحد {i}",
            "lat": 35.7,
            "lon": 51.4 + i / 10000,
            "category_names": ["گوشی موبایل"],
            "contacts": [{"channel": "phone", "display_number": "02100000000"}],
            "payment_options": [],
            "weekly_hours": {
                "thu": {"status": "declared", "shifts": [{"start_time": "10:00:00", "end_time": "22:00:00"}]}
            },
        }
        for i in range(1, 4)
    ]
    products = [
        {
            "product_id": "p1",
            "persian_title": "گوشي سامسونگ A07 ۱۲۸",
            "brand_name": "سامسونگ",
            "category_name": "گوشی موبایل",
            "model": "A07",
            "specs": [{"section": "حافظه", "key": "حافظه", "value": "۱۲۸ گیگ"}],
            "image_urls": ["https://image.torob.com/test.jpg"],
        },
        {
            "product_id": "p2",
            "persian_title": "قاب A07",
            "category_name": "قاب گوشی",
            "specs": [],
            "image_urls": [],
        },
    ]
    offers = [
        {
            "offer_id": f"o{i}",
            "shop_id": f"s{i}",
            "product_id": "p1",
            "price_toman": i * 100,
            "last_price_changed_at": "2026-10-12T00:00:00+00:00",
            "seller_title": "A07",
            "description": "",
        }
        for i in range(1, 4)
    ]
    return {"shops.csv": shops, "products.csv": products, "offers.csv": offers}


def archive(tmp_path, rows=None, prefix="", extras=None, header_override=None):
    path = tmp_path / "dataset.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, values in (rows or records()).items():
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=(header_override or {}).get(name, HEADERS[name]))
            writer.writeheader()
            for row in values:
                converted = {
                    key: (
                        "null"
                        if row.get(key) is None
                        else json.dumps(row[key], ensure_ascii=False, separators=(",", ":"))
                        if isinstance(row[key], (dict, list, bool))
                        else str(row[key])
                    )
                    for key in writer.fieldnames
                }
                writer.writerow(converted)
            z.writestr(prefix + name, buf.getvalue())
        for name, value in (extras or {}).items():
            z.writestr(name, value)
    return path
