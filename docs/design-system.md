# RTL design foundation and adoption

[← Documentation](README.md) · [Interface decisions](ui-design.md)

## Source and scope

The user supplied [RTL TailwindCSS Full UI Kit / Design System (Community)](https://www.figma.com/design/JwC2jmHbKzW4CkW6d7KTA6/). Its three pages were inspected through the owner's Figma session: **Design System**, **Components**, and **Assets**. The file identifies itself as a Persian RTL community kit; this inspection does not establish that it is Torob's official brand system or an official challenge requirement.

This implementation adopts a coherent subset of its foundations and interaction patterns. It does not claim pixel-for-pixel Figma implementation, imported component source, or full coverage of the kit. No unrelated maps, banking marks or asset library were copied into the product.

## Adoption map

| Inspected page | Observed material | Implementation decision |
|---|---|---|
| Design System | Color scales, radii, shadows/opacity, Persian type scale, spacing, max widths and breakpoints | Named semantic CSS tokens, 4px spacing foundation, consistent field/button sizes, responsive single codebase and restrained surfaces |
| Components | Buttons, Input/Input Groups, Select/Combobox, Checkbox, Dialog, Card, Alert and other primitives | Shared select-only combobox, semantic styled checkbox, composite focus treatment, button variants and existing modal focus/escape behavior |
| Assets | Icons, Iranian product/payment marks, maps, badges and other identity assets | Retain already licensed local typography and existing icon dependency; user-clicked provider names, no unnecessary logo/asset import |

## Component contracts

| Component | Visual contract | Interaction contract |
|---|---|---|
| Search group | One border/ring around icon, input and action | Child focus does not create a second input outline; keyboard focus stays visible on the group |
| Select | Same field height, radius, text alignment, selected/check and disabled states | Button/listbox semantics; arrows, Home/End, Enter/Space, Escape, Tab and outside dismissal; Escape does not close the containing modal |
| Checkbox | Consistent border, red checked surface and drawn checkmark | Native checkbox semantics, keyboard Space and visible focus retained |
| Agent composer | Leading mobile input with supported text and typed UI responses | User turn, bounded progress/cancel, explicit proposal application; no model-generated executable UI |
| Inline purchase plan | Primary/fallback roles, source-coordinate map and visible change delta | Chronological assistant response; old revisions read-only; current controls preserve revision guards |

## Persian digits and exact data

The bundled Vazirmatn font was checked with fontTools: its GSUB feature list contains `ss01`. Human-facing UI enables `font-feature-settings: "ss01"`; controls inherit it. Technical LTR fields deliberately disable the feature. This is glyph selection, not a conversion of the underlying value.

Numeric parsing/validation and exact decimal-string/BigInt money handling remain necessary. Existing localized separators and date formatting are preserved. A font feature cannot validate Persian input, select a calendar, prevent integer rounding, or change what is copied to the clipboard.

## Product decisions

- **One responsive application:** prioritize the mobile in-person use case; use one chronological conversation on desktop and mobile with bounded inline evidence components. No separate desktop product or parallel feature set.
- **Plan B is a builder-selected name:** it communicates recovery, but is not an organizer-provided product name and implies no official affiliation.
- **Agent-led, bounded GenUI:** the assistant presents source-backed cards and explicit condition proposals. Manual controls are secondary and reachable when AI is offline; they are not removed in favor of opaque chat.

Actual checks and remaining delivery work are owned by [the kanban](insured-vibe-coding/kanban.md) and [the conversation QA ledger](insured-vibe-coding/test-plans/conversation.md).
