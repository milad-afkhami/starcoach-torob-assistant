from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

MoneyToman = Annotated[str, Field(strict=True, pattern=r"^(0|[1-9][0-9]{0,18})$")]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class SearchConstraints(Record):
    query: str = Field(default="", max_length=300)
    category: str | None = Field(default=None, max_length=100)
    max_price_toman: MoneyToman | None = None
    lat: float = Field(default=35.69508821734553, ge=-90, le=90)
    lon: float = Field(default=51.41148102579503, ge=-180, le=180)
    radius_km: float = Field(default=1, gt=0, le=50)
    payment_provider: str | None = Field(default=None, max_length=100)
    visit_at: AwareDatetime | None = None
    require_declared_open: bool = True


class ProductHit(Record):
    product_id: str
    title: str | None
    category: str | None
    brand: str | None
    model: str | None
    specs: list[dict]
    image_urls: list[str]
    min_recorded_price: MoneyToman | None
    evidence_ids: list[str]


class OfferHit(Record):
    offer_id: str
    product_id: str
    shop_id: str
    shop_name: str
    identity_anonymized: bool
    address: str
    lat: float | None
    lon: float | None
    price_toman: MoneyToman | None
    recorded_price_toman: MoneyToman | None
    price_quality: Literal["normal", "missing", "flagged"]
    price_changed_at: str | None
    straight_line_km: float | None
    hours_state: Literal["open", "closed", "unknown"]
    weekly_hours: dict | None
    payment_state: Literal["supported", "unknown", "unsupported", "not_required"]
    payment_evidence: list[dict]
    stock_state: Literal["unknown"] = "unknown"
    evidence_ids: list[str]
    contact_links: list[dict]
    seller_title: str | None
    warranty: str | None
    observation_provenance: str | None = None
    observation_id: str | None = None
    observation_reasons: list[str] = Field(default_factory=list)
    observations: list[dict] = Field(default_factory=list)
    recorded_price_quality: Literal["normal", "missing", "flagged"] | None = None


class Mission(Record):
    id: str
    session_id: str
    revision: int = 1
    mode: Literal["assisted", "simulation"] = "assisted"
    selected_product_id: str
    constraints: SearchConstraints
    selected_primary_shop_id: str | None = None


class PlanOption(Record):
    offer: OfferHit
    eligibility: Literal["candidate", "needs_verification", "ineligible"]
    reason_codes: list[str]
    unresolved_checks: list[str]
    tradeoffs: list[str] = Field(default_factory=list)


class PurchasePlan(Record):
    revision: int
    primary: PlanOption | None
    fallback: PlanOption | None
    choices: list[PlanOption]
    excluded: list[PlanOption]
    shortlist_coverage: dict[str, int]


class PlanDelta(Record):
    before_revision: int
    after_revision: int
    changed_fields: list[str]
    price_delta_toman: str | None
    retained_constraints: list[str]
    reason_codes: list[str]
