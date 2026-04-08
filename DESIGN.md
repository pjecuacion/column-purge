# Design System Specification: Premium Data Utility

## 1. Overview & Creative North Star
**Creative North Star: The Precision Architect**
Data processing is often chaotic and overwhelming. This design system seeks to provide the opposite experience: a serene, hyper-organized environment that feels less like a "utility" and more like a high-end digital atelier. We achieve this through **The Precision Architect** philosophy, which emphasizes architectural layering, rhythmic whitespace, and a rejection of traditional containment (borders) in favor of tonal transitions.

By utilizing high-contrast typography scales and intentional asymmetry, we move away from "SaaS-in-a-box" layouts. We treat the interface as a series of sophisticated, stacked surfaces that guide the user's eye toward the only thing that matters: the data.

---

## 2. Colors & Tonal Depth
The palette transitions from deep, authoritative purples to refreshing mint greens, anchored by a sophisticated blue-tinted gray scale.

### Core Palette
*   **Primary (The Action):** `#572da3` (Deep Purple). Used for primary commands and high-level brand moments.
*   **Secondary/Tertiary (The Success):** `#416656` & `#005338` (Mint/Deep Green). Reserved for data validation, "Processed" states, and positive outcomes.
*   **Background & Surface:** `#f8f9ff`. A crisp, cool base that feels more premium than pure white.

### The "No-Line" Rule
Standard 1px borders are strictly prohibited for sectioning. Structural definition must be achieved via **Background Shifts**.
*   **Level 0 (Base):** `surface` (`#f8f9ff`)
*   **Level 1 (Subtle Inset):** `surface_container_low` (`#eff4ff`)
*   **Level 2 (High Definition):** `surface_container_highest` (`#d3e4fe`)

### The "Glass & Gradient" Rule
To add "soul" to the utility:
*   **Hero Elements:** Use a subtle linear gradient from `primary` (`#572da3`) to `primary_container` (`#6f48bd`) to create depth.
*   **Floating Overlays:** Use `surface_container_lowest` (`#ffffff`) at 80% opacity with a `24px` backdrop-blur to create a "frosted glass" effect for modals and hovering tooltips.

---

## 3. Typography Hierarchy
We employ a dual-font strategy: **Manrope** for authoritative, geometric headlines and **Inter** for high-legibility data density.

| Role | Font | Size | Weight | Intent |
| :--- | :--- | :--- | :--- | :--- |
| **Display-LG** | Manrope | 3.5rem | 700 | Large-scale impact branding |
| **Headline-MD**| Manrope | 1.75rem | 600 | Primary section headers |
| **Title-SM** | Inter | 1rem | 600 | Card titles and field labels |
| **Body-MD** | Inter | 0.875rem | 400 | Standard data & descriptions |
| **Label-SM** | Inter | 0.6875rem | 500 | Uppercase metadata/tags |

**Editorial Note:** Use `Headline-MD` with generous letter-spacing (-0.02em) to create a premium, "locked-in" typographic look.

---

## 4. Elevation & Depth: The Layering Principle
We move beyond shadows to convey hierarchy through **Tonal Stacking**.

*   **Natural Lift:** Place a `surface_container_lowest` (pure white) card on a `surface_container_low` background. The slight shift in brightness provides a natural, soft lift without the visual clutter of a shadow.
*   **Ambient Shadows:** When a card must "float" (e.g., a file upload zone), use a highly diffused shadow:
    *   `box-shadow: 0 20px 40px rgba(11, 28, 48, 0.06);` (Tinted with `on_surface` color).
*   **The Ghost Border Fallback:** If a container requires a boundary (e.g., for accessibility on white-on-white), use the `outline_variant` (`#c7c4d8`) at **15% opacity**. Never use a 100% opaque border.

---

## 5. Signature Components

### Buttons
*   **Primary:** Solid `primary` gradient with `0.5rem` (lg) rounding. For processing data.
*   **Secondary:** `secondary_container` (`#c3ecd7`) with `on_secondary_container` (`#476c5b`) text. Use for "Download" or "Export" actions.
*   **Ghost:** No background; `primary` text. Use for "Cancel" or "Clear" actions.

### Cards & Data Stats
Cards must never use dividers. 
*   **Stat Cards:** Use a thick (4px) vertical accent bar on the left or top of the card using `primary` or `tertiary` to categorize the data type (e.g., "Rows Kept" gets a mint green bar).
*   **Whitespace:** Cards should have a minimum internal padding of `2rem` to ensure the data has "room to breathe."

### Input Fields
*   **States:** Default state uses `surface_container_highest` background. Focus state transitions to a `ghost border` using `surface_tint`.
*   **The Upload Zone:** An oversized `surface_container_lowest` card with a dashed `outline_variant` at 40% opacity. Use a large icon to create a clear, tactile target.

### Data Preview Lists
*   Replace standard table lines with alternating row tints (`surface` vs `surface_container_low`) or simply generous vertical spacing (`1.5rem` between items).

---

## 6. Do's and Don'ts

### Do
*   **Do** use asymmetrical layouts (e.g., a small summary sidebar paired with a large data preview) to create visual interest.
*   **Do** use `secondary_fixed_dim` for non-essential chips to keep the UI quiet.
*   **Do** prioritize "Over-spacing." If a section feels crowded, double the padding.

### Don't
*   **Don't** use 1px black or dark grey borders. This instantly kills the "Premium SaaS" aesthetic.
*   **Don't** use standard "drop shadows" with high opacity. They should be felt, not seen.
*   **Don't** mix the font families. Manrope is for titles/branding; Inter is for utility/functional text.
*   **Don't** use "Alert Red" for everything. Use `error_container` (`#ffdad6`) for a softer, more integrated warning system.