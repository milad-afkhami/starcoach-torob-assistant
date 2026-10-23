export interface Constraints {
  query: string; category: string | null; max_price_toman: string | null;
  lat: number; lon: number; radius_km: number; payment_provider: string | null;
  visit_at: string | null; require_declared_open: boolean; contactable_only?: boolean; origin_label?: string | null;
}
export interface Product {
  product_id: string; title: string | null; category: string | null; brand: string | null;
  model: string | null; specs: {key?: string; value?: string; section?: string}[];
  image_urls: string[]; min_recorded_price: string | null; evidence_ids: string[];
}
export interface Offer {
  offer_id: string; product_id: string; shop_id: string; shop_name: string;
  identity_anonymized: boolean; address: string; lat: number | null; lon: number | null;
  price_toman: string | null; recorded_price_toman: string | null; price_quality: string;
  price_changed_at: string | null; straight_line_km: number | null; hours_state: string;
  weekly_hours: Record<string,{status: string; shifts: {start_time: string; end_time: string}[]}> | null;
  payment_state: string; payment_evidence: Record<string,unknown>[]; stock_state: 'unknown';
  contact_links: {channel: string; url: string}[]; seller_title: string | null; warranty: string | null;
  observation_provenance: string | null; observations: {id: string; kind: string; provenance: string; raw_text: string}[];
}
export interface Option { offer: Offer; eligibility: string; reason_codes: string[]; unresolved_checks: string[]; tradeoffs: string[] }
export interface Plan { revision: number; primary: Option | null; fallback: Option | null; choices: Option[]; excluded: Option[]; shortlist_coverage: Record<string,number>; relaxations?: ConstraintSuggestion[] }
export interface Mission { id: string; revision: number; mode: 'assisted' | 'simulation'; selected_product_id: string; constraints: Constraints; selected_primary_shop_id: string | null }
export interface MissionResponse { mission: Mission; plan: Plan; product?: Product; delta?: Delta }
export interface Delta { before_revision: number; after_revision: number; changed_fields: string[]; price_delta_toman: string | null; retained_constraints: string[]; reason_codes: string[] }
export interface Observation { id: string; kind: string; base_revision: number; raw_text: string; price_toman: string | null; effective_visit_date: string | null; provenance: 'simulation' | 'user_reported' }
export interface Followup { id: string; inquiry: string; offer_id: string; contact_links: {channel: string; url: string}[] }
export interface ExternalAction { kind: string; label: string; url: string; destination_text: string | null; prefill: string; offer_id: string | null; mission_revision: number }
export interface Recommendation { product_id: string; reason_fa: string; facts: {id: string; label: string; value: string}[] }
export interface Turn { id: string; state: string; stage: string; error_code: string | null; result: {
  products: Product[]; recommendations: Recommendation[]; clarification_fa: string | null;
  proposed_constraints: Constraints; proposal_summary?: {eligible_shops: number; applied: boolean} | null;
  observation: Observation | null; degraded: boolean;
} | null }

export interface ConstraintSuggestion {field:'max_price_toman'|'radius_km';value:string|number;delta:string;base_revision:number;constraints:Constraints;eligible_shops:number;supporting_offer_ids:string[]}
export interface LocationPoint {shop_id:string;label:string;lat:number;lon:number;source:'catalogue_shop_coordinate'}
export interface SearchDiagnostic {kind:'category'|'budget';constraints:Constraints;minimum_toman?:string}
export interface ProductFeasibility {product:Product;eligible_shops:number;distinct_shops:number;best_offer:Offer|null;exclusion_reasons:Record<string,number>}
