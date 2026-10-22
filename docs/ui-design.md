# Interface direction — Plan B before you leave

Implementation choice for T5, not new product scope. The interface is a compact Persian shopping workspace: a search/needs panel and a persistent purchase note. Its memorable element is the paired primary/fallback seller note and the visible price/decision change after a seller fails. It must work without requiring every action to pass through chat.

## Tokens

| Token | Value | Role |
|---|---|---|
| Porcelain | #F4F7FB | Cool, quiet page surface |
| Paper | #FFFFFF | Product/evidence surfaces |
| Ink | #18324A | Main Persian text |
| Torob red | #C93440 | Primary actions and selected product marker |
| Alternative teal | #157C78 | Distinct fallback role, never a verified-stock badge |
| Caution | #9A5B08 | Historical/unknown/simulation information |
| Rule | #D9E3EC | Useful boundaries and connection line |

Typeface: locally served Vazirmatn if the official font/license can be obtained; otherwise a Persian-capable system fallback. One family; size/weight express hierarchy. Body16px, small labels13px, section22px, headline36px desktop/28px mobile. Persian text right aligned; IDs and URLs isolated LTR; exact toman strings formatted with BigInt, never JavaScript Number.

## Layout and flow

Desktop: a modest brand/navigation row, then a wide discovery column and a narrower persistent mission column. Before selection the mission note explains what choosing a product unlocks. After selection it shows the exact source title/variant and locked budget/location/visit/payment chips, primary and fallback cards, one next action, and concise history. Results use varied emphasis, not a dashboard of identical metric cards. On mobile everything stacks in reading order; the selected mission remains directly reachable without horizontal scrolling.

The product begins with practical work, not a marketing hero: “قبل از رفتن، گزینه دوم را داشته باش.” Exact search and “describe what you need” are distinct actions. A visible labelled demo button loads the fixed source scenario; it does not auto-start a simulation or imply real seller contact. Search cards show source images/title/category and recorded price/unknown stock, with compare/select actions. A two-product comparison uses provided specs and explicit unknown fields.

The purchase note names roles plainly: first option and nearby alternative. It shows straight-line separation, source address/floor/unit, declared visit hours and historical price date. After user-confirmed unavailability, promote the alternative with a single change panel: what changed, why, exact price delta, and which conditions stayed fixed. Motion occurs only in response to this action and respects reduced motion.

## Essential states

- Empty search offers concrete example queries and manual filters; no invented sample products.
- Loading has immediate progress and cancel for AI; fields remain editable. A stale response cannot overwrite newer state.
- AI unavailable explains that search/planning still work; it does not expose CLI/provider credentials or implementation setup to shoppers.
- No eligible plan shows blockers and the existing editable conditions. No silent budget/radius/product change; minimum-relaxation automation remains cut.
- Seller reply remains an unconfirmed preview with original text and provenance until the user presses confirm. Simulation has a persistent banner and separate reset.
- Maps/ride actions live under one Get there chooser. Torob model search comes first; conditional TorobPay remains an external account check. Every destination updates after recovery; no external handoff is opened or prefetched without a click.

## Pre-build critique

A generic full-screen chatbot would hide the purchase constraints and make recovery hard to inspect. A map-first layout would imply routing capabilities we do not have. Both are rejected. The paired purchase note carries the distinctive interaction; avoid decorative map tiles, gradients, score gauges and runtime-agent panels. Typography and spacing stay quiet around the change panel. Every stock/price/payment label must preserve the actual evidence boundary.

## Verification owed

T5 requires a written Playwright QA plan covering typing, form edits, source search/selection, comparison, preview/confirmation, no-response/no-match, explicit constraint changes, two sessions, reload/reset, AI failure/cancel, navigation handoffs,390×844 layout, keyboard focus and console/network failures. Independent QA must drive the rendered controls; API tests do not close those rows.

## User-directed revision — agent-led shopping

The user rejected burying the agent beneath a filter form. The next revision leads with a prominent Persian composer, a visible user turn and a schema-backed response made of text, product cards and explicit condition proposals. Exact search/filters remain a secondary, discoverable control path; this is a bounded purchase assistant, not arbitrary model-generated HTML. Keep one responsive implementation, prioritizing mobile and using desktop space for the mission beside the conversation. Plan B was the builder-selected concept name, not an organizer requirement.

Use a consistent token-based control system: single composite focus ring, keyboard-accessible popover selection, custom-styled semantic checkboxes, local Vazirmatn with verified ss01 Persian glyphs, readable labels and technical LTR isolation. Preserve parsing, BigInt and localized grouping; glyph substitution does not replace numeric validation. The linked community RTL Tailwind kit is a reference, not verified as an official Torob design system. Inspect its three pages and record the exact adoption/limits before claiming conformity.
