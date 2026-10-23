"""Bounded user-quoted shopping requirements and conservative source scalar checks."""

import hashlib
import re
from decimal import Decimal, InvalidOperation
from .normalize import normalize_text

MAX_REQUIREMENTS = 6


def obj(fields):
    return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}


REQUIREMENT_SCHEMA = obj(
    {
        "label_fa": {"type": "string", "minLength": 1, "maxLength": 160},
        "source_quote": {"type": "string", "minLength": 1, "maxLength": 200},
        "kind": {"type": "string", "enum": ["spec", "location", "purpose", "other"]},
        "hard": {"type": "boolean"},
        "spec_terms": {
            "type": "array",
            "maxItems": 4,
            "items": {"type": "string", "minLength": 1, "maxLength": 40},
        },
        "numeric": {
            "anyOf": [
                {"type": "null"},
                obj(
                    {
                        "operator": {"type": "string", "enum": ["lt", "lte", "gt", "gte", "eq"]},
                        "value": {"type": "string", "pattern": r"^\d{1,12}(?:\.\d{1,4})?$"},
                        "unit": {"type": "string", "enum": ["kg", "g", "GB", "MB", "TB", "inch"]},
                    }
                ),
            ]
        },
    }
)

UNITS = {
    "kg": ("mass", Decimal("1000"), ["کیلوگرم", "کیلو گرم", "kg"]),
    "g": ("mass", Decimal("1"), ["گرم", "g"]),
    "GB": ("GB", Decimal("1"), ["گیگابایت", "گیگا بایت", "gb"]),
    "MB": ("MB", Decimal("1"), ["مگابایت", "مگا بایت", "mb"]),
    "TB": ("TB", Decimal("1"), ["ترابایت", "ترا بایت", "tb"]),
    "inch": ("inch", Decimal("1"), ["اینچ", "inch", "inches"]),
}
OPERATORS = {
    "lt": ["کمتر از", "کم تر از", "زیر", "less than", "under", "below"],
    "lte": ["حداکثر", "حد اکثر", "at most", "تا"],
    "gt": ["بیشتر از", "بیش تر از", "بالاتر از", "more than", "above"],
    "gte": ["حداقل", "حد اقل", "at least"],
    "eq": ["دقیقا", "دقیقاً", "برابر", "exactly"],
}


def text(value):
    return normalize_text(value).replace("٫", ".").strip()


def key(value):
    return re.sub(r"[^\w]+", "", text(value))


def unit_in(value, unit):
    return any(
        re.search(r"(?<![a-zآ-ی])" + re.escape(alias) + r"(?![a-zآ-ی])", text(value))
        for alias in UNITS[unit][2]
    )


def clauses(message):
    return [
        part.strip()
        for part in re.split(r"[؛;،\n]|\s+(?:و|and|but|اما)\s+", message, flags=re.I)
        if part.strip()
    ]


def user_clause_guards(message, requirements, removed_quotes):
    """Fail closed on explicit obligation/comparison/location cues the model omitted.

    This does not infer a property, threshold or satisfaction. The verbatim clause
    remains an unresolved requirement until it is represented or explicitly removed.
    """
    for clause in clauses(message):
        probe = clause
        for removed in removed_quotes:
            probe = probe.replace(removed, "")
        normalized = text(probe)
        mandatory = bool(re.search(r"\b(?:حتما|الزامی|اجباری|باید|must|required|mandatory)\b", normalized))
        location = bool(re.search(r"\b(?:نزدیک|اطراف|حوالی|محدوده|near|around)\b", normalized))
        comparative = any(
            re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", normalized)
            for words in OPERATORS.values()
            for word in words
        ) or bool(re.search(r"[<>]", normalized))
        number = bool(re.search(r"(?<!\w)\d+(?:\.\d+)?", normalized))
        preference = bool(re.search(r"ترجیح|اگر ممکن|prefer|ideally|if possible", normalized))
        canonical_money = (
            bool(re.search(r"تومان|ریال|میلیون|بودجه", normalized))
            and len(re.findall(r"(?<!\w)\d+(?:\.\d+)?", normalized)) <= 1
        )
        needs_guard = location or (
            (mandatory or (comparative and number)) and not canonical_money and (mandatory or not preference)
        )
        if not needs_guard:
            continue
        matching = [
            r
            for r in requirements
            if (r["source_quote"] in clause or clause in r["source_quote"])
            and (
                r["kind"] not in ("spec", "location")
                or (r["kind"] == "location" and location)
                or (
                    r["kind"] == "spec"
                    and any(key(term) and key(term) in key(clause) for term in r["spec_terms"])
                )
            )
        ]
        if any(r["hard"] for r in matching):
            continue
        if matching:
            for req in matching:
                req["hard"] = True
            continue
        quote = clause[:200]
        kind = "location" if location else "other"
        rid = hashlib.sha256((kind + "\x1f" + quote).encode()).hexdigest()[:20]
        requirements.append(
            {
                "id": rid,
                "label_fa": quote,
                "source_quote": quote,
                "kind": kind,
                "hard": True,
                "spec_terms": [],
                "numeric": None,
                "unparsed_user_condition": True,
            }
        )
    return requirements


