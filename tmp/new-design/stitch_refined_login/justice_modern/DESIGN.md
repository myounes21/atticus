# Design System Strategy: The Digital Atelier

## 1. Overview & Creative North Star
**Creative North Star: The Informed Architect**
In the legal sector, clarity is authority. This design system moves away from the "industrial" look of traditional legal software and moves toward the "Atelier" aesthetic—an editorial-inspired workspace that combines the precision of high-end Swiss typography with the depth of soft, layered surfaces. 

By leveraging intentional asymmetry, high-contrast typography scales, and breathing room, we replace the clutter of a standard dashboard with a curated environment. We don't just display information; we frame it. The "template" look is broken through the use of non-linear layouts, where headers might overlap background containers and cards sit on variable-depth planes.

## 2. Colors
Our palette is a sophisticated interplay of deep teals and clinical whites, anchored by a systematic approach to neutral surfaces.

*   **The "No-Line" Rule:** Explicitly prohibit the use of 1px solid borders for sectioning or layout containment. Boundaries must be defined solely through background color shifts. For example, a `surface-container-low` section sitting on a `surface` background provides all the definition required.
*   **Surface Hierarchy & Nesting:** Treat the UI as a series of physical layers. 
    *   **Base:** `surface` (#f6faf9)
    *   **Nesting:** Place a `surface-container-lowest` (#ffffff) card inside a `surface-container` (#ebefee) zone to create a sense of focus without structural noise.
*   **The "Glass & Gradient" Rule:** For floating modals, navigation overlays, or search bars, use Glassmorphism. Utilize semi-transparent versions of `surface` with a `backdrop-blur` of 12px-20px. 
*   **Signature Textures:** Main CTAs and Hero sections should avoid flat color. Use a subtle linear gradient (135deg) transitioning from `primary` (#005f5a) to `primary_container` (#0d7a74) to add "soul" and a tactile, premium finish.

## 3. Typography
The system uses a dual-font strategy to balance character with functional legibility.

*   **Display & Headlines (Manrope):** We use Manrope for all `display` and `headline` levels. Its geometric but warm construction provides an authoritative, modern voice. Use `display-lg` (3.5rem) with tighter letter-spacing (-0.02em) to create high-impact editorial moments.
*   **Body & UI (Inter):** Inter is our workhorse. It is utilized for `title`, `body`, and `label` roles. Its high x-height ensures readability in complex legal documents.
*   **Hierarchy as Brand:** Use extreme scale differences. A `display-md` headline paired with a `label-sm` metadata tag creates an "editorial" look that guides the eye instantly to the most critical information.

## 4. Elevation & Depth
In this system, elevation is conveyed through **Tonal Layering** and ambient light, not heavy drop shadows.

*   **The Layering Principle:** Depth is achieved by stacking surface-container tiers. A `surface-container-highest` element feels naturally "closer" to the user than a `surface-dim` background.
*   **Ambient Shadows:** Traditional "drop shadows" are forbidden. If a floating effect is required (e.g., for a context menu), use a shadow with a blur radius of at least 32px and an opacity of 4-6%. The shadow color must be a tinted version of `on-surface` (#181c1c), never pure black.
*   **The "Ghost Border" Fallback:** If a border is required for accessibility, use the `outline_variant` (#bdc9c7) at 20% opacity. It should be felt, not seen.
*   **Glassmorphism Depth:** When using frosted glass effects, the `surface-tint` (#006a65) can be applied at 2% opacity to the glass layer to ensure the "teal" DNA is present even in the highlights.

## 5. Components

### Buttons & Inputs
*   **Buttons:** Primary buttons use the Signature Gradient. Secondary buttons should be "Ghost" style, using `surface-container-high` as a background with no border.
*   **Input Fields:** Use `surface-container-lowest` for the field background. Labels use `label-md` in `on-surface-variant`. On focus, transition the background to `surface` and apply a 1px "Ghost Border" using the `primary` token at 40%.

### Cards & Lists
*   **No-Divider Rule:** Forbid 1px horizontal lines between list items or case entries. Instead, use vertical white space (Spacing `4` or `5`) or alternating tonal shifts (e.g., `surface` to `surface-container-low`).
*   **Case Cards:** Use `roundedness-lg` (0.5rem). The "Active" state of a case should not be a border; it should be a subtle shift to `primary_fixed` with `on_primary_fixed_variant` text.

### Professional Additions
*   **The "Case Pulse" Chip:** A selection chip using `tertiary_container` with a soft-focus animation to indicate live document ingestion.
*   **Source Citation Tooltips:** For the legal context, tooltips should use the Glassmorphism rule with `title-sm` typography, ensuring the underlying evidence is still partially visible.

## 6. Do's and Don'ts

### Do:
*   **DO** use whitespace as a functional tool. If a section feels crowded, increase the spacing from `4` (1.4rem) to `6` (2rem) before considering a divider.
*   **DO** lean into asymmetry. A wider left margin for a headline can create a premium "magazine" feel.
*   **DO** use the `surface-container` tiers to group related items (e.g., grouping "Documents" inside a `surface-container-low` area).

### Don't:
*   **DON'T** use 100% black text. Always use `on-surface` (#181c1c) to maintain the soft, professional aesthetic.
*   **DON'T** use standard 4px border radii for everything. Mix `DEFAULT` (0.25rem) for small UI elements with `xl` (0.75rem) for major layout containers.
*   **DON'T** use high-contrast borders. If the background shift isn't enough, your layout is likely too complex; simplify the information architecture instead of adding lines.