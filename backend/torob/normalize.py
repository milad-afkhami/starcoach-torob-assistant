import re
import unicodedata

_LETTERS = str.maketrans("يكى٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "یکی01234567890123456789")


def normalize_text(text: str | None) -> str:
    value = unicodedata.normalize("NFKC", text or "").translate(_LETTERS).casefold()
    value = value.replace("\u200c", " ").replace("\u200f", " ").replace("ـ", "")
    value = "".join(c for c in value if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", value).strip()
