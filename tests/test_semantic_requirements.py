import pytest
from test_semantic_continuation import requirement


def numeric(quote="وزن کمتر از 1.5 کیلوگرم", operator="lt", value="1.5", unit="kg", terms=None):
    return requirement(
        quote, "spec", True, terms or ["وزن"], {"operator": operator, "value": value, "unit": unit}
    )


@pytest.mark.parametrize(
    "value,status",
    [
        ("1.4 کیلوگرم", "matched"),
        ("1500 گرم", "excluded"),
        ("1.5 کیلوگرم", "excluded"),
        ("1.4 تا 1.6 کیلوگرم", "unresolved"),
        ("1.4", "unresolved"),
        ("نامشخص", "unresolved"),
    ],
)
def test_single_explicit_source_scalar_checks_hard_requirement_without_inference(value, status):
    from torob.semantic import check_requirement

    result = check_requirement(numeric(), [{"id": "p:spec:0", "label": "وزن", "value": value}])
    assert result["status"] == status
    assert result["facts"][0]["value"] == value


def test_unknown_bound_operator_and_foreign_field_never_qualify(tmp_path):
    from torob.semantic import check_requirement

    fact = [{"id": "p:spec:0", "label": "وزن", "value": "1.4 کیلوگرم"}]
    assert check_requirement(numeric(value="2"), fact)["status"] == "unresolved"
    assert check_requirement(numeric(operator="gt"), fact)["status"] == "unresolved"
    assert (
        check_requirement(numeric(), [{"id": "p:spec:0", "label": "وزن بسته بندی", "value": "1.4 کیلوگرم"}])[
            "status"
        ]
        == "unresolved"
    )


def test_numeric_class_is_not_weight_specific_and_preserves_unit_uncertainty():
    from torob.semantic import check_requirement

    req = numeric("رم حداقل 8 گیگابایت", operator="gte", value="8", unit="GB", terms=["رم"])
    assert (
        check_requirement(req, [{"id": "p:spec:0", "label": "رم", "value": "16 GB"}])["status"] == "matched"
    )
    assert (
        check_requirement(req, [{"id": "p:spec:0", "label": "رم", "value": "8192 MB"}])["status"]
        == "unresolved"
    )


def test_contradictory_source_values_and_unsupported_requirement_are_unresolved():
    from torob.semantic import check_requirement

    facts = [
        {"id": "p:spec:0", "label": "وزن", "value": "1.4 کیلوگرم"},
        {"id": "p:spec:1", "label": "وزن", "value": "1.8 کیلوگرم"},
    ]
    assert check_requirement(numeric(), facts)["status"] == "unresolved"
    assert check_requirement(requirement("اجرای نرم افزار خاص", "other"), facts)["status"] == "unresolved"


def test_deterministic_checks_inspect_all_matching_facts_even_beyond_the_model_fact_bound():
    from torob.agent import source_facts
    from torob.semantic import check_requirement

    product = {
        "product_id": "p",
        "title": "source",
        "brand": None,
        "category": None,
        "model": None,
        "min_recorded_price": None,
        "specs": [{"key": "وزن", "value": "1.4 کیلوگرم"} for _ in range(13)]
        + [{"key": "وزن", "value": "1.8 کیلوگرم"}],
    }
    prompt = source_facts(product, ["وزن"])
    complete = source_facts(product, ["وزن"], all_specs=True)
    assert len([f for f in prompt if ":spec:" in f["id"]]) == 8
    assert check_requirement(numeric(), complete)["status"] == "unresolved"


def test_bound_unit_and_operator_must_bind_to_the_requested_property_clause():
    from torob.semantic import check_requirement

    req = numeric("وزن کمتر از 1.5 کیلوگرم و رم کمتر از 16 گیگابایت", value="16")
    assert (
        check_requirement(req, [{"id": "p:spec:0", "label": "وزن", "value": "2 کیلوگرم"}])["status"]
        == "unresolved"
    )


def test_explicit_removal_wins_even_when_model_repeats_the_quote_in_same_turn():
    from torob.semantic import merge_requirements

    req = numeric()
    state = merge_requirements({}, [req], req["source_quote"])
    rid = state["requirements"][0]["id"]
    removed = merge_requirements(state, [req], "شرط " + req["source_quote"] + " را حذف کن", removed=[rid])
    assert removed["requirements"] == []
    repeated = merge_requirements(removed, [req], "شرط " + req["source_quote"] + " را حذف کن")
    assert repeated["requirements"] == []


def test_one_property_requirement_cannot_cover_another_hard_property_in_the_same_quote():
    from torob.semantic import merge_requirements, product_checks

    quote = "وزن کمتر از 1.5 کیلوگرم و رم کمتر از 16 گیگابایت"
    req = numeric(quote, value="1.5")
    state = merge_requirements({}, [req], quote)
    check = product_checks(
        {"product_id": "p"},
        [
            {"id": "p:spec:0", "label": "وزن", "value": "1.4 کیلوگرم"},
            {"id": "p:spec:1", "label": "رم", "value": "32 GB"},
        ],
        state["requirements"],
    )
    assert check["status"] == "unresolved"
    assert any(r.get("unparsed_user_condition") for r in state["requirements"])