def quoted_bound(req):
    numeric = req.get("numeric")
    if not numeric or numeric.get("unit") not in UNITS:
        return None
    scoped = [
        part
        for part in clauses(req["source_quote"])
        if any(key(term) and key(term) in key(part) for term in req.get("spec_terms", []))
    ]
    if len(scoped) != 1:
        return None
    quote = text(scoped[0])
    number = numeric["value"]
    if not re.search(r"(?<![\d.])" + re.escape(number) + r"(?![\d.])", quote) or not unit_in(
        quote, numeric["unit"]
    ):
        return None
    allowed = {
        op
        for op, words in OPERATORS.items()
        if any(re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", quote) for word in words)
    }
    symbols = re.search(r"(<=|>=|<|>|=)", quote)
    if symbols:
        allowed.add({"<": "lt", "<=": "lte", ">": "gt", ">=": "gte", "=": "eq"}[symbols[0]])
    if numeric["operator"] not in allowed or len(allowed) != 1:
        return None
    try:
        return Decimal(number)
    except InvalidOperation:
        return None


def scalar(fact):
    value = text(fact["value"])
    label = text(fact["label"])
    for unit, (family, scale, aliases) in UNITS.items():
        suffix = "|".join(re.escape(alias) for alias in aliases)
        match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(" + suffix + r")\s*", value)
        if match:
            return Decimal(match[1]) * scale, family
        if re.fullmatch(r"\d+(?:\.\d+)?", value) and unit_in(label, unit):
            return Decimal(value) * scale, family
    return None


def fact_matches(req, fact):
    # A unit in the source label is explicit evidence. Do not treat package/battery
    # weight or another related field as the exact requested product property.
    label = re.sub(r"\([^)]*\)|\[[^]]*\]", "", fact["label"])
    return any(
        key(term) == key(label) and key(term) in key(req["source_quote"])
        for term in req.get("spec_terms", [])
    )


def check_requirement(req, facts):
    relevant = [fact for fact in facts if fact_matches(req, fact)] if req["kind"] == "spec" else []
    result = {
        "id": req.get("id", ""),
        "label_fa": req["label_fa"],
        "hard": req["hard"],
        "status": "unresolved",
        "facts": relevant,
    }
    if req["kind"] == "location":
        if req.get("origin_resolved"):
            result["status"] = "matched"
        return result
    bound = quoted_bound(req)
    if bound is None or not relevant:
        return result
    unit = req["numeric"]["unit"]
    family, scale, _ = UNITS[unit]
    target = bound * scale
    states = []
    for fact in relevant:
        parsed = scalar(fact)
        if parsed is None or parsed[1] != family:
            return result
        actual = parsed[0]
        op = req["numeric"]["operator"]
        states.append(
            {
                "lt": actual < target,
                "lte": actual <= target,
                "gt": actual > target,
                "gte": actual >= target,
                "eq": actual == target,
            }[op]
        )
    if all(states):
        result["status"] = "matched"
    elif not any(states):
        result["status"] = "excluded"
    return result


def merge_requirements(context, extracted, message, *, removed=(), origin_confirmed=False, infer_guards=True):
    prior = {r["id"]: dict(r) for r in context.get("requirements", [])}
    retired = set(context.get("removed_requirement_ids", [])) | set(removed)
    current_removed = set(context.get("removed_in_current_turn", [])) | set(removed)
    removed_quotes = list(context.get("removed_quotes_current_turn", [])) + [
        prior[rid]["source_quote"] for rid in removed if rid in prior
    ]
    if not set(removed) <= set(prior):
        raise ValueError("unknown semantic requirement removal")
    for rid in removed:
        prior.pop(rid)
    if origin_confirmed:
        for item in prior.values():
            if item["kind"] == "location":
                item["origin_resolved"] = True
    sources = [message, *context.get("user_messages", []), *[r["source_quote"] for r in prior.values()]]
    for item in extracted:
        quote = item["source_quote"].strip()
        if not quote or not any(quote in source for source in sources):
            raise ValueError("semantic quote not from owned user text")
        rid = hashlib.sha256((item["kind"] + "\x1f" + quote).encode()).hexdigest()[:20]
        if rid in current_removed or quote in removed_quotes:
            continue
        if rid in retired and quote not in message:
            continue
        if rid not in prior:
            prior[rid] = {**item, "label_fa": quote, "source_quote": quote, "id": rid}
        elif item["kind"] == "location" and quote in message and not origin_confirmed:
            prior[rid].pop("origin_resolved", None)
    guarded = (
        user_clause_guards(message, list(prior.values()), removed_quotes)
        if infer_guards
        else list(prior.values())
    )
    if len(guarded) > MAX_REQUIREMENTS:
        raise ValueError("too many semantic requirements")
    return {
        **context,
        "requirements": guarded,
        "removed_in_current_turn": list(current_removed),
        "removed_quotes_current_turn": removed_quotes,
        "removed_requirement_ids": list(retired)[-MAX_REQUIREMENTS:],
    }


def product_checks(product, facts, requirements):
    checks = [check_requirement(r, facts) for r in requirements]
    hard = [c for c in checks if c["hard"]]
    status = (
        "excluded"
        if any(c["status"] == "excluded" for c in hard)
        else "unresolved"
        if any(c["status"] == "unresolved" for c in hard)
        else "matched"
    )
    return {"product_id": product["product_id"], "status": status, "requirements": checks}
